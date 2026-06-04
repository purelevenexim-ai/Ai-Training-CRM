import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage import init_database, get_db
from app.services.audience_service import ensure_default_templates

os.environ["ANU_LOGIN_DATABASE_PATH"] = "temp.db"
os.environ["ANU_LOGIN_ADMIN_SECRET"] = ""

def test_smoke():
    # 1. Init database
    init_database()
    ensure_default_templates()
    
    client = TestClient(app)
    
    # 2. Verify templates
    response = client.get("/api/audiences/templates")
    assert response.status_code == 200
    templates = response.json()
    print(f"Templates found: {len(templates)}")
    assert len(templates) >= 3
    
    # 3. POST /api/customers
    customer_data = {
        "email": "test@example.com",
        "phone": "1234567890",
        "meta_lead_id": "meta123",
        "google_gclid": "gclid123",
        "whatsapp_opt_in": True
    }
    response = client.post("/api/customers", json=customer_data)
    assert response.status_code in [200, 201]
    
    # 4. GET /api/customers/{email}/intelligence
    response = client.get("/api/customers/test@example.com/intelligence")
    assert response.status_code == 200
    intel = response.json()
    assert "customer_uid" in intel
    assert len(intel.get("identities", [])) >= 4
    
    # Verify score history in DB
    with get_db() as db:
        row = db.execute("SELECT * FROM customer_score_history WHERE customer_uid = ?", (intel["customer_uid"],)).fetchone()
        assert row is not None
    
    # 5. POST /api/customers/recompute-scores
    response = client.post("/api/customers/recompute-scores")
    assert response.status_code == 200
    
    # 6. Create minimal active journey
    template_id = templates[0]["id"]
    journey_data = {
        "name": "Smoke Test Journey",
        "is_active": True,
        "steps": [
            {
                "step_order": 1,
                "channel": "auto",
                "template_id": template_id,
                "delay_minutes": 0
            }
        ]
    }
    # Note: Assuming /api/journeys is the endpoint
    response = client.post("/api/journeys", json=journey_data)
    assert response.status_code in [200, 201]
    journey_id = response.json()["id"]
    
    # Enroll customer (Assuming endpoint based on usual patterns)
    enroll_data = {"email": "test@example.com"}
    response = client.post(f"/api/journeys/{journey_id}/enroll", json=enroll_data)
    assert response.status_code == 200
    
    # Verify journey_step_sends and ai_decisions
    with get_db() as db:
        send_row = db.execute("SELECT * FROM journey_step_sends").fetchone()
        assert send_row is not None
        assert send_row["channel"] in ["email", "whatsapp"]
        
        decision_row = db.execute("SELECT * FROM ai_decisions WHERE decision_type = 'journey_schedule'").fetchone()
        assert decision_row is not None

if __name__ == "__main__":
    try:
        test_smoke()
        print("SMOKE TEST PASS")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("SMOKE TEST FAIL")
        exit(1)
