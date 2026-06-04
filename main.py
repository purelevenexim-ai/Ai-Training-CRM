from dotenv import load_dotenv
load_dotenv("/app/app/.env.production")
import sys
sys.path.insert(0, '/app')

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
try:
    from app.database import engine
    from app.crm_models import Base
except ImportError:
    # Local workspace fallback where modules are at repository root.
    from database import engine
    from crm_models import Base
from pathlib import Path
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

# ============================================================================
# Prometheus Metrics
# ============================================================================
api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request latency in seconds',
    ['method', 'endpoint', 'status']
)

api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

active_websocket_connections = Gauge(
    'active_websocket_connections',
    'Number of active WebSocket connections'
)

journey_enrollments_total = Counter(
    'journey_enrollments_total',
    'Total customer enrollments in journeys'
)

audience_sync_duration = Histogram(
    'audience_sync_duration_seconds',
    'Audience sync duration in seconds',
    ['platform']  # meta, google
)

# Base.metadata.create_all(bind=engine)  # Disabled - schema managed by Alembic migrations

try:
    from app.crm_routes import router as crm_router
    from app.realtime_routes import router as realtime_router, start_listeners, stop_listeners
    from app.journeys_routes import router as journeys_router
    from app.shopify_attribution import router as attribution_router
    from app.audience_scheduler import router as scheduler_router, start_scheduler, stop_scheduler
    from app.auth_routes import router as auth_router
    from app.lead_routes import router as lead_router
    from app.offline_conversions_routes import router as offline_conversions_router
    from app.propensity_scoring_routes import router as propensity_scoring_router
    from app.cart_recovery_routes import router as cart_recovery_router
    from app.delhivery_routes import router as delhivery_router
    from app.google_forms_routes import router as google_forms_router
    from app.meta_ads_routes import router as meta_ads_router
    from app.csv_import_routes import router as csv_import_router
    from app.sms_email_routes import router as sms_email_router
    from app.customer_enrichment_routes import router as enrichment_router
    from app.analytics_routes import router as analytics_router
    from app.performance_routes import router as performance_router
    from app.customer360_routes import router as customer360_router
    from app.routes.ai_routes import router as ai_router
    from app.routes.review_routes import router as review_router
    from app.routes.wave02_routes import router as wave02_router
except ImportError:
    from crm_routes import router as crm_router
    from realtime_routes import router as realtime_router, start_listeners, stop_listeners
    from journeys_routes import router as journeys_router
    from shopify_attribution import router as attribution_router
    from audience_scheduler import router as scheduler_router, start_scheduler, stop_scheduler
    from auth_routes import router as auth_router
    from lead_routes import router as lead_router
    from offline_conversions_routes import router as offline_conversions_router
    from propensity_scoring_routes import router as propensity_scoring_router
    from cart_recovery_routes import router as cart_recovery_router
    from delhivery_routes import router as delhivery_router
    from google_forms_routes import router as google_forms_router
    from meta_ads_routes import router as meta_ads_router
    from csv_import_routes import router as csv_import_router
    from sms_email_routes import router as sms_email_router
    from customer_enrichment_routes import router as enrichment_router
    from analytics_routes import router as analytics_router
    from performance_routes import router as performance_router
    from customer360_routes import router as customer360_router
    from routes.ai_routes import router as ai_router
    from routes.review_routes import router as review_router
    from routes.wave02_routes import router as wave02_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start audience sync scheduler
    start_scheduler()
    # Start Redis pub/sub → WebSocket background listeners (Phase 3)
    start_listeners()
    yield
    # Graceful shutdown
    stop_listeners()
    stop_scheduler()


app = FastAPI(title="Pureleven CRM API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Prometheus Middleware
# ============================================================================
@app.middleware("http")
async def track_metrics(request, call_next):
    """Track request duration and status for Prometheus metrics."""
    start_time = time.time()
    
    # Extract path and method, skip /metrics to avoid infinite recursion
    path = request.url.path
    if path == "/api/metrics":
        return await call_next(request)
    
    method = request.method
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    status = response.status_code
    
    # Record metrics
    api_request_duration.labels(method=method, endpoint=path, status=status).observe(duration)
    api_requests_total.labels(method=method, endpoint=path, status=status).inc()
    
    return response

# journeys_router FIRST so its routes win over crm_router's older journey routes
app.include_router(auth_router)  # Auth endpoints (health check, token, key management)
app.include_router(ai_router)  # AI CRM endpoints (Wave 0.1)
app.include_router(review_router)  # Review workflow endpoints (Wave 0.2)
app.include_router(wave02_router)  # Wave 0.2 complete (scoring, KB, features)
app.include_router(lead_router)  # Lead management (Sprint 1 Task 1)
app.include_router(offline_conversions_router)  # Offline conversions (Sprint 1 Task 2)
app.include_router(propensity_scoring_router)  # Propensity scoring (Sprint 1 Task 3)
app.include_router(cart_recovery_router)  # Cart recovery (Sprint 1 Task 4)
app.include_router(delhivery_router)  # Delhivery shipping (Sprint 2 Task 1)
app.include_router(google_forms_router)  # Google Forms (Sprint 2 Task 2)
app.include_router(meta_ads_router)  # Meta Ads (Sprint 2 Task 3)
app.include_router(csv_import_router)  # CSV Import & Bulk Operations (Sprint 3 Task 1)
app.include_router(sms_email_router)  # SMS & Email Notifications (Sprint 3 Task 2)
app.include_router(enrichment_router)  # Customer Enrichment (Sprint 3 Task 3)
app.include_router(analytics_router)  # Analytics Dashboards (Sprint 4 Task 1)
app.include_router(performance_router)  # Performance Optimization (Sprint 4 Task 2)
app.include_router(customer360_router)  # Customer 360 Profiles & Timelines (Sprint 0)
app.include_router(journeys_router)
app.include_router(attribution_router)
app.include_router(scheduler_router)
app.include_router(realtime_router)
app.include_router(crm_router)

static_dir = Path("/app/app/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="/app/app/static"), name="static")



@app.get("/health")
def health():
    return {"status": "healthy", "module": "main"}


@app.get("/api/health")
def api_health():
    return {"status": "healthy", "module": "crm"}


@app.get("/api/metrics")
def metrics():
    """
    Prometheus metrics endpoint.
    Exposes system metrics: request count, latency, connections, enrollments.
    """
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
