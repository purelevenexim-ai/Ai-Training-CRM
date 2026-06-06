# Pureleven CRM

> Customer Relationship Management system for Pureleven — Kerala-sourced organic spices, honey, tea, coffee, and wellness products.

This repository contains the CRM backend, APIs, dashboards, and integrations for Pureleven's customer intelligence platform.

## Repository Structure

```
├── api/                # REST/GraphQL API endpoints and integrations
│   ├── ai_service/
│   ├── routes/
│   ├── csv_import_integration.py
│   ├── customer_enrichment_integration.py
│   ├── sms_email_integration.py
│   └── ...
├── app/                # CRM application code
│   ├── crm_routes.py
│   ├── crm_models.py
│   ├── realtime_routes.py
│   ├── auth_routes.py
│   ├── meta_ads_routes.py
│   ├── cart_recovery_routes.py
│   └── ...
├── alembic/            # Database migrations
├── dashboards/         # CRM dashboard components
├── deploy/             # Deployment CI/CD configurations
├── migration/          # Data migration scripts
├── scripts/            # Utility scripts
├── tests/              # Test suites
├── main.py             # FastAPI entry point
├── requirements.txt    # Python dependencies
└── package.json        # Frontend (React/Vite)
```

## Tech Stack

- **Backend**: Python (FastAPI)
- **Frontend**: React with Vite, Recharts, Zustand
- **Database**: PostgreSQL (via SQLAlchemy + Alembic)
- **Integrations**: Shopify API, Meta/Facebook Ads, Google Analytics, SendGrid, Shiprocket/Delhivery

## Setup

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure your environment
uvicorn main:app --reload
```

### Frontend
```bash
npm install
npm run dev
```

### Database
```bash
alembic upgrade head
```

## Related Repositories

- **Shopify Theme**: [purelevenexim-ai/Shopify-Theme](https://github.com/purelevenexim-ai/Shopify-Theme) — Storefront Liquid theme
- **AI Training**: [purelevenexim-ai/Ai-training](https://github.com/purelevenexim-ai/Ai-training) — AI chatbot, Wabis messaging

## Original Source

This repository was split from the monorepo at `purelevenexim-ai/Ai-Training-CRM` on 6 June 2026. Backup branch: `backup/full-monorepo-2026-06-06`.
