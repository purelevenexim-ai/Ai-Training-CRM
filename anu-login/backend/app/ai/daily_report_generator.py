"""Daily Report Generator - Creates conversation summaries

Runs nightly to generate:
- Total conversations by owner/intent
- Flow abandonment rates
- Top customer messages
- Routing errors
"""

import json
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path

from app.storage import get_db_connection


REPORTS_DIR = Path("/app/data/reports")


def ensure_reports_dir():
    """Create reports directory if it doesn't exist"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_report_path(date: datetime = None) -> Path:
    """Get path for report file for given date"""
    if date is None:
        date = datetime.now(timezone.utc)
    
    date_str = date.strftime("%Y_%m_%d")
    return REPORTS_DIR / f"conversation_review_{date_str}.md"


def generate_daily_report(date: datetime = None) -> str:
    """
    Generate daily conversation report.
    
    Scans conversation_audit_log for the given date (UTC).
    Counts conversations, routes, intents, flow abandonments, etc.
    
    Args:
        date: Date to report on (defaults to yesterday UTC)
    
    Returns:
        Markdown content
    """
    if date is None:
        # Default to yesterday (report runs at midnight)
        date = datetime.now(timezone.utc) - timedelta(days=1)
    
    date_start = datetime.combine(date.date(), datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
    date_end = (datetime.combine(date.date(), datetime.max.time()).replace(tzinfo=timezone.utc)).isoformat()
    
    conn = get_db_connection()
    
    # ── Counters ──────────────────────────────────────────
    owner_counts = defaultdict(int)
    intent_counts = defaultdict(int)
    route_counts = defaultdict(int)
    source_counts = defaultdict(int)
    
    flow_starts = defaultdict(int)
    flow_completions = defaultdict(int)
    flow_abandonments = defaultdict(int)
    
    top_messages = defaultdict(int)
    routing_errors = []
    
    unique_phones = set()
    
    # ── Scan audit log ────────────────────────────────────
    rows = conn.execute(
        """
        SELECT 
            phone, direction, source, message, owner_before, owner_after,
            active_flow, detected_intent, route_decision, reason, metadata_json
        FROM conversation_audit_log
        WHERE created_at >= ? AND created_at <= ?
        ORDER BY created_at ASC
        """,
        (date_start, date_end),
    ).fetchall()
    
    for row in rows:
        phone = row['phone']
        unique_phones.add(phone)
        
        if row['owner_after']:
            owner_counts[row['owner_after']] += 1
        
        if row['detected_intent']:
            intent_counts[row['detected_intent']] += 1
        
        if row['route_decision']:
            route_counts[row['route_decision']] += 1
        
        source_counts[row['source']] += 1
        
        # Track flow lifecycle
        if row['source'] == 'system' and row['route_decision'] == 'flow_transition':
            metadata = json.loads(row['metadata_json'] or '{}')
            if metadata.get('flow_after'):
                flow_starts[metadata['flow_after']] += 1
        
        # Count top customer messages
        if row['source'] == 'customer' and row['message']:
            msg_lower = row['message'].lower().strip()
            if len(msg_lower) > 2:  # Skip single words
                top_messages[msg_lower] += 1
        
        # Detect routing errors
        if row['source'] == 'system' and row['reason'] == 'routing_error':
            routing_errors.append({
                'phone': phone,
                'timestamp': row['created_at'],
                'message': row['message'],
                'reason': row['reason'],
                'metadata': json.loads(row['metadata_json'] or '{}'),
            })
    
    # ── Generate markdown ──────────────────────────────────
    date_str = date.strftime("%Y-%m-%d")
    md = f"""# Conversation Review - {date_str}

**Generated**: {datetime.now(timezone.utc).isoformat()}

---

## Summary

- **Total Unique Conversations**: {len(unique_phones)}
- **Total Events**: {len(rows)}
- **Date (UTC)**: {date_str}

---

## Conversations by Owner

| Owner | Count | % |
|-------|-------|---|
"""
    
    total_owned = sum(owner_counts.values())
    for owner in ['wabis', 'ai', 'catalog', 'human', 'campaign', 'system']:
        count = owner_counts.get(owner, 0)
        pct = round(100 * count / total_owned, 1) if total_owned > 0 else 0
        if count > 0:
            md += f"| {owner} | {count} | {pct}% |\n"
    
    md += "\n---\n\n## Detected Intents\n\n"
    
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1])[:15]:
        md += f"- `{intent}`: {count}\n"
    
    md += "\n---\n\n## Routing Decisions\n\n"
    
    for route, count in sorted(route_counts.items(), key=lambda x: -x[1])[:15]:
        md += f"- `{route}`: {count}\n"
    
    md += "\n---\n\n## Top Customer Messages\n\n"
    
    for msg, count in sorted(top_messages.items(), key=lambda x: -x[1])[:20]:
        if count >= 2:  # Only show messages that appear 2+ times
            md += f"- `{msg}`: {count}\n"
    
    # ── Flow Analysis ──────────────────────────────────────
    md += "\n---\n\n## Flow Analysis\n\n"
    
    md += "### Flow Starts\n\n"
    for flow, count in sorted(flow_starts.items(), key=lambda x: -x[1]):
        md += f"- `{flow}`: {count}\n"
    
    # ── Routing Errors ────────────────────────────────────
    if routing_errors:
        md += f"\n---\n\n## ⚠️ Routing Errors ({len(routing_errors)})\n\n"
        
        for error in routing_errors[:10]:  # Show first 10
            md += f"**{error['timestamp']}** | Phone: `{error['phone']}`\n\n"
            md += f"Reason: {error['reason']}\n\n"
            if error.get('message'):
                md += f"Message: {error['message']}\n\n"
            if error.get('metadata'):
                md += f"Details: {json.dumps(error['metadata'], indent=2)}\n\n"
    
    # ── Conversation Sources ───────────────────────────────
    md += "\n---\n\n## Message Sources\n\n"
    
    for source in ['customer', 'ai', 'wabis', 'system', 'human']:
        count = source_counts.get(source, 0)
        if count > 0:
            md += f"- `{source}`: {count}\n"
    
    md += "\n---\n\n"
    md += f"*Report auto-generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
    
    return md


def save_daily_report(date: datetime = None) -> Path:
    """Generate and save daily report"""
    ensure_reports_dir()
    
    if date is None:
        date = datetime.now(timezone.utc) - timedelta(days=1)
    
    report_path = get_report_path(date)
    report_content = generate_daily_report(date)
    
    report_path.write_text(report_content, encoding='utf-8')
    
    return report_path


def get_latest_report() -> str:
    """Get content of most recent report"""
    ensure_reports_dir()
    
    # Find most recent report
    reports = sorted(REPORTS_DIR.glob("conversation_review_*.md"), reverse=True)
    
    if not reports:
        return "No reports generated yet."
    
    return reports[0].read_text(encoding='utf-8')


if __name__ == "__main__":
    # Generate report for yesterday
    report_path = save_daily_report()
    print(f"✅ Report saved: {report_path}")
    print("\n" + "="*80 + "\n")
    print(report_path.read_text())
