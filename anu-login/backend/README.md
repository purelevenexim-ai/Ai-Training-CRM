# Anu Login Backend

Minimal FastAPI backend for the in-theme Anu login popup.

## Endpoints

- `POST /api/leads` saves a lead and returns the unlocked coupon code.
- `GET /api/leads` lists recent leads for lightweight marketing review.
- `GET /api/health` returns service health.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment variables

- `ANU_LOGIN_DATABASE_PATH`: optional SQLite file path.
- `ANU_LOGIN_ALLOWED_ORIGINS`: comma-separated CORS allowlist. Use `*` only for early testing.
- `ANU_LOGIN_DEFAULT_COUPON`: fallback coupon code returned to the storefront.

## Theme hookup

Set the Theme Editor field `Anu login > Lead API URL` to:

```txt
https://your-api-host.example.com/api/leads
```