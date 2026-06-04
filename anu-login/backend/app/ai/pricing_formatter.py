from __future__ import annotations

import logging
from typing import Any, Optional

from app.ai.delivery_policy import delivery_breakdown, delivery_label
from app.ai.product_knowledge import (
    build_alias_map,
    detect_product,
    get_combo_offers,
    get_image_entries,
    get_primary_image_url,
    get_product,
    list_products,
    reload_catalog,
)

logger = logging.getLogger(__name__)


REPLY_STYLE_COPY: dict[str, dict[str, str]] = {
    "english": {
        "availability": "Available 😊",
        "price_intro": "Sharing the current size options below.",
        "details_intro": "Here’s the quick product picture.",
        "delivery_time": "Usually 4-7 days ullil reach cheyyum. Pincode share ചെയ്താൽ exact estimate പറയാം.",
        "delivery_charge": "Kerala orders ₹600 and above free aanu. Below that ₹40. Outside Kerala customer charge ₹60 aanu.",
        "clarify": "Price, delivery, or order help?",
        "best_pack": "If regular use aanu, the recommended pack is usually the most practical option.",
        "order_capture": (
            "Order place cheyyan ivide details share cheyyu:\n"
            "• Name\n"
            "• Full address\n"
            "• Pincode\n"
            "• Phone number\n"
            "• Quantity / size"
        ),
        "order_delivery_cta": (
            "To order, please send:\n\n"
            "Name, full address, phone number, and pincode 😊\n\n"
            "Kerala orders ₹600+ get free delivery.\n\n"
            "Outside Kerala normal delivery is ₹120, but we collect only ₹60 from the customer.\n\n"
            "Combo order or ₹600+ purchase gets free delivery."
        ),
        "no_interest": "No problem at all 😊 If you need anything later, just message us.",
        "defer_decision": "Sure, no problem 😊 Tomorrow or later is fine. Just message us when you’re ready.",
        "wholesale": (
            "Wholesale rates available aanu.\n\n"
            "Please share:\n"
            "• Product name\n"
            "• Approx quantity\n"
            "• Delivery location"
        ),
        "fallback": "",
        "footer": "Kerala-il ₹600 kazhinjal free delivery. Outside Kerala customer charge ₹60 aanu.",
        "payment": "Payment ചെയ്താൽ screenshot അല്ലെങ്കിൽ transaction reference share cheyyu 😊 Confirm cheyyam.",
        "payment_received": "Payment screenshot received 👍 We’ll verify it and confirm shortly.",
        "payment_review_details": "Screenshot kitti 👍 Payment verify cheyyan amount / paid time onnu type cheyyamo?",
        "business_info": "PureLeven Idukki-side spices aanu. Farm story, products, delivery, എല്ലാം help cheyyാം.",
        "human_handoff": "Sure, direct support help arrange cheyyാം. Oru minute.",
        "complaint": "Sorry about that. Nammal ithu immediately support team-il raise cheyyാം.",
    },
    "manglish": {
        "availability": "Undu 😊",
        "price_intro": "Current size options thazhe share cheyyam.",
        "details_intro": "Quick details thazhe kodukkam.",
        "delivery_time": "Usually 4-7 days ullil delivery kittum. Pincode ayachal exact estimate parayam.",
        "delivery_charge": "Kerala-il ₹600 kazhinjal free delivery. Athinu thazhe ₹40 aanu. Outside Kerala customer charge ₹60 aanu.",
        "clarify": "Price, delivery, atho order help?",
        "best_pack": "Regular use aanu enkil recommended pack aanu usually nalla option.",
        "order_capture": (
            "Order cheyyan:\n\n"
            "Peru / name, address, phone number, pincode, quantity / size ayacholu 😊"
        ),
        "order_delivery_cta": (
            "Order cheyyan:\n\n"
            "Peru, address, phone number, pincode ayacholu 😊\n\n"
            "🚚 Kerala-il ₹600+ orderinu free delivery undu.\n\n"
            "🚚 Kerala-kku purathekk normal delivery charge ₹120 aanu, pakshe njangal customer-il ninn ₹60 mathram aanu edakkunnath.\n\n"
            "Combo order allenkil ₹600+ purchase cheyyumbol free delivery kittum."
        ),
        "no_interest": "Shari 😊 വേറെ എന്തെങ്കിലും venengil parayu. Pinne product name ayachal mathi.",
        "defer_decision": "Shari, no problem 😊 Nale / pinne nokki paranjal mathi. Njan help cheyyam.",
        "wholesale": (
            "Wholesale / bulk rate undu.\n\n"
            "Share cheyyu:\n"
            "• Product name\n"
            "• Approx quantity\n"
            "• Delivery place"
        ),
        "fallback": "",
        "footer": "Kerala-il ₹600 kazhinjal free delivery. Outside Kerala customer charge ₹60 aanu.",
        "payment": "Payment cheythittundengil screenshot allenkil transaction reference ayacholu 😊 Confirm cheyyam.",
        "payment_received": "Payment screenshot kitti 👍 Njan verify cheythu order confirm cheyyam. Oru minute.",
        "payment_review_details": "Screenshot kitti 👍 Payment verify cheyyan amount / paid time onnu type cheyyamo?",
        "business_info": "PureLeven Idukki side spices aanu. Farm-il ninnulla products aanu.",
        "human_handoff": "Sure, direct support connect cheyyam.",
        "complaint": "Sorry. Ithu support team-il immediate aayi raise cheyyam.",
    },
    "malayalam": {
        "availability": "ഉണ്ട് 😊",
        "price_intro": "ഇപ്പോഴത്തെ size options താഴെ കൊടുക്കുന്നു.",
        "details_intro": "Quick details താഴെ കൊടുക്കാം.",
        "delivery_time": "സാധാരണ 4-7 ദിവസത്തിനുള്ളിൽ delivery കിട്ടും. Pincode അയച്ചാൽ exact estimate പറയാം.",
        "delivery_charge": "കേരളത്തിൽ ₹600 കഴിഞ്ഞാൽ free delivery. അതിന് താഴെ ₹40. കേരളത്തിന് പുറത്തേക്ക് customer charge ₹60 ആണ്.",
        "clarify": "വിലയോ, delivery യോ, order help യോ?",
        "best_pack": "സ്ഥിരമായി ഉപയോഗത്തിനാണെങ്കിൽ recommended pack സാധാരണ നല്ല option ആണ്.",
        "order_capture": (
            "Order place ചെയ്യാൻ ഈ details അയയ്ക്കൂ:\n"
            "• പേര്\n"
            "• പൂർണ്ണ വിലാസം\n"
            "• Pincode\n"
            "• ഫോൺ നമ്പർ\n"
            "• Quantity / size"
        ),
        "order_delivery_cta": (
            "Order ചെയ്യാൻ:\n\n"
            "പേര്, address, phone number, pincode അയച്ചോളൂ 😊\n\n"
            "🚚 കേരളത്തിൽ ₹600+ order-ന് free delivery ഉണ്ട്.\n\n"
            "🚚 കേരളത്തിന് പുറത്തേക്ക് normal delivery charge ₹120 ആണ്, പക്ഷേ customer-ൽ നിന്ന് ₹60 മാത്രം ആണ് എടുക്കുന്നത്.\n\n"
            "Combo order അല്ലെങ്കിൽ ₹600+ purchase ചെയ്യുമ്പോൾ free delivery കിട്ടും."
        ),
        "no_interest": "ശരി 😊 വേറെ എന്തെങ്കിലും വേണമെങ്കിൽ പറയൂ. പിന്നെ product name അയച്ചാൽ മതി.",
        "defer_decision": "ശരി, പ്രശ്നമില്ല 😊 നാളെ / പിന്നീട് നോക്കി പറഞ്ഞാൽ മതി. ഞാൻ help ചെയ്യാം.",
        "wholesale": (
            "Wholesale / bulk rate ഉണ്ട്.\n\n"
            "ദയവായി share ചെയ്യൂ:\n"
            "• Product name\n"
            "• Approx quantity\n"
            "• Delivery place"
        ),
        "fallback": "",
        "footer": "കേരളത്തിൽ ₹600 കഴിഞ്ഞാൽ free delivery. കേരളത്തിന് പുറത്തേക്ക് customer charge ₹60 ആണ്.",
        "payment": "Payment ചെയ്തിട്ടുണ്ടെങ്കിൽ screenshot അല്ലെങ്കിൽ transaction reference അയയ്ക്കൂ 😊 Confirm ചെയ്യാം.",
        "payment_received": "Payment screenshot കിട്ടി 👍 Verify ചെയ്ത് order confirm ചെയ്യാം. ഒരു മിനിറ്റ്.",
        "payment_review_details": "Screenshot കിട്ടി 👍 Payment verify ചെയ്യാൻ amount / paid time ഒന്നു type ചെയ്യാമോ?",
        "business_info": "PureLeven Idukki-side spices ആണ്. Farm storyയും delivery helpഉം share ചെയ്യാം.",
        "human_handoff": "Sure, direct support connect ചെയ്യാം.",
        "complaint": "ക്ഷമിക്കണം. ഇത് support team-ലേക്ക് ഉടൻ raise ചെയ്യാം.",
    },
}


PRODUCT_REPLY_LIBRARY: dict[str, dict[str, Any]] = {}
COMBO_OFFER_LIBRARY: list[dict[str, Any]] = []


def _refresh_runtime_catalog() -> None:
    global PRODUCT_REPLY_LIBRARY, COMBO_OFFER_LIBRARY
    PRODUCT_REPLY_LIBRARY = {product["id"]: product for product in list_products()}
    COMBO_OFFER_LIBRARY = get_combo_offers()


def reload_product_catalog_from_file() -> None:
    reload_catalog()
    _refresh_runtime_catalog()


_refresh_runtime_catalog()


class PricingFormatter:
    @staticmethod
    def _style_key(style: str) -> str:
        value = (style or "").strip().lower()
        if value in {"malayalam", "manglish", "english"}:
            return value
        return "english"

    @staticmethod
    def get_product_alias_map() -> dict[str, str]:
        return build_alias_map()

    @staticmethod
    def get_product_catalog_entry(product_key: str) -> Optional[dict[str, Any]]:
        legacy = PRODUCT_REPLY_LIBRARY.get(product_key)
        if legacy:
            images = list(legacy.get("images") or legacy.get("media_links") or [])
            primary_image_url = ""
            for image in images:
                if image.get("is_primary") and image.get("url"):
                    primary_image_url = str(image["url"])
                    break
            if not primary_image_url and images:
                primary_image_url = str(images[0].get("url") or "")

            return {
                "product_key": str(legacy.get("id") or product_key),
                "id": str(legacy.get("id") or product_key),
                "display_name": str(legacy.get("display_name") or legacy.get("name") or product_key),
                "name": str(legacy.get("name") or legacy.get("display_name") or product_key),
                "aliases": list(legacy.get("aliases") or []),
                "origin": legacy.get("origin", ""),
                "story": str(legacy.get("story") or legacy.get("description") or ""),
                "quality": legacy.get("quality", ""),
                "description": str(legacy.get("description") or legacy.get("story") or ""),
                "use_cases": list(legacy.get("use_cases") or []),
                "variants": list(legacy.get("variants") or legacy.get("sizes") or []),
                "sizes": list(legacy.get("sizes") or legacy.get("variants") or []),
                "recommended_pack": legacy.get("recommended_pack", ""),
                "images": images,
                "media_links": images,
                "primary_image_url": primary_image_url,
            }

        product = get_product(product_key)
        if not product:
            product = get_product(detect_product(product_key or "") or "")
        if product:
            return {
                "product_key": product["id"],
                "id": product["id"],
                "display_name": product["name"],
                "name": product["name"],
                "aliases": list(product.get("aliases", [])),
                "origin": product.get("origin", ""),
                "story": product.get("story", ""),
                "quality": product.get("quality", ""),
                "description": product.get("story", ""),
                "use_cases": list(product.get("use_cases", [])),
                "variants": list(product.get("sizes", [])),
                "sizes": list(product.get("sizes", [])),
                "recommended_pack": product.get("recommended_pack", ""),
                "images": get_image_entries(product["id"]),
                "media_links": get_image_entries(product["id"]),
                "primary_image_url": get_primary_image_url(product["id"]),
            }

        return None

    @staticmethod
    def get_product_image_entries(product_key: str) -> list[dict[str, Any]]:
        entry = PricingFormatter.get_product_catalog_entry(product_key)
        if not entry:
            return []
        return list(entry.get("images", []))

    @staticmethod
    def get_product_image_urls(product_key: str) -> list[str]:
        return [image.get("url", "") for image in PricingFormatter.get_product_image_entries(product_key) if image.get("url")]

    @staticmethod
    def get_primary_product_image_url(product_key: str) -> str:
        entry = PricingFormatter.get_product_catalog_entry(product_key)
        if not entry:
            return ""
        return str(entry.get("primary_image_url") or "")

    @staticmethod
    def get_core_product_definition(product_key: str, style: str = "english") -> Optional[dict[str, Any]]:
        entry = PricingFormatter.get_product_catalog_entry(product_key)
        if not entry:
            return None
        style_key = PricingFormatter._style_key(style)
        product = get_product(entry["product_key"])
        delivery_preview = [
            {
                "size": item["size"],
                "price": item["price"],
                "delivery": delivery_label(item["price"]),
            }
            for item in entry.get("sizes", [])
        ]
        return {
            "id": entry["id"],
            "name": entry["name"],
            "display_name": entry["display_name"],
            "origin": entry["origin"],
            "description": entry["story"],
            "story": entry["story"],
            "quality": entry["quality"],
            "use_cases": entry["use_cases"],
            "variants": delivery_preview,
            "recommended_pack": entry["recommended_pack"],
            "recommendation": PricingFormatter._recommendation_line(product or entry, style_key),
        }

    @staticmethod
    def format_product_pricing(
        product_name: str,
        variants: list[dict[str, Any]],
        origin: Optional[str] = None,
        description: Optional[str] = None,
        region: str | None = None,
        include_delivery: bool = True,
    ) -> str:
        lines = [f"*{product_name.upper()}*"]
        if origin:
            lines[-1] += f" • {origin}"
        if description:
            lines.extend(["", f"_{description}_"])
        if include_delivery:
            lines.extend(["", "*Size     | Price    | Delivery*", "───────────────────────────────────"])
        else:
            lines.extend(["", "*Size     | Price*", "────────────────"])
        for variant in variants:
            size = str(variant.get("size") or "").strip()
            price = int(variant.get("price") or 0)
            if include_delivery:
                lines.append(f"{size:<7} | ₹{price:<6} | {delivery_label(price, region=region)}")
            else:
                lines.append(f"{size:<7} | ₹{price}")
        return "\n".join(lines)

    @staticmethod
    def _recommendation_line(product: dict[str, Any], style_key: str) -> str:
        recommended_pack = str(product.get("recommended_pack") or "").strip()
        product_name = str(product.get("name") or "").strip()
        if style_key == "malayalam":
            return (
                f"{recommended_pack} pack ആണ് regular use-ന് നല്ല value option."
                if recommended_pack
                else "Regular use-ന് നല്ല option suggest ചെയ്യാം."
            )
        if style_key == "manglish":
            return (
                f"{recommended_pack} pack aanu regular useinu nalla value option."
                if recommended_pack
                else "Regular useinu nalla option suggest cheyyam."
            )
        return (
            f"{recommended_pack} pack is usually the best value option for regular home use."
            if recommended_pack
            else f"For {product_name.lower()}, I can suggest the practical pack based on your use."
        )

    @staticmethod
    def _story_line(product: dict[str, Any], style_key: str) -> str:
        story = str(product.get("story") or "").strip()
        quality = str(product.get("quality") or "").strip()
        if style_key == "english":
            return story or quality
        return story or quality

    @staticmethod
    def _use_case_line(product: dict[str, Any], style_key: str) -> str:
        use_cases = list(product.get("use_cases", []))
        if not use_cases:
            return ""
        preview = ", ".join(use_cases[:3])
        if style_key == "malayalam":
            return f"ഇത് സാധാരണ {preview} എന്നിവയ്ക്ക് ഉപയോഗിക്കുന്നു."
        if style_key == "manglish":
            return f"Ithu saadhaaranam {preview} pole use cheyyunnu."
        return f"Customers usually use this for {preview}."

    @staticmethod
    def _availability_opening(product_name: str, customer_reference: str, style_key: str) -> str:
        if style_key == "malayalam":
            return "ഉണ്ട് 😊"
        if style_key == "manglish":
            return "Undu 😊"
        return "Available 😊"

    @staticmethod
    def _benefit_lines(product: dict[str, Any], style_key: str) -> list[str]:
        """Render concise catalog-backed benefits without inventing claims."""
        origin = str(product.get("origin") or "").strip()
        story = str(product.get("story") or "").strip()
        quality = str(product.get("quality") or "").strip()
        use_cases = [str(item).strip() for item in list(product.get("use_cases") or []) if str(item).strip()]
        use_case_text = ", ".join(use_cases[:3])

        if style_key == "malayalam":
            lines = ["*നല്ലത് എന്തുകൊണ്ട്*"]
            if origin:
                lines.append(f"• Source: {origin}")
            if quality:
                lines.append(f"• {quality}")
            elif story:
                lines.append(f"• {story}")
            if use_case_text:
                lines.append(f"• Use: {use_case_text}")
            return lines if len(lines) > 1 else []

        if style_key == "manglish":
            lines = ["*Nalla points*"]
            if origin:
                lines.append(f"• Source: {origin}")
            if quality:
                lines.append(f"• {quality}")
            elif story:
                lines.append(f"• {story}")
            if use_case_text:
                lines.append(f"• Use: {use_case_text}")
            return lines if len(lines) > 1 else []

        lines = ["*Why customers pick this*"]
        if origin:
            lines.append(f"• Source: {origin}")
        if quality:
            lines.append(f"• {quality}")
        elif story:
            lines.append(f"• {story}")
        if use_case_text:
            lines.append(f"• Good for: {use_case_text}")
        return lines if len(lines) > 1 else []

    @staticmethod
    def _guided_size_question(product: dict[str, Any], style_key: str) -> str:
        sizes = [str(item.get("size") or "").strip() for item in product.get("sizes", []) if item.get("size")]
        recommended_pack = str(product.get("recommended_pack") or "").strip()
        size_preview = " / ".join(sizes[:4])
        if style_key == "malayalam":
            if recommended_pack:
                return f"{recommended_pack} pack നല്ല value option ആണ്."
            return f"Available sizes: {size_preview}" if size_preview else "Size options share ചെയ്യാം."
        if style_key == "manglish":
            if recommended_pack:
                return f"{recommended_pack} pack nalla value option aanu."
            return f"Available sizes: {size_preview}" if size_preview else "Size options share cheyyam."
        if recommended_pack:
            return f"{recommended_pack} pack is the best value option here."
        return f"Available sizes: {size_preview}." if size_preview else "I can share the size options."

    @staticmethod
    def _delivery_policy_footer(style_key: str) -> str:
        return REPLY_STYLE_COPY[style_key]["footer"]

    @staticmethod
    def _value_line(product: dict[str, Any], style_key: str) -> str:
        quality = str(product.get("quality") or "").strip()
        if style_key == "malayalam":
            return quality or "Source, cleanliness, aroma എന്നിവ കൊണ്ടാണ് ഇതിന്റെ value."
        if style_key == "manglish":
            return quality or "Source, cleaning, aroma ivayokke kondu aanu ithinte value."
        return quality or "The value here mainly comes from the sourcing, clean processing, and consistent aroma."

    @staticmethod
    def format_catalog_response(products: list[dict[str, Any]]) -> str:
        sections: list[str] = []
        for product in products:
            sections.append(
                PricingFormatter.format_product_pricing(
                    product_name=str(product.get("display_name") or product.get("name") or ""),
                    variants=list(product.get("variants") or []),
                    origin=str(product.get("origin") or ""),
            description=str(product.get("description") or product.get("story") or ""),
            include_delivery=False,
        )
            )
        return "\n\n".join(section for section in sections if section.strip())

    @staticmethod
    def build_core_product_reply(product_key: str, style: str = "english") -> Optional[str]:
        payload = PricingFormatter.build_product_journey_reply_payload(
            product_key,
            style=style,
            scenario="price",
        )
        return None if not payload else str(payload.get("reply_text") or "")

    @staticmethod
    def build_wholesale_reply(style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        return REPLY_STYLE_COPY[style_key]["wholesale"]

    @staticmethod
    def build_no_interest_reply(style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        return REPLY_STYLE_COPY[style_key]["no_interest"]

    @staticmethod
    def build_defer_decision_reply(style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        return REPLY_STYLE_COPY[style_key]["defer_decision"]

    @staticmethod
    def build_order_capture_reply(style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        return REPLY_STYLE_COPY[style_key]["order_capture"]

    @staticmethod
    def build_order_delivery_cta(style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        return REPLY_STYLE_COPY[style_key]["order_delivery_cta"]

    @staticmethod
    def get_static_copy(copy_key: str, style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        return str(REPLY_STYLE_COPY.get(style_key, {}).get(copy_key) or "")

    @staticmethod
    def format_combo_response(style: str = "english") -> str:
        style_key = PricingFormatter._style_key(style)
        intro = {
            "english": "*COMBO PACKS*",
            "manglish": "*COMBO PACKS*",
            "malayalam": "*COMBO PACKS*",
        }[style_key]
        lines = [intro, "", "*Combo    | Includes                            | Price*", "────────────────────────────────────────────"]
        for combo in COMBO_OFFER_LIBRARY:
            lines.append(f"{combo['title']:<8} | {combo['includes']:<35} | ₹{combo['price']}")
        lines.extend(["", PricingFormatter._delivery_policy_footer(style_key)])
        return "\n".join(lines)

    @staticmethod
    def build_combo_reply(style: str = "english") -> str:
        return PricingFormatter.format_combo_response(style=style)

    @staticmethod
    def build_product_journey_reply(
        product_key: str,
        style: str = "english",
        scenario: str = "availability",
        customer_reference: Optional[str] = None,
    ) -> Optional[str]:
        payload = PricingFormatter.build_product_journey_reply_payload(
            product_key=product_key,
            style=style,
            scenario=scenario,
            customer_reference=customer_reference,
        )
        if not payload:
            return None
        return str(payload.get("reply_text") or "")

    @staticmethod
    def build_product_journey_reply_payload(
        product_key: str,
        style: str = "english",
        scenario: str = "availability",
        customer_reference: Optional[str] = None,
        opening_line: Optional[str] = None,
        closing_line: Optional[str] = None,
        region: str | None = None,
    ) -> Optional[dict[str, Any]]:
        entry = PricingFormatter.get_product_catalog_entry(product_key)
        if not entry:
            return None
        product = {
            "id": entry["id"],
            "name": entry["name"],
            "origin": entry.get("origin", ""),
            "story": entry.get("story", ""),
            "quality": entry.get("quality", ""),
            "sizes": list(entry.get("sizes", [])),
            "recommended_pack": entry.get("recommended_pack", ""),
            "use_cases": list(entry.get("use_cases", [])),
        }

        style_key = PricingFormatter._style_key(style)
        copy = REPLY_STYLE_COPY[style_key]
        product_name = customer_reference or product["name"]
        story_line = PricingFormatter._story_line(product, style_key)
        use_case_line = PricingFormatter._use_case_line(product, style_key)
        recommendation = PricingFormatter._recommendation_line(product, style_key)
        size_rows = [
            {
                "size": item["size"],
                "price": item["price"],
                "delivery": delivery_label(item["price"], region=region),
            }
            for item in product.get("sizes", [])
        ]
        table = PricingFormatter.format_product_pricing(
            product_name=product["name"],
            variants=product.get("sizes", []),
            origin=product.get("origin"),
            description=product.get("quality") or product.get("story"),
            region=region,
            include_delivery=False,
        )

        simple_scenarios = {"availability", "stock_check", "price"}
        if scenario in simple_scenarios:
            size_lines = [f"{item['size']} ₹{item['price']}" for item in product.get("sizes", []) if item.get("size")]
            opening_map = {
                "english": "Yes, available 😊",
                "manglish": "Undu 😊",
                "malayalam": "ഉണ്ട് 😊",
            }
            reply_lines = [opening_line or opening_map[style_key]]
            if size_lines:
                reply_lines.extend(["", "\n".join(size_lines)])
            reply_text = "\n".join(line for line in reply_lines if line is not None).strip()
            images = list(entry.get("images", []))
            primary_image_url = str(entry.get("primary_image_url") or "")
            image_urls = [image["url"] for image in images if image.get("url")][:1]
            if not image_urls and primary_image_url:
                image_urls = [primary_image_url]
            return {
                "reply_text": reply_text,
                "intent": scenario,
                "product_key": product["id"],
                "display_name": product["name"],
                "origin": product.get("origin"),
                "description": product.get("story"),
                "story": product.get("story"),
                "quality": product.get("quality"),
                "recommended_pack": product.get("recommended_pack"),
                "image_urls": image_urls,
                "primary_image_url": image_urls[0] if image_urls else "",
                "images": images,
                "media_mode": "image" if image_urls else "text",
                "scenario": scenario,
                "style": style_key,
                "sizes": size_rows,
                "extra_messages": [],
            }

        if opening_line:
            default_opening = opening_line
        elif scenario in {"availability", "stock_check"}:
            default_opening = PricingFormatter._availability_opening(product["name"], product_name, style_key)
        elif scenario == "price":
            default_opening = copy["price_intro"]
        elif scenario in {"details", "quality", "origin", "processing", "usage", "benefits", "comparison"}:
            default_opening = copy["details_intro"]
        else:
            default_opening = copy["availability"]

        lines: list[str] = []
        if scenario in {"delivery_time", "delivery"}:
            lines.extend(
                [
                    copy["delivery_time"],
                    closing_line or "",
                ]
            )
        elif scenario in {"delivery_charge", "free_delivery"}:
            lines.extend(
                [
                    copy["delivery_charge"],
                    closing_line or "",
                ]
            )
        elif scenario in {"details", "quality", "origin", "processing", "usage", "benefits", "comparison"}:
            lines.append(default_opening)
            if story_line:
                lines.append(story_line)
            benefit_lines = PricingFormatter._benefit_lines(product, style_key)
            if benefit_lines:
                lines.append("\n".join(benefit_lines))
            if use_case_line and scenario in {"details", "usage", "benefits"}:
                lines.append(use_case_line)
            if scenario == "comparison" and style_key == "manglish":
                lines.append("Ithu marketile generic item pole alla; source, cleaning, aroma ellam clear aanu.")
            elif scenario == "comparison" and style_key == "english":
                lines.append("The difference is mainly in sourcing, freshness, and how clean the spice feels in cooking.")
            elif scenario == "comparison":
                lines.append("Source, freshness, clean cooking profile ഇവയാണ് main difference.")
            lines.append(table)
            if closing_line:
                lines.append(closing_line)
        elif scenario in {"order_request", "order_confirm", "order_intent"}:
            order_openings = {
                "english": "Sure, I can arrange the order 😊",
                "manglish": "Sure, order arrange cheyyam 😊",
                "malayalam": "ശരി, order arrange ചെയ്യാം 😊",
            }
            lines.extend(
                [
                    opening_line or order_openings[style_key],
                    PricingFormatter.build_order_capture_reply(style=style_key),
                ]
            )
        elif scenario in {"best_pack", "budget"}:
            benefit_lines = PricingFormatter._benefit_lines(product, style_key)
            lines.extend([default_opening])
            if benefit_lines:
                lines.append("\n".join(benefit_lines))
            lines.append(table)
            if closing_line:
                lines.append(closing_line)
        elif scenario == "combo":
            lines.append(PricingFormatter.format_combo_response(style=style_key))
        elif scenario == "price_objection":
            benefit_lines = PricingFormatter._benefit_lines(product, style_key)
            lines.extend([default_opening, story_line, PricingFormatter._value_line(product, style_key)])
            if benefit_lines:
                lines.append("\n".join(benefit_lines))
            lines.append(table)
            if closing_line:
                lines.append(closing_line)
        elif scenario == "fallback":
            lines.extend([default_opening, story_line, closing_line or copy["clarify"]])
        else:
            lines.extend([default_opening, story_line])
            if use_case_line:
                lines.append(use_case_line)
            lines.append(table)
            if closing_line:
                lines.append(closing_line)

        reply_text = "\n\n".join(line.strip() for line in lines if line and line.strip())
        images = list(entry.get("images", []))
        primary_image_url = str(entry.get("primary_image_url") or "")
        media_scenarios = {
            "availability",
            "stock_check",
            "price",
            "details",
            "quality",
            "origin",
            "processing",
            "usage",
            "benefits",
            "best_pack",
            "budget",
            "comparison",
            "price_objection",
            "fallback",
        }
        image_urls = [image["url"] for image in images if image.get("url")] if scenario in media_scenarios else []
        intent_name = scenario if scenario in {"delivery_time", "delivery_charge", "free_delivery"} else scenario
        cta_scenarios = {"order_request", "order_confirm", "order_intent"}
        extra_messages: list[str] = []
        if scenario in cta_scenarios:
            extra_messages.append(PricingFormatter.build_order_delivery_cta(style=style_key))

        return {
            "reply_text": reply_text,
            "intent": intent_name,
            "product_key": product["id"],
            "display_name": product["name"],
            "origin": product.get("origin"),
            "description": product.get("story"),
            "story": product.get("story"),
            "quality": product.get("quality"),
            "recommended_pack": product.get("recommended_pack"),
            "image_urls": image_urls,
            "primary_image_url": primary_image_url if image_urls else "",
            "images": images,
            "media_mode": "image" if image_urls else "text",
            "scenario": scenario,
            "style": style_key,
            "sizes": size_rows,
            "extra_messages": extra_messages,
        }
