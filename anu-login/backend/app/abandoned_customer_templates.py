"""
Abandoned Lead Email Templates with AI-driven personalization

Abandoned leads are prospects who:
- Clicked on ads / visited website
- Showed interest in specific products
- Did NOT purchase
- Tracked by engagement_score (open/click events)

Cadence: 15-day intervals with warm/cold segmentation
Scoring: Warm (engagement_score ≥ 40) vs Cold (< 40)
Cold for 2+ months → Pause, resume after 90 days

All URLs are verified against actual PureLeven endpoints with homepage fallback.
"""

from datetime import datetime
import html
from app.url_config import urls


def build_abandoned_email(lead, campaign_number, interest_category="general", ai_context=""):
    """
    Build personalized abandoned lead email based on campaign sequence
    
    Args:
        lead: Lead dict with id, name, email, phone, interest_product, engagement_score
        campaign_number: Email sequence (1-6) representing 15-day intervals
        interest_category: "turmeric", "spices", "ghee", "supplements", "bundles", "general"
        ai_context: AI-generated personalization (e.g., "They love organic products")
    
    Returns:
        (subject, html_body, text_body)
    """
    
    dispatch = {
        1: _campaign_1_initial_interest,
        2: _campaign_2_social_proof,
        3: _campaign_3_exclusive_offer,
        4: _campaign_4_urgency,
        5: _campaign_5_testimonial,
        6: _campaign_6_winback,
    }
    
    handler = dispatch.get(campaign_number, _campaign_1_initial_interest)
    return handler(lead, interest_category, ai_context)


def _campaign_1_initial_interest(lead, interest_category="general", ai_context=""):
    """
    Day 0: First email - Re-engage with their specific interest
    """
    name = html.escape(lead.get("name", "there"))
    product_name = lead.get("interest_product", "PureLeven Products")
    
    subject = f"✨ Rediscover {product_name} — Organic & Pure"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2E7D32 0%, #558B2F 100%); padding: 20px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 24px; }}
            .content {{ padding: 30px; }}
            .greeting {{ font-size: 16px; color: #333; margin-bottom: 20px; }}
            .hero-text {{ background-color: #f0f5e9; border-left: 4px solid #2E7D32; padding: 15px; margin: 20px 0; border-radius: 4px; }}
            .hero-text p {{ margin: 0; color: #2E7D32; font-weight: 500; }}
            .product-highlight {{ background: #faf9f6; padding: 15px; border-radius: 6px; margin: 20px 0; border: 1px solid #e8e8e8; }}
            .product-highlight h3 {{ color: #2E7D32; margin-top: 0; }}
            .cta-button {{ display: inline-block; background: #2E7D32; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
            .ai-insight {{ font-size: 13px; color: #666; font-style: italic; margin: 15px 0; padding: 10px; background-color: #f5f5f5; border-radius: 4px; }}
            .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
            .unsubscribe {{ color: #2E7D32; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌿 We Saved Your Favorites</h1>
            </div>
            <div class="content">
                <div class="greeting">Hi {name},</div>
                
                <p>We noticed you were interested in <strong>{product_name}</strong> but didn't complete your order. No worries!</p>
                
                <div class="hero-text">
                    <p>✓ 100% Organic | ✓ Zero Chemicals | ✓ Farm-to-Table</p>
                </div>
                
                <div class="product-highlight">
                    <h3>Why PureLeven's {product_name}?</h3>
                    <ul style="margin: 10px 0; padding-left: 20px; color: #333;">
                        <li>Cold-pressed, never heated</li>
                        <li>Sourced directly from farmers</li>
                        <li>Lab-tested for purity</li>
                        <li>Ships within 24 hours</li>
                    </ul>
                </div>
                
                {f'<div class="ai-insight">💡 AI Note: {ai_context}</div>' if ai_context else ''}
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_1', utm_medium='email', email=html.escape(lead.get('email', '')))}" class="cta-button">View {product_name} →</a>
                </p>
                
                <p style="color: #666; font-size: 13px; margin-top: 30px;">
                    Questions? Reply to this email or call us at +91-8081234567
                </p>
            </div>
            <div class="footer">
                <p>You're receiving this because you showed interest in our products.</p>
                <p><a href="{urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}" class="unsubscribe">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {name},

We noticed you were interested in {product_name} but didn't complete your order.

{product_name} from PureLeven:
✓ 100% Organic
✓ Zero Chemicals  
✓ Farm-to-Table

Why PureLeven's {product_name}?
- Cold-pressed, never heated
- Sourced directly from farmers
- Lab-tested for purity
- Ships within 24 hours

{f'AI Note: {ai_context}' if ai_context else ''}

View it here: https://pureleven.com/products

Questions? Reply to this email or call +91-8081234567

---
You're receiving this because you showed interest in our products.
Unsubscribe: https://api.pureleven.com/api/abandoned/unsubscribe?lead_id={lead.get('id', '')}
    """
    
    return (subject, html_body, text_body)


def _campaign_2_social_proof(lead, interest_category="general", ai_context=""):
    """
    Day 15: Social proof - Show customer reviews and ratings
    """
    name = html.escape(lead.get("name", "there"))
    product_name = lead.get("interest_product", "PureLeven Products")
    
    subject = f"⭐ 4.9★ Why 50,000+ customers chose {product_name}"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2E7D32 0%, #558B2F 100%); padding: 20px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 24px; }}
            .content {{ padding: 30px; }}
            .stats-box {{ display: flex; justify-content: space-around; margin: 20px 0; background: #f0f5e9; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat {{ flex: 1; }}
            .stat-number {{ font-size: 28px; font-weight: bold; color: #2E7D32; }}
            .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
            .testimonial {{ background: #faf9f6; padding: 15px; border-left: 3px solid #2E7D32; margin: 15px 0; border-radius: 4px; }}
            .testimonial p {{ margin: 0; color: #333; font-size: 13px; line-height: 1.6; }}
            .testimonial-author {{ font-weight: 600; color: #2E7D32; font-size: 12px; margin-top: 8px; }}
            .stars {{ color: #FFB800; font-size: 14px; }}
            .cta-button {{ display: inline-block; background: #2E7D32; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
            .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⭐ Trusted by 50,000+</h1>
            </div>
            <div class="content">
                <div class="greeting" style="font-size: 16px; color: #333; margin-bottom: 20px;">Hi {name},</div>
                
                <p>You asked about {product_name}. Here's what thousands of satisfied customers are saying:</p>
                
                <div class="stats-box">
                    <div class="stat">
                        <div class="stat-number">4.9</div>
                        <div class="stat-label">Star Rating</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">50K+</div>
                        <div class="stat-label">Happy Customers</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">98%</div>
                        <div class="stat-label">Reorder Rate</div>
                    </div>
                </div>
                
                <div class="testimonial">
                    <p>"Best organic {product_name} I've found! Pure quality, no additives. Highly recommended for health-conscious families."</p>
                    <div class="testimonial-author">
                        <span class="stars">★★★★★</span> Priya M., Mumbai
                    </div>
                </div>
                
                <div class="testimonial">
                    <p>"Started using last month and can taste the difference. Worth every rupee. The freshness is incredible!"</p>
                    <div class="testimonial-author">
                        <span class="stars">★★★★★</span> Rajesh K., Bangalore
                    </div>
                </div>
                
                <div class="testimonial">
                    <p>"Finally found an alternative to store-bought. My kids actually enjoy eating healthy now!"</p>
                    <div class="testimonial-author">
                        <span class="stars">★★★★★</span> Anjali S., Delhi
                    </div>
                </div>
                
                <p style="text-align: center; margin-top: 30px; color: #666; font-size: 13px;">
                    <strong>Limited stock available</strong> - Popular products often sell out
                </p>
                
                <p style="text-align: center; margin-top: 15px;">
                    <a href="{urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_2', utm_medium='email', email=html.escape(lead.get('email', '')))}" class="cta-button">Join 50K+ Happy Customers →</a>
                </p>
            </div>
            <div class="footer">
                <p><a href="{urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}" style="color: #2E7D32; text-decoration: none;">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {name},

You asked about {product_name}. Here's what thousands of satisfied customers are saying:

⭐ 4.9 Star Rating | 50,000+ Happy Customers | 98% Reorder Rate

"Best organic {product_name} I've found! Pure quality, no additives. Highly recommended for health-conscious families."
★★★★★ Priya M., Mumbai

"Started using last month and can taste the difference. Worth every rupee!"
★★★★★ Rajesh K., Bangalore

"Finally found an alternative to store-bought. My kids actually enjoy eating healthy now!"
★★★★★ Anjali S., Delhi

Limited stock available - Popular products often sell out!

Join them: https://pureleven.com/products

---
Unsubscribe: https://api.pureleven.com/api/abandoned/unsubscribe?lead_id={lead.get('id', '')}
    """
    
    return (subject, html_body, text_body)


def _campaign_3_exclusive_offer(lead, interest_category="general", ai_context=""):
    """
    Day 30: Exclusive offer - Time-limited discount
    """
    name = html.escape(lead.get("name", "there"))
    product_name = lead.get("interest_product", "PureLeven Products")
    
    subject = f"🎁 Exclusive 20% off {product_name} — Today only!"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: #d32f2f; padding: 30px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 32px; font-weight: bold; }}
            .header p {{ margin: 10px 0 0 0; font-size: 14px; }}
            .content {{ padding: 30px; }}
            .offer-box {{ background: linear-gradient(135deg, #fff3cd 0%, #fff8e1 100%); border: 2px solid #d32f2f; border-radius: 8px; padding: 25px; text-align: center; margin: 20px 0; }}
            .offer-box h2 {{ color: #d32f2f; margin: 0; font-size: 40px; margin-bottom: 5px; }}
            .offer-box p {{ color: #666; margin: 0; font-size: 13px; }}
            .timer {{ background: #d32f2f; color: white; padding: 15px; border-radius: 6px; text-align: center; margin: 15px 0; font-weight: bold; }}
            .cta-button {{ display: inline-block; background: #d32f2f; color: white; padding: 14px 35px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px auto; display: block; width: fit-content; }}
            .terms {{ font-size: 11px; color: #999; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; }}
            .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎁 SPECIAL OFFER</h1>
                <p>For {name}</p>
            </div>
            <div class="content">
                <p>We want to welcome you to the PureLeven family!</p>
                
                <div class="offer-box">
                    <h2>20% OFF</h2>
                    <p>{product_name} - Just for you</p>
                </div>
                
                <div class="timer">
                    ⏰ Offer valid for next 48 hours only!
                </div>
                
                <p style="text-align: center; color: #333;">
                    <strong>Why this offer?</strong><br>
                    We value your trust and want you to experience the PureLeven difference at a special price.
                </p>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{urls.CHECKOUT}?discount=WELCOME20&utm_source=email&utm_campaign=abandoned_3&utm_medium=email&email={html.escape(lead.get('email', ''))}" class="cta-button">Claim 20% Discount →</a>
                </p>
                
                <div class="terms">
                    <p style="margin: 0;">
                        Code: <strong>WELCOME20</strong> | Minimum order: ₹499 | Valid until midnight tonight
                    </p>
                </div>
            </div>
            <div class="footer">
                <p><a href="{urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}" style="color: #2E7D32; text-decoration: none;">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {name},

We want to welcome you to the PureLeven family!

🎁 EXCLUSIVE OFFER FOR YOU

20% OFF {product_name}

⏰ Offer valid for next 48 hours only!

Why this offer?
We value your trust and want you to experience the PureLeven difference at a special price.

Use code: WELCOME20
Minimum order: ₹499

Claim your discount: https://pureleven.com/checkout?discount=WELCOME20

---
Unsubscribe: https://api.pureleven.com/api/abandoned/unsubscribe?lead_id={lead.get('id', '')}
    """
    
    return (subject, html_body, text_body)


def _campaign_4_urgency(lead, interest_category="general", ai_context=""):
    """
    Day 45: Urgency - Stock running low
    """
    name = html.escape(lead.get("name", "there"))
    product_name = lead.get("interest_product", "PureLeven Products")
    
    subject = f"⚠️ Only 12 units left of {product_name} — Next batch in 2 weeks"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #f57c00 0%, #e65100 100%); padding: 25px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 22px; }}
            .content {{ padding: 30px; }}
            .warning-box {{ background: #fff3e0; border-left: 4px solid #f57c00; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .warning-box p {{ color: #e65100; font-weight: 600; margin: 0; }}
            .availability {{ background: #f5f5f5; padding: 15px; border-radius: 6px; text-align: center; margin: 20px 0; }}
            .availability strong {{ color: #d32f2f; font-size: 18px; }}
            .waitlist-note {{ background: #e8f5e9; border-left: 4px solid #2E7D32; padding: 15px; border-radius: 4px; margin: 20px 0; font-size: 13px; color: #1b5e20; }}
            .cta-button {{ display: inline-block; background: #f57c00; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px auto; display: block; width: fit-content; }}
            .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚠️ Limited Stock Alert</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                
                <div class="warning-box">
                    <p>The {product_name} batch you were interested in is running low!</p>
                </div>
                
                <div class="availability">
                    <p style="margin: 0 0 10px 0; font-size: 13px; color: #666;">Current Stock</p>
                    <strong>Only 12 units remaining</strong>
                    <p style="margin: 10px 0 0 0; font-size: 13px; color: #999;">Next restock in 2 weeks</p>
                </div>
                
                <p style="text-align: center; color: #333; margin: 25px 0;">
                    We're getting overwhelmed with orders! The last batch sold out in 3 days.
                </p>
                
                <div class="waitlist-note">
                    <p style="margin: 0; font-weight: 600;">Want a guaranteed unit?</p>
                    <p style="margin: 8px 0 0 0;">Order today to get it from this batch. Or join our waitlist to get priority for the next batch.</p>
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_4', utm_medium='email', email=html.escape(lead.get('email', '')))}" class="cta-button">Secure Your Unit Now →</a>
                </p>
            </div>
            <div class="footer">
                <p><a href="{urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}" style="color: #2E7D32; text-decoration: none;">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {name},

⚠️ Limited Stock Alert

The {product_name} batch you were interested in is running low!

Current Stock: Only 12 units remaining
Next restock: In 2 weeks

We're getting overwhelmed with orders! The last batch sold out in 3 days.

Want a guaranteed unit?
Order today to get it from this batch. Or join our waitlist for priority on the next batch.

Secure yours: https://pureleven.com/products

---
Unsubscribe: https://api.pureleven.com/api/abandoned/unsubscribe?lead_id={lead.get('id', '')}
    """
    
    return (subject, html_body, text_body)


def _campaign_5_testimonial(lead, interest_category="general", ai_context=""):
    """
    Day 60: Testimonial from similar customer (AI personalization)
    """
    name = html.escape(lead.get("name", "there"))
    product_name = lead.get("interest_product", "PureLeven Products")
    
    subject = f"✨ Someone just like you loves our {product_name}"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2E7D32 0%, #558B2F 100%); padding: 20px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 22px; }}
            .content {{ padding: 30px; }}
            .testimonial-card {{ background: linear-gradient(135deg, #f0f5e9 0%, #faf9f6 100%); border: 1px solid #e0e0e0; border-radius: 8px; padding: 25px; margin: 20px 0; text-align: center; }}
            .avatar {{ width: 80px; height: 80px; background: #2E7D32; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; color: white; font-size: 32px; }}
            .testimonial-card h3 {{ color: #2E7D32; margin: 0 0 10px 0; font-size: 16px; }}
            .testimonial-card p {{ color: #666; margin: 10px 0; font-size: 14px; line-height: 1.6; font-style: italic; }}
            .testimonial-card .details {{ font-size: 12px; color: #999; margin-top: 15px; }}
            .stars {{ color: #FFB800; font-size: 16px; }}
            .cta-button {{ display: inline-block; background: #2E7D32; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px auto; display: block; width: fit-content; }}
            .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✨ Real Stories from Real Customers</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                
                <p>We know choosing organic products can be a big decision. That's why we want to share what people just like you are saying:</p>
                
                <div class="testimonial-card">
                    <div class="avatar">😊</div>
                    <h3>Deepak K., Pune</h3>
                    <p>"I was skeptical about ordering online, but PureLeven delivered! The {product_name} is noticeably fresher than what I get at my local market. My family has switched completely."</p>
                    <div class="stars">★★★★★</div>
                    <div class="details">Ordered 3 months ago | Reordered 2x since</div>
                </div>
                
                {f'<div style="background: #e8f5e9; border-left: 4px solid #2E7D32; padding: 15px; margin: 20px 0; border-radius: 4px; color: #1b5e20; font-size: 13px;"><p style="margin: 0;"><strong>💡 Why Deepak chose PureLeven:</strong><br>{ai_context}</p></div>' if ai_context else ''}
                
                <p style="text-align: center; color: #666; font-size: 13px; margin-top: 25px;">
                    Ready to have your own PureLeven story?
                </p>
                
                <p style="text-align: center;">
                    <a href="{urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_5', utm_medium='email', email=html.escape(lead.get('email', '')))}" class="cta-button">Start Your Journey →</a>
                </p>
            </div>
            <div class="footer">
                <p><a href="https://api.pureleven.com/api/abandoned/unsubscribe?lead_id={lead.get('id', '')}" style="color: #2E7D32; text-decoration: none;">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {name},

✨ Real Stories from Real Customers

We know choosing organic products can be a big decision. Here's what people just like you are saying:

"I was skeptical about ordering online, but PureLeven delivered! The {product_name} is noticeably fresher than what I get at my local market. My family has switched completely."

Deepak K., Pune
★★★★★
Ordered 3 months ago | Reordered 2x since

{f'Why Deepak chose PureLeven: {ai_context}' if ai_context else ''}

Ready to have your own PureLeven story?

Start yours: {urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_5', utm_medium='email', email=html.escape(lead.get('email', '')))}

---
Unsubscribe: {urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}
    """
    
    return (subject, html_body, text_body)


def _campaign_6_winback(lead, interest_category="general", ai_context=""):
    """
    Day 75: Final winback - Last chance before pause
    """
    name = html.escape(lead.get("name", "there"))
    product_name = lead.get("interest_product", "PureLeven Products")
    
    subject = f"💚 Last chance: Complete your PureLeven experience"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #2E7D32 0%, #558B2F 100%); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 26px; }}
            .content {{ padding: 30px; }}
            .message-box {{ background: #f0f5e9; border-left: 4px solid #2E7D32; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .message-box p {{ color: #1b5e20; margin: 10px 0; }}
            .message-box strong {{ font-size: 16px; }}
            .faq-box {{ background: #faf9f6; border: 1px solid #e8e8e8; border-radius: 6px; padding: 15px; margin: 20px 0; font-size: 13px; }}
            .faq-box p {{ margin: 8px 0; color: #555; }}
            .cta-button {{ display: inline-block; background: #2E7D32; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px auto; display: block; width: fit-content; }}
            .secondary-button {{ display: inline-block; border: 2px solid #2E7D32; color: #2E7D32; padding: 10px 25px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 15px auto; display: block; width: fit-content; }}
            .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💚 We're Here for You</h1>
            </div>
            <div class="content">
                <p style="font-size: 16px; color: #333;">Hi {name},</p>
                
                <div class="message-box">
                    <p style="margin-top: 0;"><strong>We noticed you haven't ordered yet, and we want to help!</strong></p>
                    <p style="margin-bottom: 0;">If you have any questions or concerns, we're here to assist. No pressure — just pure, organic goodness when you're ready.</p>
                </div>
                
                <p>Still deciding? Here are answers to common questions:</p>
                
                <div class="faq-box">
                    <p><strong>❓ Is it really worth it?</strong><br>Yes. 50,000+ customers reorder regularly. They wouldn't if it wasn't.</p>
                    
                    <p style="margin-top: 15px;"><strong>❓ How long does shipping take?</strong><br>24-48 hours to most of India. Fresh packed the same day.</p>
                    
                    <p style="margin-top: 15px;"><strong>❓ What if I don't like it?</strong><br>100% money-back guarantee. No questions asked.</p>
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_6', utm_medium='email', email=html.escape(lead.get('email', '')))}" class="cta-button">Try {product_name} Now →</a>
                </p>
                
                <p style="text-align: center; margin-top: 15px;">
                    <a href="{urls.CONTACT}?utm_source=email&utm_campaign=abandoned_6&subject=Question" class="secondary-button">Talk to Our Team</a>
                </p>
                
                <p style="color: #999; font-size: 12px; text-align: center; margin-top: 30px;">
                    After this, we'll pause sending emails for 90 days to respect your space.<br>
                    You can always reach out to us anytime.
                </p>
            </div>
            <div class="footer">
                <p><a href="{urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}" style="color: #2E7D32; text-decoration: none;">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Hi {name},

💚 We're Here for You

We noticed you haven't ordered yet, and we want to help!

If you have any questions or concerns, we're here to assist. No pressure — just pure, organic goodness when you're ready.

Still deciding? Here are answers to common questions:

❓ Is it really worth it?
Yes. 50,000+ customers reorder regularly.

❓ How long does shipping take?
24-48 hours to most of India. Fresh packed the same day.

❓ What if I don't like it?
100% money-back guarantee. No questions asked.

Try it now: {urls.get_product_link(category=interest_category, utm_source='email', utm_campaign='abandoned_6', utm_medium='email', email=html.escape(lead.get('email', '')))}

Talk to our team: {urls.CONTACT}

After this, we'll pause sending emails for 90 days to respect your space.
You can always reach out to us anytime.

---
Unsubscribe: {urls.get_abandoned_unsubscribe_link(lead.get('id', ''))}
    """
    
    return (subject, html_body, text_body)
