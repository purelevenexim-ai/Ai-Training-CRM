"""
Offline Conversion Matching & Hashing
Handles customer data hashing for Meta Conversion API matching
"""

import hashlib
import re
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from enum import Enum
import json


class MatchField(str, Enum):
    """Offline conversion match fields (Meta CAP API)"""
    EMAIL = "em"
    PHONE = "ph"
    FIRST_NAME = "fn"
    LAST_NAME = "ln"
    CITY = "ct"
    STATE = "st"
    ZIP = "zp"
    COUNTRY = "country"
    EXTERNAL_ID = "external_id"


class ConversionStatus(str, Enum):
    """Offline conversion processing status"""
    PENDING = "pending"        # Awaiting CAPI response
    MATCHED = "matched"        # Successfully matched to customer
    UNMATCHED = "unmatched"    # No match found
    FAILED = "failed"          # Error during matching
    RETRYING = "retrying"      # In retry queue


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize phone number for hashing
    
    Steps:
    1. Remove all non-digit characters
    2. Remove leading 0 if present
    3. Return last 15 digits (E.164 standard max)
    
    Args:
        phone: Raw phone number (any format)
    
    Returns:
        Normalized phone (digits only) or None if invalid
    """
    if not phone:
        return None
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', str(phone))
    
    # Must be at least 10 digits
    if len(digits) < 10:
        return None
    
    # Remove leading 0 if present (India convention)
    if digits.startswith('0') and len(digits) > 10:
        digits = digits[1:]
    
    # Keep last 15 digits (E.164 max)
    normalized = digits[-15:]
    
    return normalized if normalized else None


def normalize_email(email: str) -> Optional[str]:
    """
    Normalize email for hashing
    
    Steps:
    1. Convert to lowercase
    2. Strip whitespace
    3. Validate basic format
    
    Args:
        email: Raw email address
    
    Returns:
        Normalized email or None if invalid
    """
    if not email:
        return None
    
    normalized = email.lower().strip()
    
    # Basic validation
    if '@' not in normalized or '.' not in normalized:
        return None
    
    return normalized


def normalize_address(city: Optional[str] = None, 
                     state: Optional[str] = None,
                     postal: Optional[str] = None,
                     country: Optional[str] = None) -> Optional[str]:
    """
    Normalize address for hashing
    
    Steps:
    1. Convert all to lowercase
    2. Remove extra spaces
    3. Combine: city,state,postal,country
    
    Args:
        city: City/locality
        state: State/province
        postal: Postal code/zip
        country: Country code
    
    Returns:
        Normalized address string or None if all empty
    """
    parts = []
    
    if city:
        parts.append(city.lower().strip())
    if state:
        parts.append(state.lower().strip())
    if postal:
        parts.append(postal.lower().strip())
    if country:
        parts.append(country.lower().strip())
    
    if not parts:
        return None
    
    return ','.join(parts)


def hash_pii(value: Optional[str]) -> Optional[str]:
    """
    Hash PII (Personally Identifiable Information) using SHA256
    
    Steps:
    1. Normalize input (lowercase, trim)
    2. SHA256 hash
    3. Return hex string (lowercase)
    
    Args:
        value: PII value to hash (email, phone, etc)
    
    Returns:
        SHA256 hash (hex) or None if empty
    """
    if not value:
        return None
    
    # Normalize to lowercase and strip
    normalized = str(value).lower().strip()
    
    if not normalized:
        return None
    
    # SHA256 hash
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()


def build_hashed_fields(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal: Optional[str] = None,
    country: Optional[str] = None,
    external_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Build dictionary of hashed fields for Meta CAPI
    
    Args:
        All optional PII fields
    
    Returns:
        Dict of {field_code: hashed_value} for non-empty fields
    
    Example:
        {
            "em": "f7dc4f50...",  # email hash
            "ph": "3f5b8c2a...",  # phone hash
            "fn": "a1b2c3d4..."   # first name hash
        }
    """
    hashed = {}
    
    # Email
    if email:
        normalized = normalize_email(email)
        if normalized:
            hashed["em"] = hash_pii(normalized)
    
    # Phone
    if phone:
        normalized = normalize_phone(phone)
        if normalized:
            hashed["ph"] = hash_pii(normalized)
    
    # First name
    if first_name:
        hashed["fn"] = hash_pii(first_name)
    
    # Last name
    if last_name:
        hashed["ln"] = hash_pii(last_name)
    
    # Address
    if city:
        hashed["ct"] = hash_pii(city)
    if state:
        hashed["st"] = hash_pii(state)
    if postal:
        hashed["zp"] = hash_pii(postal)
    if country:
        hashed["country"] = hash_pii(country)
    
    # External ID (not hashed, used as-is)
    if external_id:
        hashed["external_id"] = str(external_id)
    
    return hashed


def get_hashed_fields_for_api(customer_data: Dict) -> Dict[str, str]:
    """
    Extract and hash fields from customer object for API submission
    
    Args:
        customer_data: Customer object with optional fields
    
    Returns:
        Hashed fields dict for CAPI
    """
    return build_hashed_fields(
        email=customer_data.get('email'),
        phone=customer_data.get('phone'),
        first_name=customer_data.get('name', '').split()[0] if customer_data.get('name') else None,
        last_name=' '.join(customer_data.get('name', '').split()[1:]) if customer_data.get('name') else None,
        city=customer_data.get('city'),
        state=customer_data.get('state'),
        postal=customer_data.get('postal_code'),
        country=customer_data.get('country'),
        external_id=customer_data.get('id')
    )


def get_match_confidence(match_count: int) -> float:
    """
    Calculate confidence score based on number of matching fields
    
    Logic:
    - 1 field: 0.3 (low confidence)
    - 2 fields: 0.6 (medium confidence)
    - 3+ fields: 0.9 (high confidence)
    
    Args:
        match_count: Number of fields that matched
    
    Returns:
        Confidence score 0.0-1.0
    """
    if match_count <= 0:
        return 0.0
    elif match_count == 1:
        return 0.3
    elif match_count == 2:
        return 0.6
    else:  # 3+
        return 0.9


class OfflineConversionMatcher:
    """Handles offline conversion matching and retry logic"""
    
    def __init__(self, db_session):
        """
        Initialize matcher with database session
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.max_retries = 5
        self.retry_delay_minutes = 15
    
    def match_customer(self, conversion_data: Dict) -> Dict:
        """
        Match conversion data to existing customer
        
        Algorithm:
        1. Try exact email match
        2. Try exact phone match
        3. Try normalized phone + name match
        4. Try address match (city+postal+state)
        
        Args:
            conversion_data: {
                email, phone, name, 
                city, state, postal, country,
                conversion_value, currency, timestamp
            }
        
        Returns:
            {
                matched_customer_id: str or None,
                match_fields: List[str],  # Which fields matched
                confidence: float,  # 0.0-1.0
                algorithm_used: str  # "email", "phone", "address", etc
            }
        """
        from crm_models import Customer
        
        results = {
            'matched_customer_id': None,
            'match_fields': [],
            'confidence': 0.0,
            'algorithm_used': 'none'
        }
        
        # Algorithm 1: Exact email match
        if conversion_data.get('email'):
            email_norm = normalize_email(conversion_data['email'])
            if email_norm:
                customer = self.db.query(Customer).filter(
                    Customer.email.ilike(email_norm),
                    Customer.deleted_at.is_(None)
                ).first()
                
                if customer:
                    results['matched_customer_id'] = customer.id
                    results['match_fields'] = ['email']
                    results['confidence'] = 0.95  # Email is high confidence
                    results['algorithm_used'] = 'email'
                    return results
        
        # Algorithm 2: Exact phone match
        if conversion_data.get('phone'):
            phone_norm = normalize_phone(conversion_data['phone'])
            if phone_norm:
                # Query: Match normalized phone
                customers = self.db.query(Customer).filter(
                    Customer.phone.isnot(None),
                    Customer.deleted_at.is_(None)
                ).all()
                
                for customer in customers:
                    if customer.phone and normalize_phone(customer.phone) == phone_norm:
                        results['matched_customer_id'] = customer.id
                        results['match_fields'] = ['phone']
                        results['confidence'] = 0.9
                        results['algorithm_used'] = 'phone'
                        return results
        
        # Algorithm 3: Phone + Name match (higher confidence than address alone)
        if conversion_data.get('phone') and conversion_data.get('name'):
            phone_norm = normalize_phone(conversion_data['phone'])
            if phone_norm:
                customers = self.db.query(Customer).filter(
                    Customer.phone.isnot(None),
                    Customer.name.isnot(None),
                    Customer.deleted_at.is_(None)
                ).all()
                
                for customer in customers:
                    if customer.phone and normalize_phone(customer.phone) == phone_norm:
                        # Check name similarity (simple: first word match)
                        conv_name = conversion_data['name'].split()[0].lower()
                        cust_name = customer.name.split()[0].lower()
                        
                        if conv_name == cust_name:
                            results['matched_customer_id'] = customer.id
                            results['match_fields'] = ['phone', 'name']
                            results['confidence'] = 0.85
                            results['algorithm_used'] = 'phone+name'
                            return results
        
        # Algorithm 4: Address match (city + postal + state)
        if conversion_data.get('city') and conversion_data.get('postal'):
            customers = self.db.query(Customer).filter(
                Customer.deleted_at.is_(None)
            ).all()
            
            for customer in customers:
                # Count matching address fields
                match_count = 0
                
                if customer.city and conversion_data.get('city'):
                    if customer.city.lower().strip() == conversion_data['city'].lower().strip():
                        match_count += 1
                
                if customer.postal_code and conversion_data.get('postal'):
                    if customer.postal_code.lower().strip() == conversion_data['postal'].lower().strip():
                        match_count += 1
                
                if customer.state and conversion_data.get('state'):
                    if customer.state.lower().strip() == conversion_data['state'].lower().strip():
                        match_count += 1
                
                # Match if 2+ address fields match
                if match_count >= 2:
                    results['matched_customer_id'] = customer.id
                    results['match_fields'] = ['address']
                    results['confidence'] = get_match_confidence(match_count)
                    results['algorithm_used'] = 'address'
                    return results
        
        # No match found
        results['confidence'] = 0.0
        results['algorithm_used'] = 'no_match'
        
        return results
    
    def schedule_retry(self, conversion_id: str, reason: str) -> Dict:
        """
        Schedule conversion for retry
        
        Args:
            conversion_id: Offline conversion ID
            reason: Why retry is needed
        
        Returns:
            {status, next_retry_at, retry_count}
        """
        from crm_models import OfflineConversion
        
        conversion = self.db.query(OfflineConversion).filter(
            OfflineConversion.id == conversion_id
        ).first()
        
        if not conversion:
            return {'status': 'error', 'message': 'Conversion not found'}
        
        # Check if max retries exceeded
        if conversion.retry_count >= self.max_retries:
            conversion.status = ConversionStatus.FAILED.value
            conversion.error_message = f"Max retries ({self.max_retries}) exceeded. Last error: {reason}"
            self.db.commit()
            return {
                'status': 'failed',
                'message': 'Max retries exceeded',
                'retry_count': conversion.retry_count
            }
        
        # Schedule retry
        conversion.status = ConversionStatus.RETRYING.value
        conversion.retry_count = conversion.retry_count + 1
        conversion.next_retry_at = datetime.utcnow() + timedelta(minutes=self.retry_delay_minutes)
        conversion.error_message = reason
        self.db.commit()
        
        return {
            'status': 'scheduled',
            'next_retry_at': conversion.next_retry_at,
            'retry_count': conversion.retry_count
        }
    
    def get_pending_retries(self) -> List[Dict]:
        """
        Get conversions ready for retry
        
        Returns:
            List of OfflineConversion objects ready to retry
        """
        from crm_models import OfflineConversion
        
        return self.db.query(OfflineConversion).filter(
            OfflineConversion.status == ConversionStatus.RETRYING.value,
            OfflineConversion.next_retry_at <= datetime.utcnow(),
            OfflineConversion.retry_count < self.max_retries
        ).all()


# Example usage
if __name__ == '__main__':
    # Test phone normalization
    print(normalize_phone('+91 9876 543 210'))  # 9876543210
    print(normalize_phone('09876543210'))  # 9876543210
    print(normalize_phone('918765432100'))  # 918765432100
    
    # Test email normalization
    print(normalize_email('  Test@EXAMPLE.COM  '))  # test@example.com
    
    # Test hashing
    print(hash_pii('test@example.com')[:8])  # First 8 chars of hash
    
    # Test field building
    fields = build_hashed_fields(
        email='test@example.com',
        phone='+919876543210',
        first_name='John',
        last_name='Doe'
    )
    print(f"Hashed fields: {len(fields)} fields")  # 4 fields
