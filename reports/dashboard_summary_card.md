# Dashboard Summary Card

Window: last 6 hours

## At A Glance

- Raw customer messages found: 0
- Automation/system events found: 70
- AI replies sent: 0
- Monitor journeys: 33
- Monitor issues: 0
- Follow-up suppressions: 62

## Main Signal

The dashboard is healthy at the infrastructure level, but the live WhatsApp report is not backed by raw inbound customer messages in the current 6-hour window. What is visible instead is suppressed journey activity from inactive follow-up jobs.

## Immediate Action

1. Confirm inbound WhatsApp messages are persisted to the primary audit tables.
2. Decide whether the product journey should be active or explicitly disabled.
3. Keep SQLite in WAL mode for stable dashboard reads.
