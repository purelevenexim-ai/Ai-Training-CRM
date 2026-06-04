# Deployment Note - 2026-06-04

## Scope

Deployed the new WhatsApp AI improvements to GitHub and production:

- prompt registry
- prompt observatory dashboard APIs
- prompt observatory dashboard tabs
- semantic post-delivery understanding
- improved Manglish detection for `kitti` / `nale`

GitHub commit deployed:

- `a4c889d` - `Add prompt observability and post-delivery understanding`

## Production paths updated

- Backend: `/opt/pureleven/ai-engine/app`
- Frontend: `/var/www/crm-dashboard`
- Container: `pureleven-ai-engine`

## Live production verification

Verified healthy:

- `GET /api/health` returns `{"status":"ok","app":"Anu Login API"}`
- prompt routes are live:
  - `/api/owner/dashboard/prompts`
  - `/api/owner/dashboard/prompt-observatory`

Verified in production container:

1. `black pepper undo?`
   - Intent: `availability`
   - Reply: short product reply
   - Status: good

2. `I will let you know tomorrow`
   - Intent: `followup`
   - Reply: defer reply
   - Status: acceptable, but still longer than ideal

3. `Thank u. Parcel kitti`
   - Intent: `delivery_received_confirmation`
   - Reply: post-delivery thank-you reply
   - Status: good

4. `paid`
   - Semantic understanding: `payment_confirmation`
   - Final reply still fell back to generic clarification
   - Status: not fixed fully yet

5. `[[media:image]]`
   - Intent: `media_received`
   - Reply asks for one-line clarification
   - Status: payment screenshot flow still not implemented

## Important deployment note

Production was behind the repository and missing multiple modules. During deployment, the server had to be resynced more broadly so the container could start cleanly. Missing production files included route, AI, service, and top-level app modules that the current repo already depends on.

## Next recommended fix

Priority next:

- implement payment proof / payment screenshot understanding at the router + media-analysis level
- map semantic `payment_confirmation` into a proper payment verification reply
- upgrade image/screenshot handling from generic media acknowledgement to payment-aware handling
