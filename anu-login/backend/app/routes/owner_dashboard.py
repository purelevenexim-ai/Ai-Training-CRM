from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.routes.settings import require_admin_access
from app.services.owner_dashboard_service import (
    add_product_catalog_image,
    delete_knowledge_base_entry,
    delete_product_catalog_entry,
    knowledge_base_path,
    import_product_images_from_drive_folder,
    mark_product_catalog_image_primary,
    get_ai_control_settings,
    get_customer_timeline,
    get_domain_certificate_status,
    get_owner_dashboard_summary,
    get_prompt_observatory_payload,
    get_prompt_registry_payload,
    get_product_catalog_payload,
    get_training_gaps,
    list_dashboard_customers,
    load_knowledge_base_entries,
    save_ai_control_settings,
    save_knowledge_base_entry,
    save_product_catalog_entry,
    remove_product_catalog_image,
    save_prompt_registry_entry,
)
from app.services.product_media_service import save_product_image_bytes, save_product_image_from_url
from app.services.customer_journey_service import (
    delete_customer_journey,
    list_customer_journeys,
    save_customer_journey,
)
from app.services.ai_monitoring_engine import get_ai_monitor_payload

router = APIRouter(tags=["owner-dashboard"])


class KnowledgeBaseEntryPayload(BaseModel):
    category: str = Field(default="general", max_length=80)
    product: str = Field(default="general", max_length=120)
    product_name: str = Field(default="", max_length=120)
    trigger_examples: list[str] | str = Field(default_factory=list)
    answer_primary: str = Field(default="", max_length=6000)
    customer_input: str = Field(default="", max_length=500)
    input_variations: list[str] | str = Field(default_factory=list)
    ideal_response: str = Field(default="", max_length=6000)
    language: str = Field(default="english", max_length=40)
    needs_review: bool = False
    review_reason: str = Field(default="", max_length=400)
    answer_variants: list[str] | str = Field(default_factory=list)
    follow_up: str = Field(default="", max_length=1000)
    tone: str = Field(default="", max_length=80)
    intent: str = Field(default="", max_length=120)
    tags: list[str] | str = Field(default_factory=list)


class ProductVariantPayload(BaseModel):
    size: str = Field(min_length=1, max_length=40)
    price: int = Field(ge=0)
    delivery: str = Field(default="", max_length=80)


class ProductRecommendationPayload(BaseModel):
    english: str = Field(default="", max_length=1000)
    manglish: str = Field(default="", max_length=1000)
    malayalam: str = Field(default="", max_length=1000)


class ProductPayload(BaseModel):
    product_key: str = Field(default="", max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    aliases: list[str] | str = Field(default_factory=list)
    origin: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=400)
    recommended_pack: str = Field(default="", max_length=40)
    recommendations: ProductRecommendationPayload = Field(default_factory=ProductRecommendationPayload)
    reply_cta: str = Field(default="", max_length=1000)
    images: list[dict[str, Any]] = Field(default_factory=list)
    variants: list[ProductVariantPayload] = Field(default_factory=list)


class AIControlPayload(BaseModel):
    ai_running: bool
    server_orchestration_enabled: bool = True
    flow_break_detection_enabled: bool = True
    structured_button_passthrough_enabled: bool = True
    wabis_fallback_when_disabled: bool = True
    wabis_priority_minutes: int = Field(default=5, ge=1, le=30)
    selected_model: str
    temperature: float = Field(ge=0.0, le=1.0)
    languages: list[str] = Field(default_factory=list)
    followup_send_enabled: bool = False


class ProductDriveImportPayload(BaseModel):
    folder_url: str = Field(min_length=10, max_length=500)


class CustomerJourneyStepPayload(BaseModel):
    id: str = Field(default="", max_length=120)
    step_order: int = Field(default=1, ge=1, le=50)
    delay_value: int = Field(default=4, ge=1, le=365)
    delay_unit: str = Field(default="minutes", max_length=20)
    message_type: str = Field(default="text", max_length=40)
    message_text: str = Field(default="", max_length=4000)
    active: bool = True


class CustomerJourneyPayload(BaseModel):
    id: str = Field(default="", max_length=120)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    status: str = Field(default="draft", max_length=40)
    applies_to: str = Field(default="all_products", max_length=40)
    selected_products: list[str] = Field(default_factory=list)
    trigger_type: str = Field(default="product_interest", max_length=80)
    stop_on_reply: bool = True
    stop_on_order: bool = True
    stop_on_not_interested: bool = True
    stop_on_stop: bool = True
    steps: list[CustomerJourneyStepPayload] = Field(default_factory=list)


class PromptRegistryPayload(BaseModel):
    id: str = Field(default="", max_length=120)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="general", max_length=80)
    status: str = Field(default="active", max_length=40)
    description: str = Field(default="", max_length=400)
    template_text: str = Field(default="", max_length=20000)


@router.get("/owner/dashboard/summary", dependencies=[Depends(require_admin_access)])
def owner_dashboard_summary() -> dict[str, Any]:
    return get_owner_dashboard_summary()


@router.get("/owner/dashboard/infrastructure", dependencies=[Depends(require_admin_access)])
def owner_dashboard_infrastructure() -> dict[str, Any]:
    return get_domain_certificate_status()


@router.get("/owner/dashboard/customers", dependencies=[Depends(require_admin_access)])
def owner_dashboard_customers(
    search: str = Query(default="", max_length=120),
    label: str = Query(default="all", max_length=20),
    limit: int = Query(default=100, ge=1, le=250),
) -> dict[str, Any]:
    items = list_dashboard_customers(search=search, label=label, limit=limit)
    return {
        "items": items,
        "count": len(items),
    }


@router.get("/owner/dashboard/customers/{customer_ref}/timeline", dependencies=[Depends(require_admin_access)])
def owner_dashboard_customer_timeline(customer_ref: str) -> dict[str, Any]:
    return get_customer_timeline(customer_ref)


@router.get("/owner/dashboard/knowledge-base", dependencies=[Depends(require_admin_access)])
def owner_dashboard_knowledge_base(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=1000, ge=1, le=1000),
) -> dict[str, Any]:
    items = load_knowledge_base_entries(search=search, limit=limit)
    path = knowledge_base_path()
    return {
        "items": items,
        "count": len(items),
        "search": search,
        "storage_mode": "intent_patterns",
        "source_kind": path.name,
    }


@router.post("/owner/dashboard/knowledge-base", dependencies=[Depends(require_admin_access)])
def owner_dashboard_create_kb(payload: KnowledgeBaseEntryPayload) -> dict[str, Any]:
    item = save_knowledge_base_entry(payload.model_dump())
    return {"ok": True, "item": item}


@router.put("/owner/dashboard/knowledge-base/{entry_id}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_update_kb(entry_id: str, payload: KnowledgeBaseEntryPayload) -> dict[str, Any]:
    item = save_knowledge_base_entry(payload.model_dump(), entry_id=entry_id)
    return {"ok": True, "item": item}


@router.delete("/owner/dashboard/knowledge-base/{entry_id}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_delete_kb(entry_id: str) -> dict[str, Any]:
    return delete_knowledge_base_entry(entry_id)


@router.get("/owner/dashboard/ai-control", dependencies=[Depends(require_admin_access)])
def owner_dashboard_ai_control() -> dict[str, Any]:
    return get_ai_control_settings()


@router.put("/owner/dashboard/ai-control", dependencies=[Depends(require_admin_access)])
def owner_dashboard_save_ai_control(payload: AIControlPayload) -> dict[str, Any]:
    return save_ai_control_settings(payload.model_dump())


@router.get("/owner/dashboard/training-gaps", dependencies=[Depends(require_admin_access)])
def owner_dashboard_training_gaps(limit: int = Query(default=30, ge=1, le=100)) -> dict[str, Any]:
    return get_training_gaps(limit=limit)


@router.get("/owner/dashboard/products", dependencies=[Depends(require_admin_access)])
def owner_dashboard_products() -> dict[str, Any]:
    return get_product_catalog_payload()


@router.post("/owner/dashboard/products", dependencies=[Depends(require_admin_access)])
def owner_dashboard_create_product(payload: ProductPayload) -> dict[str, Any]:
    item = save_product_catalog_entry(payload.model_dump())
    return {"ok": True, "item": item}


@router.put("/owner/dashboard/products/{product_key}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_update_product(product_key: str, payload: ProductPayload) -> dict[str, Any]:
    item = save_product_catalog_entry(payload.model_dump(), product_key=product_key)
    return {"ok": True, "item": item}


@router.delete("/owner/dashboard/products/{product_key}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_delete_product(product_key: str) -> dict[str, Any]:
    return delete_product_catalog_entry(product_key)


@router.post("/owner/dashboard/products/{product_key}/images", dependencies=[Depends(require_admin_access)])
async def owner_dashboard_upload_product_image(
    product_key: str,
    image: UploadFile | None = File(default=None),
    image_url: str = Form(default=""),
    caption: str = Form(default=""),
    is_primary: bool = Form(default=False),
    sort_order: int = Form(default=0),
) -> dict[str, Any]:
    if image is None and not image_url.strip():
        raise HTTPException(status_code=400, detail="Upload an image file or provide an image URL.")

    if image is not None:
        content = await image.read()
        image_entry = save_product_image_bytes(
            product_key=product_key,
            content=content,
            filename=image.filename or "",
            content_type=image.content_type or "",
            caption=caption,
            source="upload",
            source_url="",
            is_primary=is_primary,
            sort_order=sort_order,
        )
    else:
        image_entry = save_product_image_from_url(
            product_key=product_key,
            image_url=image_url,
            caption=caption,
            source="url",
            is_primary=is_primary,
            sort_order=sort_order,
        )

    item = add_product_catalog_image(product_key, image_entry)
    return {"ok": True, "item": item, "image": image_entry}


@router.delete("/owner/dashboard/products/{product_key}/images/{image_id}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_delete_product_image(product_key: str, image_id: str) -> dict[str, Any]:
    item = remove_product_catalog_image(product_key, image_id)
    return {"ok": True, "item": item}


@router.put("/owner/dashboard/products/{product_key}/images/{image_id}/primary", dependencies=[Depends(require_admin_access)])
def owner_dashboard_mark_primary_product_image(product_key: str, image_id: str) -> dict[str, Any]:
    item = mark_product_catalog_image_primary(product_key, image_id)
    return {"ok": True, "item": item}


@router.post("/owner/dashboard/products/import-drive-folder", dependencies=[Depends(require_admin_access)])
def owner_dashboard_import_drive_images(payload: ProductDriveImportPayload) -> dict[str, Any]:
    return import_product_images_from_drive_folder(payload.folder_url)


@router.get("/owner/dashboard/customer-journeys", dependencies=[Depends(require_admin_access)])
def owner_dashboard_customer_journeys() -> dict[str, Any]:
    return list_customer_journeys()


@router.post("/owner/dashboard/customer-journeys", dependencies=[Depends(require_admin_access)])
def owner_dashboard_create_customer_journey(payload: CustomerJourneyPayload) -> dict[str, Any]:
    item = save_customer_journey(payload.model_dump())
    return {"ok": True, "item": item}


@router.put("/owner/dashboard/customer-journeys/{journey_id}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_update_customer_journey(journey_id: str, payload: CustomerJourneyPayload) -> dict[str, Any]:
    item = save_customer_journey(payload.model_dump(), journey_id=journey_id)
    return {"ok": True, "item": item}


@router.delete("/owner/dashboard/customer-journeys/{journey_id}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_delete_customer_journey(journey_id: str) -> dict[str, Any]:
    return delete_customer_journey(journey_id)


@router.get("/owner/dashboard/prompts", dependencies=[Depends(require_admin_access)])
def owner_dashboard_prompts() -> dict[str, Any]:
    return get_prompt_registry_payload()


@router.put("/owner/dashboard/prompts/{prompt_id}", dependencies=[Depends(require_admin_access)])
def owner_dashboard_save_prompt(prompt_id: str, payload: PromptRegistryPayload) -> dict[str, Any]:
    return save_prompt_registry_entry(prompt_id, payload.model_dump())


@router.get("/owner/dashboard/prompt-observatory", dependencies=[Depends(require_admin_access)])
def owner_dashboard_prompt_observatory(
    limit: int = Query(default=50, ge=1, le=200),
    phone: str = Query(default="", max_length=40),
) -> dict[str, Any]:
    return get_prompt_observatory_payload(limit=limit, phone=phone)


@router.get("/owner/dashboard/ai-monitor", dependencies=[Depends(require_admin_access)])
def owner_dashboard_ai_monitor(
    hours: int = Query(default=4, ge=1, le=72),
    limit: int = Query(default=80, ge=1, le=200),
) -> dict[str, Any]:
    return get_ai_monitor_payload(hours=hours, limit=limit)
