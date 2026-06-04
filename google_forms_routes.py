"""
Google Forms API Routes
Form submissions, webhooks, and analytics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr
from database import SessionLocal
from google_forms_integration import (
    GoogleFormSubmissionProcessor,
    FormSubmissionStatus,
    DuplicateMatchType
)

router = APIRouter(prefix="/api/crm", tags=["google_forms"])


# ============ Pydantic Models ============

class FormFieldMapping(BaseModel):
    """Map form fields to customer fields"""
    email: Optional[str] = "Email Address"
    phone: Optional[str] = "Phone Number"
    first_name: Optional[str] = "First Name"
    last_name: Optional[str] = "Last Name"
    company: Optional[str] = "Company Name"


class FormSubmissionData(BaseModel):
    """Raw form submission data"""
    # Dynamic fields - form responses
    # Example: {"Email Address": "john@example.com", "Phone Number": "9876543210"}
    pass


class FormWebhookPayload(BaseModel):
    """Google Forms webhook payload"""
    form_id: str
    submission_id: str
    timestamp: str
    response_data: Dict[str, str]  # Form field -> value


class GoogleFormTemplate(BaseModel):
    """Save form configuration"""
    form_id: str
    form_name: str
    form_url: Optional[str] = None
    field_mapping: FormFieldMapping
    is_active: bool = True


class GoogleFormSubmissionResponse(BaseModel):
    """Submission processing result"""
    status: str
    customer_id: Optional[str]
    submission_id: str
    match_type: str
    message: str


# ============ Form Submission Management (6 endpoints) ============

@router.post("/forms/webhook")
def receive_form_submission(
    payload: FormWebhookPayload,
    db: Session = Depends(SessionLocal)
):
    """
    Receive submission from Google Forms webhook
    
    Google Forms sends via webhook when new response submitted
    
    Returns: {
        'status': 'lead_created' | 'duplicate' | 'error',
        'customer_id': str,
        'submission_id': str
    }
    """
    
    processor = GoogleFormSubmissionProcessor(db)
    
    # Process submission
    result = processor.process_submission(
        form_id=payload.form_id,
        submission_data=payload.response_data
    )
    
    return result


@router.post("/forms/submissions")
def create_submission_manual(
    form_id: str,
    submission_data: Dict,
    db: Session = Depends(SessionLocal)
):
    """
    Manually submit form data (for testing or manual entry)
    
    Returns: Submission processing result
    """
    
    processor = GoogleFormSubmissionProcessor(db)
    
    result = processor.process_submission(
        form_id=form_id,
        submission_data=submission_data
    )
    
    return result


@router.get("/forms/submissions")
def list_submissions(
    form_id: Optional[str] = None,
    status: Optional[str] = None,
    match_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(SessionLocal)
):
    """
    List form submissions (with filtering)
    
    Filters:
    - form_id: Specific form
    - status: received, processing, duplicate, lead_created, error
    - match_type: exact_email, exact_phone, no_match, etc
    """
    
    from crm_models import GoogleFormSubmission
    
    query = db.query(GoogleFormSubmission)
    
    if form_id:
        query = query.filter(GoogleFormSubmission.form_id == form_id)
    
    if status:
        query = query.filter(GoogleFormSubmission.status == status)
    
    if match_type:
        query = query.filter(GoogleFormSubmission.match_type == match_type)
    
    total = query.count()
    
    submissions = query.order_by(
        GoogleFormSubmission.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'skip': skip,
        'limit': limit,
        'submissions': [
            {
                'id': s.id,
                'form_id': s.form_id,
                'customer_id': s.customer_id,
                'status': s.status,
                'match_type': s.match_type,
                'created_at': s.created_at
            }
            for s in submissions
        ]
    }


@router.get("/forms/submissions/{submission_id}")
def get_submission_detail(
    submission_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get detailed submission information"""
    
    from crm_models import GoogleFormSubmission
    
    submission = db.query(GoogleFormSubmission).filter(
        GoogleFormSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {
        'id': submission.id,
        'form_id': submission.form_id,
        'customer_id': submission.customer_id,
        'status': submission.status,
        'match_type': submission.match_type,
        'submission_data': submission.submission_data,
        'extracted_fields': submission.extracted_fields,
        'error_message': submission.error_message,
        'created_at': submission.created_at
    }


@router.post("/forms/submissions/{submission_id}/retry")
def retry_submission(
    submission_id: str,
    db: Session = Depends(SessionLocal)
):
    """
    Retry processing failed submission
    
    Used when submission had transient error
    """
    
    from crm_models import GoogleFormSubmission
    
    submission = db.query(GoogleFormSubmission).filter(
        GoogleFormSubmission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != FormSubmissionStatus.ERROR.value:
        raise HTTPException(
            status_code=400,
            detail="Only error submissions can be retried"
        )
    
    # Reprocess
    processor = GoogleFormSubmissionProcessor(db)
    
    result = processor.process_submission(
        form_id=submission.form_id,
        submission_data=submission.submission_data
    )
    
    return result


# ============ Form Template Management (5 endpoints) ============

@router.post("/forms/templates")
def save_form_template(
    data: GoogleFormTemplate,
    db: Session = Depends(SessionLocal)
):
    """
    Save Google Form configuration/mapping
    
    Stores field mapping for form processing
    """
    
    from crm_models import GoogleFormTemplate
    import uuid
    
    # Check if exists
    existing = db.query(GoogleFormTemplate).filter(
        GoogleFormTemplate.form_id == data.form_id
    ).first()
    
    if existing:
        # Update
        existing.form_name = data.form_name
        existing.form_url = data.form_url
        existing.field_mapping = data.field_mapping.dict()
        existing.is_active = data.is_active
        existing.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'status': 'updated',
            'form_id': data.form_id,
            'template_id': existing.id
        }
    else:
        # Create
        template = GoogleFormTemplate(
            id=str(uuid.uuid4()),
            form_id=data.form_id,
            form_name=data.form_name,
            form_url=data.form_url,
            field_mapping=data.field_mapping.dict(),
            is_active=data.is_active,
            created_at=datetime.utcnow()
        )
        
        db.add(template)
        db.commit()
        
        return {
            'status': 'created',
            'form_id': data.form_id,
            'template_id': template.id
        }


@router.get("/forms/templates")
def list_form_templates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(SessionLocal)
):
    """List saved form templates"""
    
    from crm_models import GoogleFormTemplate
    
    total = db.query(GoogleFormTemplate).count()
    
    templates = db.query(GoogleFormTemplate).order_by(
        GoogleFormTemplate.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'templates': [
            {
                'id': t.id,
                'form_id': t.form_id,
                'form_name': t.form_name,
                'is_active': t.is_active,
                'created_at': t.created_at
            }
            for t in templates
        ]
    }


@router.get("/forms/templates/{form_id}")
def get_form_template(
    form_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get template for specific form"""
    
    from crm_models import GoogleFormTemplate
    
    template = db.query(GoogleFormTemplate).filter(
        GoogleFormTemplate.form_id == form_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        'id': template.id,
        'form_id': template.form_id,
        'form_name': template.form_name,
        'form_url': template.form_url,
        'field_mapping': template.field_mapping,
        'is_active': template.is_active
    }


@router.put("/forms/templates/{form_id}")
def update_form_template(
    form_id: str,
    data: GoogleFormTemplate,
    db: Session = Depends(SessionLocal)
):
    """Update form template"""
    
    from crm_models import GoogleFormTemplate
    
    template = db.query(GoogleFormTemplate).filter(
        GoogleFormTemplate.form_id == form_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.form_name = data.form_name
    template.form_url = data.form_url
    template.field_mapping = data.field_mapping.dict()
    template.is_active = data.is_active
    template.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {'status': 'updated', 'form_id': form_id}


@router.delete("/forms/templates/{form_id}")
def delete_form_template(
    form_id: str,
    db: Session = Depends(SessionLocal)
):
    """Delete form template"""
    
    from crm_models import GoogleFormTemplate
    
    template = db.query(GoogleFormTemplate).filter(
        GoogleFormTemplate.form_id == form_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {'status': 'deleted', 'form_id': form_id}


# ============ Analytics (4 endpoints) ============

@router.get("/forms/analytics/{form_id}")
def get_form_analytics(
    form_id: str,
    db: Session = Depends(SessionLocal)
):
    """
    Form submission analytics
    
    Returns:
    - Total submissions
    - Status breakdown (new leads, duplicates, errors)
    - Match type distribution
    - Lead creation rate
    """
    
    processor = GoogleFormSubmissionProcessor(db)
    analytics = processor.get_submission_analytics(form_id)
    
    return analytics


@router.get("/forms/analytics/all")
def get_all_forms_analytics(
    db: Session = Depends(SessionLocal)
):
    """Get analytics for all forms"""
    
    from crm_models import GoogleFormTemplate
    
    templates = db.query(GoogleFormTemplate).all()
    
    processor = GoogleFormSubmissionProcessor(db)
    
    all_analytics = {}
    for template in templates:
        analytics = processor.get_submission_analytics(template.form_id)
        all_analytics[template.form_id] = {
            'form_name': template.form_name,
            'analytics': analytics
        }
    
    return all_analytics


@router.get("/forms/analytics/{form_id}/by-date")
def get_form_analytics_by_date(
    form_id: str,
    days: int = 30,
    db: Session = Depends(SessionLocal)
):
    """
    Daily submission volume for form
    
    Useful for tracking form performance over time
    """
    
    from crm_models import GoogleFormSubmission
    from sqlalchemy import func, cast
    import sqlalchemy
    
    # Get submissions from last N days
    start_date = datetime.utcnow() - timedelta(days=days)
    
    submissions = db.query(
        cast(GoogleFormSubmission.created_at, sqlalchemy.Date).label('date'),
        func.count(GoogleFormSubmission.id).label('count'),
        GoogleFormSubmission.status
    ).filter(
        GoogleFormSubmission.form_id == form_id,
        GoogleFormSubmission.created_at >= start_date
    ).group_by(
        cast(GoogleFormSubmission.created_at, sqlalchemy.Date),
        GoogleFormSubmission.status
    ).order_by(
        cast(GoogleFormSubmission.created_at, sqlalchemy.Date).desc()
    ).all()
    
    # Format results
    daily_data = {}
    for date, count, status in submissions:
        date_str = str(date)
        if date_str not in daily_data:
            daily_data[date_str] = {}
        daily_data[date_str][status] = count
    
    return {
        'form_id': form_id,
        'period_days': days,
        'daily_data': daily_data
    }


# ============ Health Check ============

@router.get("/forms/health")
def forms_health(
    db: Session = Depends(SessionLocal)
):
    """Health check for forms integration"""
    
    try:
        from crm_models import GoogleFormSubmission
        
        total_submissions = db.query(GoogleFormSubmission).count()
        
        return {
            "status": "ok",
            "service": "google_forms",
            "total_submissions": total_submissions
        }
    
    except Exception as e:
        return {
            "status": "error",
            "service": "google_forms",
            "message": str(e)
        }
