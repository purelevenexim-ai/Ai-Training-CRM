#!/usr/bin/env python3
"""
Pure Leven CRM — Test Data Generator
Creates 1000 journeys + 1000 customers + enrollments on the VPS API.
Usage:
    python generate_test_data.py            # Create all test data
    python generate_test_data.py --count 50 # Create 50 of each
    python generate_test_data.py --dry-run  # Print what would be created
"""

import asyncio
import uuid
import argparse
import json
import time
import sys
from datetime import datetime
from typing import Optional

import aiohttp

BASE = "https://track.pureleven.com/api/crm"
TEST_EMAIL_DOMAIN = "test.pureleven.com"
JOURNEY_PREFIX = "Scale Test Journey"
SEMAPHORE_LIMIT = 20  # Max concurrent requests

ENTRY_TRIGGERS = ["signup", "purchase", "cart_abandon", "browse", "reactivation"]
JOURNEY_STATUSES = ["ACTIVE", "ACTIVE", "ACTIVE", "DRAFT"]  # 75% active

STEP_TEMPLATES = [
    {
        "steps": [
            {"id": "step_1", "type": "email", "delay_days": 0, "action_data": {"subject": "Welcome to Pureleven"}},
            {"id": "step_2", "type": "email", "delay_days": 3, "action_data": {"subject": "Top Products for You"}},
            {"id": "step_3", "type": "email", "delay_days": 7, "action_data": {"subject": "Don't miss out"}},
        ]
    },
    {
        "steps": [
            {"id": "step_1", "type": "email", "delay_days": 0, "action_data": {"subject": "Cart Reminder"}},
            {"id": "step_2", "type": "email", "delay_days": 1, "action_data": {"subject": "Still interested?"}},
        ]
    },
    {
        "steps": [
            {"id": "step_1", "type": "email", "delay_days": 0, "action_data": {"subject": "Your order is confirmed"}},
            {"id": "step_2", "type": "email", "delay_days": 7, "action_data": {"subject": "How was your experience?"}},
            {"id": "step_3", "type": "email", "delay_days": 14, "action_data": {"subject": "Order again?"}},
            {"id": "step_4", "type": "email", "delay_days": 30, "action_data": {"subject": "We miss you"}},
        ]
    },
    {
        "steps": [
            {"id": "step_1", "type": "email", "delay_days": 0, "action_data": {"subject": "We noticed you browsed"}},
            {"id": "step_2", "type": "email", "delay_days": 2, "action_data": {"subject": "Special offer inside"}},
        ]
    },
]

PRODUCT_TAGS = [
    "spices", "oils", "grains", "organic", "premium", "kerala",
    "north-india", "south-india", "everyday", "gift-set",
]

CUSTOMER_NAMES = [
    ("Aarav", "Sharma"), ("Vivaan", "Patel"), ("Aditya", "Mehta"),
    ("Vihaan", "Gupta"), ("Arjun", "Kumar"), ("Sai", "Reddy"),
    ("Reyansh", "Nair"), ("Ayaan", "Singh"), ("Krishna", "Iyer"),
    ("Ishaan", "Verma"), ("Ananya", "Das"), ("Diya", "Shah"),
    ("Saanvi", "Joshi"), ("Myra", "Bhat"), ("Avni", "Rao"),
    ("Aanya", "Pillai"), ("Aarohi", "Menon"), ("Pari", "Sinha"),
    ("Kavya", "Ghosh"), ("Isha", "Mukherjee"),
]


def unique_id() -> str:
    return uuid.uuid4().hex[:12]


def test_email(prefix: str = "gen") -> str:
    return f"{prefix}_{unique_id()}@{TEST_EMAIL_DOMAIN}"


def journey_payload(index: int) -> dict:
    template = STEP_TEMPLATES[index % len(STEP_TEMPLATES)]
    tag = PRODUCT_TAGS[index % len(PRODUCT_TAGS)]
    trigger = ENTRY_TRIGGERS[index % len(ENTRY_TRIGGERS)]
    status = JOURNEY_STATUSES[index % len(JOURNEY_STATUSES)]
    return {
        "name": f"{JOURNEY_PREFIX} {index:04d} {unique_id()}",
        "entry_trigger": trigger,
        "status": status,
        "template_json": {
            **template,
            "meta": {
                "product_tag": tag,
                "created_by": "test_generator",
                "batch": "scale_test_2026",
            },
        },
    }


def customer_payload(index: int) -> dict:
    first, last = CUSTOMER_NAMES[index % len(CUSTOMER_NAMES)]
    suffix = unique_id()
    return {
        "email": test_email(f"gen_{first.lower()}_{last.lower()}"),
        "first_name": first,
        "last_name": f"{last} {index}",
        "phone": f"+91{9000000000 + index:010d}"[:13],
        "tags": [PRODUCT_TAGS[index % len(PRODUCT_TAGS)]],
        "source": "test_generator",
    }


class DataGenerator:
    def __init__(self, base_url: str, count: int, dry_run: bool = False):
        self.base = base_url
        self.count = count
        self.dry_run = dry_run
        self.sem = asyncio.Semaphore(SEMAPHORE_LIMIT)
        self.results = {
            "journeys": {"success": 0, "fail": 0, "ids": []},
            "customers": {"success": 0, "fail": 0, "ids": []},
            "enrollments": {"success": 0, "fail": 0},
            "errors": [],
        }

    async def create_journey(self, session: aiohttp.ClientSession, index: int) -> Optional[str]:
        payload = journey_payload(index)
        if self.dry_run:
            print(f"[DRY] Would create journey: {payload['name']}")
            return f"dry_run_{index}"

        async with self.sem:
            try:
                async with session.post(f"{self.base}/journeys", json=payload) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        self.results["journeys"]["success"] += 1
                        self.results["journeys"]["ids"].append(data["id"])
                        return data["id"]
                    else:
                        text = await resp.text()
                        self.results["journeys"]["fail"] += 1
                        self.results["errors"].append(
                            f"Journey {index}: HTTP {resp.status} — {text[:200]}"
                        )
                        return None
            except Exception as e:
                self.results["journeys"]["fail"] += 1
                self.results["errors"].append(f"Journey {index} exception: {str(e)[:100]}")
                return None

    def generate_customer_email(self, index: int) -> str:
        """Generate a unique customer email (no API call needed — enrollment auto-creates customers)."""
        payload = customer_payload(index)
        email = payload["email"]
        if self.dry_run:
            print(f"[DRY] Would use customer: {email}")
        self.results["customers"]["success"] += 1
        self.results["customers"]["ids"].append(email)
        return email

    async def enroll_customer(
        self,
        session: aiohttp.ClientSession,
        journey_id: str,
        customer_email: str,
        index: int,
    ) -> None:
        if self.dry_run:
            return

        async with self.sem:
            try:
                async with session.post(
                    f"{self.base}/journeys/{journey_id}/enroll",
                    json={"customer_email": customer_email},
                ) as resp:
                    if resp.status in (200, 201):
                        self.results["enrollments"]["success"] += 1
                    elif resp.status == 409:
                        # Duplicate enrollment - expected sometimes
                        pass
                    else:
                        self.results["enrollments"]["fail"] += 1
            except Exception as e:
                self.results["enrollments"]["fail"] += 1
                self.results["errors"].append(f"Enroll {index} exception: {str(e)[:100]}")

    async def run(self):
        print(f"\n{'='*60}")
        print(f"Pure Leven CRM Test Data Generator")
        print(f"Target: {self.count} journeys + {self.count} customers")
        print(f"API: {self.base}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"{'='*60}\n")

        # Verify API health first
        if not self.dry_run:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base}/health/full") as resp:
                        health = await resp.json()
                        if health.get("status") not in ("healthy", "ok"):
                            print(f"❌ API unhealthy: {health}")
                            sys.exit(1)
                        print(f"✅ API healthy: DB={health['checks']['database']['status']}, "
                              f"Redis={health['checks']['redis']['status']}")
            except Exception as e:
                print(f"❌ Cannot reach API: {e}")
                sys.exit(1)

        connector = aiohttp.TCPConnector(limit=50, ssl=False)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Step 1: Create journeys in batches
            print(f"\n[1/4] Creating {self.count} test journeys...")
            start = time.time()
            journey_tasks = [
                self.create_journey(session, i) for i in range(1, self.count + 1)
            ]
            journey_ids = await asyncio.gather(*journey_tasks)
            valid_journey_ids = [j for j in journey_ids if j]
            elapsed = time.time() - start
            print(
                f"    ✅ {self.results['journeys']['success']}/{self.count} journeys created "
                f"in {elapsed:.1f}s ({self.results['journeys']['fail']} failed)"
            )

            # Step 2: Generate customer emails (enrollment auto-creates them in DB)
            print(f"\n[2/4] Generating {self.count} test customer emails (auto-created on enrollment)...")
            start = time.time()
            valid_emails = [self.generate_customer_email(i) for i in range(1, self.count + 1)]
            elapsed = time.time() - start
            print(
                f"    ✅ {self.results['customers']['success']}/{self.count} customer emails ready "
                f"in {elapsed:.2f}s"
            )

            # Step 3: Enroll each customer in 2 journeys
            print(f"\n[3/4] Enrolling customers into journeys (2 each)...")
            start = time.time()
            enroll_tasks = []
            for idx, email in enumerate(valid_emails):
                if valid_journey_ids:
                    j1 = valid_journey_ids[idx % len(valid_journey_ids)]
                    j2 = valid_journey_ids[(idx + 1) % len(valid_journey_ids)]
                    enroll_tasks.append(self.enroll_customer(session, j1, email, idx))
                    enroll_tasks.append(self.enroll_customer(session, j2, email, idx + len(valid_emails)))

            await asyncio.gather(*enroll_tasks)
            elapsed = time.time() - start
            print(
                f"    ✅ {self.results['enrollments']['success']} enrollments created "
                f"in {elapsed:.1f}s ({self.results['enrollments']['fail']} failed)"
            )

            # Step 4: Create variants for first 100 journeys
            print(f"\n[4/4] Creating A/B variants for first 100 journeys...")
            start = time.time()
            variant_success = 0
            variant_tasks = []
            for jid in valid_journey_ids[:100]:
                async def create_variant(session=session, jid=jid):
                    nonlocal variant_success
                    async with self.sem:
                        try:
                            async with session.post(
                                f"{self.base}/journeys/{jid}/variants",
                                json={
                                    "variant_name": f"Variant B {unique_id()}",
                                    "traffic_split_pct": 50,
                                    "status": "ACTIVE",
                                },
                            ) as resp:
                                if resp.status in (200, 201):
                                    variant_success += 1
                        except Exception:
                            pass

                if not self.dry_run:
                    variant_tasks.append(create_variant())

            if variant_tasks:
                await asyncio.gather(*variant_tasks)
            elapsed = time.time() - start
            print(f"    ✅ {variant_success}/100 variants created in {elapsed:.1f}s")

        # Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Journeys:    {self.results['journeys']['success']} created, {self.results['journeys']['fail']} failed")
        print(f"Customers:   {self.results['customers']['success']} created, {self.results['customers']['fail']} failed")
        print(f"Enrollments: {self.results['enrollments']['success']} created, {self.results['enrollments']['fail']} failed")
        if self.results["errors"]:
            print(f"\n⚠️  First 10 errors:")
            for err in self.results["errors"][:10]:
                print(f"   - {err}")

        # Save results to JSON
        if not self.dry_run:
            result_file = f"test_data_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, "w") as f:
                json.dump(self.results, f, indent=2)
            print(f"\n📁 Full results saved to: {result_file}")

        print(f"\n{'='*60}")
        print("Test data created. All test data uses:")
        print(f"  Email domain: @{TEST_EMAIL_DOMAIN}")
        print(f"  Journey prefix: '{JOURNEY_PREFIX}'")
        print("To clean up: run cleanup_test_data.py")
        print(f"{'='*60}\n")


async def main():
    parser = argparse.ArgumentParser(description="Pureleven CRM test data generator")
    parser.add_argument("--count", type=int, default=1000, help="Number of journeys/customers to create")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without doing it")
    parser.add_argument("--base", default=BASE, help="API base URL")
    args = parser.parse_args()

    gen = DataGenerator(base_url=args.base, count=args.count, dry_run=args.dry_run)
    await gen.run()


if __name__ == "__main__":
    asyncio.run(main())
