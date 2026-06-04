# Quick Reference: Flow Validation Deployment & Testing

## Deploy Now

```bash
# From local machine
cd /Users/bthomas/Documents/pureleven_dev
bash deploy_flow_fixes.sh
```

## Monitor Deployment

```bash
# SSH to VPS and watch for flow events
ssh root@192.46.213.140
docker logs -f pureleven-ai-engine | grep -E "FLOW|ROUTE"

# Should see logs like:
# [FLOW-ABANDONED] phone=919876543210 flow=language_selection reason=product_intent_override
# [ROUTE-DECISION] 919876543210 → catalog (product detected)
```

## Test Scenarios (Manual)

1. **Test Product Override** (Cardamom example)
   ```
   Wabis to customer: "Choose Language: English / Malayalam"
   Customer types: "Cardamom"
   Expected: Catalog shows cardamom
   Check logs: [FLOW-ABANDONED] ... reason=product_intent_override
   ```

2. **Test Fuzzy Match** (English please)
   ```
   Wabis to customer: "Choose Language: English / Malayalam"
   Customer types: "English please"
   Expected: Language selected successfully
   Check logs: No FLOW-ABANDONED (matches "english")
   ```

3. **Test Numeric Option**
   ```
   Wabis to customer: "Choose Language: 1 English / 2 Malayalam"
   Customer types: "1"
   Expected: Option 1 selected
   Check logs: No FLOW-ABANDONED (matches "1")
   ```

## Database Audit Trail

```bash
# SSH to VPS
ssh root@192.46.213.140
docker exec pureleven-ai-engine sqlite3 /app/data/anu_login.sqlite3

# Inside SQLite shell:
-- View all abandonments
SELECT phone, flow_name, abandonment_reason, received_message, timestamp 
FROM flow_audit 
ORDER BY timestamp DESC LIMIT 20;

-- Count by reason
SELECT abandonment_reason, COUNT(*) 
FROM flow_audit 
WHERE flow_name='language_selection' 
GROUP BY abandonment_reason;

-- Calculate product override percentage
SELECT 
    ROUND(100.0 * SUM(CASE WHEN abandonment_reason='product_intent_override' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_product_overrides
FROM flow_audit
WHERE flow_name='language_selection' AND timestamp > datetime('now', '-7 days');
```

## Logs to Watch

### Success Indicator
```
[FLOW-ABANDONED] phone=919876543210 flow=language_selection reason=product_intent_override expected=['english', 'malayalam', '1', '2'] received=Cardamom
```
→ Customer tried product name → flow correctly abandoned

### Error to Fix
```
[FLOW-ABANDONED] phone=919876543210 flow=language_selection reason=unrelated_input
```
→ Customer sent unrelated text → flow abandoned (expected)

## Rollback (if needed)

```bash
# Just restart without these changes
docker restart pureleven-ai-engine
# Service reverts to old behavior
```

## Files Deployed

```
✅ /app/app/storage.py                    (database schema)
✅ /app/app/ai/flow_helpers.py           (fuzzy match + product detection)
✅ /app/app/ai/conversation_state_manager.py (expected_responses support)
✅ /app/app/ai/intent_router.py          (flow validation logic)
✅ /app/app/routes/wave02_wabis_routes.py (pass expected_responses through)
```

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Product Override | ❌ Loops back | ✅ Detects intent |
| Fuzzy Matching | ❌ Exact match | ✅ Variations work |
| Audit Trail | ❌ No logs | ✅ flow_audit table |
| Measurement | ❌ Manual | ✅ SQL queries |

---

**Question?** Check conversation history or FLOW_VALIDATION_IMPLEMENTATION.md
