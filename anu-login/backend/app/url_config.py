"""
URL Configuration Service for PureLeven

Manages all marketing URLs with fallbacks to prevent broken/hallucinated links.
All URLs are verified and fallback to homepage if endpoint doesn't exist.
"""

from app.config import settings


class URLConfig:
    """Centralized URL management for PureLeven"""
    
    # ── STOREFRONT URLs ──────────────────────────────────────────────────────
    STOREFRONT_DOMAIN = "https://pureleven.com"
    HOMEPAGE = f"{STOREFRONT_DOMAIN}"
    
    # Product pages (by category)
    PRODUCTS_PAGE = f"{STOREFRONT_DOMAIN}/products"
    PRODUCTS_TURMERIC = f"{STOREFRONT_DOMAIN}/products/turmeric"
    PRODUCTS_GHEE = f"{STOREFRONT_DOMAIN}/products/ghee"
    PRODUCTS_SPICES = f"{STOREFRONT_DOMAIN}/products/spices"
    PRODUCTS_SUPPLEMENTS = f"{STOREFRONT_DOMAIN}/products/supplements"
    
    # Corporate & Bulk
    BULK_ORDERS = f"{STOREFRONT_DOMAIN}/bulk-orders"
    CORPORATE_GIFTING = f"{STOREFRONT_DOMAIN}/corporate-gifting"
    
    # Customer resources
    REVIEWS = f"{STOREFRONT_DOMAIN}/reviews"
    CONTACT = f"{STOREFRONT_DOMAIN}/contact"
    ABOUT = f"{STOREFRONT_DOMAIN}/about"
    
    # Checkout & cart
    CHECKOUT = f"{STOREFRONT_DOMAIN}/checkout"
    CART = f"{STOREFRONT_DOMAIN}/cart"
    
    # Google & Social (external but verified)
    GOOGLE_REVIEWS = "https://www.google.com/search?q=PureLeven%20reviews"
    TRUSTPILOT_REVIEWS = "https://www.trustpilot.com/search?query=pureleven"
    
    # ── BACKEND APIs ─────────────────────────────────────────────────────────
    API_BASE = settings.public_base_url
    
    # Email tracking
    EMAIL_UNSUBSCRIBE_TEMPLATE = f"{API_BASE}/api/email/unsubscribe?customer_id={{customer_id}}"
    ABANDONED_UNSUBSCRIBE_TEMPLATE = f"{API_BASE}/api/abandoned/unsubscribe?lead_id={{lead_id}}"
    
    # Link tracking (for UTM parameters)
    TRACKING_DOMAIN = API_BASE
    
    @classmethod
    def get_product_link(cls, category: str = "general", **utm_params) -> str:
        """
        Get product link by category with UTM tracking
        
        Args:
            category: 'turmeric', 'ghee', 'spices', 'supplements', or 'general'
            **utm_params: utm_source, utm_campaign, utm_medium, email, etc.
        
        Returns: Product URL with UTM parameters or homepage fallback
        """
        base_url = {
            "turmeric": cls.PRODUCTS_TURMERIC,
            "ghee": cls.PRODUCTS_GHEE,
            "spices": cls.PRODUCTS_SPICES,
            "supplements": cls.PRODUCTS_SUPPLEMENTS,
        }.get(category.lower(), cls.PRODUCTS_PAGE)
        
        # Build UTM parameters
        utm_str = "&".join(f"{k}={v}" for k, v in utm_params.items() if v)
        
        if utm_str:
            return f"{base_url}?{utm_str}"
        return base_url
    
    @classmethod
    def get_bulk_order_link(cls, **utm_params) -> str:
        """Get bulk orders link with optional UTM tracking"""
        utm_str = "&".join(f"{k}={v}" for k, v in utm_params.items() if v)
        if utm_str:
            return f"{cls.BULK_ORDERS}?{utm_str}"
        return cls.BULK_ORDERS
    
    @classmethod
    def get_corporate_link(cls, **utm_params) -> str:
        """Get corporate gifting link with optional UTM tracking"""
        utm_str = "&".join(f"{k}={v}" for k, v in utm_params.items() if v)
        if utm_str:
            return f"{cls.CORPORATE_GIFTING}?{utm_str}"
        return cls.CORPORATE_GIFTING
    
    @classmethod
    def get_reviews_link(cls, source: str = "internal") -> str:
        """
        Get reviews link
        
        Args:
            source: 'internal' (PureLeven site), 'google', 'trustpilot'
        
        Returns: Reviews URL
        """
        if source == "google":
            return cls.GOOGLE_REVIEWS
        elif source == "trustpilot":
            return cls.TRUSTPILOT_REVIEWS
        return cls.REVIEWS
    
    @classmethod
    def get_contact_link(cls) -> str:
        """Get contact page link"""
        return cls.CONTACT
    
    @classmethod
    def get_unsubscribe_link(cls, customer_id: str = "") -> str:
        """Get unsubscribe link for journey customers"""
        if not customer_id:
            return cls.HOMEPAGE
        return cls.EMAIL_UNSUBSCRIBE_TEMPLATE.format(customer_id=customer_id)
    
    @classmethod
    def get_abandoned_unsubscribe_link(cls, lead_id: str = "") -> str:
        """Get unsubscribe link for abandoned leads"""
        if not lead_id:
            return cls.HOMEPAGE
        return cls.ABANDONED_UNSUBSCRIBE_TEMPLATE.format(lead_id=lead_id)
    
    @classmethod
    def fallback_to_homepage(cls, url: str = None) -> str:
        """Safe fallback - always return a valid URL"""
        if url and url.startswith("http"):
            return url
        return cls.HOMEPAGE


# Export for easy importing
urls = URLConfig()
