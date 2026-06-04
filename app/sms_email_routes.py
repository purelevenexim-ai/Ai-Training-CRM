"""
SMS & Email Notifications Routes
14 REST API endpoints for SMS, email campaigns, templates
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.sms_email_integration import (
    TwilioSMSClient, PlunkEmailClient, SMSCampaignManager, EmailTemplateManager,
    EmailCampaignManager, NotificationAnalytics, MessageStatus, CampaignStatus
)
from app.crm_models import (
    SMSMessage, SMSCampaign, EmailTemplate, EmailMessage, EmailCampaign, Customer
)
import os

router = APIRouter(prefix="/api/crm/notifications", tags=["SMS & Email"])

# Initialize clients from environment
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "+1234567890")
PLUNK_API_KEY = os.getenv("PLUNK_API_KEY", "")

sms_client = TwilioSMSClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)
email_client = PlunkEmailClient(PLUNK_API_KEY)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SendSMSRequest(BaseModel):
    """Send SMS request"""
    customer_id: str
    message_text: str


class SendEmailRequest(BaseModel):
    """Send email request"""
    customer_id: str
    subject: str
    html_content: str


class SMSCampaignCreateRequest(BaseModel):
    """Create SMS campaign"""
    campaign_name: str
    message_text: str
    audience_filter: Dict[str, Any]


class SMSCampaignResponse(BaseModel):
    """SMS campaign response"""
    campaign_id: str
    campaign_name: str
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
    created_at: str


class EmailTemplateCreateRequest(BaseModel):
    """Create email template"""
    template_name: str
    subject: str
    html_content: str


class EmailTemplateResponse(BaseModel):
    """Email template response"""
    template_id: str
    template_name: str
    subject: str
    html_content: str
    is_active: bool
    created_at: str


class EmailCampaignCreateRequest(BaseModel):
    """Create email campaign"""
    campaign_name: str
    template_id: str
    audience_filter: Dict[str, Any]


class EmailCampaignResponse(BaseModel):
    """Email campaign response"""
    campaign_id: str
    campaign_name: str
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
    created_at: str


class SMSMessageResponse(BaseModel):
    """SMS message response"""
    message_id: str
    customer_id: str
    phone_number: str
    status: str
    created_at: str


class EmailMessageResponse(BaseModel):
    """Email message response"""
    message_id: str
    customer_id: str
    email_address: str
    status: str
    created_at: str


# ============================================================================
# SMS ENDPOINTS
# ============================================================================

@router.post("/sms/send", response_model=SMSMessageResponse)
async def send_sms(
    request: SendSMSRequest,
    db: Session = Depends(get_db)
):
    """Send SMS to single customer"""
    customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
    if not customer or not customer.phone:
        raise HTTPException(status_code=400, detail="Customer or phone not found")
    
    result = sms_client.send_sms(customer.phone, request.message_text)
    
    # Record message
    message = SMSMessage(
        id=result.get("sid") or str(__import__("uuid").uuid4()),
        customer_id=request.customer_id,
        phone_number=customer.phone,
        message_text=request.message_text,
        status=result.get("status"),
        twilio_sid=result.get("sid"),
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    
    return SMSMessageResponse(
        message_id=message.id,
        customer_id=message.customer_id,
        phone_number=message.phone_number,
        status=message.status,
        created_at=message.created_at.isoformat()
    )


@router.post("/sms/campaign", response_model=SMSCampaignResponse)
async def create_sms_campaign(
    request: SMSCampaignCreateRequest,
    db: Session = Depends(get_db)
):
    """Create SMS campaign"""
    campaign = SMSCampaignManager.create_campaign(
        db=db,
        campaign_name=request.campaign_name,
        message_text=request.message_text,
        audience_filter=request.audience_filter,
        created_by="api_user"
    )
    
    return SMSCampaignResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.campaign_name,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        created_at=campaign.created_at.isoformat()
    )


@router.post("/sms/campaign/{campaign_id}/execute")
async def execute_sms_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute SMS campaign in background"""
    campaign = db.query(SMSCampaign).filter(SMSCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    webhook_url = os.getenv("SMS_WEBHOOK_URL", "")
    
    background_tasks.add_task(
        SMSCampaignManager.execute_sms_campaign,
        db=db,
        campaign_id=campaign_id,
        twilio_client=sms_client,
        webhook_url=webhook_url
    )
    
    return {
        "campaign_id": campaign_id,
        "status": "executing",
        "message": "Campaign execution started in background"
    }


@router.get("/sms/campaign/{campaign_id}", response_model=SMSCampaignResponse)
async def get_sms_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Get SMS campaign details"""
    campaign = db.query(SMSCampaign).filter(SMSCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return SMSCampaignResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.campaign_name,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        created_at=campaign.created_at.isoformat()
    )


@router.get("/sms/messages", response_model=List[SMSMessageResponse])
async def list_sms_messages(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List SMS messages"""
    query = db.query(SMSMessage)
    
    if status:
        query = query.filter(SMSMessage.status == status)
    
    messages = query.order_by(SMSMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        SMSMessageResponse(
            message_id=m.id,
            customer_id=m.customer_id,
            phone_number=m.phone_number,
            status=m.status,
            created_at=m.created_at.isoformat()
        )
        for m in messages
    ]


@router.post("/sms/webhook/delivery")
async def sms_delivery_webhook(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Twilio delivery status webhook"""
    sid = request.get("MessageSid")
    status = request.get("MessageStatus")
    
    message = db.query(SMSMessage).filter(SMSMessage.twilio_sid == sid).first()
    if message:
        message.status = status
        message.updated_at = datetime.utcnow()
        db.commit()
    
    return {"received": True}


# ============================================================================
# EMAIL ENDPOINTS
# ============================================================================

@router.post("/email/send", response_model=EmailMessageResponse)
async def send_email(
    request: SendEmailRequest,
    db: Session = Depends(get_db)
):
    """Send email to single customer"""
    customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
    if not customer or not customer.email:
        raise HTTPException(status_code=400, detail="Customer or email not found")
    
    result = email_client.send_email(
        to_email=customer.email,
        subject=request.subject,
        html_content=request.html_content
    )
    
    # Record message
    message = EmailMessage(
        id=result.get("message_id") or str(__import__("uuid").uuid4()),
        customer_id=request.customer_id,
        email_address=customer.email,
        subject=request.subject,
        status=result.get("status"),
        plunk_message_id=result.get("message_id"),
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    
    return EmailMessageResponse(
        message_id=message.id,
        customer_id=message.customer_id,
        email_address=message.email_address,
        status=message.status,
        created_at=message.created_at.isoformat()
    )


@router.post("/email/template", response_model=EmailTemplateResponse)
async def create_email_template(
    request: EmailTemplateCreateRequest,
    db: Session = Depends(get_db)
):
    """Create email template"""
    template = EmailTemplateManager.create_template(
        db=db,
        template_name=request.template_name,
        subject=request.subject,
        html_content=request.html_content,
        created_by="api_user"
    )
    
    return EmailTemplateResponse(
        template_id=template.id,
        template_name=template.template_name,
        subject=template.subject,
        html_content=template.html_content,
        is_active=template.is_active,
        created_at=template.created_at.isoformat()
    )


@router.get("/email/templates", response_model=List[EmailTemplateResponse])
async def list_email_templates(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List email templates"""
    templates = db.query(EmailTemplate).order_by(
        EmailTemplate.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        EmailTemplateResponse(
            template_id=t.id,
            template_name=t.template_name,
            subject=t.subject,
            html_content=t.html_content,
            is_active=t.is_active,
            created_at=t.created_at.isoformat()
        )
        for t in templates
    ]


@router.get("/email/template/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(template_id: str, db: Session = Depends(get_db)):
    """Get email template details"""
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return EmailTemplateResponse(
        template_id=template.id,
        template_name=template.template_name,
        subject=template.subject,
        html_content=template.html_content,
        is_active=template.is_active,
        created_at=template.created_at.isoformat()
    )


@router.post("/email/campaign", response_model=EmailCampaignResponse)
async def create_email_campaign(
    request: EmailCampaignCreateRequest,
    db: Session = Depends(get_db)
):
    """Create email campaign"""
    campaign = EmailCampaignManager.create_campaign(
        db=db,
        campaign_name=request.campaign_name,
        template_id=request.template_id,
        audience_filter=request.audience_filter,
        created_by="api_user"
    )
    
    return EmailCampaignResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.campaign_name,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        created_at=campaign.created_at.isoformat()
    )


@router.post("/email/campaign/{campaign_id}/execute")
async def execute_email_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute email campaign in background"""
    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    background_tasks.add_task(
        EmailCampaignManager.execute_email_campaign,
        db=db,
        campaign_id=campaign_id,
        plunk_client=email_client,
        template_manager=EmailTemplateManager
    )
    
    return {
        "campaign_id": campaign_id,
        "status": "executing",
        "message": "Campaign execution started in background"
    }


@router.get("/email/campaign/{campaign_id}", response_model=EmailCampaignResponse)
async def get_email_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Get email campaign details"""
    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return EmailCampaignResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.campaign_name,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        created_at=campaign.created_at.isoformat()
    )


@router.get("/email/messages", response_model=List[EmailMessageResponse])
async def list_email_messages(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List email messages"""
    query = db.query(EmailMessage)
    
    if status:
        query = query.filter(EmailMessage.status == status)
    
    messages = query.order_by(EmailMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        EmailMessageResponse(
            message_id=m.id,
            customer_id=m.customer_id,
            email_address=m.email_address,
            status=m.status,
            created_at=m.created_at.isoformat()
        )
        for m in messages
    ]


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/sms/analytics")
async def sms_analytics(days: int = 30, db: Session = Depends(get_db)):
    """Get SMS analytics"""
    analytics = NotificationAnalytics.get_sms_analytics(db, days)
    return analytics


@router.get("/email/analytics")
async def email_analytics(days: int = 30, db: Session = Depends(get_db)):
    """Get email analytics"""
    analytics = NotificationAnalytics.get_email_analytics(db, days)
    return analytics


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def notifications_health():
    """Health check for notifications service"""
    return {
        "status": "healthy",
        "service": "SMS & Email Notifications",
        "timestamp": datetime.utcnow().isoformat(),
        "sms_configured": bool(TWILIO_ACCOUNT_SID),
        "email_configured": bool(PLUNK_API_KEY)
    }
