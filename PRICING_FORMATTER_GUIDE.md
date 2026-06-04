# Pricing Formatter Guide - Clean Product Display

## Overview

The `PricingFormatter` module provides clean, structured formatting for product pricing in WhatsApp messages. Instead of cluttered, long-form pricing text, it produces organized tables that are mobile-friendly.

**Before:**
```
Direct from Idukki 🌿 Pure taste and authentic aroma from the hills of Idukki Export Cardamom – 8.5 mm A Grade 🔥 100g – ₹460 ₹40 Delivery 🔥 200g – ₹840 ✅ Free Delivery 🔥 500g – ₹1799 ✅ Free Delivery...
```

**After:**
```
*CARDAMOM* • Idukki

_Pure taste and authentic aroma from the hills_

*Size     | Price    | Delivery*
───────────────────────────────────
100g    | ₹460     | ₹40
200g    | ₹840     | ✅ FREE
500g    | ₹1799    | ✅ FREE
```

## Installation

Already deployed to production at `/opt/pureleven/ai-engine/app/ai/pricing_formatter.py`

## Usage Examples

### 1. Single Product with Variants

```python
from app.ai.pricing_formatter import PricingFormatter

response = PricingFormatter.format_product_pricing(
    product_name="Cardamom",
    variants=[
        {"size": "100g", "price": 460, "delivery": "₹40"},
        {"size": "200g", "price": 840, "delivery": "Free"},
        {"size": "500g", "price": 1799, "delivery": "Free"},
    ],
    origin="Idukki",
    description="Pure taste and authentic aroma from the hills"
)

# Send via Wabis
WabisAPIClient.send_text_message(phone, response)
```

### 2. Multiple Products (Catalog Search Response)

```python
products = [
    {
        "name": "Cardamom",
        "origin": "Idukki",
        "description": "Pure taste from the hills",
        "variants": [
            {"size": "100g", "price": 460, "delivery": "₹40"},
            {"size": "200g", "price": 840, "delivery": "Free"},
        ]
    },
    {
        "name": "Black Pepper",
        "origin": "Idukki",
        "description": "Premium washed & cleaned",
        "variants": [
            {"size": "250g", "price": 300, "delivery": "₹40"},
            {"size": "500g", "price": 540, "delivery": "Free"},
        ]
    }
]

response = PricingFormatter.format_catalog_response(products)
WabisAPIClient.send_text_message(phone, response)
```

### 3. Quick Price Mention

For inline mentions in broader responses:

```python
quick = PricingFormatter.format_quick_price(
    product="Cardamom",
    price_range="₹180 - ₹1799"
)
# Output: "*Cardamom* • ₹180 - ₹1799"
```

### 4. Single Size Response

For specific product + size queries:

```python
response = PricingFormatter.format_single_size(
    product="Ceylon Cinnamon",
    size="100g",
    price=320,
    delivery="FREE",
    origin="Ceylon"
)

# Output:
# *CEYLON CINNAMON*
# Origin: Ceylon
#
# Size: 100g
# Price: ₹320
# Delivery: ✅ FREE
```

## Integration Points

### 1. Catalog Search Handler

When customer searches for a product by name ("Sesame oil", "Cardamom"):

```python
# In wave02_wabis_routes.py
if route == "catalog":
    # Get product from knowledge_retriever
    product_data = knowledge_retriever.search(incoming_message)
    
    if product_data:
        # Use formatter to display pricing
        response = PricingFormatter.format_product_pricing(
            product_name=product_data["name"],
            variants=product_data["variants"],
            origin=product_data.get("origin"),
            description=product_data.get("description")
        )
        WabisAPIClient.send_text_message(customer_phone, response)
```

### 2. Product Recommendation Responses

When AI recommends a product:

```python
if route == "ai" and decision.get("require_knowledge"):
    # Generate recommendation with pricing
    product = knowledge_retriever.get_best_match(incoming_message)
    
    response = PricingFormatter.format_product_pricing(
        product_name=product["name"],
        variants=product["variants"],
        origin=product.get("origin"),
        description=product.get("description")
    )
```

### 3. FAQ Responses with Pricing

When FAQ mentions pricing:

```python
if route == "faq":
    faq_answer = faq_knowledge_base.search(incoming_message)
    
    if faq_answer and "₹" in faq_answer:
        # Extract pricing and reformat
        response = PricingFormatter.format_quick_price(
            product=product_name,
            price_range=extract_price_range(faq_answer)
        )
```

## Data Structure

### Variant Structure

```python
{
    "size": "100g",           # Weight/volume
    "price": 460,             # Price in rupees (number only)
    "delivery": "₹40"         # "Free" or "₹40" or other cost
}
```

### Product Structure

```python
{
    "name": "Cardamom",                  # Product name
    "origin": "Idukki",                  # Origin (optional)
    "description": "Pure taste...",      # Long description (optional)
    "variants": [...]                    # List of variants
}
```

## Output Features

✅ **Clean Table Format** - Easy to read on mobile
✅ **Mobile Optimized** - Works well on WhatsApp
✅ **Clear Pricing** - Price and delivery side-by-side
✅ **Free Delivery Badge** - ✅ FREE marking for free delivery
✅ **Product Origin** - Shows origin in header
✅ **Shipping Info Footer** - Standard footer included

## Best Practices

1. **Always Use for Pricing** - Don't send raw pricing text with emojis
2. **Keep Descriptions Short** - Italicized description should be brief (1-2 sentences)
3. **Use Canonical Names** - Normalize product names (e.g., "Black Pepper" not "pepper" or "kali mirch")
4. **Set Delivery Accurately** - Use "Free" for free, or "₹XY" for cost
5. **Group by Product** - Show all variants together, not scattered

## Example: Complete Catalog Search

```python
# Customer says: "Black pepper"
# Route: catalog
# Handler:

incoming = "Black pepper"
product_data = {
    "name": "Black Pepper",
    "origin": "Idukki",
    "description": "Premium grade, washed & cleaned",
    "variants": [
        {"size": "250g", "price": 300, "delivery": "₹40"},
        {"size": "500g", "price": 540, "delivery": "Free"},
        {"size": "1kg", "price": 1080, "delivery": "Free"},
    ]
}

response = PricingFormatter.format_product_pricing(
    product_name=product_data["name"],
    variants=product_data["variants"],
    origin=product_data["origin"],
    description=product_data["description"]
)

WabisAPIClient.send_text_message(customer_phone, response)
```

**Output:**
```
*BLACK PEPPER* • Idukki

_Premium grade, washed & cleaned_

*Size     | Price    | Delivery*
───────────────────────────────────
250g    | ₹300     | ₹40
500g    | ₹540     | ✅ FREE
1kg     | ₹1080    | ✅ FREE

📦 *Shipping*: 1-2 business days dispatch, 3-7 days delivery
✅ Free delivery on orders ₹500+
🌿 Direct from farms • Freshly packed
```

## Deployment Status

✅ **File**: `/opt/pureleven/ai-engine/app/ai/pricing_formatter.py`  
✅ **Integrated with**: `wabis_reply_generator.py`  
✅ **Container**: pureleven-ai-engine (restarted 2026-06-01 18:58:59 UTC)  
✅ **Status**: Ready for use

## Testing

To test locally:

```bash
cd /opt/pureleven/ai-engine

docker exec pureleven-ai-engine python3 -c "
from app.ai.pricing_formatter import PricingFormatter

# Test
response = PricingFormatter.format_product_pricing(
    'Black Pepper',
    [{'size': '500g', 'price': 540, 'delivery': 'Free'}],
    'Idukki'
)
print(response)
"
```

---

**Last Updated**: 2026-06-01  
**Status**: 🟢 Production Ready
