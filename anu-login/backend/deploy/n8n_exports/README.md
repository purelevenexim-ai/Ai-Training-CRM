# N8N Workflow Export Set (8 Workflows)

Import these JSON files into n8n (Workflows -> Import from File):

1. 01_shopify_catalog_sync.json
2. 02_daily_journey_preview.json
3. 03_daily_journey_orchestrate.json
4. 04_ai_followup_dispatch_webhook.json
5. 05_meta_delivery_webhook_relay.json
6. 06_customer_reply_tracking_webhook.json
7. 07_delhivery_webhook_relay.json
8. 08_health_daily_report.json

## Before activating
- Update backend base URL if not local:
  - Current default: http://127.0.0.1:8000/api
- For production, replace with your API host:
  - Example: https://adsapi.pureleven.com/api
- For webhook relay workflows, publish webhook URLs from n8n and wire sources:
  - Meta/Wabis inbound -> 05 / 06
  - Delhivery webhook -> 07

## Smoke test sequence
- Activate 01 and run once.
- Confirm GET /api/ai/catalog returns product_count > 0.
- Run 02 and confirm preview payload has total_would_send.
- Run 03 in dry-run first by editing payload in node if needed.
- Activate 08 and confirm daily-report endpoint responds with status sent.
