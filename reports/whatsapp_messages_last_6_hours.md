# PureLeven WhatsApp Messages Report

- Window: last 6 hours
- Generated from live production database on 2026-06-05 UTC

## Raw Customer Messages

No raw customer messages were stored in the primary message tables during this window.

Checked tables:
- `conversation_audit_log`
- `ai_incoming_messages`
- `ai_outgoing_replies`

## Related Automation Events

| Timestamp | Source | Phone | Product | Event | Stage | Message ID |
|---|---|---:|---|---|---|---|
| 2026-06-05T04:31:37.812914+00:00 | customer_journey_logs | 919000000001 | cardamom | step_suppressed | text | 5ae229a6-f72c-41b6-9958-ce5fa17d931a |
| 2026-06-05T04:32:07.850346+00:00 | customer_journey_logs | 919000000002 | clove | step_suppressed | text | 79255988-0dbb-44e1-a67e-2dbf8b014b0d |
| 2026-06-05T04:32:37.887092+00:00 | customer_journey_logs | 919000000001 | cardamom | step_suppressed | text_with_image | 9cf810cb-e43f-4872-b8e1-83db5d798c39 |
| 2026-06-05T04:33:07.923685+00:00 | customer_journey_logs | 919000000002 | clove | step_suppressed | text_with_image | 3a64a653-b1bb-46d6-b115-592337a45de5 |
| 2026-06-05T04:33:37.963042+00:00 | customer_journey_logs | 919000000001 | cardamom | step_suppressed | combo | 72420706-750d-48fa-bfe1-64c67b65f3d6 |
| 2026-06-05T04:34:08.008834+00:00 | customer_journey_logs | 919000000002 | clove | step_suppressed | combo | d120fc45-a90f-4565-9202-ad7591d6bcea |
| 2026-06-05T04:39:08.402636+00:00 | customer_journey_logs | 919000000001 | cardamom | step_suppressed | text | 539b989e-0bf9-4217-890b-1d157435dacd |
| 2026-06-05T04:39:38.446112+00:00 | customer_journey_logs | 919000000002 | clove | step_suppressed | text | 99e29575-8618-4782-9aa0-90904b55e87f |

## Suppression Summary

| Product | Stage | Count |
|---|---|---:|
| cardamom | gentle_reminder | 3 |
| clove | gentle_reminder | 3 |
| white_pepper | combo_offer | 3 |
| white_pepper | final_followup | 3 |
| white_pepper | gentle_reminder | 3 |
| white_pepper | image_only | 3 |
| white_pepper | soft_nudge | 3 |
| black_pepper | combo_offer | 2 |
| black_pepper | final_followup | 2 |
| black_pepper | gentle_reminder | 2 |
| black_pepper | image_only | 2 |
| black_pepper | soft_nudge | 2 |
| cardamom | combo_offer | 2 |
| cardamom | final_followup | 2 |
| cardamom | image_only | 2 |
| cardamom | soft_nudge | 2 |
| cardamom | text | 2 |
| clove | combo_offer | 2 |
| clove | final_followup | 2 |
| clove | image_only | 2 |
| clove | soft_nudge | 2 |
| clove | text | 2 |
| cardamom | combo | 1 |
| cardamom | cross_sell | 1 |
| cardamom | text_with_image | 1 |
| cinnamon | cross_sell | 1 |
| cinnamon | gentle_reminder | 1 |
| clove | combo | 1 |
| clove | cross_sell | 1 |
| clove | text_with_image | 1 |
| pepper | cross_sell | 1 |
| pepper | gentle_reminder | 1 |
| pepper | order_capture_reminder | 1 |

## Conclusion

No raw customer chat messages were present in the main message tables for the last 6 hours. The system activity was dominated by inactive journey suppression.
