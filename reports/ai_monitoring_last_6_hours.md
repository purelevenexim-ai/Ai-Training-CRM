# PureLeven AI Monitoring Report

- Window: last 6 hours
- Generated from live production database on 2026-06-05 UTC

## Monitor Metrics

| Metric | Value |
|---|---:|
| Journeys | 33 |
| Messages | 33 |
| AI Messages | 0 |
| Issues | 0 |
| Journeys With Issues | 0 |
| Average Success Score | 100.0 |
| AI Success Rate | 0.0 |

## Message Control Metrics

| Metric | Value |
|---|---:|
| Decisions | 20 |
| AI Skipped | 1 |
| Audited Replies | 0 |
| Duplicate Lock Groups | 0 |

## What The Monitor Is Seeing

- The monitor is seeing 33 conversation-state snapshots.
- It is not seeing raw inbound/outbound WhatsApp rows for this 6-hour window.
- No AI replies were logged in this window.
- No issue rows were generated because there were no raw AI conversation events to score.

## Follow-up Suppression

- 62 follow-up rows were suppressed because the active product journey is inactive.
- The most frequent suppressed products were:
  - `white_pepper`
  - `black_pepper`
  - `cardamom`
  - `clove`

## Live Data Sources Checked

- `conversation_audit_log`: 0
- `ai_incoming_messages`: 0
- `ai_outgoing_replies`: 0
- `customer_journey_logs`: 8 recent rows
- `product_journey_followups`: 62 recent suppressed rows
- `conversation_state`: 33 state rows

## Operational Read

The dashboard is now reading the persistent mounted SQLite database and not the empty container-local file. That fixed the empty tab problem, but it also exposed a deeper reporting gap: the raw WhatsApp message pipeline is not writing recent customer messages into the main audit tables.

## Recommended Next Step

Reconcile the webhook/message ingest path so every inbound WhatsApp message writes a raw row first, then let the monitor and dashboard build from that source of truth.
