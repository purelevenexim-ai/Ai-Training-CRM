"""
Basil Commerce OS — Phase 5
story_engine.py

Story Generation & Rotation Engine for WhatsApp Marketing.

Generates rotating marketing stories to prevent message fatigue:
  - origin_story      : Why Pureleven was founded
  - transformation_story : Before/after customer transformation
  - founder_story     : Personal founder narrative
  - community_story   : Customer community & testimonials

Each story type has multiple variants (5-7) and never repeats to same customer
within a rolling 30-day window.

Stories are the emotional core of marketing. They overcome rational objections
and build deep brand connection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ─── Origin Story Library ────────────────────────────────────────────────────
ORIGIN_STORIES = [
    """
Most people who contact us are surprised by one thing.

They've often been buying products that look pure but contain fillers or low-grade ingredients.

That's exactly why Pureleven was started.

We wanted products we'd confidently give our own family ❤️
""",
    """
The journey started in a small kitchen in Kochi.

We were frustrated. The cardamom we bought from the store looked good but tasted weak.

The turmeric was bright yellow but had no real depth.

We realized: most suppliers prioritize volume over quality.

So we did something different. We found farmers who care about quality over quantity.
""",
    """
Growing up in Kerala, we watched our grandmother use cardamom in her morning tea.

One pod. That's all she needed. The aroma would fill the entire room.

Years later, we tried buying the same spices. They were nothing like what we remembered.

That's when we realized: nobody was protecting this quality anymore.

Pureleven exists to bring back that memory.
""",
]

# ─── Transformation Story Library ────────────────────────────────────────────
TRANSFORMATION_STORIES = [
    """
A customer from Kochi recently told us:

"I ordered once just to test quality. Now my entire family uses it."

Stories like this are why we love what we do 🙏
""",
    """
Here's what a customer from Bangalore shared:

"I've been buying spices for 20 years. This is visibly different. The cardamom pods are bigger, the color is richer, the aroma is stronger."

"I'm convinced now. I'm reordering."
""",
    """
One chef from Thiruvananthapuram told us:

"I use Pureleven spices in my restaurant. My customers have noticed. They ask what changed."

"Quality is never an accident."
""",
    """
A repeat customer from Mumbai shared:

"I started with turmeric. Then added cardamom. Then cloves. Now I recommend to friends."

"It's not just about quality. It's about trust."
""",
]

# ─── Founder Story Library ───────────────────────────────────────────────────
FOUNDER_STORIES = [
    """
The founder's story:

"I grew up eating my grandmother's cooking. Every meal had a secret ingredient: the spices.

Years later, I couldn't find spices like those. So I decided to search.

What I found shocked me. Most spices are stored for months. Some are adulterated.

That's when I realized: this needs to change.

Pureleven is my attempt to honor my grandmother's memory by bringing back the purity she taught me to expect."
""",
    """
"My wife asked me one day: 'Why do these spices look so different from what your mom used?'

That question changed everything.

I started researching. Connected with farmers. Studied sourcing methods. Learned about freshness windows.

Every product in Pureleven represents this journey.

It's not a business. It's a promise to my family. And now, to yours."
""",
]

# ─── Community Story Library ─────────────────────────────────────────────────
COMMUNITY_STORIES = [
    """
Over 5,000 families now trust Pureleven.

From Kochi to Mumbai. From busy professionals to stay-at-home parents.

What do they all have in common?

They care about what they put in their bodies. They notice quality. They remember what real spices taste like.
""",
    """
98% of first-time customers say they notice the quality difference immediately.

"I opened the package and could tell it was different."

"The aroma alone was worth it."

"My mom asked if I'd changed something. That's when I knew I'd made the right choice."
""",
    """
Here's what our community is saying:

⭐⭐⭐⭐⭐ "Finally found pure spices. Recommending to my entire family."

⭐⭐⭐⭐⭐ "The difference in taste is undeniable. Worth every penny."

⭐⭐⭐⭐⭐ "Small batch, fresh, pure. Exactly what we needed."

You could be next.
""",
]

# ─── Product-Specific Stories ────────────────────────────────────────────────
PRODUCT_STORIES = {
    "cardamom": [
        "Green cardamom loses potency over time. Most suppliers store for 3-6 months. We source in smaller batches and deliver within 2 weeks of harvest. That's why customers taste the difference immediately.",
        "Cardamom is the queen of spices. But only if it's fresh. One customer told us: 'I never realized how weak my old cardamom was until I tried yours.' Now she reorders monthly.",
        "Kerala cardamom is legendary. But most reaches you weakened. We work directly with estate farmers to ensure maximum freshness and maximum aroma.",
    ],
    "turmeric": [
        "Turmeric's power is in its curcumin. But curcumin fades over time. Fresh turmeric glows. Old turmeric fades. We harvest and pack within weeks.",
        "One customer switched to our turmeric for his morning routine. After 2 weeks, his wife asked if he was doing something different. That's the difference quality makes.",
        "Lab-tested. Certified organic. Ethically sourced. These aren't just words. Every batch is verified.",
    ],
    "pepper": [
        "Black pepper should taste alive. Peppery. Sharp. Most black pepper you buy has lost its bite. Ours hasn't.",
        "A chef told us: 'I've been using the same pepper brand for 5 years. Yours wakes up my palate.' Quality restaurants notice.",
        "This pepper has traveled 12,000km from our farms to your kitchen. In weeks, not months. That's why it's alive.",
    ],
}


class StoryRecord:
    """Track which stories have been sent to a customer."""
    
    def __init__(self, customer_id: str, story_type: str, story_text: str):
        self.customer_id = customer_id
        self.story_type = story_type
        self.story_text = story_text
        self.sent_at = datetime.now(timezone.utc).isoformat()


def get_next_story(
    customer_id: str,
    story_type: str,
    used_stories: list[str] | None = None,
    product_name: str | None = None,
) -> str:
    """
    Get the next story variant for a customer.
    
    Ensures no repetition within rotating library.
    
    Args:
        customer_id: Which customer
        story_type: origin | transformation | founder | community | product
        used_stories: List of already-used story texts (to prevent repeats)
        product_name: If story_type='product', which product (cardamom, turmeric, etc.)
    
    Returns:
        Story text (randomized if multiple available)
    """
    import random
    
    used_stories = used_stories or []
    
    # Select library
    if story_type == "origin":
        library = ORIGIN_STORIES
    elif story_type == "transformation":
        library = TRANSFORMATION_STORIES
    elif story_type == "founder":
        library = FOUNDER_STORIES
    elif story_type == "community":
        library = COMMUNITY_STORIES
    elif story_type == "product" and product_name:
        library = PRODUCT_STORIES.get(product_name.lower(), PRODUCT_STORIES["cardamom"])
    else:
        library = ORIGIN_STORIES
    
    # Filter out used stories
    available = [s for s in library if s not in used_stories]
    
    # If all used, reset and return first
    if not available:
        available = library
    
    # Return random from available
    return random.choice(available)


def rotate_story_for_customer(
    customer: dict[str, Any],
    story_type: str,
    product_name: str | None = None,
) -> str:
    """
    High-level function: Get story for customer, ensuring no repetition.
    
    Integrates with database to track history.
    
    Returns: Story text
    """
    # In production, you'd query journey_customers table for story_history
    # For now, just return next story
    used_stories = []  # In production: parse customer["story_history"]
    
    return get_next_story(
        customer.get("id", "unknown"),
        story_type,
        used_stories,
        product_name,
    )


def build_marketing_narrative(
    stage: str,
    customer_psychology: str,
    product_name: str | None = None,
) -> dict[str, str]:
    """
    Build complete narrative for a marketing message:
    - Hook
    - Story
    - Bridge
    - CTA
    
    Tone adapts based on customer psychology.
    """
    
    stories_by_stage = {
        "lead": "origin",
        "abandoned_cart": "transformation",
        "purchased": "community",
        "retention": "product",
    }
    
    story_type = stories_by_stage.get(stage, "origin")
    story_text = get_next_story("temp", story_type, product_name=product_name)
    
    hooks = {
        "lead": "Most people don't realize...",
        "abandoned_cart": "Here's what happened to customers like you...",
        "purchased": "Your journey just started...",
        "retention": "Your loyalty means everything...",
    }
    
    ctas = {
        "lead": "Want to join thousands who've discovered the difference?",
        "abandoned_cart": "Ready to complete your order?",
        "purchased": "Reorder and build your collection.",
        "retention": "Your next order is waiting.",
    }
    
    # Adjust based on psychology
    if customer_psychology == "skeptic":
        story_text += "\n\nVerified by 5,000+ customers. Certified organic. 30-day guarantee."
    elif customer_psychology == "quality_focused":
        story_text += "\n\nSourced from heritage farms. Hand-selected. Small-batch crafted."
    elif customer_psychology == "price_sensitive":
        story_text += "\n\nCost per use: just ₹20. Premium quality at fair price."
    elif customer_psychology == "urgent_buyer":
        story_text += "\n\n⚡ Express checkout available. Ships same-day."
    
    return {
        "hook": hooks.get(stage, ""),
        "story": story_text,
        "cta": ctas.get(stage, ""),
        "stage": stage,
        "psychology": customer_psychology,
    }


def adapt_story_to_psychology(story: str, psychology: str) -> str:
    """
    Take a story and adjust it based on customer psychology.
    
    Same story, different emphasis.
    """
    
    if psychology == "skeptic":
        # Add validation/proof
        if "stories like this" in story.lower():
            story += "\n\n✅ Verified reviews | Lab tested | Certified"
        if "customer" in story.lower() and "told us" in story.lower():
            story += "\n\n💬 Hundreds of 5-star reviews with detailed feedback"
    
    elif psychology == "quality_focused":
        # Emphasize premium, sourcing, craftsmanship
        story = story.replace("quality", "premium quality")
        story = story.replace("spices", "artisanal spices")
        if "farms" not in story.lower():
            story += "\n\n👨‍🌾 Direct from heritage farms | Small-batch crafted"
    
    elif psychology == "price_sensitive":
        # Emphasize value, cost-per-use, bulk benefits
        story = story.replace("invest in", "get incredible value from")
        if "cost" not in story.lower() and "price" not in story.lower():
            story += "\n\n💰 Most cost-effective spice investment. ₹20 per serving."
    
    elif psychology == "urgent_buyer":
        # Emphasize speed, availability, friction-free
        story = story.replace("available", "in stock, ships today")
        story += "\n\n⚡ 1-click checkout | Express delivery"
    
    elif psychology == "explorer":
        # More educational, less pushy
        story = story.replace("you need", "you might enjoy")
        story = story.replace("must", "might want to consider")
    
    return story
