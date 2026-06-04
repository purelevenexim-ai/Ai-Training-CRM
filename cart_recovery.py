"""
Cart Recovery & Abandonment Management
Tracks abandoned carts and manages recovery email campaigns
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func


class CartRecoveryStatus(str, Enum):
    """Cart recovery status workflow"""
    PENDING = "pending"                # Cart abandoned, awaiting recovery
    EMAIL_SENT = "email_sent"          # Recovery email sent
    RECOVERED = "recovered"            # Cart recovered/purchased
    EXPIRED = "expired"                # Recovery window passed
    LOST = "lost"                      # No recovery attempt


class CartRecoveryPhase(str, Enum):
    """Recovery email phases"""
    IMMEDIATE = "immediate"             # 1 hour after abandon
    URGENT = "urgent"                   # 24 hours after abandon
    LAST_CHANCE = "last_chance"         # 72 hours after abandon


class CartAbandonmentTracker:
    """Track and manage abandoned shopping carts"""
    
    def __init__(self, db: Session):
        """Initialize tracker"""
        self.db = db
        self.recovery_window_hours = 72  # 3-day recovery window
    
    def track_cart_abandonment(self, 
                              customer_email: str,
                              customer_id: Optional[str] = None,
                              cart_token: Optional[str] = None,
                              cart_value: Optional[float] = None,
                              items_count: int = 0,
                              cart_items: Optional[List[Dict]] = None,
                              reason: str = "checkout") -> Dict:
        """
        Record new cart abandonment event
        
        Args:
            customer_email: Customer email address
            customer_id: Customer ID (may be null for guests)
            cart_token: Shopify cart token
            cart_value: Total cart value
            items_count: Number of items in cart
            cart_items: List of items [{sku, product_id, name, price, qty}]
            reason: Why cart was abandoned (checkout, shipping, payment, etc)
        
        Returns:
            {
                cart_abandonment_id: str,
                status: 'pending',
                cart_value: float,
                recovery_scheduled: bool
            }
        """
        from crm_models import CartAbandonment, Customer
        import uuid
        
        # Find or create customer
        customer = None
        if customer_id:
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
        elif customer_email:
            customer = self.db.query(Customer).filter(
                Customer.email.ilike(customer_email)
            ).first()
        
        # Create abandonment record
        abandonment = CartAbandonment(
            id=str(uuid.uuid4()),
            customer_id=customer.id if customer else None,
            cart_token=cart_token,
            cart_value=cart_value or 0.0,
            items_count=items_count,
            cart_items=cart_items,
            abandoned_at=datetime.utcnow(),
            reason=reason,
            recovery_status=CartRecoveryStatus.PENDING.value
        )
        
        self.db.add(abandonment)
        self.db.commit()
        
        return {
            'cart_abandonment_id': abandonment.id,
            'status': 'pending',
            'cart_value': cart_value or 0.0,
            'recovery_scheduled': True
        }
    
    def get_recoverable_carts(self, 
                             phase: CartRecoveryPhase = None,
                             limit: int = 100) -> List[Dict]:
        """
        Get carts ready for recovery in specific phase
        
        Args:
            phase: Recovery phase (immediate=1h, urgent=24h, last_chance=72h)
            limit: Max carts to return
        
        Returns:
            List of recoverable carts with customer info
        """
        from crm_models import CartAbandonment
        
        now = datetime.utcnow()
        
        if phase == CartRecoveryPhase.IMMEDIATE:
            # 1 hour after abandon
            cutoff = now - timedelta(hours=1, minutes=5)
            min_cutoff = now - timedelta(hours=1, minutes=-5)
        elif phase == CartRecoveryPhase.URGENT:
            # 24 hours after abandon
            cutoff = now - timedelta(hours=24, minutes=5)
            min_cutoff = now - timedelta(hours=24, minutes=-5)
        elif phase == CartRecoveryPhase.LAST_CHANCE:
            # 72 hours after abandon
            cutoff = now - timedelta(hours=72, minutes=5)
            min_cutoff = now - timedelta(hours=72, minutes=-5)
        else:
            # All pending
            cutoff = now - timedelta(hours=self.recovery_window_hours)
            min_cutoff = None
        
        query = self.db.query(CartAbandonment).filter(
            CartAbandonment.recovery_status == CartRecoveryStatus.PENDING.value,
            CartAbandonment.abandoned_at <= cutoff,
        )
        
        if min_cutoff:
            query = query.filter(CartAbandonment.abandoned_at >= min_cutoff)
        
        carts = query.order_by(
            CartAbandonment.cart_value.desc()
        ).limit(limit).all()
        
        return [
            {
                'cart_abandonment_id': c.id,
                'customer_id': c.customer_id,
                'cart_value': c.cart_value,
                'items_count': c.items_count,
                'abandoned_at': c.abandoned_at,
                'hours_since_abandon': (now - c.abandoned_at).total_seconds() / 3600,
                'recovery_attempts': c.recovery_attempts
            }
            for c in carts
        ]
    
    def mark_recovered(self, 
                      cart_abandonment_id: str,
                      recovered_value: Optional[float] = None,
                      recovery_campaign_id: Optional[str] = None) -> Dict:
        """
        Mark cart as recovered (customer completed purchase)
        
        Args:
            cart_abandonment_id: Cart ID
            recovered_value: Value of items actually purchased
            recovery_campaign_id: Which recovery campaign led to recovery
        
        Returns:
            {
                status: 'recovered',
                recovered_value: float,
                recovery_time: str
            }
        """
        from crm_models import CartAbandonment
        
        cart = self.db.query(CartAbandonment).filter(
            CartAbandonment.id == cart_abandonment_id
        ).first()
        
        if not cart:
            return {'error': 'Cart not found', 'status': 'error'}
        
        now = datetime.utcnow()
        time_to_recovery = (now - cart.abandoned_at).total_seconds() / 3600
        
        cart.recovery_status = CartRecoveryStatus.RECOVERED.value
        cart.recovered_value = recovered_value or cart.cart_value
        cart.recovered_at = now
        cart.time_to_recovery_hours = int(time_to_recovery)
        
        if recovery_campaign_id:
            cart.last_recovery_campaign_id = recovery_campaign_id
            cart.last_recovery_at = now
        
        self.db.commit()
        
        return {
            'status': 'recovered',
            'recovered_value': recovered_value or cart.cart_value,
            'recovery_time_hours': int(time_to_recovery),
            'time_to_recovery_formatted': f"{int(time_to_recovery)}h {int((time_to_recovery % 1) * 60)}m"
        }
    
    def mark_expired(self, cart_abandonment_id: str) -> Dict:
        """Mark cart as expired (recovery window passed)"""
        from crm_models import CartAbandonment
        
        cart = self.db.query(CartAbandonment).filter(
            CartAbandonment.id == cart_abandonment_id
        ).first()
        
        if not cart:
            return {'error': 'Cart not found'}
        
        cart.recovery_status = CartRecoveryStatus.EXPIRED.value
        self.db.commit()
        
        return {'status': 'expired'}
    
    def get_recovery_analytics(self) -> Dict:
        """
        Get cart recovery analytics
        
        Returns:
        {
            total_abandonments: int,
            pending: int,
            recovered: int,
            recovery_rate: float,
            total_value_lost: float,
            total_value_recovered: float,
            avg_recovery_time_hours: float
        }
        """
        from crm_models import CartAbandonment
        
        total = self.db.query(CartAbandonment).count()
        
        if total == 0:
            return {
                'total_abandonments': 0,
                'message': 'No cart abandonment data'
            }
        
        pending = self.db.query(CartAbandonment).filter(
            CartAbandonment.recovery_status == CartRecoveryStatus.PENDING.value
        ).count()
        
        recovered = self.db.query(CartAbandonment).filter(
            CartAbandonment.recovery_status == CartRecoveryStatus.RECOVERED.value
        ).count()
        
        total_value_lost = self.db.query(
            func.sum(CartAbandonment.cart_value)
        ).filter(
            CartAbandonment.recovery_status != CartRecoveryStatus.RECOVERED.value
        ).scalar() or 0.0
        
        total_value_recovered = self.db.query(
            func.sum(CartAbandonment.recovered_value)
        ).filter(
            CartAbandonment.recovery_status == CartRecoveryStatus.RECOVERED.value
        ).scalar() or 0.0
        
        avg_recovery_time = self.db.query(
            func.avg(CartAbandonment.time_to_recovery_hours)
        ).filter(
            CartAbandonment.recovery_status == CartRecoveryStatus.RECOVERED.value
        ).scalar()
        
        recovery_rate = (recovered / total * 100) if total > 0 else 0
        
        return {
            'total_abandonments': total,
            'pending_count': pending,
            'recovered_count': recovered,
            'recovery_rate': round(recovery_rate, 2),
            'total_value_abandoned': round(total_value_lost, 2),
            'total_value_recovered': round(total_value_recovered, 2),
            'avg_recovery_time_hours': round(avg_recovery_time or 0, 2)
        }


class CartRecoveryEmailManager:
    """Manage cart recovery email campaigns"""
    
    def __init__(self, db: Session):
        """Initialize manager"""
        self.db = db
    
    def get_template_by_phase(self, phase: CartRecoveryPhase) -> Optional[Dict]:
        """
        Get recovery email template for specific phase
        
        Args:
            phase: Recovery phase (immediate, urgent, last_chance)
        
        Returns:
            Template details or None if not found
        """
        from crm_models import CartRecoveryTemplate
        
        # Map phase to template trigger time
        trigger_hours = {
            CartRecoveryPhase.IMMEDIATE: 1,
            CartRecoveryPhase.URGENT: 24,
            CartRecoveryPhase.LAST_CHANCE: 72
        }
        
        template = self.db.query(CartRecoveryTemplate).filter(
            CartRecoveryTemplate.trigger_hours_after_abandon == trigger_hours[phase],
            CartRecoveryTemplate.is_active == True
        ).first()
        
        if not template:
            return None
        
        return {
            'id': template.id,
            'subject': template.subject,
            'template_html': template.template_html,
            'cta_text': template.cta_text,
            'discount_code': template.discount_code,
            'phase': phase.value
        }
    
    def create_recovery_campaign(self,
                                cart_abandonment_id: str,
                                customer_email: str,
                                template_id: str) -> Dict:
        """
        Create new recovery email campaign
        
        Args:
            cart_abandonment_id: Cart to recover
            customer_email: Recipient email
            template_id: Email template to use
        
        Returns:
            Campaign details with ID for tracking
        """
        from crm_models import CartRecoveryCampaign
        import uuid
        
        campaign = CartRecoveryCampaign(
            id=str(uuid.uuid4()),
            cart_abandonment_id=cart_abandonment_id,
            template_id=template_id,
            customer_email=customer_email,
            status='pending',
            utm_campaign=f"cart_recovery_{cart_abandonment_id[:8]}"
        )
        
        self.db.add(campaign)
        self.db.commit()
        
        return {
            'campaign_id': campaign.id,
            'status': 'pending',
            'customer_email': customer_email
        }
    
    def record_email_sent(self, campaign_id: str) -> Dict:
        """Record that recovery email was sent"""
        from crm_models import CartRecoveryCampaign
        
        campaign = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.id == campaign_id
        ).first()
        
        if not campaign:
            return {'error': 'Campaign not found'}
        
        campaign.status = 'sent'
        campaign.email_sent_at = datetime.utcnow()
        self.db.commit()
        
        return {'status': 'sent'}
    
    def record_email_opened(self, campaign_id: str) -> Dict:
        """Record that recovery email was opened"""
        from crm_models import CartRecoveryCampaign, CartAbandonment
        
        campaign = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.id == campaign_id
        ).first()
        
        if not campaign:
            return {'error': 'Campaign not found'}
        
        campaign.status = 'opened'
        campaign.email_opened_at = datetime.utcnow()
        
        # Update abandonment email open count
        cart = self.db.query(CartAbandonment).filter(
            CartAbandonment.id == campaign.cart_abandonment_id
        ).first()
        
        if cart:
            cart.recovery_emails_clicked = (cart.recovery_emails_clicked or 0) + 1
        
        self.db.commit()
        
        return {'status': 'opened'}
    
    def record_email_clicked(self, campaign_id: str) -> Dict:
        """Record that recovery email link was clicked"""
        from crm_models import CartRecoveryCampaign, CartAbandonment
        
        campaign = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.id == campaign_id
        ).first()
        
        if not campaign:
            return {'error': 'Campaign not found'}
        
        campaign.status = 'clicked'
        campaign.email_clicked_at = datetime.utcnow()
        
        # Update cart stats
        cart = self.db.query(CartAbandonment).filter(
            CartAbandonment.id == campaign.cart_abandonment_id
        ).first()
        
        if cart:
            cart.recovery_emails_clicked = (cart.recovery_emails_clicked or 0) + 1
            if cart.recovery_emails_sent > 0:
                cart.recovery_email_click_rate = (cart.recovery_emails_clicked / cart.recovery_emails_sent) * 100
        
        self.db.commit()
        
        return {'status': 'clicked'}


class CartRecoveryMetrics:
    """Calculate cart recovery performance metrics"""
    
    def __init__(self, db: Session):
        """Initialize metrics calculator"""
        self.db = db
    
    def get_funnel_metrics(self) -> Dict:
        """
        Get recovery email funnel metrics
        
        Shows: abandon → sent → opened → clicked → converted
        """
        from crm_models import CartRecoveryCampaign
        
        # Get campaign status counts
        sent = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.status.in_(['sent', 'delivered', 'opened', 'clicked', 'converted'])
        ).count()
        
        delivered = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.status.in_(['delivered', 'opened', 'clicked', 'converted'])
        ).count()
        
        opened = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.status.in_(['opened', 'clicked', 'converted'])
        ).count()
        
        clicked = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.status.in_(['clicked', 'converted'])
        ).count()
        
        converted = self.db.query(CartRecoveryCampaign).filter(
            CartRecoveryCampaign.recovered == True
        ).count()
        
        return {
            'emails_sent': sent,
            'emails_delivered': delivered,
            'emails_opened': opened,
            'emails_clicked': clicked,
            'conversions': converted,
            'open_rate': round(opened / sent * 100, 2) if sent > 0 else 0,
            'click_rate': round(clicked / sent * 100, 2) if sent > 0 else 0,
            'conversion_rate': round(converted / sent * 100, 2) if sent > 0 else 0
        }


# Example usage
if __name__ == '__main__':
    print("Cart recovery module loaded")
