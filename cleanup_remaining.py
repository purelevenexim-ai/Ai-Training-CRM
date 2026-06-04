#!/usr/bin/env python3
"""Cleanup all test journeys from pureleven CRM database"""
import subprocess

# Delete Load Test journeys and SQL injection test journeys
sql_statements = [
    "DELETE FROM crm_bulk_enrollment_jobs WHERE journey_id IN (SELECT id FROM crm_journeys WHERE name LIKE 'Load Test%')",
    "DELETE FROM crm_journey_variants WHERE journey_id IN (SELECT id FROM crm_journeys WHERE name LIKE 'Load Test%')",
    "DELETE FROM crm_journey_instances WHERE journey_id IN (SELECT id FROM crm_journeys WHERE name LIKE 'Load Test%')",
    "DELETE FROM crm_journey_attribution WHERE journey_id IN (SELECT id FROM crm_journeys WHERE name LIKE 'Load Test%')",
    "DELETE FROM crm_journeys WHERE name LIKE 'Load Test%'",
    # SQL injection test data
    "DELETE FROM crm_journeys WHERE name SIMILAR TO '%OR%=%|%DROP TABLE%|%SELECT%FROM%|admin--|--%'",
    # Empty name
    "DELETE FROM crm_journeys WHERE name = '' OR name IS NULL",
    # Any remaining ${} or {{}} template injection
    "DELETE FROM crm_journeys WHERE name LIKE '${%' OR name LIKE '{{%'",
]

for stmt in sql_statements:
    r = subprocess.run(
        ['docker', 'exec', 'pureleven-postgres', 'psql', '-U', 'pureleven', '-d', 'pureleven', '-c', stmt],
        capture_output=True, text=True
    )
    print(f"[{stmt[:60]}] -> {r.stdout.strip()} {r.stderr.strip()[:50]}")

# Count remaining
r = subprocess.run(
    ['docker', 'exec', 'pureleven-postgres', 'psql', '-U', 'pureleven', '-d', 'pureleven', '-c',
     "SELECT COUNT(*) as journeys FROM crm_journeys; SELECT COUNT(*) as customers FROM crm_customers;"],
    capture_output=True, text=True
)
print("\nFinal counts:")
print(r.stdout)
