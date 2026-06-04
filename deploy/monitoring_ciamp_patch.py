"""
Health endpoint for CIAMP (Customer Intelligence & Marketing Platform).
Appended to routes/monitoring.py.
"""

# ── CIAMP Health (Sprint 0) ────────────────────────────────────────────────────
# Added below existing health endpoints. Uses PostgreSQL via get_db().
# Separate from the existing /monitoring/health which uses SQLite.

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db


@router.get("/health/ciamp")
def health_ciamp(db: Session = Depends(get_db)):
    """
    Health check for the CIAMP stack (PostgreSQL-backed).
    Validates database connectivity against crm_customers.
    """
    from datetime import datetime, timezone

    try:
        result = db.execute(text("SELECT COUNT(*) FROM crm_customers")).scalar()
        return {
            "status": "ok",
            "service": "ciamp",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "crm_customers_count": result,
        }
    except Exception as exc:
        logger.error("CIAMP health check failed: %s", exc)
        return {
            "status": "error",
            "service": "ciamp",
            "database": "failed",
            "message": str(exc)[:200],
        }
