"""
Journeys API Routes

CRUD for multi-channel automated journey sequences.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services import journey_engine_v2 as je

logger = logging.getLogger(__name__)
router = APIRouter(tags=['journeys'])


# ── Auth ───────────────────────────────────────────────────────────────────────

def _require_admin(admin_secret: str = Query(..., alias='admin_secret')) -> None:
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail='Invalid admin_secret')


# ── Models ─────────────────────────────────────────────────────────────────────

class StepModel(BaseModel):
    name: str | None = None
    delay_days: int = 0
    delay_hours: int = 0
    channel: str = 'email'       # email | whatsapp | both
    template_id: str | None = None
    conditions: dict = {}
    max_retries: int = 1


class JourneyCreateRequest(BaseModel):
    name: str
    description: str | None = None
    trigger_event: str = 'order_delivered'
    trigger_delay_hours: int = 0
    target_list_id: str | None = None
    steps: list[StepModel] = []


class JourneyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_event: str | None = None
    trigger_delay_hours: int | None = None
    target_list_id: str | None = None
    status: str | None = None


class EnrollRequest(BaseModel):
    customer_email: str
    trigger_context: dict = {}


class ReplaceStepsRequest(BaseModel):
    steps: list[StepModel]


# ── Journey CRUD ───────────────────────────────────────────────────────────────

@router.get('/journeys')
def list_journeys(
    status: str | None = Query(None),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    return {'journeys': je.list_journeys(status=status)}


@router.post('/journeys')
def create_journey(
    body: JourneyCreateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    steps = [s.model_dump() for s in body.steps]
    return je.create_journey(
        body.name,
        description=body.description,
        trigger_event=body.trigger_event,
        trigger_delay_hours=body.trigger_delay_hours,
        target_list_id=body.target_list_id,
        steps=steps,
    )


@router.get('/journeys/{journey_id}')
def get_journey(
    journey_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    j = je.get_journey(journey_id)
    if not j:
        raise HTTPException(status_code=404, detail='Journey not found')
    return j


@router.put('/journeys/{journey_id}')
def update_journey(
    journey_id: str,
    body: JourneyUpdateRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_none=True)
    updated = je.update_journey(journey_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail='Journey not found')
    return updated


@router.post('/journeys/{journey_id}/activate')
def activate_journey(
    journey_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    updated = je.update_journey(journey_id, {'status': 'active'})
    if not updated:
        raise HTTPException(status_code=404, detail='Journey not found')
    return updated


@router.post('/journeys/{journey_id}/pause')
def pause_journey(
    journey_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    updated = je.update_journey(journey_id, {'status': 'paused'})
    if not updated:
        raise HTTPException(status_code=404, detail='Journey not found')
    return updated


# ── Steps ──────────────────────────────────────────────────────────────────────

@router.post('/journeys/{journey_id}/steps')
def add_step(
    journey_id: str,
    body: StepModel,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    j = je.get_journey(journey_id)
    if not j:
        raise HTTPException(status_code=404, detail='Journey not found')
    return je.add_step(journey_id, body.model_dump())


@router.put('/journeys/{journey_id}/steps')
def replace_steps(
    journey_id: str,
    body: ReplaceStepsRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    j = je.get_journey(journey_id)
    if not j:
        raise HTTPException(status_code=404, detail='Journey not found')
    steps = je.replace_steps(journey_id, [s.model_dump() for s in body.steps])
    return {'steps': steps, 'journey_id': journey_id}


@router.delete('/journeys/steps/{step_id}')
def delete_step(
    step_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    deleted = je.delete_step(step_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Step not found')
    return {'deleted': True, 'step_id': step_id}


# ── Enrollment & execution ─────────────────────────────────────────────────────

@router.post('/journeys/{journey_id}/enroll')
def enroll_customer(
    journey_id: str,
    body: EnrollRequest,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    execution = je.enroll_customer(
        journey_id,
        body.customer_email,
        trigger_context=body.trigger_context,
    )
    if execution is None:
        raise HTTPException(status_code=409, detail='Customer already enrolled or journey not active')
    return execution


@router.post('/journeys/run-due-steps')
def run_due_steps(
    dry_run: bool = Query(False),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """Manually trigger the step-send scheduler (normally runs automatically)."""
    results = je.run_due_steps(dry_run=dry_run)
    return {
        'processed': len(results),
        'sent': sum(1 for r in results if r.status == 'sent'),
        'skipped': sum(1 for r in results if r.status == 'skipped'),
        'failed': sum(1 for r in results if r.status == 'failed'),
        'dry_run': dry_run,
    }


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get('/journeys/{journey_id}/stats')
def journey_stats(
    journey_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    stats = je.get_journey_stats(journey_id)
    if not stats:
        raise HTTPException(status_code=404, detail='Journey not found')
    return stats


@router.get('/journeys/graph/summary')
def journey_graph_summary(
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    return {'items': je.get_journey_graph_summary()}
