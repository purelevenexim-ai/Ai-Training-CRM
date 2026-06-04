"""
Delhivery Shipping API Routes
Order creation, tracking, and fulfillment management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from database import SessionLocal
from delhivery_integration import (
    DelhiveryAPIClient,
    DelhiveryOrderManager,
    DelhiveryStatus
)

router = APIRouter(prefix="/api/crm", tags=["delhivery"])


# ============ Pydantic Models ============

class AddressModel(BaseModel):
    """Delivery address"""
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "IN"


class ItemModel(BaseModel):
    """Order item"""
    sku: str
    name: str
    qty: int
    price: float


class DelhiveryOrderCreate(BaseModel):
    """Create Delhivery order"""
    order_number: str
    customer_id: Optional[str] = None
    recipient_name: str
    recipient_phone: str
    recipient_email: Optional[str] = None
    address: AddressModel
    items: List[ItemModel]
    subtotal: float
    shipping_charge: float = 0.0
    tax: float = 0.0
    total_amount: float


class DelhiveryOrderResponse(BaseModel):
    """Delhivery order response"""
    id: str
    order_number: str
    waybill: Optional[str]
    delhivery_status: str
    tracking_url: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Order Management (6 endpoints) ============

@router.post("/delhivery/orders")
def create_delhivery_order(
    data: DelhiveryOrderCreate,
    db: Session = Depends(SessionLocal)
):
    """
    Create Delhivery order from Shopify order
    
    Links order to fulfillment system
    Generates tracking number
    
    Returns: {
        'order_id': str,
        'waybill': str,
        'tracking_url': str
    }
    """
    
    # Initialize Delhivery client
    import os
    api_key = os.getenv('DELHIVERY_API_KEY')
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="DELHIVERY_API_KEY not configured"
        )
    
    delhivery_client = DelhiveryAPIClient(api_key)
    manager = DelhiveryOrderManager(db, delhivery_client)
    
    # Create order metadata
    metadata = {
        'email': data.recipient_email,
        'subtotal': data.subtotal,
        'shipping': data.shipping_charge,
        'tax': data.tax,
        'length': 10,  # Default dimensions
        'width': 10,
        'height': 10,
        'weight': 0.5
    }
    
    try:
        result = manager.create_order(
            order_number=data.order_number,
            customer_id=data.customer_id,
            recipient_name=data.recipient_name,
            recipient_phone=data.recipient_phone,
            address=data.address.dict(),
            items=[item.dict() for item in data.items],
            total_amount=data.total_amount,
            order_metadata=metadata
        )
        
        if result.get('status') != 'created':
            raise HTTPException(status_code=400, detail=result.get('message'))
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delhivery/orders/{order_id}")
def get_delhivery_order(
    order_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get detailed order info"""
    
    from crm_models import DelhiveryOrder
    
    order = db.query(DelhiveryOrder).filter(
        DelhiveryOrder.id == order_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        'id': order.id,
        'order_number': order.order_number,
        'waybill': order.delhivery_waybill,
        'status': order.delhivery_status,
        'recipient_name': order.recipient_name,
        'recipient_phone': order.recipient_phone,
        'total_amount': order.total_amount,
        'delivered_at': order.delivered_at,
        'tracking_url': order.tracking_url,
        'created_at': order.created_at
    }


@router.get("/delhivery/orders")
def list_delhivery_orders(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(SessionLocal)
):
    """
    List Delhivery orders
    
    Filter by:
    - status: pending, picked, in_transit, delivered, failed
    - date range
    """
    
    from crm_models import DelhiveryOrder
    
    query = db.query(DelhiveryOrder)
    
    if status:
        query = query.filter(DelhiveryOrder.delhivery_status == status)
    
    total = query.count()
    
    orders = query.order_by(
        DelhiveryOrder.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'skip': skip,
        'limit': limit,
        'orders': [
            {
                'id': o.id,
                'order_number': o.order_number,
                'waybill': o.delhivery_waybill,
                'status': o.delhivery_status,
                'total_amount': o.total_amount,
                'created_at': o.created_at
            }
            for o in orders
        ]
    }


@router.post("/delhivery/orders/{order_id}/cancel")
def cancel_delhivery_order(
    order_id: str,
    reason: str = "Customer requested",
    db: Session = Depends(SessionLocal)
):
    """Cancel a Delhivery order"""
    
    from crm_models import DelhiveryOrder
    import os
    
    order = db.query(DelhiveryOrder).filter(
        DelhiveryOrder.id == order_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if not order.delhivery_waybill:
        raise HTTPException(
            status_code=400,
            detail="No waybill assigned - cannot cancel"
        )
    
    # Cancel via Delhivery API
    api_key = os.getenv('DELHIVERY_API_KEY')
    client = DelhiveryAPIClient(api_key)
    
    result = client.cancel_shipment(order.delhivery_waybill, reason)
    
    if result.get('status') == 'cancelled':
        order.delhivery_status = 'cancelled'
        order.cancellation_reason = reason
        db.commit()
        
        return {'status': 'cancelled', 'order_id': order_id}
    else:
        raise HTTPException(status_code=400, detail=result.get('message'))


@router.post("/delhivery/orders/{order_id}/retrack")
def retrack_order(
    order_id: str,
    db: Session = Depends(SessionLocal)
):
    """Force refresh tracking from Delhivery"""
    
    from crm_models import DelhiveryOrder
    import os
    
    order = db.query(DelhiveryOrder).filter(
        DelhiveryOrder.id == order_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if not order.delhivery_waybill:
        raise HTTPException(status_code=400, detail="No waybill assigned")
    
    # Get latest tracking
    api_key = os.getenv('DELHIVERY_API_KEY')
    client = DelhiveryAPIClient(api_key)
    manager = DelhiveryOrderManager(db, client)
    
    result = manager.update_tracking(order.delhivery_waybill)
    
    if result.get('status') == 'updated':
        return {
            'status': 'updated',
            'waybill': order.delhivery_waybill,
            'delhivery_status': order.delhivery_status
        }
    else:
        raise HTTPException(status_code=400, detail=result.get('message'))


# ============ Tracking (4 endpoints) ============

@router.get("/delhivery/track/{waybill}")
def track_shipment(
    waybill: str,
    db: Session = Depends(SessionLocal)
):
    """
    Get real-time tracking for shipment
    
    Returns:
    - Current status
    - Location
    - Estimated delivery
    - Complete tracking history
    """
    
    from crm_models import DelhiveryOrder, DelhiveryTracking
    import os
    
    # Get order from CRM
    order = db.query(DelhiveryOrder).filter(
        DelhiveryOrder.delhivery_waybill == waybill
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get tracking events from CRM
    events = db.query(DelhiveryTracking).filter(
        DelhiveryTracking.delhivery_order_id == order.id
    ).order_by(DelhiveryTracking.event_timestamp.desc()).all()
    
    return {
        'waybill': waybill,
        'order_number': order.order_number,
        'status': order.delhivery_status,
        'location': events[0].location if events else None,
        'estimated_delivery': order.estimated_delivery,
        'delivered_at': order.delivered_at,
        'tracking_events': [
            {
                'event': e.event_type,
                'timestamp': e.event_timestamp,
                'location': e.location,
                'message': e.status_message
            }
            for e in events
        ]
    }


@router.get("/delhivery/track/order/{order_number}")
def track_by_order_number(
    order_number: str,
    db: Session = Depends(SessionLocal)
):
    """Track shipment by order number (Shopify order)"""
    
    from crm_models import DelhiveryOrder
    
    order = db.query(DelhiveryOrder).filter(
        DelhiveryOrder.order_number == order_number
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if not order.delhivery_waybill:
        return {
            'order_number': order_number,
            'status': 'pending',
            'message': 'Waybill not yet assigned'
        }
    
    # Redirect to waybill tracking
    return {
        'order_number': order_number,
        'waybill': order.delhivery_waybill,
        'tracking_url': order.tracking_url
    }


@router.post("/delhivery/webhook/track")
def receive_tracking_webhook(
    data: dict,
    db: Session = Depends(SessionLocal)
):
    """
    Receive tracking update from Delhivery webhook
    
    Delhivery sends:
    {
        'waybill': '123456',
        'shipment_status': 'delivered',
        'location': 'Delhi',
        'time': '2026-05-22T10:30:00Z'
    }
    """
    
    from crm_models import DelhiveryOrder, DelhiveryTracking
    import uuid
    
    waybill = data.get('waybill')
    
    if not waybill:
        raise HTTPException(status_code=400, detail="Waybill required")
    
    # Find order
    order = db.query(DelhiveryOrder).filter(
        DelhiveryOrder.delhivery_waybill == waybill
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update order status
    status = data.get('shipment_status', 'in_transit').lower()
    order.delhivery_status = status
    order.last_track_at = datetime.utcnow()
    
    # Create tracking event
    if data.get('location'):
        tracking = DelhiveryTracking(
            id=str(uuid.uuid4()),
            delhivery_order_id=order.id,
            event_type=status,
            event_timestamp=datetime.fromisoformat(
                data.get('time', datetime.utcnow().isoformat())
            ) if data.get('time') else datetime.utcnow(),
            location=data.get('location'),
            status_message=data.get('status_message'),
            metadata=data
        )
        
        db.add(tracking)
    
    db.commit()
    
    return {'status': 'received', 'waybill': waybill}


# ============ Analytics (3 endpoints) ============

@router.get("/delhivery/analytics/summary")
def get_delivery_analytics(
    db: Session = Depends(SessionLocal)
):
    """
    Delivery performance overview
    
    Returns:
    - Total orders
    - Delivered %
    - Avg delivery time
    - Failed/in-transit count
    """
    
    import os
    api_key = os.getenv('DELHIVERY_API_KEY')
    client = DelhiveryAPIClient(api_key)
    manager = DelhiveryOrderManager(db, client)
    
    analytics = manager.get_delivery_analytics()
    return analytics


@router.get("/delhivery/analytics/by-status")
def get_orders_by_status(
    db: Session = Depends(SessionLocal)
):
    """Get order count breakdown by status"""
    
    from crm_models import DelhiveryOrder
    
    statuses = [
        'pending', 'picked', 'in_transit',
        'out_for_delivery', 'delivered', 'failed', 'cancelled'
    ]
    
    breakdown = {}
    for status in statuses:
        count = db.query(DelhiveryOrder).filter(
            DelhiveryOrder.delhivery_status == status
        ).count()
        
        breakdown[status] = count
    
    return breakdown


@router.get("/delhivery/health")
def delhivery_health(
    db: Session = Depends(SessionLocal)
):
    """Health check for Delhivery integration"""
    
    try:
        from crm_models import DelhiveryOrder
        
        total = db.query(DelhiveryOrder).count()
        
        return {
            "status": "ok",
            "service": "delhivery",
            "total_orders": total
        }
    
    except Exception as e:
        return {
            "status": "error",
            "service": "delhivery",
            "message": str(e)
        }
