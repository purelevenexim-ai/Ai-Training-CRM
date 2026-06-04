# Sprint 0 Implementation Roadmap

**Timeline:** Week 1 (May 26-31, 2026)  
**Objective:** Infrastructure setup + scaffold code ready for Sprint 1 event ingestion

---

## Deliverables (In Order)

### 1. Folder Structure & Scaffolding

```
app/
├── domains/
│   ├── tracking/
│   │   ├── __init__.py
│   │   ├── event_service.py
│   │   ├── event_validator.py
│   │   ├── activity_formatter.py
│   │   ├── activity_feed_service.py
│   │   ├── models.py
│   │   └── repository.py
│   │
│   ├── customers/
│   │   ├── __init__.py
│   │   ├── identity_service.py
│   │   ├── profile_service.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── api.py
│   │
│   ├── communications/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── api.py
│   │
│   └── automation/
│       ├── __init__.py
│       ├── models.py
│       └── api.py
│
├── shared/
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/
│   │       └── (Alembic migrations)
│   │
│   ├── events/
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── auth.py
│
├── api/
│   ├── __init__.py
│   ├── health.py
│   └── v1/
│       ├── __init__.py
│       └── customers.py
│
├── celery_tasks.py
├── settings.py
├── main.py
└── requirements.txt
```

---

### 2. Core Configuration Files

#### settings.py

```python
# app/settings.py

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://pureleven:password@localhost:5432/pureleven"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Pureleven Customer Intelligence Platform"
    API_VERSION: str = "1.0.0"
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Environment
    ENV: str = os.getenv("ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

#### requirements.txt

```
# Core
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9
pydantic==2.4.2
pydantic-settings==2.1.0

# Async
celery==5.3.4
redis==5.0.1
python-dateutil==2.8.2

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
PyJWT==2.8.1

# Utils
python-dotenv==1.0.0
requests==2.31.0
httpx==0.25.2

# Monitoring
sentry-sdk==1.39.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Logging
python-json-logger==2.0.7
```

---

#### docker-compose.yml

```yaml
version: "3.9"

services:
  pureleven-postgres:
    image: postgres:15-alpine
    container_name: pureleven-postgres
    environment:
      POSTGRES_DB: pureleven
      POSTGRES_USER: pureleven
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - pureleven-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pureleven"]
      interval: 10s
      timeout: 5s
      retries: 5

  pureleven-redis:
    image: redis:7-alpine
    container_name: pureleven-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - pureleven-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  pureleven-pgbouncer:
    image: pgbouncer:1.21-alpine
    container_name: pureleven-pgbouncer
    environment:
      PGHOST: pureleven-postgres
      PGPORT: 5432
      PGUSER: pureleven
      PGPASSWORD: ${DB_PASSWORD:-password}
      PGDATABASE: pureleven
    ports:
      - "6432:6432"
    volumes:
      - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
    networks:
      - pureleven-network
    depends_on:
      pureleven-postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "psql", "-U", "pureleven", "-d", "pureleven", "-c", "SELECT 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  pureleven-ai-engine:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pureleven-ai-engine
    environment:
      DATABASE_URL: postgresql://pureleven:${DB_PASSWORD:-password}@pureleven-pgbouncer:6432/pureleven
      REDIS_URL: redis://pureleven-redis:6379/0
      CELERY_BROKER_URL: redis://pureleven-redis:6379/0
      CELERY_RESULT_BACKEND: redis://pureleven-redis:6379/1
      ENV: ${ENV:-development}
      JWT_SECRET: ${JWT_SECRET:-dev-secret}
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app
    networks:
      - pureleven-network
    depends_on:
      pureleven-postgres:
        condition: service_healthy
      pureleven-redis:
        condition: service_healthy
      pureleven-pgbouncer:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  pureleven-celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pureleven-celery-worker
    environment:
      DATABASE_URL: postgresql://pureleven:${DB_PASSWORD:-password}@pureleven-pgbouncer:6432/pureleven
      REDIS_URL: redis://pureleven-redis:6379/0
      CELERY_BROKER_URL: redis://pureleven-redis:6379/0
      CELERY_RESULT_BACKEND: redis://pureleven-redis:6379/1
      ENV: ${ENV:-development}
    networks:
      - pureleven-network
    depends_on:
      pureleven-postgres:
        condition: service_healthy
      pureleven-redis:
        condition: service_healthy
    command: celery -A app.celery_tasks worker --loglevel=info --concurrency=4

  pureleven-celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pureleven-celery-beat
    environment:
      DATABASE_URL: postgresql://pureleven:${DB_PASSWORD:-password}@pureleven-pgbouncer:6432/pureleven
      REDIS_URL: redis://pureleven-redis:6379/0
      CELERY_BROKER_URL: redis://pureleven-redis:6379/0
      CELERY_RESULT_BACKEND: redis://pureleven-redis:6379/1
      ENV: ${ENV:-development}
    networks:
      - pureleven-network
    depends_on:
      pureleven-postgres:
        condition: service_healthy
      pureleven-redis:
        condition: service_healthy
    command: celery -A app.celery_tasks beat --loglevel=info

volumes:
  postgres_data:
  redis_data:

networks:
  pureleven-network:
    driver: bridge
```

---

### 3. Database Session Management

#### shared/database/session.py

```python
# app/shared/database/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "development",
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True  # Validate connections before using
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Dependency for FastAPI to inject DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 4. Database Models & Migrations

#### shared/database/models.py

```python
# app/shared/database/models.py

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_customer_id = Column(String(100), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default="active")

class BehaviorEvent(Base):
    __tablename__ = "behavior_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, nullable=False)
    visitor_id = Column(UUID(as_uuid=True), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    gclid = Column(String(100), nullable=True)
    fbclid = Column(String(100), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Visitor(Base):
    __tablename__ = "visitors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    browser_id = Column(String(100), unique=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    has_email = Column(Boolean, default=False)
    has_phone = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("visitors.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    gclid = Column(String(100), nullable=True)
    fbclid = Column(String(100), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    event_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class CustomerIdentity(Base):
    __tablename__ = "customer_identities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, unique=True)
    shopify_customer_id = Column(String(100), unique=True)
    email = Column(String(100), unique=True)
    phone = Column(String(20), unique=True)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("visitors.id"), unique=True)
    primary_key_type = Column(String(50))  # shopify_id | email | phone | visitor_id
    confidence = Column(Float, default=1.0)
    retroactively_linked_event_count = Column(Integer, default=0)
    linked_events_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, unique=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    shopify_customer_id = Column(String(100), nullable=True)
    lifetime_value = Column(Float, default=0)
    total_orders = Column(Integer, default=0)
    average_order_value = Column(Float, default=0)
    page_views = Column(Integer, default=0)
    product_views = Column(Integer, default=0)
    total_events = Column(Integer, default=0)
    first_seen = Column(DateTime, nullable=True)
    first_purchase = Column(DateTime, nullable=True)
    last_purchase = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    segment = Column(String(50))  # vip | repeat | first_time | prospect | at_risk
    health_score = Column(Integer)
    dirty = Column(Boolean, default=False)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CustomerActivityFeed(Base):
    __tablename__ = "customer_activity_feed"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("behavior_events.id"), nullable=True)
    event_type = Column(String(50), nullable=True)
    action = Column(String(50))
    display_text = Column(String(500), nullable=False)
    context = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class EventError(Base):
    __tablename__ = "event_errors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=True)
    raw_event_data = Column(JSON, nullable=True)
    error_message = Column(String(500), nullable=True)
    error_code = Column(String(50), nullable=True)
    validation_failed_field = Column(String(100), nullable=True)
    stack_trace = Column(String(2000), nullable=True)
    visitor_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessedWebhook(Base):
    __tablename__ = "processed_webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(String(100), unique=True, nullable=False)
    webhook_type = Column(String(50))
    processed = Column(Boolean, default=True)
    result_status = Column(String(50))  # success | failed | retry
    error_message = Column(String(500), nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    shopify_order_id = Column(String(100), nullable=True)

class EventProcessingLog(Base):
    __tablename__ = "event_processing_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("behavior_events.id"), nullable=True)
    event_type = Column(String(50), nullable=True)
    status = Column(String(50))  # pending | processing | processed | failed | retried
    processor_name = Column(String(100))
    attempted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### 5. Celery Configuration

#### celery_tasks.py

```python
# app/celery_tasks.py

from celery import Celery
from app.settings import settings
import logging

celery_app = Celery(
    "pureleven",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes (soft limit before hard)
    broker_connection_retry_on_startup=True,
    result_expires=3600,
)

logger = logging.getLogger(__name__)

# Import tasks
from app.domains.customers.profile_service import rebuild_profile

__all__ = ["celery_app"]
```

---

### 6. Main FastAPI Application

#### main.py

```python
# app/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging

from app.settings import settings
from app.shared.database.session import get_db, engine
from app.shared.database.models import Base
from app.api import health
from app.api.v1 import customers

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(customers.router, prefix="/api/v1", tags=["customers"])

# Logging
logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENV == "development"
    )
```

---

### 7. Health Check Endpoint

#### api/health.py

```python
# app/api/health.py

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "pureleven-api"
    }
```

---

### 8. .env Template

```bash
# Database
DATABASE_URL=postgresql://pureleven:password@pureleven-pgbouncer:6432/pureleven
DB_PASSWORD=password

# Redis
REDIS_URL=redis://pureleven-redis:6379/0

# Celery
CELERY_BROKER_URL=redis://pureleven-redis:6379/0
CELERY_RESULT_BACKEND=redis://pureleven-redis:6379/1

# API
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET=your-super-secret-key-change-this

# Environment
ENV=development
LOG_LEVEL=info
```

---

## Sprint 0 Checklist

- [ ] Clone/setup repo
- [ ] Create folder structure
- [ ] Create all configuration files (settings.py, requirements.txt, .env)
- [ ] Create database models (models.py)
- [ ] Create docker-compose.yml
- [ ] Create Dockerfile
- [ ] Create main FastAPI application (main.py)
- [ ] Create Celery configuration (celery_tasks.py)
- [ ] Create health check endpoint
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Build Docker images (`docker-compose build`)
- [ ] Start containers (`docker-compose up`)
- [ ] Verify containers running (`docker ps`)
- [ ] Test health endpoint (`curl http://localhost:8000/api/health`)
- [ ] Verify database connection
- [ ] Verify Redis connection
- [ ] Create Alembic migrations
- [ ] Run migrations
- [ ] Commit to git

---

## Next: Sprint 1

Once Sprint 0 is complete:

1. Event validation module (`event_validator.py`)
2. Event ingestion endpoint (`POST /api/v1/events`)
3. Browser integration (update crm-attribution.js)
4. Test event flow end-to-end

---

**Status:** Ready to build  
**Owner:** (Your name)  
**Date:** May 25, 2026
