"""Routing Error Detector - Flags mismatches between expected and actual routing

Detects issues like:
- Expected Catalog, but routed to Wabis
- Expected AI, but routed to Wabis
- Expected Human escalation, but routed to AI
"""

from typing import List, Dict, Any
from datetime import datetime, timezone

from app.storage import get_db_connection


class RoutingError:
    """Represents a potential routing error"""
    
    def __init__(
        self,
        phone: str,
        timestamp: str,
        message: str,
        detected_intent: str,
        expected_route: str,
        actual_route: str,
        reason: str,
        severity: str = "warning",  # "error", "warning", "info"
    ):
        self.phone = phone
        self.timestamp = timestamp
        self.message = message
        self.detected_intent = detected_intent
        self.expected_route = expected_route
        self.actual_route = actual_route
        self.reason = reason
        self.severity = severity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "timestamp": self.timestamp,
            "message": self.message,
            "detected_intent": self.detected_intent,
            "expected_route": self.expected_route,
            "actual_route": self.actual_route,
            "reason": self.reason,
            "severity": self.severity,
        }


# Routing expectations based on detected intent
INTENT_TO_EXPECTED_ROUTE = {
    "product_search": "catalog",
    "product_inquiry": "catalog",
    "price_inquiry": "catalog",
    "purchase_inquiry": "catalog",
    
    "order_tracking": "order_system",
    "order_status": "order_system",
    "shipment_tracking": "order_system",
    
    "complaint": "human",
    "escalation": "human",
    
    "greeting": "wabis",
    "language_selection": "wabis",
    
    "faq": "ai",
    "general_inquiry": "ai",
    "recipe": "ai",
    "health_benefit": "ai",
    
    "unknown": "clarification",
}


def detect_routing_errors(
    hours: int = 24,
) -> List[RoutingError]:
    """
    Scan recent audit logs for routing mismatches.
    
    Args:
        hours: How many hours back to scan
    
    Returns:
        List of detected routing errors
    """
    from datetime import timedelta
    
    conn = get_db_connection()
    errors = []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_iso = cutoff.isoformat()
    
    # Find all customer messages with detected intent and subsequent routing
    rows = conn.execute(
        """
        SELECT 
            phone, created_at, message, detected_intent, route_decision, reason
        FROM conversation_audit_log
        WHERE source = 'customer' 
          AND created_at >= ?
          AND detected_intent IS NOT NULL
        ORDER BY phone, created_at ASC
        """,
        (cutoff_iso,),
    ).fetchall()
    
    for row in rows:
        intent = row['detected_intent']
        actual_route = row['route_decision'] or 'unknown'
        expected_route = INTENT_TO_EXPECTED_ROUTE.get(intent, 'unknown')
        
        # Check for mismatch
        if expected_route != 'unknown' and actual_route != expected_route:
            # Determine severity
            severity = "warning"
            if actual_route == "wabis" and expected_route == "catalog":
                severity = "error"  # Product query stuck in Wabis
            elif actual_route == "ai" and expected_route == "human":
                severity = "error"  # Complaint routed to AI instead of human
            
            error = RoutingError(
                phone=row['phone'],
                timestamp=row['created_at'],
                message=row['message'],
                detected_intent=intent,
                expected_route=expected_route,
                actual_route=actual_route,
                reason=row['reason'] or "routing_mismatch",
                severity=severity,
            )
            
            errors.append(error)
    
    return errors


def get_routing_error_summary(hours: int = 24) -> Dict[str, Any]:
    """Get summary of routing errors"""
    errors = detect_routing_errors(hours)
    
    # Count by type
    type_counts = {}
    for error in errors:
        key = f"{error.expected_route}→{error.actual_route}"
        type_counts[key] = type_counts.get(key, 0) + 1
    
    # Count by severity
    severity_counts = {"error": 0, "warning": 0, "info": 0}
    for error in errors:
        severity_counts[error.severity] += 1
    
    # Get affected phones
    affected_phones = set(e.phone for e in errors)
    
    return {
        "total_errors": len(errors),
        "hours_lookback": hours,
        "by_type": type_counts,
        "by_severity": severity_counts,
        "affected_phones": sorted(list(affected_phones)),
        "critical_errors": [e.to_dict() for e in errors if e.severity == "error"][:20],
    }
