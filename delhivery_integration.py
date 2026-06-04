"""
Delhivery Shipping Integration
Manages orders, shipments, and tracking with Delhivery API
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func
import requests
import json


class DelhiveryStatus(str, Enum):
    """Delhivery shipment status"""
    PENDING = "pending"
    PICKED = "picked"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DelhiveryEventType(str, Enum):
    """Delhivery tracking event types"""
    PICKUP = "pickup"
    IN_TRANSIT = "in_transit"
    DELIVERY_ATTEMPT = "delivery_attempt"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETURN_INITIATED = "return_initiated"
    RETURNED = "returned"


class DelhiveryAPIClient:
    """Delhivery API integration"""
    
    def __init__(self, api_key: str, client_name: str = "PURELEVEN"):
        """
        Initialize Delhivery API client
        
        Args:
            api_key: Delhivery API key
            client_name: Your account name on Delhivery
        """
        self.api_key = api_key
        self.client_name = client_name
        self.base_url = "https://track.delhivery.com/api/v1"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {api_key}'
        }
    
    def create_shipment(self,
                       order_number: str,
                       recipient_name: str,
                       recipient_phone: str,
                       address: Dict,
                       items: List[Dict],
                       total_amount: float,
                       order_metadata: Optional[Dict] = None) -> Dict:
        """
        Create shipment in Delhivery
        
        Args:
            order_number: Your order ID (e.g., from Shopify)
            recipient_name: Customer name
            recipient_phone: Customer phone (E.164 format)
            address: {street, city, state, postal_code}
            items: [{name, qty, price, sku}]
            total_amount: Total order value
            order_metadata: Custom data
        
        Returns:
            {
                'status': 'created',
                'waybill': '12345678901',
                'delhivery_response': {...}
            }
        """
        
        payload = {
            'shipment': [{
                'name': recipient_name,
                'phone': recipient_phone,
                'email': order_metadata.get('email') if order_metadata else None,
                'address': address.get('address_line1'),
                'address_2': address.get('address_line2'),
                'city': address.get('city'),
                'state': address.get('state'),
                'pin': address.get('postal_code'),
                'country': address.get('country', 'India'),
                'waybill': '',  # Let Delhivery assign
                'order': order_number,
                'shipment_length': order_metadata.get('length', 10) if order_metadata else 10,
                'shipment_width': order_metadata.get('width', 10) if order_metadata else 10,
                'shipment_height': order_metadata.get('height', 10) if order_metadata else 10,
                'weight': order_metadata.get('weight', 0.5) if order_metadata else 0.5,
                'declared_value': total_amount,
                'cod': 0,  # Cash on delivery disabled
                'client_name': self.client_name,
                'sku': items[0]['sku'] if items else 'MIXED'
            }]
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/shipment/create/',
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                data = response.json()
                waybill = data['shipment'][0].get('waybill') if data.get('shipment') else None
                
                return {
                    'status': 'created',
                    'waybill': waybill,
                    'delhivery_response': data
                }
            else:
                return {
                    'status': 'error',
                    'message': response.text,
                    'code': response.status_code
                }
        
        except requests.RequestException as e:
            return {
                'status': 'error',
                'message': str(e),
                'code': 'connection_error'
            }
    
    def track_shipment(self, waybill: str) -> Dict:
        """
        Get real-time tracking for shipment
        
        Args:
            waybill: Delhivery tracking number
        
        Returns:
            {
                'status': 'in_transit',
                'location': 'Delhi',
                'last_event': {...},
                'tracking_events': [...]
            }
        """
        
        try:
            response = requests.get(
                f'{self.base_url}/packages/{waybill}/',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse tracking data
                package_info = data.get('data', {}) if isinstance(data, dict) else {}
                
                # Get current status
                current_status = package_info.get('current_status', 'unknown')
                
                # Get tracking events (scans)
                events = package_info.get('tracking_data', [])
                
                last_event = events[0] if events else None
                
                return {
                    'status': 'found',
                    'waybill': waybill,
                    'delhivery_status': current_status,
                    'location': last_event.get('location') if last_event else None,
                    'last_event': last_event,
                    'tracking_events': events,
                    'timestamp': last_event.get('time') if last_event else None
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Shipment not found',
                    'code': response.status_code
                }
        
        except requests.RequestException as e:
            return {
                'status': 'error',
                'message': str(e),
                'code': 'connection_error'
            }
    
    def cancel_shipment(self, waybill: str, reason: str = "Customer requested") -> Dict:
        """Cancel a shipment"""
        
        payload = {
            'waybill': waybill,
            'reason': reason
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/shipment/cancel/',
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return {'status': 'cancelled', 'waybill': waybill}
            else:
                return {'status': 'error', 'message': response.text}
        
        except requests.RequestException as e:
            return {'status': 'error', 'message': str(e)}


class DelhiveryOrderManager:
    """Manage Delhivery orders in CRM"""
    
    def __init__(self, db: Session, delhivery_client: DelhiveryAPIClient):
        """Initialize manager"""
        self.db = db
        self.delhivery = delhivery_client
    
    def create_order(self,
                    order_number: str,
                    customer_id: Optional[str],
                    recipient_name: str,
                    recipient_phone: str,
                    address: Dict,
                    items: List[Dict],
                    total_amount: float,
                    order_metadata: Optional[Dict] = None) -> Dict:
        """
        Create Delhivery order and track in CRM
        
        Returns: {
            'order_id': str,
            'waybill': str,
            'status': 'created',
            'tracking_url': str
        }
        """
        from crm_models import DelhiveryOrder
        import uuid
        
        # Create in Delhivery
        delhivery_result = self.delhivery.create_shipment(
            order_number, recipient_name, recipient_phone,
            address, items, total_amount, order_metadata
        )
        
        if delhivery_result['status'] != 'created':
            return {
                'status': 'error',
                'message': delhivery_result.get('message', 'Creation failed')
            }
        
        waybill = delhivery_result.get('waybill')
        
        # Create in CRM
        order = DelhiveryOrder(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            order_number=order_number,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            address_line1=address.get('address_line1', ''),
            address_line2=address.get('address_line2'),
            city=address.get('city', ''),
            state=address.get('state', ''),
            postal_code=address.get('postal_code', ''),
            country=address.get('country', 'IN'),
            items_count=len(items),
            items=items,
            subtotal=order_metadata.get('subtotal') if order_metadata else total_amount,
            shipping_charge=order_metadata.get('shipping', 0) if order_metadata else 0,
            tax=order_metadata.get('tax', 0) if order_metadata else 0,
            total_amount=total_amount,
            delhivery_waybill=waybill,
            delhivery_status=DelhiveryStatus.PENDING.value,
            delhivery_response=delhivery_result.get('delhivery_response'),
            tracking_url=f'https://track.delhivery.com/shipment/{waybill}'
        )
        
        self.db.add(order)
        self.db.commit()
        
        return {
            'order_id': order.id,
            'waybill': waybill,
            'status': 'created',
            'tracking_url': order.tracking_url
        }
    
    def update_tracking(self, waybill: str) -> Dict:
        """
        Fetch latest tracking from Delhivery and update CRM
        
        Returns: {
            'status': 'updated',
            'delhivery_status': str,
            'events': int
        }
        """
        from crm_models import DelhiveryOrder, DelhiveryTracking
        import uuid
        
        # Get order
        order = self.db.query(DelhiveryOrder).filter(
            DelhiveryOrder.delhivery_waybill == waybill
        ).first()
        
        if not order:
            return {'error': 'Order not found'}
        
        # Track with Delhivery
        tracking_result = self.delhivery.track_shipment(waybill)
        
        if tracking_result['status'] != 'found':
            return tracking_result
        
        # Update order status
        new_status = tracking_result.get('delhivery_status', 'pending').lower()
        
        # Map to our status enum
        status_map = {
            'pending': DelhiveryStatus.PENDING.value,
            'picked': DelhiveryStatus.PICKED.value,
            'in_transit': DelhiveryStatus.IN_TRANSIT.value,
            'out_for_delivery': DelhiveryStatus.OUT_FOR_DELIVERY.value,
            'delivered': DelhiveryStatus.DELIVERED.value,
            'failed': DelhiveryStatus.FAILED.value,
            'cancelled': DelhiveryStatus.CANCELLED.value
        }
        
        order.delhivery_status = status_map.get(new_status, new_status)
        order.last_track_at = datetime.utcnow()
        
        # Create tracking events
        events_created = 0
        for event in tracking_result.get('tracking_events', []):
            # Check if event already exists
            existing = self.db.query(DelhiveryTracking).filter(
                DelhiveryTracking.delhivery_order_id == order.id,
                DelhiveryTracking.status_message == event.get('status')
            ).first()
            
            if not existing:
                tracking = DelhiveryTracking(
                    id=str(uuid.uuid4()),
                    delhivery_order_id=order.id,
                    event_type=self._map_event_type(event.get('status', '')),
                    event_timestamp=datetime.fromisoformat(
                        event.get('time', datetime.utcnow().isoformat())
                    ) if event.get('time') else datetime.utcnow(),
                    location=event.get('location'),
                    status_message=event.get('status'),
                    metadata=event
                )
                
                self.db.add(tracking)
                events_created += 1
        
        # Update timestamps based on status
        if order.delhivery_status == DelhiveryStatus.PICKED.value and not order.picked_at:
            order.picked_at = datetime.utcnow()
        elif order.delhivery_status == DelhiveryStatus.IN_TRANSIT.value and not order.in_transit_at:
            order.in_transit_at = datetime.utcnow()
        elif order.delhivery_status == DelhiveryStatus.OUT_FOR_DELIVERY.value and not order.out_for_delivery_at:
            order.out_for_delivery_at = datetime.utcnow()
        elif order.delhivery_status == DelhiveryStatus.DELIVERED.value and not order.delivered_at:
            order.delivered_at = datetime.utcnow()
        elif order.delhivery_status == DelhiveryStatus.FAILED.value and not order.failed_at:
            order.failed_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            'status': 'updated',
            'waybill': waybill,
            'delhivery_status': order.delhivery_status,
            'events_created': events_created
        }
    
    def get_delivery_analytics(self) -> Dict:
        """Get delivery performance metrics"""
        from crm_models import DelhiveryOrder
        
        total = self.db.query(DelhiveryOrder).count()
        
        if total == 0:
            return {'message': 'No orders'}
        
        delivered = self.db.query(DelhiveryOrder).filter(
            DelhiveryOrder.delhivery_status == DelhiveryStatus.DELIVERED.value
        ).count()
        
        in_transit = self.db.query(DelhiveryOrder).filter(
            DelhiveryOrder.delhivery_status == DelhiveryStatus.IN_TRANSIT.value
        ).count()
        
        failed = self.db.query(DelhiveryOrder).filter(
            DelhiveryOrder.delhivery_status == DelhiveryStatus.FAILED.value
        ).count()
        
        # Calculate avg delivery time
        from sqlalchemy import and_
        delivered_orders = self.db.query(DelhiveryOrder).filter(
            and_(
                DelhiveryOrder.delivered_at.isnot(None),
                DelhiveryOrder.created_at.isnot(None)
            )
        ).all()
        
        avg_delivery_hours = 0
        if delivered_orders:
            total_hours = sum(
                (o.delivered_at - o.created_at).total_seconds() / 3600
                for o in delivered_orders
            )
            avg_delivery_hours = total_hours / len(delivered_orders)
        
        return {
            'total_orders': total,
            'delivered': delivered,
            'delivery_rate': round((delivered / total * 100) if total > 0 else 0, 2),
            'in_transit': in_transit,
            'failed': failed,
            'avg_delivery_hours': round(avg_delivery_hours, 2)
        }
    
    def _map_event_type(self, status_string: str) -> str:
        """Map Delhivery status to event type"""
        status_lower = status_string.lower()
        
        if 'pickup' in status_lower or 'picked' in status_lower:
            return DelhiveryEventType.PICKUP.value
        elif 'transit' in status_lower:
            return DelhiveryEventType.IN_TRANSIT.value
        elif 'out for delivery' in status_lower:
            return DelhiveryEventType.OUT_FOR_DELIVERY.value
        elif 'delivered' in status_lower:
            return DelhiveryEventType.DELIVERED.value
        elif 'failed' in status_lower:
            return DelhiveryEventType.FAILED.value
        elif 'cancelled' in status_lower:
            return DelhiveryEventType.CANCELLED.value
        else:
            return DelhiveryEventType.IN_TRANSIT.value


# Example usage
if __name__ == '__main__':
    print("Delhivery integration module loaded")
