# Catalog Search Handler Example - Using Pricing Formatter

This example shows how to implement the catalog search handler using the pricing formatter to display clean pricing.

## Implementation Pattern

```python
# In wave02_wabis_routes.py

from app.ai.pricing_formatter import PricingFormatter
from app.ai.knowledge_retriever import KnowledgeRetriever
from app.wabis_client import WabisAPIClient

class WaveO2Handlers:
    """Route handlers for Phase 1A"""
    
    @staticmethod
    async def handle_catalog_search(
        customer_phone: str,
        customer_name: str,
        incoming_message: str,
        conversation_id: str
    ) -> dict:
        """
        Handle catalog product search.
        
        Customer says product name like "Cardamom", "Black pepper", etc.
        
        Response: Clean pricing table with all variants
        """
        logger.info(f"[CATALOG] Searching for: {incoming_message}")
        
        # Step 1: Search knowledge base for product
        knowledge = KnowledgeRetriever()
        search_results = knowledge.search_products(incoming_message)
        
        if not search_results:
            # Product not found - log as missing product
            from app.ai.clarification_flow import log_missing_product
            log_missing_product(
                product_query=incoming_message,
                clarification="Not found in catalog search"
            )
            
            return {
                "reply_text": (
                    f"Hi {customer_name},\n\n"
                    f"I couldn't find '{incoming_message}' in our catalog right now. "
                    "Could you describe what you're looking for? "
                    "(e.g., spice type, usage, ingredient)\n\n"
                    "Our popular items:\n"
                    "🌿 Black Pepper\n"
                    "🌿 Cardamom\n"
                    "🌿 Cinnamon\n"
                    "🌿 Clove"
                ),
                "intent": "catalog_not_found",
                "should_escalate": False,
                "escalation_reason": None,
                "suggested_action": "send_reply"
            }
        
        # Step 2: Found product - format using PricingFormatter
        product = search_results[0]  # Best match
        
        # Build variant list from knowledge base
        variants = [
            {
                "size": variant.get("size"),
                "price": variant.get("price"),
                "delivery": "Free" if variant.get("free_delivery") else variant.get("delivery_cost", "₹40")
            }
            for variant in product.get("variants", [])
        ]
        
        # Format using PricingFormatter
        formatted_response = PricingFormatter.format_product_pricing(
            product_name=product.get("name"),
            variants=variants,
            origin=product.get("origin"),
            description=product.get("description")
        )
        
        # Step 3: Add action buttons (if Wabis supports them)
        # For now, append simple text CTA
        cta_text = "\n\n💬 Reply with:\n'Add to cart' or 'Need help?'"
        full_response = formatted_response + cta_text
        
        logger.info(f"[CATALOG] Formatted response for {customer_phone}")
        
        return {
            "reply_text": full_response,
            "intent": "catalog_found",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply"
        }
    
    @staticmethod
    async def handle_catalog_multiple_matches(
        customer_phone: str,
        customer_name: str,
        incoming_message: str,
        conversation_id: str
    ) -> dict:
        """
        Handle case where multiple products match (e.g., "pepper").
        Show all with pricing using PricingFormatter.
        """
        logger.info(f"[CATALOG-MULTI] Multiple matches for: {incoming_message}")
        
        knowledge = KnowledgeRetriever()
        search_results = knowledge.search_products(incoming_message, limit=5)
        
        if not search_results:
            return {
                "reply_text": f"Hi {customer_name},\n\nNo products found for '{incoming_message}'",
                "intent": "catalog_empty",
                "should_escalate": False,
                "escalation_reason": None,
                "suggested_action": "send_reply"
            }
        
        # Format multiple products
        products = [
            {
                "name": product.get("name"),
                "origin": product.get("origin"),
                "description": product.get("description"),
                "variants": [
                    {
                        "size": v.get("size"),
                        "price": v.get("price"),
                        "delivery": "Free" if v.get("free_delivery") else v.get("delivery_cost", "₹40")
                    }
                    for v in product.get("variants", [])
                ]
            }
            for product in search_results
        ]
        
        # Use format_catalog_response for multiple products
        formatted_response = PricingFormatter.format_catalog_response(products)
        
        logger.info(f"[CATALOG-MULTI] Showing {len(products)} products to {customer_phone}")
        
        return {
            "reply_text": formatted_response,
            "intent": "catalog_multiple",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply"
        }
```

## Integration in wave02_wabis_routes.py

```python
async def _generate_and_send_reply(
    conversation_id: str,
    customer_phone: str,
    customer_name: str,
    incoming_message: str
):
    """Main routing flow with handler integration"""
    
    # ... [existing code] ...
    
    # Route the message
    decision = route_message(customer_phone, incoming_message)
    
    # ... [existing code] ...
    
    # ROUTE: Catalog Search (Product name query)
    if decision.get("route") == "catalog":
        handler_result = await WaveO2Handlers.handle_catalog_search(
            customer_phone,
            customer_name,
            incoming_message,
            conversation_id
        )
        
        reply_text = handler_result.get("reply_text")
        log_routing_decision(
            customer_phone,
            incoming_message,
            conversation_state_before,
            decision
        )
        
        # Send via Wabis
        await WabisAPIClient.send_text_message(customer_phone, reply_text)
        return
    
    # ... [other routes] ...
```

## Expected Output Example

**Customer Message**: "Cardamom"

**Routing Decision**: 
```
[ROUTE-DECISION] 919201111111 → catalog (Product catalog search (no AI))
```

**Formatted Response**:
```
*CARDAMOM* • Idukki

_Pure taste and authentic aroma from the hills of Idukki_

*Size     | Price    | Delivery*
───────────────────────────────────
100g    | ₹460     | ₹40
200g    | ₹840     | ✅ FREE
500g    | ₹1799    | ✅ FREE

📦 *Shipping*: 1-2 business days dispatch, 3-7 days delivery
✅ Free delivery on orders ₹500+
🌿 Direct from farms • Freshly packed

💬 Reply with:
'Add to cart' or 'Need help?'
```

## Product Data Structure (From Knowledge Base)

```python
{
    "name": "Cardamom",
    "origin": "Idukki",
    "description": "Pure taste and authentic aroma from the hills of Idukki",
    "category": "spices",
    "rating": 4.8,
    "reviews": 234,
    "variants": [
        {
            "size": "100g",
            "price": 460,
            "sku": "CARDA-100",
            "stock": 150,
            "free_delivery": False,
            "delivery_cost": "₹40"
        },
        {
            "size": "200g",
            "price": 840,
            "sku": "CARDA-200",
            "stock": 200,
            "free_delivery": True,
            "delivery_cost": "Free"
        },
        {
            "size": "500g",
            "price": 1799,
            "sku": "CARDA-500",
            "stock": 100,
            "free_delivery": True,
            "delivery_cost": "Free"
        }
    ]
}
```

## Key Features of This Handler

✅ **Uses PricingFormatter** - Clean table formatting  
✅ **Logs Missing Products** - When product not in catalog  
✅ **Handles Multiple Matches** - Shows all relevant products  
✅ **Includes CTA** - "Add to cart" next steps  
✅ **Proper Intent Logging** - For analytics  
✅ **Knowledge Integration** - Gets pricing from knowledge base

## Testing

### Test Single Product
```bash
curl -X POST https://track.pureleven.com/api/ai/wave02/webhook/wabis/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "subscriber_id": "test_001",
    "phone": "919191919191",
    "first_name": "Test",
    "text": "Cardamom",
    "type": "message"
  }'
```

### Expected Log
```
[ROUTE-START] 919191919191: Cardamom
[ROUTE-DECISION] 919191919191 → catalog (Product catalog search (no AI))
[CATALOG] Searching for: Cardamom
[CATALOG] Formatted response for 919191919191
```

---

**Status**: Example for implementation  
**Next Step**: Deploy handler and test with real product queries
