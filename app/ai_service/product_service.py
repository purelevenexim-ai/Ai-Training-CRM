"""
Product Service - Product catalog lookup
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProductService:
    """Product catalog lookups"""
    
    def __init__(self, db: Session):
        """Initialize product service"""
        self.db = db
    
    def get_all_products(self, active_only: bool = True) -> List[dict]:
        """
        Get all products from catalog
        
        Returns list of dicts with:
        - product_id
        - name
        - price_inr
        - stock
        - category
        - status
        """
        try:
            from crm_models import ProductCatalog
            
            query = self.db.query(ProductCatalog)
            
            if active_only:
                query = query.filter(ProductCatalog.status == 'active')
            
            products = query.order_by(ProductCatalog.name).all()
            
            return [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "price_inr": float(p.price_inr),
                    "stock": p.stock,
                    "category": p.category,
                    "status": p.status
                }
                for p in products
            ]
        
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []
    
    def get_product_by_name(self, name: str) -> Optional[dict]:
        """
        Get single product by name
        
        Returns dict or None
        """
        try:
            from crm_models import ProductCatalog
            
            product = self.db.query(ProductCatalog).filter(
                ProductCatalog.name.ilike(f"%{name}%")
            ).first()
            
            if not product:
                return None
            
            return {
                "product_id": product.product_id,
                "name": product.name,
                "price_inr": float(product.price_inr),
                "stock": product.stock,
                "category": product.category,
                "status": product.status
            }
        
        except Exception as e:
            logger.error(f"Error getting product by name: {e}")
            return None
    
    def get_products_by_category(self, category: str) -> List[dict]:
        """
        Get all products in a category
        """
        try:
            from crm_models import ProductCatalog
            
            products = self.db.query(ProductCatalog).filter(
                ProductCatalog.category.ilike(f"%{category}%"),
                ProductCatalog.status == 'active'
            ).order_by(ProductCatalog.name).all()
            
            return [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "price_inr": float(p.price_inr),
                    "stock": p.stock,
                    "category": p.category,
                    "status": p.status
                }
                for p in products
            ]
        
        except Exception as e:
            logger.error(f"Error getting products by category: {e}")
            return []
    
    def get_in_stock_products(self) -> List[dict]:
        """
        Get all products currently in stock
        """
        try:
            from crm_models import ProductCatalog
            
            products = self.db.query(ProductCatalog).filter(
                ProductCatalog.stock > 0,
                ProductCatalog.status == 'active'
            ).order_by(ProductCatalog.name).all()
            
            return [
                {
                    "product_id": p.product_id,
                    "name": p.name,
                    "price_inr": float(p.price_inr),
                    "stock": p.stock,
                    "category": p.category,
                    "status": p.status
                }
                for p in products
            ]
        
        except Exception as e:
            logger.error(f"Error getting in-stock products: {e}")
            return []
