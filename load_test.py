"""
Pure Leven CRM — Locust Load Test (1000 Concurrent Users)
Usage:
    pip install locust
    locust -f load_test.py --host https://track.pureleven.com/api/crm \
           --users 1000 --spawn-rate 50 --run-time 10m --headless \
           --html load_test_report.html
"""

import json
import uuid
import time
from random import choice, randint
from locust import HttpUser, task, between, events
from locust.env import Environment

BASE = "/api/crm"

def uid():
    return uuid.uuid4().hex[:10]


def test_email():
    return f"loadtest_{uid()}@test.pureleven.com"


JOURNEY_TEMPLATES = [
    {
        "entry_trigger": "signup",
        "template_json": {
            "steps": [{"id": "s1", "type": "email", "delay_days": 0}]
        },
    },
    {
        "entry_trigger": "purchase",
        "template_json": {
            "steps": [
                {"id": "s1", "type": "email", "delay_days": 0},
                {"id": "s2", "type": "email", "delay_days": 7},
            ]
        },
    },
    {
        "entry_trigger": "cart_abandon",
        "template_json": {
            "steps": [{"id": "s1", "type": "email", "delay_days": 0}]
        },
    },
]


class CRMUser(HttpUser):
    """Simulates a typical CRM user making API requests."""
    wait_time = between(0.5, 2.0)
    journey_ids: list[str] = []

    def on_start(self):
        """Each user creates a journey on start."""
        template = choice(JOURNEY_TEMPLATES)
        with self.client.post(
            f"{BASE}/journeys",
            json={
                "name": f"Load Test Journey {uid()}",
                "status": "ACTIVE",
                **template,
            },
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                CRMUser.journey_ids.append(data["id"])
                resp.success()
            else:
                resp.failure(f"Failed to create journey: {resp.status_code}")

    @task(5)
    def list_journeys(self):
        """Most common operation: listing journeys."""
        with self.client.get(f"{BASE}/journeys", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"List journeys failed: {r.status_code}")

    @task(3)
    def create_journey(self):
        """Create a new journey."""
        template = choice(JOURNEY_TEMPLATES)
        with self.client.post(
            f"{BASE}/journeys",
            json={
                "name": f"Load Test {uid()}",
                "status": "ACTIVE",
                **template,
            },
            catch_response=True,
        ) as r:
            if r.status_code in (200, 201):
                data = r.json()
                CRMUser.journey_ids.append(data["id"])
                r.success()
            else:
                r.failure(f"Create journey: {r.status_code}")

    @task(4)
    def enroll_customer(self):
        """Enroll a customer into a random journey."""
        if not CRMUser.journey_ids:
            return
        journey_id = choice(CRMUser.journey_ids)
        email = test_email()
        with self.client.post(
            f"{BASE}/journeys/{journey_id}/enroll",
            json={"customer_email": email},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 201, 409):  # 409 = already enrolled
                r.success()
            else:
                r.failure(f"Enroll: {r.status_code}")

    @task(2)
    def get_journey_analytics(self):
        """Fetch analytics for a journey."""
        if not CRMUser.journey_ids:
            return
        journey_id = choice(CRMUser.journey_ids)
        with self.client.get(
            f"{BASE}/journeys/{journey_id}/analytics",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                r.success()
            elif r.status_code == 404:
                # Journey may have been deleted
                if journey_id in CRMUser.journey_ids:
                    CRMUser.journey_ids.remove(journey_id)
                r.success()
            else:
                r.failure(f"Analytics: {r.status_code}")

    @task(2)
    def get_enrollments(self):
        """List enrollments for a journey."""
        if not CRMUser.journey_ids:
            return
        journey_id = choice(CRMUser.journey_ids)
        with self.client.get(
            f"{BASE}/journeys/{journey_id}/enrollments",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f"Enrollments: {r.status_code}")

    @task(1)
    def health_check(self):
        """Check API health."""
        with self.client.get(f"{BASE}/health", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Health: {r.status_code}")

    @task(1)
    def create_variant(self):
        """Create an A/B variant for a journey."""
        if not CRMUser.journey_ids:
            return
        journey_id = choice(CRMUser.journey_ids)
        with self.client.post(
            f"{BASE}/journeys/{journey_id}/variants",
            json={
                "variant_name": f"Variant {uid()}",
                "traffic_split_pct": 50,
                "status": "ACTIVE",
            },
            catch_response=True,
        ) as r:
            if r.status_code in (200, 201, 404):
                r.success()
            else:
                r.failure(f"Create variant: {r.status_code}")

    @task(1)
    def clone_journey(self):
        """Clone a journey."""
        if not CRMUser.journey_ids:
            return
        journey_id = choice(CRMUser.journey_ids)
        with self.client.post(
            f"{BASE}/journeys/{journey_id}/clone",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 201, 404):
                r.success()
            else:
                r.failure(f"Clone: {r.status_code}")

    @task(1)
    def shopify_webhook(self):
        """Simulate a Shopify order webhook."""
        with self.client.post(
            f"{BASE}/webhooks/shopify/order-paid",
            json={
                "id": randint(1000000000, 9999999999),
                "email": test_email(),
                "total_price": f"{randint(99, 999)}.00",
                "currency": "INR",
                "line_items": [
                    {
                        "product_id": 9119327281398,
                        "title": "Kerala Cardamom 50gm",
                        "quantity": 1,
                        "price": "199.00",
                    }
                ],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            headers={"X-Shopify-Topic": "orders/paid"},
            catch_response=True,
        ) as r:
            # Accept 200, 401 (HMAC), 400 (missing fields) — just not 500
            if r.status_code < 500:
                r.success()
            else:
                r.failure(f"Webhook: {r.status_code}")

    @task(1)
    def scheduler_status(self):
        """Check audience sync scheduler status."""
        with self.client.get(f"{BASE}/sync/status", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Scheduler: {r.status_code}")


class ReadHeavyUser(HttpUser):
    """Simulates a read-heavy analytics user (lower concurrency)."""
    wait_time = between(1, 3)
    weight = 20  # 20% of users

    @task(8)
    def list_journeys(self):
        with self.client.get(f"{BASE}/journeys", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"List: {r.status_code}")

    @task(5)
    def health_check(self):
        with self.client.get(f"{BASE}/health/full", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Full health: {r.status_code}")

    @task(3)
    def scheduler_status(self):
        with self.client.get(f"{BASE}/sync/status", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Sync status: {r.status_code}")


@events.quitting.add_listener
def on_locust_quit(environment: Environment, **kwargs):
    """Print summary on exit."""
    stats = environment.stats
    print("\n" + "="*60)
    print("LOAD TEST SUMMARY")
    print("="*60)
    total = stats.total
    print(f"Total requests: {total.num_requests}")
    print(f"Failures: {total.num_failures} ({100 * total.fail_ratio:.1f}%)")
    print(f"Avg response time: {total.avg_response_time:.0f}ms")
    print(f"95th percentile: {total.get_response_time_percentile(0.95):.0f}ms")
    print(f"99th percentile: {total.get_response_time_percentile(0.99):.0f}ms")
    print(f"Max response time: {total.max_response_time:.0f}ms")
    print(f"RPS: {total.current_rps:.1f}")
    print("="*60)

    # Fail if error rate > 5%
    if total.fail_ratio > 0.05:
        print(f"\n❌ LOAD TEST FAILED: error rate {100*total.fail_ratio:.1f}% > 5% threshold")
        environment.process_exit_code = 1
    else:
        print(f"\n✅ LOAD TEST PASSED: error rate {100*total.fail_ratio:.1f}% < 5%")
