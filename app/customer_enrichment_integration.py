"""
Customer Enrichment Integration
LinkedIn profiles, company data, intent signals
"""

import requests
import hashlib
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from app.crm_models import (
    Customer, CustomerEnrichment, CompanyData, IntentSignal
)


class EnrichmentStatus(str, Enum):
    """Enrichment status"""
    PENDING = "pending"
    ENRICHING = "enriching"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class DataSource(str, Enum):
    """Data enrichment sources"""
    LINKEDIN = "linkedin"
    CLEARBIT = "clearbit"
    HUNTER = "hunter"
    INTERNAL = "internal"


class IntentSignalType(str, Enum):
    """Intent signal types"""
    WEBSITE_VISIT = "website_visit"
    PRODUCT_PAGE_VISIT = "product_page_visit"
    PRICING_PAGE_VISIT = "pricing_page_visit"
    WHITEPAPER_DOWNLOAD = "whitepaper_download"
    DEMO_REQUEST = "demo_request"
    HIGH_ENGAGEMENT = "high_engagement"
    CONTENT_CONSUMPTION = "content_consumption"
    COMPETITOR_SIGNAL = "competitor_signal"


class LinkedInProfileClient:
    """LinkedIn profile enrichment"""
    
    def __init__(self, api_key: str):
        """Initialize LinkedIn client"""
        self.api_key = api_key
        self.api_url = "https://api.linkedin.com/v2"
    
    def search_profile(
        self,
        first_name: str,
        last_name: str,
        email: str,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for LinkedIn profile
        Returns: {found, profile_id, profile_url, headline, current_company}
        """
        try:
            # For this implementation, we'll simulate API response
            # In production, use actual LinkedIn API or clearbit
            
            # Create signature for caching
            search_sig = hashlib.sha256(
                f"{first_name}{last_name}{email}".encode()
            ).hexdigest()
            
            return {
                "found": True,
                "profile_id": search_sig[:20],
                "profile_url": f"https://linkedin.com/in/{search_sig[:15]}",
                "headline": "Professional",
                "current_company": company or "Unknown",
                "location": "India",
                "data_source": DataSource.LINKEDIN.value
            }
        
        except Exception as e:
            return {
                "found": False,
                "error": str(e)
            }


class CompanyEnrichmentClient:
    """Company data enrichment (Clearbit, Hunter, etc)"""
    
    def __init__(self, clearbit_api_key: str, hunter_api_key: str):
        """Initialize company enrichment client"""
        self.clearbit_api_key = clearbit_api_key
        self.hunter_api_key = hunter_api_key
    
    def enrich_company_by_domain(self, domain: str) -> Dict[str, Any]:
        """
        Enrich company data by domain
        Returns: {company_name, industry, employees, revenue, founded_year}
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.clearbit_api_key}"
            }
            
            response = requests.get(
                f"https://company-stream.clearbit.com/v2/companies/find?domain={domain}",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                company = data.get("company", {})
                
                return {
                    "found": True,
                    "company_name": company.get("name"),
                    "industry": company.get("category", {}).get("industry"),
                    "employees": company.get("metrics", {}).get("employees"),
                    "revenue": company.get("metrics", {}).get("annualRevenue"),
                    "founded_year": company.get("founded", {}).get("year"),
                    "website": company.get("site", {}).get("domain"),
                    "location": company.get("location", {}).get("country"),
                    "data_source": DataSource.CLEARBIT.value
                }
            
            return {"found": False, "error": "Company not found"}
        
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def enrich_company_by_name(self, company_name: str) -> Dict[str, Any]:
        """Enrich company by name"""
        # Simplified implementation
        return {
            "found": True,
            "company_name": company_name,
            "industry": "Technology",
            "employees": "Unknown",
            "revenue": "Unknown",
            "founded_year": None,
            "data_source": DataSource.CLEARBIT.value
        }
    
    def verify_email(self, email: str, domain: str) -> Dict[str, Any]:
        """
        Verify email validity via Hunter
        Returns: {is_valid, confidence, email, domain}
        """
        try:
            params = {
                "email": email,
                "domain": domain
            }
            headers = {
                "Authorization": f"Bearer {self.hunter_api_key}"
            }
            
            response = requests.get(
                "https://api.hunter.io/v2/email-verifier",
                params=params,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {})
                
                return {
                    "is_valid": result.get("status") == "valid",
                    "confidence": result.get("confidence"),
                    "email": email,
                    "domain": domain,
                    "data_source": DataSource.HUNTER.value
                }
            
            return {"is_valid": None, "error": "Verification failed"}
        
        except Exception as e:
            return {"is_valid": None, "error": str(e)}


class IntentSignalDetector:
    """Detects buyer intent signals"""
    
    @staticmethod
    def analyze_engagement(db: Session, customer_id: str) -> List[Dict[str, Any]]:
        """
        Analyze customer engagement to detect intent signals
        Returns: List of {signal_type, score, source, timestamp}
        """
        signals = []
        
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return signals
        
        # Signal 1: Recent website visits (check cart/offline conversion activity)
        cart_activities = 0  # Would query from cart_recovery table
        if cart_activities > 0:
            signals.append({
                "signal_type": IntentSignalType.HIGH_ENGAGEMENT.value,
                "score": 0.85,
                "source": "cart_activity",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Signal 2: Propensity scoring
        if customer.propensity_score and customer.propensity_score > 0.7:
            signals.append({
                "signal_type": IntentSignalType.CONTENT_CONSUMPTION.value,
                "score": customer.propensity_score,
                "source": "propensity_model",
                "timestamp": customer.updated_at.isoformat()
            })
        
        # Signal 3: Purchase history
        if customer.has_purchased:
            signals.append({
                "signal_type": IntentSignalType.WEBSITE_VISIT.value,
                "score": 0.9,
                "source": "purchase_history",
                "timestamp": customer.updated_at.isoformat()
            })
        
        return signals
    
    @staticmethod
    def detect_competitor_signals(company_name: str) -> Optional[Dict[str, Any]]:
        """
        Detect if company uses competitor products
        This would integrate with third-party APIs like G2, Stackshare, etc.
        """
        # Simplified mock implementation
        competitors = ["Salesforce", "HubSpot", "Marketo", "Pipedrive"]
        
        for competitor in competitors:
            if competitor.lower() in company_name.lower():
                return {
                    "signal_type": IntentSignalType.COMPETITOR_SIGNAL.value,
                    "competitor": competitor,
                    "score": 0.8,
                    "source": "company_data"
                }
        
        return None


class CustomerEnrichmentManager:
    """Manages customer data enrichment"""
    
    @staticmethod
    def create_enrichment_job(
        db: Session,
        customer_id: str,
        enrichment_type: str
    ) -> CustomerEnrichment:
        """Create enrichment job"""
        enrichment = CustomerEnrichment(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            enrichment_type=enrichment_type,
            status=EnrichmentStatus.PENDING.value,
            enriched_fields=[],
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(enrichment)
        db.commit()
        return enrichment
    
    @staticmethod
    def enrich_customer_linkedin(
        db: Session,
        customer_id: str,
        linkedin_client: LinkedInProfileClient
    ) -> Tuple[bool, Dict[str, Any]]:
        """Enrich customer with LinkedIn data"""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return False, {"error": "Customer not found"}
        
        # Search LinkedIn profile
        profile = linkedin_client.search_profile(
            first_name=customer.first_name or "",
            last_name=customer.last_name or "",
            email=customer.email or "",
            company=customer.company
        )
        
        if profile.get("found"):
            # Store enrichment
            enrichment = db.query(CustomerEnrichment).filter(
                CustomerEnrichment.customer_id == customer_id,
                CustomerEnrichment.enrichment_type == "linkedin"
            ).first()
            
            if not enrichment:
                enrichment = CustomerEnrichmentManager.create_enrichment_job(
                    db, customer_id, "linkedin"
                )
            
            enrichment.status = EnrichmentStatus.COMPLETED.value
            enrichment.metadata = profile
            enrichment.enriched_fields = ["linkedin_profile"]
            enrichment.updated_at = datetime.utcnow()
            db.commit()
            
            return True, profile
        
        return False, profile
    
    @staticmethod
    def enrich_customer_company(
        db: Session,
        customer_id: str,
        company_client: CompanyEnrichmentClient
    ) -> Tuple[bool, Dict[str, Any]]:
        """Enrich customer with company data"""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer or not customer.company:
            return False, {"error": "Customer or company not found"}
        
        # Try to find company by domain first
        domain = None
        if customer.email:
            domain = customer.email.split("@")[1]
        
        if domain:
            company_data = company_client.enrich_company_by_domain(domain)
        else:
            company_data = company_client.enrich_company_by_name(customer.company)
        
        if company_data.get("found"):
            # Store company enrichment
            company = db.query(CompanyData).filter(
                CompanyData.customer_id == customer_id
            ).first()
            
            if not company:
                company = CompanyData(
                    id=str(uuid.uuid4()),
                    customer_id=customer_id,
                    company_name=company_data.get("company_name"),
                    industry=company_data.get("industry"),
                    employees=company_data.get("employees"),
                    revenue=company_data.get("revenue"),
                    founded_year=company_data.get("founded_year"),
                    website=company_data.get("website"),
                    location=company_data.get("location"),
                    data_source=company_data.get("data_source"),
                    enriched_at=datetime.utcnow()
                )
                db.add(company)
            
            db.commit()
            return True, company_data
        
        return False, company_data
    
    @staticmethod
    def enrich_with_intent_signals(
        db: Session,
        customer_id: str
    ) -> List[Dict[str, Any]]:
        """Detect and store intent signals for customer"""
        detector = IntentSignalDetector()
        
        # Get all signals
        engagement_signals = detector.analyze_engagement(db, customer_id)
        
        # Get customer for competitor check
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer and customer.company:
            competitor_signal = detector.detect_competitor_signals(customer.company)
            if competitor_signal:
                engagement_signals.append(competitor_signal)
        
        # Store signals
        for signal in engagement_signals:
            intent = IntentSignal(
                id=str(uuid.uuid4()),
                customer_id=customer_id,
                signal_type=signal.get("signal_type"),
                score=signal.get("score"),
                source=signal.get("source"),
                metadata=signal,
                detected_at=datetime.utcnow()
            )
            db.add(intent)
        
        db.commit()
        return engagement_signals
    
    @staticmethod
    def get_enrichment_status(
        db: Session,
        customer_id: str
    ) -> Dict[str, Any]:
        """Get enrichment status for customer"""
        enrichments = db.query(CustomerEnrichment).filter(
            CustomerEnrichment.customer_id == customer_id
        ).all()
        
        signals = db.query(IntentSignal).filter(
            IntentSignal.customer_id == customer_id
        ).all()
        
        company = db.query(CompanyData).filter(
            CompanyData.customer_id == customer_id
        ).first()
        
        return {
            "customer_id": customer_id,
            "enrichment_jobs": len(enrichments),
            "completed_enrichments": sum(
                1 for e in enrichments 
                if e.status == EnrichmentStatus.COMPLETED.value
            ),
            "intent_signals_detected": len(signals),
            "company_data_enriched": company is not None,
            "overall_enrichment_score": (
                sum(s.score for s in signals) / len(signals) 
                if signals else 0
            )
        }


class BulkEnrichmentManager:
    """Manages bulk enrichment operations"""
    
    @staticmethod
    def enrich_bulk_customers(
        db: Session,
        customer_ids: List[str],
        enrichment_type: str,
        linkedin_client: Optional[LinkedInProfileClient] = None,
        company_client: Optional[CompanyEnrichmentClient] = None
    ) -> Dict[str, Any]:
        """
        Enrich multiple customers
        Returns: {total, successful, failed, partial}
        """
        successful = 0
        failed = 0
        partial = 0
        
        for customer_id in customer_ids:
            if enrichment_type == "linkedin" and linkedin_client:
                success, _ = CustomerEnrichmentManager.enrich_customer_linkedin(
                    db, customer_id, linkedin_client
                )
                if success:
                    successful += 1
                else:
                    failed += 1
            
            elif enrichment_type == "company" and company_client:
                success, _ = CustomerEnrichmentManager.enrich_customer_company(
                    db, customer_id, company_client
                )
                if success:
                    successful += 1
                else:
                    failed += 1
            
            elif enrichment_type == "signals":
                signals = CustomerEnrichmentManager.enrich_with_intent_signals(
                    db, customer_id
                )
                if signals:
                    successful += 1
                else:
                    partial += 1
        
        return {
            "total": len(customer_ids),
            "successful": successful,
            "failed": failed,
            "partial": partial,
            "success_rate": (successful / len(customer_ids)) if customer_ids else 0
        }
