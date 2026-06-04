"""
AI CRM API Routes
10 endpoints for AI gateway, customer management, products, KB, and debugging
"""

import logging
from typing import Optional
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from crm_models import (
    Customer, CustomerAIProfile, CustomerEvent, AIConversation,
    ProductCatalog, KnowledgeBase, AILog
)
from app.ai_service import (
    RuleEngine, GeminiProvider, ScoringEngine,
    ProductService, KnowledgeService, Intent, Language
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


# ─── PYDANTIC MODELS ────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    """Customer message input"""
    customer_id: str
    message: str
    phone: Optional[str] = None
    language: Optional[str] = None


class TestSandboxRequest(BaseModel):
    """Sandbox test input"""
    message: str


class ProductCreateRequest(BaseModel):
    """Create product input"""
    name: str
    price_inr: float
    stock: int = 0
    category: Optional[str] = None


class ProductUpdateRequest(BaseModel):
    """Update product input"""
    price_inr: Optional[float] = None
    stock: Optional[int] = None


class KBCreateRequest(BaseModel):
    """Create KB entry input"""
    question: str
    answer: str
    category: Optional[str] = None


# ─── ENDPOINT 1: POST /api/ai/webhook/wabis ────────────────────────────────

@router.post("/webhook/wabis")
async def webhook_wabis(
    request: MessageRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Main Wabis webhook endpoint
    Receives customer message, detects intent, generates response
    """
    try:
        logger.info(f"Received message from customer {request.customer_id}")
        
        # Initialize services
        rule_engine = RuleEngine()
        product_service = ProductService(db)
        kb_service = KnowledgeService(db)
        scoring_engine = ScoringEngine(db)
        
        # Detect language & intent
        language, lang_conf = rule_engine.detect_language(request.message)
        intent, intent_conf = rule_engine.detect_intent(request.message, language)
        
        # Decide if we need Gemini
        use_gemini = rule_engine.should_use_gemini(intent_conf)
        
        # Get context for response
        products = product_service.get_all_products()
        kb_results = kb_service.search_kb(request.message, limit=3)
        
        response_text = ""
        tokens_used = 0
        latency_ms = 0
        
        if use_gemini:
            # Use Gemini for uncertain intents
            try:
                gemini = GeminiProvider()
                context = {
                    "products": products,
                    "kb": kb_results
                }
                response_text, tokens_used = gemini.generate_response(
                    request.message,
                    context=context,
                    language=language.value
                )
            except Exception as e:
                logger.error(f"Gemini error: {e}")
                response_text = "I'm having trouble generating a response. Please try again."
                tokens_used = 0
        else:
            # Use rule-based response for confident intents
            response_text = _generate_rule_based_response(
                intent, products, kb_results, language
            )
            tokens_used = 0  # No tokens for rule-based
        
        # Create or get conversation
        conversation = AIConversation(
            conversation_id=str(uuid4()),
            customer_id=request.customer_id,
            intents_in_path=[intent.value],
            outcome="pending"
        )
        db.add(conversation)
        
        # Log event
        event = CustomerEvent(
            event_id=str(uuid4()),
            customer_id=request.customer_id,
            conversation_id=conversation.conversation_id,
            event_type=intent.value,
            context_json={
                "language": language.value,
                "intent_confidence": intent_conf,
                "message": request.message
            }
        )
        db.add(event)
        
        # Log AI response
        ai_log = AILog(
            log_id=str(uuid4()),
            customer_id=request.customer_id,
            conversation_id=conversation.conversation_id,
            intent_detected=intent.value,
            language_detected=language.value,
            response_text=response_text,
            tokens_used=tokens_used,
            latency_ms=int(latency_ms)
        )
        db.add(ai_log)
        
        # Update customer score
        scoring_engine.update_customer_score(request.customer_id)
        
        db.commit()
        
        return {
            "conversation_id": conversation.conversation_id,
            "response": response_text,
            "intent": intent.value,
            "language": language.value,
            "intent_confidence": intent_conf,
            "tokens_used": tokens_used,
            "used_gemini": use_gemini
        }
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 2: GET /api/ai/customers ──────────────────────────────────────

@router.get("/customers")
async def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> dict:
    """List all customers with AI scores"""
    try:
        query = db.query(Customer).join(
            CustomerAIProfile,
            Customer.id == CustomerAIProfile.customer_id,
            isouter=True
        )
        
        if status:
            query = query.filter(CustomerAIProfile.lead_status == status)
        
        # Sort by score descending
        query = query.order_by(
            CustomerAIProfile.overall_score.desc()
        )
        
        total = query.count()
        customers = query.skip(skip).limit(limit).all()
        
        results = []
        for c in customers:
            profile = db.query(CustomerAIProfile).filter(
                CustomerAIProfile.customer_id == c.id
            ).first()
            
            results.append({
                "customer_id": c.id,
                "name": f"{c.first_name or ''} {c.last_name or ''}".strip(),
                "email": c.email,
                "phone": c.phone,
                "overall_score": profile.overall_score if profile else 0,
                "lead_status": profile.lead_status if profile else "Cold",
                "total_spent": c.total_spent,
                "orders_count": c.orders_count,
                "last_activity": profile.last_activity if profile else None
            })
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "customers": results
        }
    
    except Exception as e:
        logger.error(f"Error getting customers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 3: GET /api/ai/customers/{id} ─────────────────────────────────

@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Get customer details with AI profile"""
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        profile = db.query(CustomerAIProfile).filter(
            CustomerAIProfile.customer_id == customer_id
        ).first()
        
        recent_events = db.query(CustomerEvent).filter(
            CustomerEvent.customer_id == customer_id
        ).order_by(CustomerEvent.created_at.desc()).limit(10).all()
        
        return {
            "customer_id": customer.id,
            "name": f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
            "email": customer.email,
            "phone": customer.phone,
            "total_spent": customer.total_spent,
            "orders_count": customer.orders_count,
            "ai_profile": {
                "overall_score": profile.overall_score if profile else 0,
                "engagement_score": profile.engagement_score if profile else 0,
                "purchase_intent_score": profile.purchase_intent_score if profile else 0,
                "customer_value_score": profile.customer_value_score if profile else 0,
                "lead_status": profile.lead_status if profile else "Cold",
                "next_action": profile.next_action if profile else None
            },
            "recent_events": [
                {
                    "event_type": e.event_type,
                    "created_at": e.created_at.isoformat()
                }
                for e in recent_events
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 4: POST /api/ai/sandbox/test ──────────────────────────────────

@router.post("/sandbox/test")
async def sandbox_test(
    request: TestSandboxRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Debugging tool: test message detection
    Shows language, intent, confidence, detection method
    """
    try:
        rule_engine = RuleEngine()
        product_service = ProductService(db)
        kb_service = KnowledgeService(db)
        
        # Language detection
        language, lang_conf = rule_engine.detect_language(request.message)
        
        # Intent detection
        intent, intent_conf = rule_engine.detect_intent(request.message, language)
        
        # Determine method
        use_gemini = rule_engine.should_use_gemini(intent_conf)
        method = "Gemini" if use_gemini else "Rule Engine"
        
        # Get products & KB context
        products = product_service.get_all_products(active_only=True)
        kb = kb_service.search_kb(request.message, limit=3)
        
        response_text = ""
        if not use_gemini:
            response_text = _generate_rule_based_response(
                intent, products, kb, language
            )
        
        return {
            "message": request.message,
            "detected_language": language.value,
            "language_confidence": round(lang_conf, 2),
            "detected_intent": intent.value,
            "intent_confidence": round(intent_conf, 2),
            "detection_method": method,
            "will_use_gemini": use_gemini,
            "products_available": len(products),
            "kb_matches": len(kb),
            "sample_response": response_text[:100] if response_text else "(No rule-based response)"
        }
    
    except Exception as e:
        logger.error(f"Error in sandbox test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 5: GET /api/ai/products ───────────────────────────────────────

@router.get("/products")
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    """List all products in catalog"""
    try:
        query = db.query(ProductCatalog)
        total = query.count()
        products = query.skip(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "products": [
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
        }
    
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 6: POST /api/ai/products ──────────────────────────────────────

@router.post("/products")
async def create_product(
    request: ProductCreateRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Create new product"""
    try:
        product = ProductCatalog(
            product_id=str(uuid4()),
            name=request.name,
            price_inr=request.price_inr,
            stock=request.stock,
            category=request.category
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        return {
            "product_id": product.product_id,
            "name": product.name,
            "price_inr": float(product.price_inr),
            "stock": product.stock,
            "category": product.category,
            "status": product.status,
            "created_at": product.created_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 7: PUT /api/ai/products/{id} ──────────────────────────────────

@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Update product price or stock"""
    try:
        product = db.query(ProductCatalog).filter(
            ProductCatalog.product_id == product_id
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if request.price_inr is not None:
            product.price_inr = request.price_inr
        
        if request.stock is not None:
            product.stock = request.stock
        
        product.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(product)
        
        return {
            "product_id": product.product_id,
            "name": product.name,
            "price_inr": float(product.price_inr),
            "stock": product.stock,
            "updated_at": product.updated_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 8: GET /api/ai/knowledge-base ─────────────────────────────────

@router.get("/knowledge-base")
async def get_knowledge_base(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    db: Session = Depends(get_db)
) -> dict:
    """List knowledge base entries"""
    try:
        query = db.query(KnowledgeBase).filter(
            KnowledgeBase.status == 'active'
        )
        
        if category:
            query = query.filter(KnowledgeBase.category.ilike(f"%{category}%"))
        
        total = query.count()
        entries = query.skip(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "entries": [
                {
                    "kb_id": e.kb_id,
                    "question": e.question,
                    "answer": e.answer,
                    "category": e.category,
                    "updated_at": e.updated_at.isoformat()
                }
                for e in entries
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting KB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 9: POST /api/ai/knowledge-base ────────────────────────────────

@router.post("/knowledge-base")
async def create_kb_entry(
    request: KBCreateRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Create new KB entry"""
    try:
        entry = KnowledgeBase(
            kb_id=str(uuid4()),
            question=request.question,
            answer=request.answer,
            category=request.category
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        return {
            "kb_id": entry.kb_id,
            "question": entry.question,
            "answer": entry.answer,
            "category": entry.category,
            "status": entry.status,
            "created_at": entry.created_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error creating KB entry: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 10: GET /api/ai/logs ──────────────────────────────────────────

@router.get("/logs")
async def get_ai_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> dict:
    """View AI logs (audit trail)"""
    try:
        query = db.query(AILog)
        
        if customer_id:
            query = query.filter(AILog.customer_id == customer_id)
        
        total = query.count()
        logs = query.order_by(AILog.created_at.desc()).skip(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "logs": [
                {
                    "log_id": l.log_id,
                    "customer_id": l.customer_id,
                    "intent_detected": l.intent_detected,
                    "language_detected": l.language_detected,
                    "tokens_used": l.tokens_used,
                    "latency_ms": l.latency_ms,
                    "created_at": l.created_at.isoformat()
                }
                for l in logs
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── HELPERS ────────────────────────────────────────────────────────────────

def _generate_rule_based_response(
    intent: Intent,
    products: list,
    kb: list,
    language: Language
) -> str:
    """Generate rule-based response based on intent"""
    
    if intent == Intent.PRICE_INQUIRY:
        if products:
            product = products[0]  # Return first product
            if language == Language.MALAYALAM:
                return f"{product['name']} വിലയുടെ ₹{product['price_inr']} ആണ്. സ്റ്റോക്ക് ഉണ്ട്: {product['stock']} ഉണ്ട്."
            elif language == Language.MANGLISH:
                return f"{product['name']} vila {product['price_inr']} anu. Stock: {product['stock']}"
            else:
                return f"The price of {product['name']} is ₹{product['price_inr']}. Stock: {product['stock']}"
        return "We have spices available. Please ask about a specific product."
    
    elif intent == Intent.SHIPPING_INQUIRY:
        if language == Language.MALAYALAM:
            return "സൗജന്യ ഡെലിവറി ভാരതീയ ഞ്ഞന്നര്! 2-4 വരവ്. വിതരണ സമയം അവലംബിതമാണ്."
        elif language == Language.MANGLISH:
            return "Free delivery entire India! 2-4 days delivery time."
        else:
            return "We offer free delivery across India with 2-4 business days delivery time."
    
    elif intent == Intent.COD_INQUIRY:
        if language == Language.MALAYALAM:
            return "കാശ് വിതരണത്തിൽ (COD) ആണ് സാധാരണ്. പണം കിട്ടിയാൽ നൈതികം കൊടുത്ത് എങ്ങ് വാങ്ങും?"
        elif language == Language.MANGLISH:
            return "Haan, COD available. Pay when you receive. Easy option for all."
        else:
            return "Yes, we accept Cash on Delivery (COD). Pay when you receive your order."
    
    elif intent == Intent.PURCHASE:
        if language == Language.MALAYALAM:
            return "മികച്ചത് ഓർഡർ ചെയ്യാൻ! നമ്മുടെ ആപ്ലിേക്ഷനിൽ വിതരണം സ്ഥിരമായ്. നിങ്ങൾ ആവശ്യമുള്ളത് അറിയിക്കണ്ടായ്."
        elif language == Language.MANGLISH:
            return "Great to order! Tell me, kaun sa product chahiye? Mujhe batao product name."
        else:
            return "Great! I'd love to help you order. Which spice product would you like?"
    
    else:
        # GENERAL or COMPLAINT
        if kb:
            return f"This might help: {kb[0]['answer'][:200]}"
        return "Thanks for your message. How can I help you with Pure leven spices?"
