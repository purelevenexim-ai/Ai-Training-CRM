# Deep Issue Report

Window: last 6 hours

## What Broke

1. The raw WhatsApp message pipeline did not yield any new stored customer messages in `conversation_audit_log`, `ai_incoming_messages`, or `ai_outgoing_replies`.
2. The monitor and message-control views had to rely on fallback state snapshots instead of real message rows.
3. The follow-up engine kept generating jobs, but the journey was inactive, so everything was suppressed instead of sent.
4. SQLite lock contention was affecting dashboard reads until WAL mode and lock-safe fallbacks were applied.

## What To Fix Next

1. Make sure every inbound WhatsApp message is written to the raw audit table before any routing decision.
2. Use raw message rows as the source of truth for AI Monitor and Message Control, with fallback state only as a backup.
3. Add a clear active/inactive journey control so suppression noise is intentional, not accidental.
4. Keep the production SQLite database on the mounted persistent path with WAL enabled.
5. Add a daily report that distinguishes:
   - raw customer messages
   - automation events
   - AI-generated replies
   - suppressed follow-ups

## Notes

- The dashboard fixes are deployed and the tabs now load successfully.
- The remaining gap is data fidelity, not the dashboard shell itself.
