"""
SMS & Email Notifications Integration
Twilio SMS + Plunk Email for customer communications
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
import requests
from sqlalchemy.orm import Session
from app.crm_models import Customer, SMSMessage, SMSCampaign, EmailTemplate, EmailMessage, EmailCampaign


class MessageStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class CampaignStatus(str, Enum):
    """Campaign status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TwilioSMSClient:
    """Twilio SMS client for SMS delivery"""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """
        Initialize Twilio client
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number (e.g., +1234567890)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        self.webhook_url = None
    
    def send_sms(
        self,
        to_number: str,
        message_text: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS message via Twilio
        Returns: {status_sid, phone_number, body, error}
        """
        try:
            # Normalize phone to E.164
            to_number = self._normalize_phone(to_number)
            
            data = {
                "From": self.from_number,
                "To": to_number,
                "Body": message_text
            }
            
            if webhook_url:
                data["StatusCallback"] = webhook_url
            
            response = requests.post(
                self.api_url,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": "sent",
                    "sid": result.get("sid"),
                    "phone_number": to_number,
                    "body": message_text
                }
            else:
                return {
                    "status": "failed",
                    "phone_number": to_number,
                    "error": response.json().get("message", "Unknown error")
                }
        
        except Exception as e:
            return {
                "status": "failed",
                "phone_number": to_number,
                "error": str(e)
            }
    
    def send_bulk_sms(
        self,
        recipients: List[Dict[str, str]],  # [{phone, message}, ...]
        webhook_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Send SMS to multiple recipients
        Returns: List of results
        """
        results = []
        for recipient in recipients:
            result = self.send_sms(
                to_number=recipient.get("phone"),
                message_text=recipient.get("message"),
                webhook_url=webhook_url
            )
            results.append(result)
        
        return results
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone to E.164 format"""
        # Remove spaces and dashes
        phone = phone.replace(" ", "").replace("-", "")
        
        # If 10 digits (India), prepend +91
        if len(phone) == 10 and phone.isdigit():
            return f"+91{phone}"
        
        # If doesn't start with +, add it
        if not phone.startswith("+"):
            return f"+{phone}"
        
        return phone


class PlunkEmailClient:
    """Plunk email client for email delivery"""
    
    def __init__(self, api_key: str):
        """
        Initialize Plunk client
        Args:
            api_key: Plunk API key
        """
        self.api_key = api_key
        self.api_url = "https://api.useplunk.com/v1/send"
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_name: str = "Pureleven",
        reply_to: Optional[str] = None,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send email via Plunk
        Returns: {status, message_id, error}
        """
        try:
            payload = {
                "to": to_email,
                "subject": subject,
                "from": from_name,
                "html": html_content
            }
            
            if reply_to:
                payload["reply_to"] = reply_to
            
            if template_id:
                payload["template_id"] = template_id
            
            if template_data:
                payload["variables"] = template_data
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": "sent",
                    "message_id": result.get("id"),
                    "email": to_email
                }
            else:
                return {
                    "status": "failed",
                    "email": to_email,
                    "error": response.json().get("message", "Unknown error")
                }
        
        except Exception as e:
            return {
                "status": "failed",
                "email": to_email,
                "error": str(e)
            }
    
    def send_bulk_email(
        self,
        recipients: List[Dict[str, Any]],  # [{email, subject, html}, ...]
        from_name: str = "Pureleven"
    ) -> List[Dict[str, Any]]:
        """Send email to multiple recipients"""
        results = []
        for recipient in recipients:
            result = self.send_email(
                to_email=recipient.get("email"),
                subject=recipient.get("subject"),
                html_content=recipient.get("html"),
                from_name=from_name
            )
            results.append(result)
        
        return results


class SMSCampaignManager:
    """Manages SMS campaigns"""
    
    @staticmethod
    def create_campaign(
        db: Session,
        campaign_name: str,
        message_text: str,
        audience_filter: Dict[str, Any],
        created_by: str
    ) -> SMSCampaign:
        """Create new SMS campaign"""
        campaign = SMSCampaign(
            id=str(uuid.uuid4()),
            campaign_name=campaign_name,
            message_text=message_text,
            audience_filter=audience_filter,
            status=CampaignStatus.DRAFT.value,
            total_recipients=0,
            sent_count=0,
            failed_count=0,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(campaign)
        db.commit()
        return campaign
    
    @staticmethod
    def get_campaign_recipients(
        db: Session,
        audience_filter: Dict[str, Any]
    ) -> List[Customer]:
        """Get customers matching campaign filter"""
        query = db.query(Customer).filter(Customer.deleted_at.is_(None))
        
        # Apply filters
        if audience_filter.get("source"):
            query = query.filter(Customer.source == audience_filter["source"])
        
        if audience_filter.get("min_propensity_score"):
            query = query.filter(
                Customer.propensity_score >= audience_filter["min_propensity_score"]
            )
        
        if audience_filter.get("has_purchased"):
            query = query.filter(Customer.has_purchased == True)
        
        return query.all()
    
    @staticmethod
    def execute_sms_campaign(
        db: Session,
        campaign_id: str,
        twilio_client: TwilioSMSClient,
        webhook_url: str
    ) -> Dict[str, Any]:
        """Execute SMS campaign"""
        campaign = db.query(SMSCampaign).filter(SMSCampaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Get recipients
        recipients = SMSCampaignManager.get_campaign_recipients(db, campaign.audience_filter)
        
        campaign.status = CampaignStatus.SENDING.value
        campaign.total_recipients = len(recipients)
        db.commit()
        
        sent_count = 0
        failed_count = 0
        
        for customer in recipients:
            if not customer.phone:
                failed_count += 1
                continue
            
            result = twilio_client.send_sms(
                to_number=customer.phone,
                message_text=campaign.message_text,
                webhook_url=webhook_url
            )
            
            # Record message
            message = SMSMessage(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                customer_id=customer.id,
                phone_number=customer.phone,
                message_text=campaign.message_text,
                status=result.get("status"),
                twilio_sid=result.get("sid"),
                created_at=datetime.utcnow()
            )
            db.add(message)
            
            if result.get("status") == "sent":
                sent_count += 1
            else:
                failed_count += 1
        
        campaign.status = CampaignStatus.COMPLETED.value
        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        campaign.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "campaign_id": campaign_id,
            "total_recipients": campaign.total_recipients,
            "sent_count": sent_count,
            "failed_count": failed_count
        }


class EmailTemplateManager:
    """Manages email templates"""
    
    TEMPLATE_VARIABLES = {
        "first_name": "Customer first name",
        "last_name": "Customer last name",
        "email": "Customer email",
        "company": "Customer company",
        "message": "Custom message body"
    }
    
    @staticmethod
    def create_template(
        db: Session,
        template_name: str,
        subject: str,
        html_content: str,
        created_by: str
    ) -> EmailTemplate:
        """Create email template"""
        template = EmailTemplate(
            id=str(uuid.uuid4()),
            template_name=template_name,
            subject=subject,
            html_content=html_content,
            variables=list(EmailTemplateManager.TEMPLATE_VARIABLES.keys()),
            is_active=True,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(template)
        db.commit()
        return template
    
    @staticmethod
    def render_template(
        template: EmailTemplate,
        variables: Dict[str, str]
    ) -> Dict[str, str]:
        """Render template with variables"""
        subject = template.subject
        html_content = template.html_content
        
        for key, value in variables.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            html_content = html_content.replace(f"{{{{{key}}}}}", str(value))
        
        return {
            "subject": subject,
            "html_content": html_content
        }


class EmailCampaignManager:
    """Manages email campaigns"""
    
    @staticmethod
    def create_campaign(
        db: Session,
        campaign_name: str,
        template_id: str,
        audience_filter: Dict[str, Any],
        created_by: str
    ) -> EmailCampaign:
        """Create email campaign"""
        campaign = EmailCampaign(
            id=str(uuid.uuid4()),
            campaign_name=campaign_name,
            template_id=template_id,
            audience_filter=audience_filter,
            status=CampaignStatus.DRAFT.value,
            total_recipients=0,
            sent_count=0,
            failed_count=0,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(campaign)
        db.commit()
        return campaign
    
    @staticmethod
    def execute_email_campaign(
        db: Session,
        campaign_id: str,
        plunk_client: PlunkEmailClient,
        template_manager: EmailTemplateManager
    ) -> Dict[str, Any]:
        """Execute email campaign"""
        campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        template = db.query(EmailTemplate).filter(
            EmailTemplate.id == campaign.template_id
        ).first()
        if not template:
            raise ValueError(f"Template {campaign.template_id} not found")
        
        # Get recipients
        recipients = EmailCampaignManager.get_campaign_recipients(db, campaign.audience_filter)
        
        campaign.status = CampaignStatus.SENDING.value
        campaign.total_recipients = len(recipients)
        db.commit()
        
        sent_count = 0
        failed_count = 0
        
        for customer in recipients:
            if not customer.email:
                failed_count += 1
                continue
            
            # Render template
            rendered = template_manager.render_template(
                template,
                {
                    "first_name": customer.first_name or "",
                    "last_name": customer.last_name or "",
                    "email": customer.email,
                    "company": customer.company or ""
                }
            )
            
            result = plunk_client.send_email(
                to_email=customer.email,
                subject=rendered["subject"],
                html_content=rendered["html_content"]
            )
            
            # Record message
            message = EmailMessage(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                customer_id=customer.id,
                email_address=customer.email,
                subject=rendered["subject"],
                status=result.get("status"),
                plunk_message_id=result.get("message_id"),
                created_at=datetime.utcnow()
            )
            db.add(message)
            
            if result.get("status") == "sent":
                sent_count += 1
            else:
                failed_count += 1
        
        campaign.status = CampaignStatus.COMPLETED.value
        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        campaign.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "campaign_id": campaign_id,
            "total_recipients": campaign.total_recipients,
            "sent_count": sent_count,
            "failed_count": failed_count
        }
    
    @staticmethod
    def get_campaign_recipients(
        db: Session,
        audience_filter: Dict[str, Any]
    ) -> List[Customer]:
        """Get customers matching campaign filter"""
        query = db.query(Customer).filter(Customer.deleted_at.is_(None))
        
        if audience_filter.get("source"):
            query = query.filter(Customer.source == audience_filter["source"])
        
        if audience_filter.get("min_propensity_score"):
            query = query.filter(
                Customer.propensity_score >= audience_filter["min_propensity_score"]
            )
        
        return query.all()


class NotificationAnalytics:
    """SMS and Email analytics"""
    
    @staticmethod
    def get_sms_analytics(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get SMS analytics"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        campaigns = db.query(SMSCampaign).filter(
            SMSCampaign.created_at >= start_date
        ).all()
        
        total_sent = sum(c.sent_count for c in campaigns)
        total_failed = sum(c.failed_count for c in campaigns)
        
        return {
            "period_days": days,
            "total_campaigns": len(campaigns),
            "total_sent": total_sent,
            "total_failed": total_failed,
            "success_rate": (
                total_sent / (total_sent + total_failed) 
                if (total_sent + total_failed) > 0 
                else 0
            )
        }
    
    @staticmethod
    def get_email_analytics(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get email analytics"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        campaigns = db.query(EmailCampaign).filter(
            EmailCampaign.created_at >= start_date
        ).all()
        
        total_sent = sum(c.sent_count for c in campaigns)
        total_failed = sum(c.failed_count for c in campaigns)
        
        return {
            "period_days": days,
            "total_campaigns": len(campaigns),
            "total_sent": total_sent,
            "total_failed": total_failed,
            "success_rate": (
                total_sent / (total_sent + total_failed)
                if (total_sent + total_failed) > 0
                else 0
            )
        }
