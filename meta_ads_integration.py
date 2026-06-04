"""
Meta Ads Integration (Facebook Pixel + Conversions API)
Audience creation, pixel tracking, and conversion submission
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import json
import requests


class MetaEventType(str, Enum):
    """Meta Conversions API event types"""
    PAGE_VIEW = "PageView"
    VIEW_CONTENT = "ViewContent"
    SEARCH = "Search"
    ADD_TO_CART = "AddToCart"
    ADD_TO_WISHLIST = "AddToWishlist"
    INITIATE_CHECKOUT = "InitiateCheckout"
    ADD_PAYMENT_INFO = "AddPaymentInfo"
    PURCHASE = "Purchase"
    LEAD = "Lead"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    CONTACT = "Contact"
    CUSTOM = "CustomEvent"


class MetaAudienceType(str, Enum):
    """Meta audience types"""
    CUSTOMER_LIST = "CUSTOMER_LIST"  # Custom audience from customer data
    LOOKALIKE = "LOOKALIKE"           # Lookalike audience
    WEBSITE = "WEBSITE"               # Website pixel audience
    ENGAGEMENT = "ENGAGEMENT"         # Page engagement
    OFFLINE = "OFFLINE"               # Offline conversion data


class MetaPixelEventTracker:
    """Track pixel events (client-side or server-side via CAPI)"""
    
    def __init__(self, pixel_id: str, access_token: str):
        """
        Initialize Meta Pixel tracker
        
        Args:
            pixel_id: Facebook Pixel ID
            access_token: Meta API access token
        """
        self.pixel_id = pixel_id
        self.access_token = access_token
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def track_event(self,
                   event_name: str,
                   customer_data: Optional[Dict] = None,
                   content_data: Optional[Dict] = None,
                   custom_data: Optional[Dict] = None,
                   event_id: Optional[str] = None) -> Dict:
        """
        Send event to Meta Conversions API (server-side tracking)
        
        Args:
            event_name: Type of event (PageView, Purchase, Lead, etc)
            customer_data: {em (email), ph (phone), fn (first name), ln (last name), ct (city), st (state), zp (zip)}
            content_data: {content_ids, content_name, content_type, content_category, quantity, value}
            custom_data: {currency, value, status}
            event_id: Unique event identifier (for deduplication)
        
        Returns:
            {
                'status': 'success' | 'error',
                'event_id': str,
                'code': int,
                'message': str
            }
        """
        
        # Hash customer data for PII compliance
        hashed_data = {}
        if customer_data:
            for key in ['em', 'ph', 'fn', 'ln', 'ct', 'st', 'zp']:
                if key in customer_data:
                    value = customer_data[key]
                    if value:
                        # Normalize & hash
                        normalized = value.lower().strip()
                        hashed_data[key] = hashlib.sha256(
                            normalized.encode()
                        ).hexdigest()
        
        payload = {
            'data': [{
                'event_name': event_name,
                'event_time': int(datetime.utcnow().timestamp()),
                'event_id': event_id or str(int(datetime.utcnow().timestamp() * 1000)),
                'user_data': {
                    'em': hashed_data.get('em'),
                    'ph': hashed_data.get('ph'),
                    'fn': hashed_data.get('fn'),
                    'ln': hashed_data.get('ln'),
                    'ct': hashed_data.get('ct'),
                    'st': hashed_data.get('st'),
                    'zp': hashed_data.get('zp'),
                    'country': 'IN'
                },
                'custom_data': custom_data or {},
                'content_data': content_data or {}
            }],
            'test_event_code': None  # Remove if not testing
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/{self.pixel_id}/events',
                json=payload,
                params={'access_token': self.access_token},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'status': 'success',
                    'event_id': payload['data'][0]['event_id'],
                    'code': response.status_code,
                    'message': 'Event tracked'
                }
            else:
                return {
                    'status': 'error',
                    'event_id': payload['data'][0]['event_id'],
                    'code': response.status_code,
                    'message': response.text
                }
        
        except requests.RequestException as e:
            return {
                'status': 'error',
                'event_id': None,
                'code': 0,
                'message': str(e)
            }


class MetaAudienceManager:
    """Create and manage custom audiences in Meta"""
    
    def __init__(self, ad_account_id: str, access_token: str):
        """
        Initialize Meta audience manager
        
        Args:
            ad_account_id: Facebook Ad Account ID (act_XXXXX)
            access_token: Meta API access token
        """
        self.ad_account_id = ad_account_id
        self.access_token = access_token
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def create_custom_audience(self,
                              audience_name: str,
                              audience_description: Optional[str] = None) -> Dict:
        """
        Create custom audience for pixel/CAPI data
        
        Returns:
            {
                'status': 'created',
                'audience_id': str,
                'audience_name': str
            }
        """
        
        payload = {
            'name': audience_name,
            'description': audience_description,
            'subtype': 'CUSTOM',
            'pixel_id': None  # Will link to pixel
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/{self.ad_account_id}/customaudiences',
                json=payload,
                params={'access_token': self.access_token},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                audience_id = data.get('id')
                
                return {
                    'status': 'created',
                    'audience_id': audience_id,
                    'audience_name': audience_name
                }
            else:
                return {
                    'status': 'error',
                    'message': response.text
                }
        
        except requests.RequestException as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def add_users_to_audience(self,
                             audience_id: str,
                             customers: List[Dict]) -> Dict:
        """
        Add customer list to custom audience
        
        Args:
            audience_id: Meta audience ID
            customers: List of {email, phone, first_name, last_name, city, state, postal_code}
        
        Returns:
            {
                'status': 'added',
                'audience_id': str,
                'count': int,
                'failed': int
            }
        """
        
        # Hash PII for Meta
        hashed_records = []
        for customer in customers:
            hashed = {}
            
            if customer.get('email'):
                email = customer['email'].lower().strip()
                hashed['em'] = hashlib.sha256(email.encode()).hexdigest()
            
            if customer.get('phone'):
                phone = customer['phone'].lower().strip()
                hashed['ph'] = hashlib.sha256(phone.encode()).hexdigest()
            
            if customer.get('first_name'):
                fn = customer['first_name'].lower().strip()
                hashed['fn'] = hashlib.sha256(fn.encode()).hexdigest()
            
            if customer.get('last_name'):
                ln = customer['last_name'].lower().strip()
                hashed['ln'] = hashlib.sha256(ln.encode()).hexdigest()
            
            if hashed:
                hashed_records.append(hashed)
        
        # Upload in batches (Meta limit: 10K per request)
        batch_size = 10000
        total_added = 0
        total_failed = 0
        
        for i in range(0, len(hashed_records), batch_size):
            batch = hashed_records[i:i + batch_size]
            
            payload = {
                'payload': {
                    'schema': ['em', 'ph', 'fn', 'ln'],
                    'data': batch
                }
            }
            
            try:
                response = requests.post(
                    f'{self.base_url}/{audience_id}/users',
                    json=payload,
                    params={'access_token': self.access_token},
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    total_added += len(batch)
                else:
                    total_failed += len(batch)
            
            except requests.RequestException:
                total_failed += len(batch)
        
        return {
            'status': 'added',
            'audience_id': audience_id,
            'count': total_added,
            'failed': total_failed
        }
    
    def get_audience_stats(self, audience_id: str) -> Dict:
        """Get audience size and stats"""
        
        try:
            response = requests.get(
                f'{self.base_url}/{audience_id}',
                params={
                    'fields': 'id,name,approximate_count,data_sources',
                    'access_token': self.access_token
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'audience_id': audience_id,
                    'name': data.get('name'),
                    'approximate_count': data.get('approximate_count'),
                    'data_sources': data.get('data_sources')
                }
            else:
                return {'error': response.text}
        
        except requests.RequestException as e:
            return {'error': str(e)}


class MetaConversionTracker:
    """Track offline conversions and sync with Meta"""
    
    def __init__(self, db: Session, pixel_tracker: MetaPixelEventTracker, audience_manager: MetaAudienceManager):
        """Initialize conversion tracker"""
        self.db = db
        self.pixel_tracker = pixel_tracker
        self.audience_manager = audience_manager
    
    def track_conversion(self,
                        customer_id: str,
                        event_name: str,
                        value: Optional[float] = None,
                        currency: str = "INR",
                        status: Optional[str] = None) -> Dict:
        """
        Track offline conversion and send to Meta
        
        Args:
            customer_id: Customer ID in CRM
            event_name: Conversion event type
            value: Transaction value
            currency: Currency code
            status: Conversion status
        
        Returns:
            {
                'status': 'tracked',
                'conversion_id': str,
                'meta_response': {...}
            }
        """
        from crm_models import Customer, MetaConversion
        import uuid
        
        # Get customer data
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return {'error': 'Customer not found'}
        
        # Prepare event data
        customer_data = {
            'em': customer.email,
            'ph': customer.phone,
            'fn': customer.first_name,
            'ln': customer.last_name
        }
        
        custom_data = {
            'value': value,
            'currency': currency,
            'status': status
        }
        
        # Send to Meta
        meta_response = self.pixel_tracker.track_event(
            event_name=event_name,
            customer_data=customer_data,
            custom_data=custom_data,
            event_id=customer_id
        )
        
        # Record in CRM
        conversion = MetaConversion(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            event_name=event_name,
            value=value,
            currency=currency,
            status=status,
            meta_response=meta_response,
            synced_to_meta=meta_response.get('status') == 'success',
            created_at=datetime.utcnow()
        )
        
        self.db.add(conversion)
        self.db.commit()
        
        return {
            'status': 'tracked',
            'conversion_id': conversion.id,
            'meta_response': meta_response
        }
    
    def sync_customers_to_audience(self,
                                   audience_id: str,
                                   filter_by_status: Optional[str] = None) -> Dict:
        """
        Sync CRM customers to Meta custom audience
        
        Args:
            audience_id: Meta audience ID
            filter_by_status: Optional: "lead", "customer", "prospect"
        
        Returns:
            {
                'status': 'synced',
                'total_synced': int,
                'failed': int
            }
        """
        from crm_models import Customer
        
        # Get customers
        query = self.db.query(Customer)
        
        if filter_by_status:
            query = query.filter(Customer.lead_status == filter_by_status)
        
        customers = query.all()
        
        # Prepare for Meta
        customer_list = []
        for c in customers:
            if c.email or c.phone:  # At least one identifier
                customer_list.append({
                    'email': c.email,
                    'phone': c.phone,
                    'first_name': c.first_name,
                    'last_name': c.last_name,
                    'city': None,  # Extend as needed
                    'state': None,
                    'postal_code': None
                })
        
        # Sync to Meta
        if customer_list:
            result = self.audience_manager.add_users_to_audience(
                audience_id, customer_list
            )
            return result
        else:
            return {'status': 'no_customers', 'message': 'No customers to sync'}


# Example usage
if __name__ == '__main__':
    print("Meta Ads integration module loaded")
