"""
Wabis AI Reply Generator - Generate intelligent responses to incoming WhatsApp messages

Handles:
- Greetings → Warm welcome with trained data
- Product questions → Specific info from training data (e.g., black pepper → product details)
- Complaints → Acknowledgment + escalation
- Customer inquiries → Matched against trained responses
- Unsubscribe requests → Confirmation
"""

import logging
from typing import Any, Optional
import json
from app.ai.openrouter_client import ai_client
from app.ai.gemini_client import gemini_client
from app.ai.intent_registry import is_pure_greeting
from app.ai.product_knowledge import detect_product
from app.ai.training_data_loader import (
    find_best_match,
    find_product_response,
    is_greeting,
    extract_product_mention,
    extract_product_mentions,
    get_greeting_response,
    get_product_catalog,
)
from app.ai.pricing_formatter import PricingFormatter
from app.ai.whatsapp_response_pipeline import generate_dynamic_reply

logger = logging.getLogger(__name__)


class WabisReplyGenerator:
    """Generate AI responses to customer messages via Wabis"""

    COMPLAINT_KEYWORDS = (
        "refund",
        "money back",
        "returned",
        "return",
        "not received",
        "did not receive",
        "didn't receive",
        "wrong item",
        "damaged",
        "damage",
        "broken",
        "complaint",
        "issue",
        "late",
        "delay",
        "delayed",
        "missing",
        "missing item",
        "sent only",
        "short",
        "replace",
        "replacement",
    )

    COMBO_KEYWORDS = (
        "combo",
        "combo offer",
        "combo pack",
        "bundle",
        "special offer",
        "special combo",
    )

    WHOLESALE_KEYWORDS = (
        "wholesale",
        "bulk",
        "bulk rate",
        "bulk price",
        "wholesale rate",
        "wholesale price",
        "b2b",
        "trader",
        "reseller",
        "hotel",
        "restaurant",
    )

    NEGATION_KEYWORDS = (
        "venda",
        "vendaa",
        "vendallo",
        "not interested",
        "dont want",
        "don't want",
        "do not want",
        "no need",
        "later nokkam",
        "later nokkam",
        "vendam",
    )

    DELIVERY_KEYWORDS = (
        "delivery",
        "deliver",
        "shipping",
        "ship",
        "courier",
        "dispatch",
        "pincode",
        "pin code",
        "days",
        "day",
        "divasam",
        "tracking",
        "track",
        "how long",
        "how many days",
        "when",
        "reach",
        "arrive",
        "eta",
        "timeline",
    )

    PRICE_KEYWORDS = (
        "price",
        "rate",
        "cost",
        "how much",
        "how many",
        "ethra",
        "ethraya",
        "ethra aanu",
        "vil",
        "vila",
        "price list",
        "mrp",
    )

    ORDER_KEYWORDS = (
        "venam",
        "need",
        "buy",
        "order",
        "place",
        "ok",
        "okay",
        "yes",
        "engane",
        "engane ayakunath",
        "ayakunath",
        "ayakkunath",
        "ayakkum",
        "how to order",
        "how can order",
        "how to buy",
        "how will you send",
        "edukkam",
        "edukam",
        "take",
        "book",
        "confirm",
        "purchase",
        "send details",
        "how to order",
        "how can i order",
    )

    VALUE_KEYWORDS = (
        "expensive",
        "costly",
        "kooduthal",
        "high rate",
        "premium",
        "budget",
        "cheap",
        "worth",
        "pricey",
        "kuravaanu",
        "kuravaanuo",
    )
    
    @staticmethod
    def generate_reply(
        incoming_message: str,
        customer_phone: str,
        customer_name: str = "Customer",
        conversation_id: str = "",
        product_id: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Generate an intelligent AI reply to customer message.
        
        Uses trained data for better, contextual responses.
        
        Args:
            incoming_message: Customer's message text
            customer_phone: Customer phone number
            customer_name: Customer name for personalization
            conversation_id: Wabis conversation ID
            product_id: Related product if any
            context: Additional context (order history, etc)
            
        Returns:
            {
                "reply_text": "Generated response message",
                "intent": "greeting|question_product|complaint|...",
                "should_escalate": bool,
                "escalation_reason": "...",
                "suggested_action": "send_reply|escalate|no_reply|..."
            }
        """
        try:
            media_type = WabisReplyGenerator._media_message_type(incoming_message)
            if media_type:
                reply_style = WabisReplyGenerator._detect_reply_style(incoming_message)
                return WabisReplyGenerator._handle_media_message(media_type, reply_style)

            if is_pure_greeting(incoming_message, product_detected=bool(detect_product(incoming_message))):
                logger.warning(
                    "[AI] Pure greeting detected for %s: '%s' - skipping AI reply to let Wabis own welcome",
                    customer_phone,
                    incoming_message,
                )
                return {
                    "reply_text": None,
                    "intent": "greeting",
                    "should_escalate": False,
                    "escalation_reason": None,
                    "suggested_action": "skip_reply"
                }

            result = generate_dynamic_reply(
                incoming_message=incoming_message,
                customer_name=customer_name,
                context=context,
            )

            analysis = result.get("message_understanding") or {}
            reply_style = str(analysis.get("reply_style") or WabisReplyGenerator._detect_reply_style(incoming_message))

            if result.get("intent") in {"followup", "negation"}:
                try:
                    from app.services.product_followup_service import cancel_product_followups
                    from app.ai.conversation_state_manager import reset_conversation_state

                    reason = "customer_deferred_decision" if result.get("intent") == "followup" else "customer_not_interested"
                    cancel_product_followups(customer_phone, reason=reason)
                    reset_conversation_state(customer_phone)
                except Exception as exc:
                    logger.warning(f"[AI] Failed to cancel queued followups/state for {customer_phone}: {exc}")
                return {
                    "reply_text": result.get("reply_text")
                    or (
                        PricingFormatter.build_no_interest_reply(style=reply_style)
                        if result.get("intent") == "negation"
                        else PricingFormatter.build_defer_decision_reply(style=reply_style)
                    ),
                    "intent": "product_negation" if result.get("intent") == "negation" else "followup",
                    "should_escalate": False,
                    "escalation_reason": None,
                    "suggested_action": "send_reply",
                    "message_understanding": analysis,
                }

            if result.get("intent") == "wholesale":
                try:
                    from app.ai.alert_sender import alert_bulk_inquiry

                    alert_bulk_inquiry(customer_phone, incoming_message)
                except Exception as exc:
                    logger.warning("[AI] Wholesale alert skipped for %s: %s", customer_phone, exc)

            if result.get("product_key") and result.get("suggested_action") == "send_reply":
                scenario = str(analysis.get("scenario") or result.get("intent") or "availability")
                WabisReplyGenerator._remember_product_journey(
                    customer_phone,
                    result.get("product_key"),
                    scenario,
                    reply_style,
                    customer_reference=result.get("customer_reference")
                    or (analysis.get("customer_reference") if isinstance(analysis, dict) else None)
                    or result.get("display_name")
                    or (context or {}).get("customer_reference"),
                    follow_up_plan=result.get("follow_up_plan"),
                    queue_followups=bool(result.get("follow_up_plan")),
                )

            return result
                
        except Exception as e:
            logger.error(f"Error generating reply for {customer_phone}: {e}")
            return {
                "reply_text": f"Thank you for your message! We'll get back to you shortly.",
                "intent": "unknown",
                "should_escalate": True,
                "escalation_reason": "AI generation error",
                "suggested_action": "escalate"
            }
    
    @staticmethod
    def _handle_complaint(message: str, customer_name: str) -> dict[str, Any]:
        """Handle complaint messages"""
        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="complaint",
            style="english",
            customer_message=message,
            customer_name=customer_name,
        )
        reply_text = WabisReplyGenerator._join_reply_lines(
            bridge.get("opening_line") or f"Hi {customer_name},",
            bridge.get("closing_line")
            or (
                "We sincerely apologize for the inconvenience. Your concern is important to us. "
                "We're escalating this to our support team who will reach out within 2 hours."
            ),
        )
        return {
            "reply_text": reply_text,
            "intent": "complaint",
            "should_escalate": True,
            "escalation_reason": "Customer complaint - needs human attention",
            "suggested_action": "escalate"
        }

    @staticmethod
    def _looks_like_complaint(message: str) -> bool:
        """Detect complaint-like messages early so they don't get misrouted to pricing."""
        msg_lower = (message or "").lower()
        return any(keyword in msg_lower for keyword in WabisReplyGenerator.COMPLAINT_KEYWORDS)

    @staticmethod
    def _looks_like_combo_request(message: str) -> bool:
        """Detect combo / bundle requests early."""
        msg_lower = (message or "").lower()
        return any(keyword in msg_lower for keyword in WabisReplyGenerator.COMBO_KEYWORDS)

    @staticmethod
    def _detect_reply_style(message: str) -> str:
        """
        Detect whether the customer is writing in English, Manglish, or Malayalam.

        If the message contains English script with Malayalam-style terms like
        "undo", "veno", or "ethra", we keep the reply in Manglish.
        """
        msg = (message or "").strip()
        msg_lower = msg.lower()

        if any("\u0D00" <= ch <= "\u0D7F" for ch in msg):
            return "malayalam"

        manglish_markers = (
            "undo",
            "undu",
            "veno",
            "venam",
            "venda",
            "vendam",
            "ethra",
            "ethrya",
            "engane",
            "ayakunath",
            "ayakkunath",
            "ayakkum",
            "aano",
            "aano",
            "kooduthal",
            "divasam",
            "ayachal",
            "venengil",
            "edukkam",
            "edukkunath",
            "parayamo",
            "cheyyam",
            "cheyyamo",
            "tharamo",
            "undo ?",
        )
        if any(marker in msg_lower for marker in manglish_markers):
            return "manglish"

        return "english"

    @staticmethod
    def _media_message_type(message: str) -> str:
        text = (message or "").strip().lower()
        if text.startswith("[[media:") and text.endswith("]]"):
            return text.removeprefix("[[media:").removesuffix("]]").strip() or "media"
        return ""

    @staticmethod
    def _handle_media_message(media_type: str, reply_style: str = "english") -> dict[str, Any]:
        style_key = PricingFormatter._style_key(reply_style)
        copy = {
            "english": (
                f"I received the {media_type} 😊\n\n"
                "If this is for an order/payment, please type one line also so I can understand it clearly."
            ),
            "manglish": (
                f"{media_type} kitti 😊\n\n"
                "Order/payment related aanenkil oru line text ayachu parayamo? Appo clear aayi help cheyyam."
            ),
            "malayalam": (
                f"{media_type} കിട്ടി 😊\n\n"
                "Order/payment related ആണെങ്കിൽ ഒരു line text കൂടി അയയ്ക്കാമോ? അപ്പോൾ clear ആയി help ചെയ്യാം."
            ),
        }[style_key]
        return {
            "reply_text": copy,
            "intent": "media_received",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
            "media_mode": "text",
            "extra_messages": [],
            "message_understanding": {
                "detected_intent": "media_received",
                "detected_language": style_key,
                "media_type": media_type,
            },
        }

    @staticmethod
    def _looks_like_wholesale_request(message: str) -> bool:
        """Detect wholesale / bulk buying requests early."""
        msg_lower = (message or "").lower()
        return any(keyword in msg_lower for keyword in WabisReplyGenerator.WHOLESALE_KEYWORDS)

    @staticmethod
    def _looks_like_negation(message: str) -> bool:
        msg_lower = (message or "").lower()
        return any(keyword in msg_lower for keyword in WabisReplyGenerator.NEGATION_KEYWORDS)

    @staticmethod
    def _contains_any(message: str, keywords: tuple[str, ...]) -> bool:
        msg_lower = (message or "").lower()
        return any(keyword in msg_lower for keyword in keywords)

    @staticmethod
    def _generate_bridge_lines(
        *,
        scenario: str,
        style: str,
        customer_message: str,
        customer_name: str,
        product_key: Optional[str] = None,
        product_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, str]:
        """Ask Gemini for short conversational lines around fixed factual content."""
        product_payload = product_payload or {}
        instruction_map = {
            "availability": "Confirm stock warmly and give a short helpful follow-up. Do not invent facts.",
            "price_check": "Give a short pricing intro before the factual block, then a friendly soft CTA.",
            "delivery": "Answer only the delivery-time question. Keep it short and polite. Do not pitch the product.",
            "value_objection": "Acknowledge the concern about price and reassure on value, quality, and freshness.",
            "order_intent": "Move the customer toward order capture by politely asking for name, full address, pincode, phone number, and quantity.",
            "clarification": "Ask whether they want price, delivery, or order help, in a friendly way.",
            "negation": "Be polite, non-pushy, and close the sales loop gently.",
            "combo_offer": "Introduce the combo offers in a value-focused way.",
            "wholesale": "Reply like a helpful wholesale assistant and ask for the minimum details needed for a quote.",
            "complaint": "Be empathetic, apologize sincerely, and promise a quick human follow-up.",
            "general": "Keep it warm, short, and helpful.",
        }
        facts = {
            "product_key": product_key,
            "product_name": product_payload.get("display_name") or product_key,
            "origin": product_payload.get("origin"),
            "description": product_payload.get("description"),
            "recommended_pack": product_payload.get("recommended_pack"),
            "recommendation": product_payload.get("recommendation"),
            "scenario": scenario,
        }
        try:
            return gemini_client.generate_whatsapp_reply_lines(
                scenario=scenario,
                customer_message=customer_message,
                customer_name=customer_name,
                style=style,
                product_name=str(product_payload.get("display_name") or product_key or ""),
                facts=facts,
                instruction=instruction_map.get(scenario, instruction_map["general"]),
            )
        except Exception as exc:
            logger.warning(f"[AI] Gemini bridge lines failed for {scenario}: {exc}")
            return {"opening_line": "", "closing_line": ""}

    @staticmethod
    def _join_reply_lines(*lines: str) -> str:
        return "\n\n".join(line.strip() for line in lines if line and line.strip())

    @staticmethod
    def _rewrite_training_match_reply(
        *,
        customer_message: str,
        customer_name: str,
        reply_style: str,
        training_entry: dict[str, Any],
    ) -> str:
        """Polish a matched training answer using Gemini while preserving the facts."""
        raw_answer = str(training_entry.get("ideal_response") or "").strip()
        if not raw_answer:
            return ""

        facts = {
            "matched_question": training_entry.get("customer_input"),
            "matched_answer": raw_answer,
            "product": training_entry.get("product"),
            "product_name": training_entry.get("product_name"),
            "category": training_entry.get("category"),
            "language": training_entry.get("language"),
        }
        try:
            bridge = gemini_client.generate_whatsapp_reply_lines(
                scenario="training_match",
                customer_message=customer_message,
                customer_name=customer_name,
                style=reply_style,
                product_name=str(training_entry.get("product_name") or training_entry.get("product") or ""),
                facts=facts,
                instruction=(
                    "Rewrite the matched training answer into a polished WhatsApp reply. "
                    "Keep the factual meaning, fix awkward wording, and make it human and concise. "
                    "Put the full improved answer in opening_line and leave closing_line empty. "
                    "Do not invent new facts."
                ),
            )
            polished = bridge.get("opening_line") or ""
            if polished:
                return polished
        except Exception as exc:
            logger.warning(f"[AI] Gemini rewrite failed for training match: {exc}")

        product_key = str(training_entry.get("product") or "").strip()
        if product_key:
            category = str(training_entry.get("category") or "").strip().lower()
            scenario_map = {
                "delivery_query": "delivery",
                "delivery": "delivery",
                "price_check": "price_check",
                "product_inquiry": "availability",
                "order_placement": "order_intent",
                "payment_query": "clarification",
                "wholesale_inquiry": "wholesale",
                "complaint": "complaint",
            }
            scenario = scenario_map.get(category, "availability")
            product_in_message = bool(extract_product_mention(customer_message))
            if scenario == "delivery" and not product_in_message:
                style_key = PricingFormatter._style_key(reply_style)
                delivery_copy = {
                    "english": "Usually 4-7 days for delivery. If you share your pincode, I can give the exact estimate.",
                    "manglish": "Usually 4-7 days ullil delivery kittum. Pincode ayachal exact estimate parayam.",
                    "malayalam": "സാധാരണ 4-7 ദിവസത്തിനുള്ളിൽ delivery കിട്ടും. Pincode അയച്ചാൽ കൃത്യമായ estimate പറയാം.",
                }
                return delivery_copy.get(style_key, delivery_copy["english"])
            fallback = PricingFormatter.build_product_journey_reply(
                product_key=product_key,
                style=reply_style,
                scenario=scenario,
                customer_reference=WabisReplyGenerator._extract_customer_product_reference(
                    product_key,
                    customer_message,
                ),
            )
            if fallback:
                return fallback

        return " ".join(raw_answer.split())

    @staticmethod
    def _analyze_customer_message(
        message: str,
        reply_style: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Infer product, tone, and reply scenario for the incoming customer message."""
        context = context or {}
        product_mentions = extract_product_mentions(message)
        product_mentioned = (
            product_mentions[0]
            if product_mentions
            else extract_product_mention(message)
            or context.get("product_key")
        )

        if not product_mentioned:
            return {
                "style": reply_style,
                "scenario": "general",
                "product": None,
                "product_mentions": [],
            }

        if WabisReplyGenerator._looks_like_negation(message):
            scenario = "negation"
        elif WabisReplyGenerator._contains_any(message, WabisReplyGenerator.DELIVERY_KEYWORDS):
            scenario = "delivery"
        elif WabisReplyGenerator._contains_any(message, WabisReplyGenerator.VALUE_KEYWORDS):
            scenario = "value_objection"
        elif WabisReplyGenerator._contains_any(message, WabisReplyGenerator.ORDER_KEYWORDS):
            scenario = "order_intent"
        elif WabisReplyGenerator._contains_any(message, WabisReplyGenerator.PRICE_KEYWORDS):
            scenario = "price_check"
        else:
            scenario = "availability"

        return {
            "style": reply_style,
            "scenario": scenario,
            "product": product_mentioned,
            "product_mentions": product_mentions or ([product_mentioned] if product_mentioned else []),
        }

    @staticmethod
    def _extract_customer_product_reference(product_key: str, message: str) -> str:
        """Try to reuse the customer's own product wording in the reply."""
        catalog = PricingFormatter.get_product_catalog_entry(product_key) or {}
        msg_lower = (message or "").lower()
        best_match = None
        for alias in catalog.get("aliases", []):
            alias_lower = alias.lower()
            if alias_lower in msg_lower:
                if best_match is None or len(alias_lower) > len(best_match):
                    best_match = alias
        return best_match or catalog.get("display_name", product_key)

    @staticmethod
    def _build_follow_up_plan(scenario: str) -> list[dict[str, Any]]:
        if scenario in {"availability", "price_check", "delivery", "value_objection", "clarification", "order_intent"}:
            return [
                {"after_minutes": 5, "stage": "gentle_reminder"},
                {"after_minutes": 30, "stage": "combo_offer"},
                {"after_minutes": 240, "stage": "image_only"},
                {"after_minutes": 360, "stage": "soft_nudge"},
                {"after_minutes": 1380, "stage": "final_followup"},
            ]
        return []

    @staticmethod
    def _remember_product_journey(
        customer_phone: str,
        product_key: Optional[str],
        scenario: str,
        reply_style: str,
        customer_reference: Optional[str] = None,
        follow_up_plan: Optional[list[dict[str, Any]]] = None,
        queue_followups: bool = True,
    ) -> None:
        if not customer_phone:
            return
        try:
            from app.ai.conversation_state_manager import set_conversation_state
            from app.services.product_followup_service import queue_product_followups

            plan = follow_up_plan if follow_up_plan is not None else WabisReplyGenerator._build_follow_up_plan(scenario)
            set_conversation_state(
                phone=customer_phone,
                owner="ai",
                owner_reason=f"product_{scenario}",
                flow_id="product_journey",
                flow_step="awaiting_customer_reply" if scenario != "order_intent" else "awaiting_order_details",
                expected_responses="yes,no,price,delivery,order,wholesale",
                context={
                    "product_key": product_key,
                    "scenario": scenario,
                    "reply_style": reply_style,
                    "customer_reference": customer_reference,
                    "follow_up_plan": plan,
                },
            )
            if queue_followups and plan:
                queue_product_followups(
                    phone=customer_phone,
                    product_key=product_key,
                    scenario=scenario,
                    reply_style=reply_style,
                    follow_up_plan=plan,
                    customer_reference=customer_reference,
                )
        except Exception as exc:
            logger.warning(f"[AI] Failed to persist conversation state for {customer_phone}: {exc}")
    
    @staticmethod
    def _handle_bulk_inquiry(message: str, customer_name: str) -> dict[str, Any]:
        """Handle bulk inquiry messages"""
        return {
            "reply_text": (
                f"Hi {customer_name},\n\n"
                "Thank you for your interest in bulk orders! We'd love to help. "
                "I'm connecting you with our B2B sales team who specialize in bulk pricing and customization.\n\n"
                "You'll hear from them shortly!"
            ),
            "intent": "bulk_inquiry",
            "should_escalate": True,
            "escalation_reason": "Bulk inquiry - B2B sales team needed",
            "suggested_action": "escalate"
        }

    @staticmethod
    def _handle_wholesale_inquiry(message: str, customer_name: str, customer_phone: str, reply_style: str = "english") -> dict[str, Any]:
        """Handle wholesale / bulk buyer messages with a clean reply and owner alert."""
        try:
            from app.ai.alert_sender import alert_bulk_inquiry

            alert_bulk_inquiry(customer_phone, message)
        except Exception as exc:
            logger.warning(f"[AI] Wholesale alert skipped for {customer_phone}: {exc}")

        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="wholesale",
            style=reply_style,
            customer_message=message,
            customer_name=customer_name,
        )
        reply_text = WabisReplyGenerator._join_reply_lines(
            bridge.get("opening_line") or PricingFormatter.build_wholesale_reply(style=reply_style).split("\n\n")[0],
            PricingFormatter.build_wholesale_reply(style=reply_style).split("\n\n", 1)[1] if "\n\n" in PricingFormatter.build_wholesale_reply(style=reply_style) else "",
            bridge.get("closing_line"),
        )

        return {
            "reply_text": reply_text or PricingFormatter.build_wholesale_reply(style=reply_style),
            "intent": "wholesale_inquiry",
            "should_escalate": True,
            "escalation_reason": "Wholesale / bulk inquiry - B2B sales team needed",
            "suggested_action": "escalate"
        }
    
    @staticmethod
    def _handle_purchase_intent(message: str, customer_name: str) -> dict[str, Any]:
        """Handle purchase intent messages"""
        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="order_intent",
            style="english",
            customer_message=message,
            customer_name=customer_name,
        )
        reply_text = WabisReplyGenerator._join_reply_lines(
            bridge.get("opening_line") or f"Hi {customer_name},",
            bridge.get("closing_line")
            or (
                "Great! I can help you with your order. Our team will reach out within 30 minutes "
                "with all the details and answer any questions you have."
            ),
        )
        return {
            "reply_text": reply_text,
            "intent": "purchase_intent",
            "should_escalate": True,
            "escalation_reason": "High-intent customer - sales team follow-up",
            "suggested_action": "escalate"
        }
    
    @staticmethod
    def _handle_product_question(message: str, customer_name: str, product_id: str = "") -> dict[str, Any]:
        """Handle product-specific questions"""
        from app.storage import get_db_connection

        with get_db_connection() as conn:
            product = None
            if product_id:
                product = conn.execute(
                    "SELECT * FROM shopify_products WHERE id = ? LIMIT 1",
                    (product_id,)
                ).fetchone()
            
            product_info = ""
            if product:
                product_dict = dict(product)
                product_info = f"\n\n📦 **{product_dict.get('title', 'Product')}**\n"
                if product_dict.get('description'):
                    product_info += f"{product_dict['description'][:200]}...\n"
                if product_dict.get('price'):
                    product_info += f"💰 Price: ₹{product_dict['price']}"
        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="general",
            style="english",
            customer_message=message,
            customer_name=customer_name,
            product_key=product_id or "general",
            product_payload={
                "display_name": product.get("title") if product else product_id,
                "description": product_dict.get("description") if product else "",
                "origin": "",
            } if product else {},
        )
        
        return {
            "reply_text": WabisReplyGenerator._join_reply_lines(
                bridge.get("opening_line") or f"Hi {customer_name},",
                "Thanks for your question! Here's what I found:" + product_info,
                bridge.get("closing_line")
                or "For more details or to purchase, reply with 'ORDER' or our team will be happy to help!",
            ),
            "intent": "question_product",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply"
        }
    
    @staticmethod
    def _handle_unsubscribe(customer_name: str) -> dict[str, Any]:
        """Handle unsubscribe requests"""
        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="general",
            style="english",
            customer_message="unsubscribe",
            customer_name=customer_name,
        )
        return {
            "reply_text": WabisReplyGenerator._join_reply_lines(
                bridge.get("opening_line") or f"Hi {customer_name},",
                "We've unsubscribed you from our marketing messages. You won't receive any more updates from us.",
                bridge.get("closing_line") or "We'll miss you! Reply anytime if you'd like to re-subscribe.",
            ),
            "intent": "unsubscribe",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply"
        }
    
    @staticmethod
    def _handle_positive_engagement(message: str, customer_name: str) -> dict[str, Any]:
        """Handle positive feedback and affirmations"""
        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="general",
            style="english",
            customer_message=message,
            customer_name=customer_name,
        )
        return {
            "reply_text": WabisReplyGenerator._join_reply_lines(
                bridge.get("opening_line") or f"Hi {customer_name},",
                bridge.get("closing_line")
                or "Thank you so much! We appreciate your kind words and love serving you.",
            ),
            "intent": "positive",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply"
        }
    
    @staticmethod
    def _handle_general_inquiry(message: str, customer_name: str) -> dict[str, Any]:
        """Handle general questions and inquiries"""
        bridge = WabisReplyGenerator._generate_bridge_lines(
            scenario="general",
            style="english",
            customer_message=message,
            customer_name=customer_name,
        )
        return {
            "reply_text": WabisReplyGenerator._join_reply_lines(
                bridge.get("opening_line") or f"Hi {customer_name},",
                bridge.get("closing_line")
                or "Thanks for reaching out! I'm here to help. Could you please share a bit more about what you need?",
            ),
            "intent": "general",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply"
        }
    
    @staticmethod
    def _reformat_pricing_response(response_text: str, product_name: str) -> str:
        """
        Reformat pricing information in responses to be clean and structured.
        
        Detects if response contains pricing (₹ symbol) and reformats into table format.
        
        Args:
            response_text: Original response text from training data
            product_name: Product name (for context)
            
        Returns:
            Reformatted response with clean pricing table or original if no pricing found
        """
        if not response_text or "₹" not in response_text:
            return response_text  # No pricing, return as-is
        
        # Check if response already has clean formatting (has pipe separator)
        if "|" in response_text:
            return response_text  # Already formatted
        
        # Response contains pricing but not formatted - return as-is for now
        # (Full parsing would require complex regex; defer to catalog search handler)
        logger.info(f"Pricing detected in response for {product_name}, kept original format")
        return response_text
