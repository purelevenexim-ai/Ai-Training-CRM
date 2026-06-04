from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.abandoned_customer import router as abandoned_customer_router
from app.routes.ai_dispatch import router as ai_dispatch_router
from app.routes.ai_routes import router as ai_router
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router
from app.routes.checkout import router as checkout_router
from app.routes.crm_whatsapp import router as crm_whatsapp_router
from app.routes.customer_profiles import router as customer_profiles_router
from app.routes.delhivery_webhook import router as delhivery_router
from app.routes.email_webhooks import router as email_webhooks_router
from app.routes.events import router as events_router
from app.routes.experiments import router as experiments_router
from app.routes.flags import router as flags_router
from app.routes.google_my_business import router as google_my_business_router
from app.routes.journey_orchestrator import router as journey_orchestrator_router
from app.routes.leads import router as leads_router
from app.routes.link_tracker import router as link_tracker_router
from app.routes.meta_whatsapp_webhook import router as meta_whatsapp_webhook_router
from app.routes.monitoring import router as monitoring_router
from app.routes.owner_dashboard import router as owner_dashboard_router
from app.routes.promotional_campaigns import router as promotional_campaigns_router
from app.routes.review_journey import router as review_journey_router
from app.routes.root_tracking_bridge import router as root_tracking_bridge_router
from app.routes.rules import router as rules_router
from app.routes.settings import router as settings_router
from app.routes.shopify_webhook import router as shopify_webhook_router
from app.routes.test_journey import router as test_journey_router
from app.routes.wave02_wabis_routes import router as wave02_wabis_router
from app.routes.whatsapp_journey import router as whatsapp_journey_router
from app.routes.whatsapp_tracking import router as whatsapp_tracking_router
from app.routes.conversation_replay_routes import router as conversation_replay_router
from app.routes.review_journey import router as review_journey_router
from app.routes.root_tracking_bridge import router as root_tracking_bridge_router
from app.routes.rules import router as rules_router
from app.routes.settings import router as settings_router
from app.routes.shopify_webhook import router as shopify_webhook_router
from app.routes.test_journey import router as test_journey_router
from app.routes.whatsapp_journey import router as whatsapp_journey_router
from app.routes.whatsapp_tracking import router as whatsapp_tracking_router
from app.services.promotional_campaign_queue_worker import (
    start_promotional_queue_worker,
    stop_promotional_queue_worker,
)
from app.services.product_followup_scheduler import (
    start_product_followup_scheduler,
    stop_product_followup_scheduler,
)
from app.services.ai_reply_queue_scheduler import (
    start_ai_reply_queue_scheduler,
    stop_ai_reply_queue_scheduler,
)
from app.services.product_media_service import product_media_root
from app.storage import init_database


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_database()
    start_promotional_queue_worker()
    start_product_followup_scheduler()
    start_ai_reply_queue_scheduler()


@app.on_event("shutdown")
def shutdown() -> None:
    stop_promotional_queue_worker()
    stop_product_followup_scheduler()
    stop_ai_reply_queue_scheduler()


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/admin", include_in_schema=False)
def admin_page() -> Response:
    index_path = settings.admin_ui_path / "index.html"

    if index_path.exists():
        return FileResponse(index_path)

    return HTMLResponse(
        "<h1>Anu admin server is running</h1>"
        "<p>The embedded Shopify admin is served by the separate anu-login-admin app host, not by this FastAPI backend.</p>"
        "<p>Use the Shopify embedded app entrypoint or the current app tunnel URL to access the admin UI.</p>",
        status_code=200,
    )


@app.get("/admin/campaigns", include_in_schema=False)
def campaigns_dashboard() -> Response:
    campaigns_path = settings.admin_ui_path / "campaigns.html"

    if campaigns_path.exists():
        return FileResponse(campaigns_path)

    return HTMLResponse(
        "<h1>Promotional Campaigns Dashboard</h1>"
        "<p>Dashboard HTML file not found at " + str(campaigns_path) + "</p>",
        status_code=404,
    )


assets_path = settings.admin_ui_path / "assets"
if Path(assets_path).exists():
    app.mount("/admin/assets", StaticFiles(directory=assets_path), name="admin-assets")

product_media_path = product_media_root()
app.mount("/api/product-media", StaticFiles(directory=product_media_path), name="product-media")


app.include_router(auth_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(flags_router, prefix="/api")
app.include_router(checkout_router, prefix="/api")
app.include_router(rules_router, prefix="/api")
app.include_router(experiments_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(customer_profiles_router, prefix="/api")
app.include_router(whatsapp_tracking_router, prefix="/api")
app.include_router(delhivery_router, prefix="/api")
app.include_router(whatsapp_journey_router, prefix="/api")
app.include_router(shopify_webhook_router, prefix="/api")
app.include_router(journey_orchestrator_router, prefix="/api")
app.include_router(link_tracker_router)
app.include_router(meta_whatsapp_webhook_router, prefix="/api")
app.include_router(ai_dispatch_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(owner_dashboard_router, prefix="/api")
app.include_router(email_webhooks_router, prefix="/api")
app.include_router(abandoned_customer_router, prefix="/api")
app.include_router(google_my_business_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(wave02_wabis_router, prefix="/api")
app.include_router(conversation_replay_router, prefix="/api")
app.include_router(promotional_campaigns_router, prefix="/api")
app.include_router(review_journey_router, prefix="/api")
app.include_router(crm_whatsapp_router, prefix="/api")
app.include_router(root_tracking_bridge_router, prefix="/api")
app.include_router(test_journey_router, prefix="/api")
