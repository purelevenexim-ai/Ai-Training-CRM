"""
Feature Toggle Management - Control Wave features on/off
"""

import logging
from typing import List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class FeatureToggleService:
    """Manage feature flags and toggles"""
    
    def __init__(self, db: Session):
        """Initialize feature toggle service"""
        self.db = db
    
    def initialize_default_features(self):
        """
        Create default feature flags
        Called on first run
        """
        try:
            from crm_models import FeatureToggle
            
            default_features = [
                {
                    "feature_key": "wave_0_2_review_queue",
                    "feature_name": "Wave 0.2 - Daily Review Queue",
                    "description": "Flag low-confidence messages for human review",
                    "enabled": True,
                    "category": "Wave 0.2"
                },
                {
                    "feature_key": "wave_0_2_learning_engine",
                    "feature_name": "Wave 0.2 - Learning Engine",
                    "description": "Improve rule engine accuracy from corrections",
                    "enabled": True,
                    "category": "Wave 0.2"
                },
                {
                    "feature_key": "wave_0_2_advanced_scoring",
                    "feature_name": "Wave 0.2 - Advanced Scoring",
                    "description": "Track response quality and churn risk scores",
                    "enabled": True,
                    "category": "Wave 0.2"
                },
                {
                    "feature_key": "wave_0_2_kb_organization",
                    "feature_name": "Wave 0.2 - KB Auto-Organization",
                    "description": "Track KB performance and suggest archiving",
                    "enabled": True,
                    "category": "Wave 0.2"
                },
                {
                    "feature_key": "wave_1_product_affinity",
                    "feature_name": "Wave 1 - Product Affinity",
                    "description": "Recommend complementary products",
                    "enabled": False,
                    "category": "Wave 1"
                },
            ]
            
            for feature in default_features:
                existing = self.db.query(FeatureToggle).filter(
                    FeatureToggle.feature_key == feature['feature_key']
                ).first()
                
                if not existing:
                    from uuid import uuid4
                    new_feature = FeatureToggle(
                        toggle_id=str(uuid4()),
                        feature_key=feature['feature_key'],
                        feature_name=feature['feature_name'],
                        description=feature['description'],
                        enabled=feature['enabled'],
                        category=feature['category'],
                        created_at=datetime.utcnow()
                    )
                    self.db.add(new_feature)
            
            self.db.commit()
            logger.info("Initialized default feature toggles")
        
        except Exception as e:
            logger.error(f"Error initializing features: {e}")
            self.db.rollback()
    
    def is_feature_enabled(self, feature_key: str) -> bool:
        """
        Check if a feature is enabled
        
        Used by API endpoints as a gate
        """
        try:
            from crm_models import FeatureToggle
            
            feature = self.db.query(FeatureToggle).filter(
                FeatureToggle.feature_key == feature_key
            ).first()
            
            if not feature:
                logger.warning(f"Feature not found: {feature_key}")
                return False
            
            return feature.enabled
        
        except Exception as e:
            logger.error(f"Error checking feature {feature_key}: {e}")
            return False
    
    def toggle_feature(self, feature_key: str, enabled: bool) -> dict:
        """
        Enable or disable a feature
        """
        try:
            from crm_models import FeatureToggle
            
            feature = self.db.query(FeatureToggle).filter(
                FeatureToggle.feature_key == feature_key
            ).first()
            
            if not feature:
                return {"toggled": False, "error": "Feature not found"}
            
            feature.enabled = enabled
            feature.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            status = "enabled" if enabled else "disabled"
            logger.info(f"Feature {feature_key} {status}")
            
            return {
                "toggled": True,
                "feature_key": feature_key,
                "feature_name": feature.feature_name,
                "enabled": enabled
            }
        
        except Exception as e:
            logger.error(f"Error toggling feature {feature_key}: {e}")
            self.db.rollback()
            return {"toggled": False, "error": str(e)}
    
    def get_all_features(self) -> List[dict]:
        """
        Get all features with their current status
        """
        try:
            from crm_models import FeatureToggle
            
            features = self.db.query(FeatureToggle).order_by(
                FeatureToggle.category,
                FeatureToggle.feature_name
            ).all()
            
            return [
                {
                    "feature_key": f.feature_key,
                    "feature_name": f.feature_name,
                    "description": f.description,
                    "enabled": f.enabled,
                    "category": f.category,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "updated_at": f.updated_at.isoformat() if f.updated_at else None
                }
                for f in features
            ]
        
        except Exception as e:
            logger.error(f"Error getting features: {e}")
            return []
    
    def get_features_by_category(self, category: str) -> List[dict]:
        """
        Get features in a specific category
        """
        try:
            from crm_models import FeatureToggle
            
            features = self.db.query(FeatureToggle).filter(
                FeatureToggle.category == category
            ).all()
            
            return [
                {
                    "feature_key": f.feature_key,
                    "feature_name": f.feature_name,
                    "description": f.description,
                    "enabled": f.enabled,
                    "category": f.category
                }
                for f in features
            ]
        
        except Exception as e:
            logger.error(f"Error getting features by category: {e}")
            return []
    
    def get_feature_status_summary(self) -> dict:
        """
        Get summary of all feature status
        """
        try:
            from crm_models import FeatureToggle
            
            all_features = self.db.query(FeatureToggle).all()
            
            by_category = {}
            for feature in all_features:
                if feature.category not in by_category:
                    by_category[feature.category] = {
                        "total": 0,
                        "enabled": 0,
                        "disabled": 0,
                        "features": []
                    }
                
                by_category[feature.category]["total"] += 1
                if feature.enabled:
                    by_category[feature.category]["enabled"] += 1
                else:
                    by_category[feature.category]["disabled"] += 1
                
                by_category[feature.category]["features"].append({
                    "name": feature.feature_name,
                    "enabled": feature.enabled
                })
            
            return by_category
        
        except Exception as e:
            logger.error(f"Error getting feature summary: {e}")
            return {}
