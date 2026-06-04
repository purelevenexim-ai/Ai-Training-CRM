set -e
PHONE="919999000123"
SHOP="rwxtic-gz.myshopify.com"

# 1) Seed test customer directly in sqlite
echo "--- STEP 1: SEEDING ---"
/Users/bthomas/Documents/pureleven_dev/.venv/bin/python - <<'PY'
import uuid
from datetime import datetime, timedelta, timezone
from app.storage import get_db_connection
phone='919999000123'
shop='rwxtic-gz.myshopify.com'
now=datetime.now(timezone.utc)
with get_db_connection() as conn:
    existing=conn.execute("SELECT id FROM journey_customers WHERE shop_domain=? AND phone=? ORDER BY created_at DESC LIMIT 1",(shop,phone)).fetchone()
    if existing:
        cid=existing['id']
        conn.execute("""
        UPDATE journey_customers
        SET name='Live Test Customer', delivery_status='delivered', delivered_at=?,
            day1_sent=0, day2_sent=0, day5_sent=0, day15_sent=0, day30_sent=0, day60_sent=0, day75_sent=0, day95_sent=0,
            do_not_message=0, whatsapp_subscription_status='subscribed', engagement_score=10, customer_segment='low',
            is_responsive=0, updated_at=?
        WHERE id=?
        """, ((now - timedelta(days=1)).isoformat(), now.isoformat(), cid))
    else:
        cid=str(uuid.uuid4())
        conn.execute("""
        INSERT INTO journey_customers (
            id, shop_domain, phone, name, email, journey_started_at, delivery_status, delivered_at,
            created_at, updated_at, whatsapp_subscription_status, do_not_message,
            engagement_score, customer_segment, is_responsive
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'subscribed', 0, 10, 'low', 0)
        """, (cid, shop, phone, 'Live Test Customer', 'livetest@example.com', (now - timedelta(days=2)).isoformat(), 'delivered', (now - timedelta(days=1)).isoformat(), now.isoformat(), now.isoformat()))
print('SEEDED_PHONE', phone)
PY

# 2) Core health checks
printf "\nSTEP2_HEALTH\n"
curl -s http://127.0.0.1:8000/api/health
printf "\n"
curl -s http://127.0.0.1:8000/api/monitoring/health
printf "\n"

# 3) Journey preview for shop
printf "\nSTEP3_PREVIEW\n"
curl -s -X POST http://127.0.0.1:8000/api/journey/orchestrate/preview -H 'Content-Type: application/json' -d '{"shop_domain":"rwxtic-gz.myshopify.com"}'
printf "\n"

# 4) Journey single-customer dry-run send
printf "\nSTEP4_ORCHESTRATE_CUSTOMER\n"
CID=$(/Users/bthomas/Documents/pureleven_dev/.venv/bin/python - <<'PY'
from app.storage import get_db_connection
with get_db_connection() as conn:
    row=conn.execute("SELECT id FROM journey_customers WHERE shop_domain=? AND phone=? ORDER BY created_at DESC LIMIT 1",('rwxtic-gz.myshopify.com','919999000123')).fetchone()
    print(row['id'])
PY
)
curl -s -X POST http://127.0.0.1:8000/api/journey/orchestrate/customer -H 'Content-Type: application/json' -d "{\"shop_domain\":\"$SHOP\",\"customer_id\":\"$CID\",\"stage\":\"delivered\",\"dry_run\":true}"
printf "\n"

# 5) Tracking flow: click + reply + call
printf "\nSTEP5_TRACKING\n"
curl -s -X POST http://127.0.0.1:8000/api/tracking/whatsapp-click -H 'Content-Type: application/json' -d "{\"customer_phone\":\"$PHONE\",\"shop_domain\":\"$SHOP\",\"template_name\":\"delivered_review_request_v1\",\"button_text\":\"Write Review\",\"journey_stage\":\"day5\",\"metadata\":{}}"
printf "\n"
curl -s -X POST http://127.0.0.1:8000/api/tracking/whatsapp-reply -H 'Content-Type: application/json' -d "{\"customer_phone\":\"$PHONE\",\"shop_domain\":\"$SHOP\",\"template_name\":\"delivered_review_request_v1\",\"reply_text\":\"I want to buy more\",\"journey_stage\":\"day5\",\"metadata\":{}}"
printf "\n"
curl -s -X POST http://127.0.0.1:8000/api/tracking/whatsapp-call -H 'Content-Type: application/json' -d "{\"customer_phone\":\"$PHONE\",\"shop_domain\":\"$SHOP\",\"template_name\":\"corporate_pitch_high_v1\",\"journey_stage\":\"day60\",\"metadata\":{}}"
printf "\n"

# 6) AI session open and dispatch
printf "\nSTEP6_AI_SESSION\n"
SESSION_JSON=$(curl -s -X POST http://127.0.0.1:8000/api/ai/session/open -H 'Content-Type: application/json' -d "{\"customer_phone\":\"$PHONE\",\"shop_domain\":\"$SHOP\",\"trigger_template\":\"delivery_webhook\"}")
echo "$SESSION_JSON"
SESSION_ID=$(echo "$SESSION_JSON" | /Users/bthomas/Documents/pureleven_dev/.venv/bin/python - <<'PY'
import sys, json
try:
    obj=json.load(sys.stdin)
    print(obj.get('session_id',''))
except Exception:
    print('')
PY
)

# force one pending followup due now so dispatch can return should_send=true
if [ -n "$SESSION_ID" ]; then
/Users/bthomas/Documents/pureleven_dev/.venv/bin/python - <<PY
from datetime import datetime, timezone, timedelta
from app.storage import get_db_connection
sid='''$SESSION_ID'''
with get_db_connection() as conn:
    conn.execute("UPDATE conversation_followups SET scheduled_at=? WHERE session_id=? AND sent=0", ((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(), sid))
print('FOLLOWUP_FORCED_DUE', sid)
PY
fi

DISPATCH1=$(curl -s -X POST http://127.0.0.1:8000/api/ai/dispatch -H 'Content-Type: application/json' -d "{\"customer_phone\":\"$PHONE\",\"shop_domain\":\"$SHOP\",\"incoming_reply\":\"\"}")
echo "$DISPATCH1"

DISPATCH2=$(curl -s -X POST http://127.0.0.1:8000/api/ai/dispatch -H 'Content-Type: application/json' -d "{\"customer_phone\":\"$PHONE\",\"shop_domain\":\"$SHOP\",\"incoming_reply\":\"I need bulk pricing for office\"}")
echo "$DISPATCH2"

# 7) Dashboard + status checks
printf "\nSTEP7_STATUS\n"
curl -s http://127.0.0.1:8000/api/monitoring/dashboard
printf "\n"
curl -s "http://127.0.0.1:8000/api/journey/orchestrate/status?shop_domain=$SHOP"
printf "\n"

# 8) Final DB assertions for this test phone
printf "\nSTEP8_DB_ASSERT\n"
/Users/bthomas/Documents/pureleven_dev/.venv/bin/python - <<'PY'
from app.storage import get_db_connection
phone='919999000123'
shop='rwxtic-gz.myshopify.com'
with get_db_connection() as conn:
    c=conn.execute("SELECT id, engagement_score, customer_segment, is_responsive, do_not_message FROM journey_customers WHERE shop_domain=? AND phone=? ORDER BY created_at DESC LIMIT 1",(shop,phone)).fetchone()
    ev=conn.execute("SELECT COUNT(*) AS cnt FROM journey_engagement_events WHERE customer_id=?",(c['id'],)).fetchone()['cnt']
    sess=conn.execute("SELECT COUNT(*) AS cnt FROM conversation_sessions WHERE customer_phone=?",(phone,)).fetchone()['cnt']
    fu=conn.execute("SELECT COUNT(*) AS cnt FROM conversation_followups WHERE session_id IN (SELECT id FROM conversation_sessions WHERE customer_phone=?)",(phone,)).fetchone()['cnt']
print({'engagement_score': c['engagement_score'], 'segment': c['customer_segment'], 'is_responsive': c['is_responsive'], 'do_not_message': c['do_not_message'], 'events_logged': ev, 'sessions': sess, 'followups': fu})
PY

echo "LIVE_JOURNEY_TEST_DONE"
