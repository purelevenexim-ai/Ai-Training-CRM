"""
Customer 360 Profile & Timeline API Endpoints
Unified customer view with profile, stats, timeline, and segments
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List, Any, Dict
import logging

try:
    from database import SessionLocal
    from crm_models import Customer, Order, Event, MessageLog
    from auth import verify_access_token
except ImportError:
    from app.database import SessionLocal
    from app.crm_models import Customer, Order, Event, MessageLog
    from app.auth import verify_access_token

logger = logging.getLogger("pureleven.customer360")

router = APIRouter(prefix="/api/crm", tags=["customer360"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token from Authorization header"""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return verify_access_token(parts[1])
    return None

# ============= PYDANTIC SCHEMAS =============

class ContactResponse(BaseModel):
    """Contact / Customer response"""
    id: str
    email: Optional[str]
    phone: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: Optional[str]
    shopify_customer_id: Optional[str]

    class Config:
        from_attributes = True


class ContactsListResponse(BaseModel):
    """List of contacts response"""
    total: int
    limit: int
    offset: int
    contacts: List[ContactResponse]

    class Config:
        from_attributes = True


# ============= ENDPOINTS =============

@router.get("/contacts", response_model=ContactsListResponse, tags=["people"])
def get_contacts(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    admin_secret: Optional[str] = Query(None),
):
    """
    Get paginated list of contacts/customers
    
    - **limit**: Results per page (1-500, default 50)
    - **offset**: Pagination offset
    - **search**: Filter by email/phone/name
    - **admin_secret**: Admin authentication (temporary, will use JWT later)
    """
    try:
        # Admin secret verification (temporary)
        if admin_secret != "basil":
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Build query
        query = db.query(Customer)
        
        # Apply search filter
        if search:
            query = query.filter(
                (Customer.email.ilike(f"%{search}%")) |
                (Customer.phone.ilike(f"%{search}%")) |
                (Customer.first_name.ilike(f"%{search}%")) |
                (Customer.last_name.ilike(f"%{search}%"))
            )
        
        # Get total count
        total = query.count()
        
        # Get paginated customers
        customers = query.order_by(desc(Customer.created_at)).limit(limit).offset(offset).all()
        
        contacts = [
            ContactResponse(
                id=c.id,
                email=c.email,
                phone=c.phone,
                first_name=c.first_name,
                last_name=c.last_name,
                created_at=c.created_at.isoformat() if c.created_at else None,
                shopify_customer_id=c.shopify_customer_id,
            )
            for c in customers
        ]
        
        return ContactsListResponse(
            total=total,
            limit=limit,
            offset=offset,
            contacts=contacts
        )
    except Exception as e:
        logger.error(f"Error fetching contacts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{customer_id}", tags=["people"])
def get_customer_profile(
    customer_id: str,
    db: Session = Depends(get_db),
    admin_secret: Optional[str] = Query(None),
):
    """
    Get complete Customer 360 profile
    Includes: profile, stats, health, latest order
    
    - **customer_id**: Unique customer identifier
    - **admin_secret**: Admin authentication
    """
    try:
        # Admin secret verification (temporary)
        if admin_secret != "basil":
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Get customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Calculate stats
        orders = db.query(Order).filter(Order.customer_id == customer_id).all()
        total_revenue = sum(o.total_amount or 0 for o in orders)
        order_count = len(orders)
        latest_order = max(orders, key=lambda o: o.created_at or o.id) if orders else None
        
        # Get recent activity count
        recent_events = db.query(func.count(Event.id)).filter(
            Event.customer_id == customer_id
        ).scalar() or 0
        
        # Get messages count
        messages_count = db.query(func.count(MessageLog.id)).filter(
            MessageLog.customer_id == customer_id
        ).scalar() or 0
        
        # Determine health status
        if latest_order is None:
            health_status = "inactive"
        else:
            from datetime import datetime, timedelta
            order_created = latest_order.created_at or datetime.utcnow()
            days_since = (datetime.utcnow() - order_created).days
            health_status = "active" if days_since <= 90 else "lapsed"
        
        return {
            "customer": {
                "id": customer.id,
                "email": customer.email,
                "phone": customer.phone,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
                "shopify_customer_id": customer.shopify_customer_id,
            },
            "stats": {
                "total_revenue": round(total_revenue, 2),
                "order_count": order_count,
                "last_order_date": (latest_order.created_at.isoformat() if latest_order and latest_order.created_at else None),
            },
            "latest_order": (
                {
                    "id": latest_order.id,
                    "shopify_order_id": latest_order.shopify_order_id,
                    "date": latest_order.created_at.isoformat() if latest_order.created_at else None,
                    "amount": latest_order.total_amount,
                    "status": latest_order.status,
                }
                if latest_order
                else None
            ),
            "recent_activity_count": recent_events,
            "messages_count": messages_count,
            "customer_health": {
                "status": health_status,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching customer 360 for {customer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers", response_model=ContactsListResponse, tags=["people"])
def get_customers_alias(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    admin_secret: Optional[str] = Query(None),
):
    """
    Alias for /api/crm/contacts
    Get paginated list of customers
    """
    return get_contacts(
        db=db,
        limit=limit,
        offset=offset,
        search=search,
        admin_secret=admin_secret,
    )
