"""
Pure Leven Journey Management API - Phase 3/4/5
Journey CRUD, enrollment, analytics, A/B variants, bulk enrollment
Publishes to Redis pub/sub for WebSocket real-time updates
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, desc, text
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import logging
import os
import random
import uuid
from dotenv import load_dotenv

logger = logging.getLogger("pureleven.journeys")

for env_path in ["/opt/pureleven/ai-engine/.env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

from sqlalchemy.orm import sessionmaker
DATABASE_URL = os.getenv("DATABASE_URL") or (
    "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "pureleven"),
        pw=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "pureleven-postgres"),
        port=os.getenv("POSTGRES_PORT", 5432),
        db=os.getenv("POSTGRES_DB", "pureleven"),
    )
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    from app.crm_models import (
        Journey, JourneyInstance, JourneyStep, Customer,
        JourneyAttribution, JourneyVariant, BulkEnrollmentJob
    )
except ImportError:
    Journey = JourneyInstance = JourneyStep = Customer = None
    JourneyAttribution = JourneyVariant = BulkEnrollmentJob = None

router = APIRouter(prefix="/api/crm", tags=["journeys"])


# ─── Redis Publisher ──────────────────────────────────────────────────────────

def _publish(channel: str, payload: dict):
    try:
        import redis as _redis
        r = _redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://pureleven-redis:6379/0"),
            decode_responses=True
        )
        r.publish(channel, json.dumps(payload))
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")


def _publish_metrics(event_type: str, journey_id: str, data: dict):
    _publish("pubsub:metrics", {
        "type": "journey_event",
        "event_type": event_type,
        "journey_id": journey_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    })


def _publish_step(journey_id: str, customer_email: str, status: str, step: int):
    _publish("pubsub:steps", {
        "type": "enrollment_update",
        "journey_id": journey_id,
        "customer_email": customer_email,
        "status": status,
        "current_step": step,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class JourneyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    entry_trigger: str
    exit_criteria: Optional[Dict[str, Any]] = None
    template_json: Optional[Dict[str, Any]] = None
    status: str = "DRAFT"
    n8n_workflow_id: Optional[str] = None


class JourneyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entry_trigger: Optional[str] = None
    exit_criteria: Optional[Dict[str, Any]] = None
    template_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    n8n_workflow_id: Optional[str] = None


class JourneyEnroll(BaseModel):
    customer_email: Optional[str] = None
    customer_id: Optional[str] = None
    variant_id: Optional[str] = None


class JourneyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    entry_trigger: Optional[str] = None
    exit_criteria: Optional[Dict[str, Any]] = None
    template_json: Optional[Dict[str, Any]] = None
    status: str
    n8n_workflow_id: Optional[str] = None
    created_at: str
    updated_at: str
    enroll_count: int
    completion_count: int

    class Config:
        from_attributes = True


class VariantCreate(BaseModel):
    variant_name: str
    traffic_split_pct: int = 50
    template_json: Optional[Dict[str, Any]] = None
    config_changes: Optional[Dict[str, Any]] = None


class VariantResponse(BaseModel):
    id: str
    journey_id: str
    variant_name: str
    traffic_split_pct: int
    status: str
    enrollments: int
    conversions: int
    revenue: float
    created_at: str

    class Config:
        from_attributes = True


class BulkEnrollResponse(BaseModel):
    job_id: str
    journey_id: str
    status: str
    total_rows: int
    message: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _journey_to_resp(journey, db: Session) -> JourneyResponse:
    enroll_count = db.query(func.count(JourneyInstance.id)).filter(
        JourneyInstance.journey_id == journey.id
    ).scalar() or 0
    completion_count = db.query(func.count(JourneyInstance.id)).filter(
        JourneyInstance.journey_id == journey.id,
        JourneyInstance.status == "COMPLETED"
    ).scalar() or 0
    return JourneyResponse(
        id=journey.id,
        name=journey.name,
        description=journey.description,
        entry_trigger=journey.entry_trigger,
        exit_criteria=journey.exit_criteria,
        template_json=journey.template_json or {},
        status=journey.status or "DRAFT",
        n8n_workflow_id=journey.n8n_workflow_id,
        created_at=journey.created_at.isoformat() if journey.created_at else "",
        updated_at=journey.updated_at.isoformat() if journey.updated_at else "",
        enroll_count=enroll_count,
        completion_count=completion_count,
    )


# ─── JOURNEY CRUD ─────────────────────────────────────────────────────────────

@router.get("/journeys", response_model=List[JourneyResponse])
def list_journeys(
    active_only: bool = Query(False),
    db: Session = Depends(_get_db)
):
    q = db.query(Journey)
    if active_only:
        q = q.filter(Journey.status == "ACTIVE")
    journeys = q.order_by(desc(Journey.created_at)).all()
    return [_journey_to_resp(j, db) for j in journeys]


@router.post("/journeys", response_model=JourneyResponse)
def create_journey(body: JourneyCreate, background_tasks: BackgroundTasks, db: Session = Depends(_get_db)):
    try:
        journey = Journey(
            id=str(uuid.uuid4()),
            name=body.name,
            description=body.description,
            entry_trigger=body.entry_trigger,
            exit_criteria=body.exit_criteria,
            template_json=body.template_json or {},
            status=body.status,
            n8n_workflow_id=body.n8n_workflow_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(journey)
        db.commit()
        db.refresh(journey)
        background_tasks.add_task(_publish_metrics, "created", journey.id, {"name": journey.name, "status": journey.status})
        logger.info(f"Created journey: {journey.name}")
        return _journey_to_resp(journey, db)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journeys/{journey_id}", response_model=JourneyResponse)
def get_journey(journey_id: str, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return _journey_to_resp(journey, db)


@router.put("/journeys/{journey_id}", response_model=JourneyResponse)
def update_journey(journey_id: str, body: JourneyUpdate, background_tasks: BackgroundTasks, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    for field, value in body.dict(exclude_none=True).items():
        setattr(journey, field, value)
    journey.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(journey)
    background_tasks.add_task(_publish_metrics, "updated", journey_id, {"name": journey.name, "status": journey.status})
    return _journey_to_resp(journey, db)


@router.delete("/journeys/{journey_id}")
def delete_journey(journey_id: str, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    db.delete(journey)
    db.commit()
    return {"status": "deleted", "journey_id": journey_id}


# ─── JOURNEY ANALYTICS ────────────────────────────────────────────────────────

@router.get("/journeys/{journey_id}/analytics")
def get_journey_analytics(journey_id: str, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    total = db.query(func.count(JourneyInstance.id)).filter(
        JourneyInstance.journey_id == journey_id
    ).scalar() or 0
    active = db.query(func.count(JourneyInstance.id)).filter(
        JourneyInstance.journey_id == journey_id, JourneyInstance.status == "ACTIVE"
    ).scalar() or 0
    completed = db.query(func.count(JourneyInstance.id)).filter(
        JourneyInstance.journey_id == journey_id, JourneyInstance.status == "COMPLETED"
    ).scalar() or 0

    conversion_rate = round(completed / total * 100, 2) if total > 0 else 0.0

    done = db.query(JourneyInstance).filter(
        JourneyInstance.journey_id == journey_id,
        JourneyInstance.status == "COMPLETED",
        JourneyInstance.completed_at.isnot(None),
    ).all()
    avg_days = None
    if done:
        total_secs = sum(
            (j.completed_at - j.started_at).total_seconds()
            for j in done if j.started_at and j.completed_at
        )
        avg_days = round(total_secs / len(done) / 86400, 1)

    step_counts = {}
    steps = (
        db.query(JourneyStep)
        .join(JourneyInstance, JourneyStep.journey_instance_id == JourneyInstance.id)
        .filter(JourneyInstance.journey_id == journey_id)
        .all()
    )
    for s in steps:
        k = s.step_type or "unknown"
        step_counts[k] = step_counts.get(k, 0) + 1

    total_revenue = db.query(func.sum(JourneyAttribution.attributed_revenue)).filter(
        JourneyAttribution.journey_id == journey_id
    ).scalar() or 0

    return {
        "journey_id": journey_id,
        "journey_name": journey.name,
        "status": journey.status,
        "total_enrolled": total,
        "active_instances": active,
        "completed_instances": completed,
        "conversion_rate": conversion_rate,
        "avg_completion_time_days": avg_days,
        "step_breakdown": step_counts,
        "attributed_revenue": round(float(total_revenue), 2),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── ENROLLMENT ───────────────────────────────────────────────────────────────

@router.post("/journeys/{journey_id}/enroll")
def enroll_customer(
    journey_id: str,
    body: JourneyEnroll,
    background_tasks: BackgroundTasks,
    db: Session = Depends(_get_db),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    customer = None
    if body.customer_email:
        customer = db.query(Customer).filter(Customer.email == body.customer_email).first()
        if not customer:
            customer = Customer(
                id=str(uuid.uuid4()),
                email=body.customer_email,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(customer)
            db.commit()
    elif body.customer_id:
        customer = db.query(Customer).filter(Customer.id == body.customer_id).first()

    if not customer:
        raise HTTPException(status_code=400, detail="Customer not found or customer_email required")

    existing = db.query(JourneyInstance).filter(
        JourneyInstance.journey_id == journey_id,
        JourneyInstance.customer_id == customer.id,
        JourneyInstance.status == "ACTIVE",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Customer already actively enrolled")

    variant_id = body.variant_id
    if not variant_id:
        active_variants = db.query(JourneyVariant).filter(
            JourneyVariant.journey_id == journey_id,
            JourneyVariant.status == "ACTIVE",
        ).all()
        if active_variants:
            total_split = sum(v.traffic_split_pct for v in active_variants)
            r = random.randint(1, max(total_split, 1))
            cumulative = 0
            for v in active_variants:
                cumulative += v.traffic_split_pct
                if r <= cumulative:
                    variant_id = v.id
                    v.enrollments = (v.enrollments or 0) + 1
                    break

    instance = JourneyInstance(
        id=str(uuid.uuid4()),
        journey_id=journey_id,
        customer_id=customer.id,
        email=customer.email,
        status="ACTIVE",
        current_step=0,
        started_at=datetime.utcnow(),
        result_data={"variant_id": variant_id} if variant_id else {},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    background_tasks.add_task(_publish_step, journey_id, customer.email or "", "ACTIVE", 0)
    background_tasks.add_task(_publish_metrics, "enrolled", journey_id, {
        "customer_email": customer.email,
        "instance_id": instance.id,
    })

    return {
        "instance_id": instance.id,
        "journey_id": journey_id,
        "customer_id": customer.id,
        "customer_email": customer.email,
        "status": "ACTIVE",
        "variant_id": variant_id,
    }


@router.get("/journeys/{journey_id}/enrollments")
def get_enrollments(
    journey_id: str,
    status: Optional[str] = None,
    limit: int = Query(100),
    db: Session = Depends(_get_db),
):
    q = db.query(JourneyInstance).filter(JourneyInstance.journey_id == journey_id)
    if status:
        q = q.filter(JourneyInstance.status == status)
    instances = q.order_by(desc(JourneyInstance.started_at)).limit(limit).all()
    return [
        {
            "instance_id": i.id,
            "customer_id": i.customer_id,
            "customer_email": i.email,
            "status": i.status,
            "current_step": i.current_step,
            "started_at": i.started_at.isoformat() if i.started_at else "",
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in instances
    ]


@router.put("/journey-instances/{instance_id}")
def update_instance(instance_id: str, body: dict, db: Session = Depends(_get_db)):
    instance = db.query(JourneyInstance).filter(JourneyInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    allowed = {"status", "current_step", "exit_reason", "result_data", "completed_at"}
    for k, v in body.items():
        if k in allowed:
            setattr(instance, k, v)
    instance.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "updated", "instance_id": instance_id}


@router.post("/journeys/{journey_id}/stop")
def stop_journey(journey_id: str, background_tasks: BackgroundTasks, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    active = db.query(JourneyInstance).filter(
        JourneyInstance.journey_id == journey_id,
        JourneyInstance.status == "ACTIVE",
    ).all()
    for inst in active:
        inst.status = "PAUSED"
    journey.status = "PAUSED"
    db.commit()
    background_tasks.add_task(_publish_metrics, "stopped", journey_id, {"paused_count": len(active)})
    return {"status": "success", "paused_instances": len(active)}


@router.post("/journeys/{journey_id}/clone", response_model=JourneyResponse)
def clone_journey(journey_id: str, background_tasks: BackgroundTasks, db: Session = Depends(_get_db)):
    source = db.query(Journey).filter(Journey.id == journey_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Journey not found")
    cloned = Journey(
        id=str(uuid.uuid4()),
        name=f"{source.name} (Copy)",
        description=source.description,
        entry_trigger=source.entry_trigger,
        exit_criteria=source.exit_criteria,
        template_json=source.template_json,
        status="DRAFT",
        n8n_workflow_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    background_tasks.add_task(_publish_metrics, "cloned", cloned.id, {"cloned_from": journey_id})
    return _journey_to_resp(cloned, db)


# ─── A/B TESTING (Phase 5) ────────────────────────────────────────────────────

@router.get("/journeys/{journey_id}/variants", response_model=List[VariantResponse])
def list_variants(journey_id: str, db: Session = Depends(_get_db)):
    variants = db.query(JourneyVariant).filter(JourneyVariant.journey_id == journey_id).all()
    return [
        VariantResponse(
            id=v.id,
            journey_id=v.journey_id,
            variant_name=v.variant_name,
            traffic_split_pct=v.traffic_split_pct,
            status=v.status,
            enrollments=v.enrollments or 0,
            conversions=v.conversions or 0,
            revenue=float(v.revenue or 0),
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in variants
    ]


@router.post("/journeys/{journey_id}/variants", response_model=VariantResponse)
def create_variant(journey_id: str, body: VariantCreate, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    variant = JourneyVariant(
        id=str(uuid.uuid4()),
        journey_id=journey_id,
        variant_name=body.variant_name,
        traffic_split_pct=body.traffic_split_pct,
        template_json=body.template_json or journey.template_json,
        config_changes=body.config_changes,
        status="DRAFT",
        enrollments=0,
        conversions=0,
        revenue=0.0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return VariantResponse(
        id=variant.id,
        journey_id=variant.journey_id,
        variant_name=variant.variant_name,
        traffic_split_pct=variant.traffic_split_pct,
        status=variant.status,
        enrollments=0,
        conversions=0,
        revenue=0.0,
        created_at=variant.created_at.isoformat(),
    )


@router.put("/journeys/{journey_id}/variants/{variant_id}")
def update_variant(journey_id: str, variant_id: str, body: dict, db: Session = Depends(_get_db)):
    variant = db.query(JourneyVariant).filter(
        JourneyVariant.id == variant_id,
        JourneyVariant.journey_id == journey_id,
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    allowed = {"variant_name", "traffic_split_pct", "template_json", "config_changes", "status"}
    for k, v in body.items():
        if k in allowed and hasattr(variant, k):
            setattr(variant, k, v)
    variant.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "updated", "variant_id": variant_id}


@router.post("/journeys/{journey_id}/variants/{variant_id}/promote")
def promote_variant(
    journey_id: str,
    variant_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(_get_db),
):
    """
    Promote a variant as the winner.
    Sets this variant status to WINNER; all other variants for the journey → PAUSED.
    Journey itself remains ACTIVE with 100% traffic going to the winning variant config.
    """
    winner = db.query(JourneyVariant).filter(
        JourneyVariant.id == variant_id,
        JourneyVariant.journey_id == journey_id,
    ).first()
    if not winner:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Pause all siblings
    db.query(JourneyVariant).filter(
        JourneyVariant.journey_id == journey_id,
        JourneyVariant.id != variant_id,
    ).update({"status": "PAUSED", "updated_at": datetime.utcnow()}, synchronize_session=False)

    # Mark winner
    winner.status = "WINNER"
    winner.traffic_split_pct = 100
    winner.updated_at = datetime.utcnow()
    db.commit()

    background_tasks.add_task(
        _publish_metrics,
        "variant_promoted",
        journey_id,
        {"variant_id": variant_id, "variant_name": winner.variant_name},
    )

    return {
        "status": "promoted",
        "variant_id": variant_id,
        "variant_name": winner.variant_name,
        "journey_id": journey_id,
    }


# ─── BULK ENROLLMENT (Phase 5) ────────────────────────────────────────────────

class BulkEnrollPayload(BaseModel):
    emails: List[str]


@router.post("/journeys/{journey_id}/enroll-bulk", response_model=BulkEnrollResponse)
def bulk_enroll(
    journey_id: str,
    body: BulkEnrollPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(_get_db),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    emails = [e.strip().lower() for e in body.emails if e.strip()]
    if not emails:
        raise HTTPException(status_code=400, detail="No valid emails provided")

    rows = [{"customer_email": e} for e in emails]

    job = BulkEnrollmentJob(
        id=str(uuid.uuid4()),
        journey_id=journey_id,
        status="PENDING",
        total_rows=len(rows),
        success_count=0,
        error_count=0,
        error_rows=[],
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_process_bulk_enrollment, job.id, journey_id, rows)

    return BulkEnrollResponse(
        job_id=job.id,
        journey_id=journey_id,
        status="PENDING",
        total_rows=len(rows),
        message=f"Processing {len(rows)} rows. Poll /api/crm/jobs/{job.id}/status",
    )


def _process_bulk_enrollment(job_id: str, journey_id: str, rows: list):
    db = SessionLocal()
    try:
        job = db.query(BulkEnrollmentJob).filter(BulkEnrollmentJob.id == job_id).first()
        if not job:
            return
        job.status = "RUNNING"
        db.commit()

        success, errors, error_rows = 0, 0, []
        for row in rows:
            email = (row.get("customer_email") or "").strip().lower()
            if not email:
                errors += 1
                error_rows.append({"email": "", "reason": "empty email"})
                continue
            try:
                customer = db.query(Customer).filter(Customer.email == email).first()
                if not customer:
                    customer = Customer(
                        id=str(uuid.uuid4()),
                        email=email,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(customer)
                    db.commit()
                existing = db.query(JourneyInstance).filter(
                    JourneyInstance.journey_id == journey_id,
                    JourneyInstance.customer_id == customer.id,
                    JourneyInstance.status == "ACTIVE",
                ).first()
                if existing:
                    continue
                inst = JourneyInstance(
                    id=str(uuid.uuid4()),
                    journey_id=journey_id,
                    customer_id=customer.id,
                    email=email,
                    status="ACTIVE",
                    current_step=0,
                    started_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(inst)
                db.commit()
                success += 1
            except Exception as row_err:
                errors += 1
                error_rows.append({"email": email, "reason": str(row_err)})

        job = db.query(BulkEnrollmentJob).filter(BulkEnrollmentJob.id == job_id).first()
        if job:
            job.status = "COMPLETED"
            job.success_count = success
            job.error_count = errors
            job.error_rows = error_rows[:100]
            job.completed_at = datetime.utcnow()
            db.commit()

        _publish_metrics("bulk_enrolled", journey_id, {
            "job_id": job_id,
            "success_count": success,
            "error_count": errors,
        })
    except Exception as e:
        logger.error(f"Bulk job {job_id} failed: {e}")
        try:
            j = db.query(BulkEnrollmentJob).filter(BulkEnrollmentJob.id == job_id).first()
            if j:
                j.status = "FAILED"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/jobs/{job_id}/status")
def get_job_status(job_id: str, db: Session = Depends(_get_db)):
    job = db.query(BulkEnrollmentJob).filter(BulkEnrollmentJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "journey_id": job.journey_id,
        "status": job.status,
        "total_rows": job.total_rows,
        "success_count": job.success_count,
        "error_count": job.error_count,
        "progress_pct": round((job.success_count + job.error_count) / max(job.total_rows, 1) * 100, 1),
        "error_rows": job.error_rows or [],
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


# ─── ATTRIBUTION (Phase 4) ────────────────────────────────────────────────────

@router.get("/journeys/{journey_id}/attribution")
def get_attribution(journey_id: str, db: Session = Depends(_get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    rows = db.query(JourneyAttribution).filter(JourneyAttribution.journey_id == journey_id).all()
    total_revenue = sum(r.attributed_revenue or 0 for r in rows)
    total_orders = len(rows)
    avg_order = round(total_revenue / total_orders, 2) if total_orders else 0
    total_enrolled = db.query(func.count(JourneyInstance.id)).filter(
        JourneyInstance.journey_id == journey_id
    ).scalar() or 0
    roas = round(total_revenue / max(1, total_enrolled) * 100, 2)

    return {
        "journey_id": journey_id,
        "journey_name": journey.name,
        "total_attributed_revenue": round(float(total_revenue), 2),
        "total_orders": total_orders,
        "avg_order_value": avg_order,
        "roas": roas,
        "attribution_model": "first_touch",
        "currency": "INR",
        "details": [
            {
                "order_id": r.order_id,
                "order_value": r.order_value,
                "attributed_revenue": r.attributed_revenue,
                "conversion_date": r.conversion_date.isoformat() if r.conversion_date else None,
            }
            for r in rows[:50]
        ],
    }


# ─── FULL SYSTEM HEALTH (Phase 4) ─────────────────────────────────────────────

@router.get("/health/full")
def full_health(db: Session = Depends(_get_db)):
    checks = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    try:
        import redis as _r
        r = _r.Redis.from_url(os.getenv("REDIS_URL", "redis://pureleven-redis:6379/0"))
        r.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)}

    try:
        checks["journeys"] = {"count": db.query(func.count(Journey.id)).scalar() or 0}
        checks["customers"] = {"count": db.query(func.count(Customer.id)).scalar() or 0}
        active_instances = (
            db.query(func.count(JourneyInstance.id))
            .filter(JourneyInstance.status == "ACTIVE")
            .scalar() or 0
        )
        checks["active_journey_instances"] = {"count": active_instances}
    except Exception as e:
        checks["counts"] = {"status": "error", "detail": str(e)}

    overall = "healthy" if all(
        v.get("status") in ("ok", None) for v in checks.values() if isinstance(v, dict) and "status" in v
    ) else "degraded"

    return {
        "status": overall,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
