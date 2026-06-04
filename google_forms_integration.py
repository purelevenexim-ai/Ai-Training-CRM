"""
Google Forms Integration
Receives form submissions and creates leads
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import json
import re


class FormSubmissionStatus(str, Enum):
    """Submission processing status"""
    RECEIVED = "received"           # Raw submission received
    PROCESSING = "processing"       # Being deduplicated/validated
    DUPLICATE = "duplicate"         # Matched existing customer
    LEAD_CREATED = "lead_created"   # New lead created
    ENRICHED = "enriched"           # Propensity scored
    ERROR = "error"                 # Processing failed


class DuplicateMatchType(str, Enum):
    """Type of duplicate match found"""
    EXACT_EMAIL = "exact_email"
    EXACT_PHONE = "exact_phone"
    EMAIL_PHONE = "email_phone"
    EMAIL_NAME = "email_name"
    PHONE_NAME = "phone_name"
    NO_MATCH = "no_match"


class GoogleFormDeduplicator:
    """Deduplicate form submissions against existing customers"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _normalize_email(self, email: Optional[str]) -> Optional[str]:
        """Normalize email: lowercase, trim, validate"""
        if not email:
            return None
        email = email.strip().lower()
        if '@' in email and '.' in email.split('@')[1]:
            return email
        return None
    
    def _normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """Normalize phone: E.164 format (critical for Indian numbers)"""
        if not phone:
            return None
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Handle Indian numbers
        if len(digits) == 10:
            # Local 10-digit number
            digits = '91' + digits  # Add country code
        elif len(digits) == 12 and digits.startswith('91'):
            # Already has country code
            pass
        elif len(digits) >= 11 and len(digits) <= 15:
            # International format
            if not digits.startswith('+'):
                digits = digits  # Already normalized
        else:
            return None  # Invalid length
        
        # E.164 format
        return f"+{digits}" if not digits.startswith('+') else digits
    
    def _normalize_name(self, name: Optional[str]) -> Optional[str]:
        """Normalize name: title case, trim"""
        if not name:
            return None
        return name.strip().title()
    
    def _hash_field(self, value: Optional[str]) -> Optional[str]:
        """SHA256 hash for comparison"""
        if not value:
            return None
        return hashlib.sha256(value.lower().encode()).hexdigest()
    
    def find_duplicates(self,
                       email: Optional[str] = None,
                       phone: Optional[str] = None,
                       first_name: Optional[str] = None,
                       last_name: Optional[str] = None) -> Tuple[Optional[str], DuplicateMatchType]:
        """
        Find matching customer in database
        
        Args:
            email: Email address
            phone: Phone number
            first_name: First name
            last_name: Last name
        
        Returns:
            (customer_id, match_type) or (None, NO_MATCH)
        """
        from crm_models import Customer
        
        email = self._normalize_email(email)
        phone = self._normalize_phone(phone)
        first_name = self._normalize_name(first_name)
        last_name = self._normalize_name(last_name)
        
        # 1. Exact email match (highest confidence)
        if email:
            customer = self.db.query(Customer).filter(
                func.lower(Customer.email) == email
            ).first()
            
            if customer:
                return (customer.id, DuplicateMatchType.EXACT_EMAIL)
        
        # 2. Exact phone match
        if phone:
            customer = self.db.query(Customer).filter(
                Customer.phone == phone
            ).first()
            
            if customer:
                return (customer.id, DuplicateMatchType.EXACT_PHONE)
        
        # 3. Email + Phone match
        if email and phone:
            customer = self.db.query(Customer).filter(
                func.lower(Customer.email) == email,
                Customer.phone == phone
            ).first()
            
            if customer:
                return (customer.id, DuplicateMatchType.EMAIL_PHONE)
        
        # 4. Email + First Name match
        if email and first_name:
            customer = self.db.query(Customer).filter(
                func.lower(Customer.email) == email,
                func.lower(Customer.first_name) == first_name.lower()
            ).first()
            
            if customer:
                return (customer.id, DuplicateMatchType.EMAIL_NAME)
        
        # 5. Phone + Name match
        if phone and first_name:
            customer = self.db.query(Customer).filter(
                Customer.phone == phone,
                func.lower(Customer.first_name) == first_name.lower()
            ).first()
            
            if customer:
                return (customer.id, DuplicateMatchType.PHONE_NAME)
        
        return (None, DuplicateMatchType.NO_MATCH)
    
    def get_submission_hash(self, submission_data: Dict) -> str:
        """
        Generate unique hash for submission
        (Prevent duplicate processing if webhook fires twice)
        """
        # Use email + timestamp as unique identifier
        key = f"{submission_data.get('email', '')}:{submission_data.get('timestamp', '')}"
        return hashlib.sha256(key.encode()).hexdigest()


class GoogleFormSubmissionProcessor:
    """Process form submissions and create leads"""
    
    def __init__(self, db: Session):
        self.db = db
        self.deduplicator = GoogleFormDeduplicator(db)
    
    def process_submission(self,
                          form_id: str,
                          submission_data: Dict,
                          form_field_mapping: Optional[Dict] = None) -> Dict:
        """
        Process Google Form submission
        
        Args:
            form_id: Form identifier
            submission_data: Raw form data (field_name -> value)
            form_field_mapping: Map form fields to customer fields
                {
                  'email': 'Email Address',
                  'phone': 'Phone Number',
                  'first_name': 'First Name',
                  'last_name': 'Last Name',
                  'company': 'Company Name'
                }
        
        Returns:
            {
                'status': 'lead_created' | 'duplicate' | 'error',
                'customer_id': str,
                'submission_id': str,
                'message': str
            }
        """
        from crm_models import Customer, GoogleFormSubmission
        import uuid
        
        # Default mapping
        if not form_field_mapping:
            form_field_mapping = {
                'email': 'Email Address',
                'phone': 'Phone Number',
                'first_name': 'First Name',
                'last_name': 'Last Name',
                'company': 'Company Name',
                'message': 'Message'
            }
        
        # Extract fields from submission
        extracted = {}
        for crm_field, form_field in form_field_mapping.items():
            extracted[crm_field] = submission_data.get(form_field)
        
        # Check for duplicates
        existing_customer_id, match_type = self.deduplicator.find_duplicates(
            email=extracted.get('email'),
            phone=extracted.get('phone'),
            first_name=extracted.get('first_name'),
            last_name=extracted.get('last_name')
        )
        
        # Generate submission ID
        submission_id = str(uuid.uuid4())
        submission_hash = self.deduplicator.get_submission_hash(submission_data)
        
        try:
            if existing_customer_id:
                # Link to existing customer
                customer_id = existing_customer_id
                
                # Update if new data
                customer = self.db.query(Customer).filter(
                    Customer.id == customer_id
                ).first()
                
                if customer:
                    # Update empty fields
                    if not customer.phone and extracted.get('phone'):
                        customer.phone = extracted['phone']
                    if not customer.company and extracted.get('company'):
                        customer.company = extracted['company']
                    if not customer.lead_source:
                        customer.lead_source = f"google_form_{form_id}"
                    
                    customer.updated_at = datetime.utcnow()
                    self.db.commit()
                
                status = FormSubmissionStatus.DUPLICATE
            else:
                # Create new customer/lead
                customer_id = str(uuid.uuid4())
                
                customer = Customer(
                    id=customer_id,
                    email=extracted.get('email'),
                    phone=extracted.get('phone'),
                    first_name=extracted.get('first_name'),
                    last_name=extracted.get('last_name'),
                    company=extracted.get('company'),
                    is_lead=True,
                    lead_source=f"google_form_{form_id}",
                    lead_status="new",
                    lead_score=0.3,  # Starting score for new leads
                    contacted_at=None,
                    created_at=datetime.utcnow()
                )
                
                self.db.add(customer)
                self.db.commit()
                
                status = FormSubmissionStatus.LEAD_CREATED
            
            # Record submission
            submission = GoogleFormSubmission(
                id=submission_id,
                form_id=form_id,
                customer_id=customer_id,
                submission_data=submission_data,
                extracted_fields=extracted,
                match_type=match_type.value,
                submission_hash=submission_hash,
                status=status.value,
                created_at=datetime.utcnow()
            )
            
            self.db.add(submission)
            self.db.commit()
            
            return {
                'status': status.value,
                'customer_id': customer_id,
                'submission_id': submission_id,
                'match_type': match_type.value,
                'message': f"Submission processed: {status.value}"
            }
        
        except Exception as e:
            # Record error
            submission = GoogleFormSubmission(
                id=submission_id,
                form_id=form_id,
                customer_id=None,
                submission_data=submission_data,
                extracted_fields=extracted,
                match_type=DuplicateMatchType.NO_MATCH.value,
                submission_hash=submission_hash,
                status=FormSubmissionStatus.ERROR.value,
                error_message=str(e),
                created_at=datetime.utcnow()
            )
            
            self.db.add(submission)
            self.db.commit()
            
            return {
                'status': 'error',
                'customer_id': None,
                'submission_id': submission_id,
                'message': f"Error: {str(e)}"
            }
    
    def get_submission_analytics(self, form_id: str) -> Dict:
        """Get analytics for a form"""
        from crm_models import GoogleFormSubmission
        
        total = self.db.query(GoogleFormSubmission).filter(
            GoogleFormSubmission.form_id == form_id
        ).count()
        
        if total == 0:
            return {'message': 'No submissions'}
        
        # Count by status
        status_breakdown = {}
        for status in [s.value for s in FormSubmissionStatus]:
            count = self.db.query(GoogleFormSubmission).filter(
                GoogleFormSubmission.form_id == form_id,
                GoogleFormSubmission.status == status
            ).count()
            status_breakdown[status] = count
        
        # Count by match type
        match_breakdown = {}
        for match_type in [m.value for m in DuplicateMatchType]:
            count = self.db.query(GoogleFormSubmission).filter(
                GoogleFormSubmission.form_id == form_id,
                GoogleFormSubmission.match_type == match_type
            ).count()
            match_breakdown[match_type] = count
        
        # Leads created rate
        leads_created = status_breakdown.get(FormSubmissionStatus.LEAD_CREATED.value, 0)
        leads_rate = round((leads_created / total * 100), 2) if total > 0 else 0
        
        return {
            'form_id': form_id,
            'total_submissions': total,
            'status_breakdown': status_breakdown,
            'match_breakdown': match_breakdown,
            'leads_created': leads_created,
            'leads_creation_rate': leads_rate
        }


# Example usage
if __name__ == '__main__':
    print("Google Forms integration module loaded")
