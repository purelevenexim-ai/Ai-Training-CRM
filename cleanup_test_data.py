#!/usr/bin/env python3
"""
Pure Leven CRM — Archive & Cleanup Script
Moves all test data to archive tables and removes from production tables.
Usage:
    python cleanup_test_data.py --dry-run     # Preview what will be archived
    python cleanup_test_data.py --archive-only # Archive only, don't delete
    python cleanup_test_data.py               # Archive + delete
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime

import asyncpg

DB_URL = "postgresql://postgres:postgres@127.0.0.1:5432/pureleven_crm"
TEST_EMAIL_DOMAIN = "@test.pureleven.com"
JOURNEY_PREFIX = "Scale Test Journey"

ARCHIVE_TABLES = [
    "crm_journeys",
    "crm_customers",
    "crm_journey_instances",
    "crm_journey_variants",
    "crm_journey_attribution",
    "crm_journey_steps",
    "crm_bulk_enrollment_jobs",
]

CREATE_ARCHIVE_TABLES_SQL = """
DO $$
BEGIN
    -- crm_journeys_archive
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_journeys_archive') THEN
        CREATE TABLE crm_journeys_archive AS SELECT *, NOW() AS archived_at FROM crm_journeys WHERE 1=0;
        ALTER TABLE crm_journeys_archive ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Created crm_journeys_archive';
    END IF;

    -- crm_customers_archive
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_customers_archive') THEN
        CREATE TABLE crm_customers_archive AS SELECT *, NOW() AS archived_at FROM crm_customers WHERE 1=0;
        ALTER TABLE crm_customers_archive ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Created crm_customers_archive';
    END IF;

    -- crm_journey_instances_archive
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_journey_instances_archive') THEN
        CREATE TABLE crm_journey_instances_archive AS SELECT *, NOW() AS archived_at FROM crm_journey_instances WHERE 1=0;
        ALTER TABLE crm_journey_instances_archive ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Created crm_journey_instances_archive';
    END IF;

    -- crm_journey_variants_archive
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_journey_variants_archive') THEN
        CREATE TABLE crm_journey_variants_archive AS SELECT *, NOW() AS archived_at FROM crm_journey_variants WHERE 1=0;
        ALTER TABLE crm_journey_variants_archive ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Created crm_journey_variants_archive';
    END IF;

    -- crm_journey_attribution_archive
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_journey_attribution_archive') THEN
        CREATE TABLE crm_journey_attribution_archive AS SELECT *, NOW() AS archived_at FROM crm_journey_attribution WHERE 1=0;
        ALTER TABLE crm_journey_attribution_archive ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Created crm_journey_attribution_archive';
    END IF;

    -- crm_bulk_enrollment_jobs_archive
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crm_bulk_enrollment_jobs_archive') THEN
        CREATE TABLE crm_bulk_enrollment_jobs_archive AS SELECT *, NOW() AS archived_at FROM crm_bulk_enrollment_jobs WHERE 1=0;
        ALTER TABLE crm_bulk_enrollment_jobs_archive ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ DEFAULT NOW();
        RAISE NOTICE 'Created crm_bulk_enrollment_jobs_archive';
    END IF;
END $$;
"""


async def get_counts(conn: asyncpg.Connection) -> dict:
    """Get current counts of test vs production data."""
    counts = {}
    for table in ARCHIVE_TABLES:
        try:
            if table == "crm_journeys":
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table} WHERE name LIKE $1",
                    f"{JOURNEY_PREFIX}%",
                )
            elif table == "crm_customers":
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table} WHERE email LIKE $1",
                    f"%{TEST_EMAIL_DOMAIN}%",
                )
            elif table == "crm_journey_instances":
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = await conn.fetchval(
                    f"""SELECT COUNT(*) FROM {table} ji
                        JOIN crm_journeys j ON ji.journey_id = j.id
                        WHERE j.name LIKE $1""",
                    f"{JOURNEY_PREFIX}%",
                )
            elif table == "crm_journey_variants":
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = await conn.fetchval(
                    f"""SELECT COUNT(*) FROM {table} jv
                        JOIN crm_journeys j ON jv.journey_id = j.id
                        WHERE j.name LIKE $1""",
                    f"{JOURNEY_PREFIX}%",
                )
            elif table == "crm_journey_attribution":
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = await conn.fetchval(
                    f"""SELECT COUNT(*) FROM {table} ja
                        JOIN crm_journeys j ON ja.journey_id = j.id
                        WHERE j.name LIKE $1""",
                    f"{JOURNEY_PREFIX}%",
                )
            elif table == "crm_bulk_enrollment_jobs":
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table} WHERE metadata::text LIKE $1",
                    "%test_generator%",
                )
            else:
                total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                test = 0
            counts[table] = {"total": total, "test": test, "production": total - test}
        except Exception as e:
            counts[table] = {"error": str(e)}
    return counts


async def archive_test_data(conn: asyncpg.Connection, dry_run: bool = False) -> dict:
    """Archive all test data to *_archive tables."""
    results = {}

    operations = [
        # (source_table, archive_table, where_clause, description)
        (
            "crm_journeys",
            "crm_journeys_archive",
            f"name LIKE '{JOURNEY_PREFIX}%'",
            "journeys named 'Scale Test Journey *'",
        ),
        (
            "crm_customers",
            "crm_customers_archive",
            f"email LIKE '%{TEST_EMAIL_DOMAIN}%'",
            f"customers with email @{TEST_EMAIL_DOMAIN}",
        ),
        (
            "crm_journey_instances",
            "crm_journey_instances_archive",
            f"""journey_id IN (
                SELECT id FROM crm_journeys WHERE name LIKE '{JOURNEY_PREFIX}%'
            )""",
            "instances for test journeys",
        ),
        (
            "crm_journey_variants",
            "crm_journey_variants_archive",
            f"""journey_id IN (
                SELECT id FROM crm_journeys WHERE name LIKE '{JOURNEY_PREFIX}%'
            )""",
            "variants for test journeys",
        ),
        (
            "crm_journey_attribution",
            "crm_journey_attribution_archive",
            f"""journey_id IN (
                SELECT id FROM crm_journeys WHERE name LIKE '{JOURNEY_PREFIX}%'
            )""",
            "attributions for test journeys",
        ),
    ]

    for src, dst, where, description in operations:
        if dry_run:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {src} WHERE {where}")
            print(f"  [DRY] Would archive {count} rows from {src} ({description})")
            results[src] = {"archived": count, "dry_run": True}
        else:
            # Get columns from source (excluding archived_at if it exists)
            cols_raw = await conn.fetch(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_name = $1 AND column_name != 'archived_at'
                   ORDER BY ordinal_position""",
                src,
            )
            cols = ", ".join(r["column_name"] for r in cols_raw)

            count = await conn.fetchval(f"SELECT COUNT(*) FROM {src} WHERE {where}")
            if count > 0:
                await conn.execute(
                    f"""INSERT INTO {dst} ({cols}, archived_at)
                        SELECT {cols}, NOW() FROM {src} WHERE {where}
                        ON CONFLICT DO NOTHING"""
                )
                print(f"  ✅ Archived {count} rows to {dst}")
            else:
                print(f"  ℹ️  No test data in {src}")
            results[src] = {"archived": count}

    return results


async def delete_test_data(conn: asyncpg.Connection, dry_run: bool = False) -> dict:
    """Delete all test data from production tables (archive first!)."""
    results = {}

    deletions = [
        # Order matters: delete dependent tables first
        (
            "crm_journey_attribution",
            f"""journey_id IN (
                SELECT id FROM crm_journeys WHERE name LIKE '{JOURNEY_PREFIX}%'
            )""",
        ),
        (
            "crm_journey_instances",
            f"""journey_id IN (
                SELECT id FROM crm_journeys WHERE name LIKE '{JOURNEY_PREFIX}%'
            )""",
        ),
        (
            "crm_journey_variants",
            f"""journey_id IN (
                SELECT id FROM crm_journeys WHERE name LIKE '{JOURNEY_PREFIX}%'
            )""",
        ),
        (
            "crm_journeys",
            f"name LIKE '{JOURNEY_PREFIX}%'",
        ),
        (
            "crm_customers",
            f"email LIKE '%{TEST_EMAIL_DOMAIN}%'",
        ),
    ]

    for table, where in deletions:
        if dry_run:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table} WHERE {where}")
            print(f"  [DRY] Would delete {count} rows from {table}")
            results[table] = {"deleted": count, "dry_run": True}
        else:
            result = await conn.execute(f"DELETE FROM {table} WHERE {where}")
            count = int(result.split(" ")[-1])
            print(f"  🗑️  Deleted {count} rows from {table}")
            results[table] = {"deleted": count}

    return results


async def main():
    parser = argparse.ArgumentParser(description="Archive and clean up CRM test data")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--archive-only", action="store_true", help="Archive but don't delete")
    parser.add_argument("--db-url", default=DB_URL, help="PostgreSQL connection URL")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Pure Leven CRM — Test Data Cleanup")
    print(f"Mode: {'DRY RUN' if args.dry_run else ('ARCHIVE ONLY' if args.archive_only else 'ARCHIVE + DELETE')}")
    print(f"{'='*60}\n")

    try:
        conn = await asyncpg.connect(args.db_url)
    except Exception as e:
        print(f"❌ Cannot connect to database: {e}")
        print(f"   URL: {args.db_url}")
        sys.exit(1)

    try:
        # 1. Show current state
        print("[1/4] Current data counts:")
        counts = await get_counts(conn)
        total_test = 0
        for table, data in counts.items():
            if "error" in data:
                print(f"  ⚠️  {table}: ERROR — {data['error']}")
            else:
                print(f"  {table}: {data['production']} prod + {data['test']} test = {data['total']} total")
                total_test += data["test"]

        print(f"\n  Total test rows to process: {total_test}")

        if total_test == 0:
            print("\n✅ No test data found. Nothing to clean up.")
            return

        # 2. Create archive tables
        if not args.dry_run:
            print("\n[2/4] Creating archive tables (if not exist)...")
            await conn.execute(CREATE_ARCHIVE_TABLES_SQL)
            print("  ✅ Archive tables ready")
        else:
            print("\n[2/4] [DRY] Would create archive tables")

        # 3. Archive test data
        print("\n[3/4] Archiving test data...")
        archive_results = await archive_test_data(conn, dry_run=args.dry_run)

        # 4. Delete test data (unless archive-only)
        if not args.archive_only:
            print("\n[4/4] Deleting test data from production tables...")
            delete_results = await delete_test_data(conn, dry_run=args.dry_run)
        else:
            print("\n[4/4] Skipped deletion (--archive-only mode)")
            delete_results = {}

        # 5. Final counts
        if not args.dry_run:
            print("\nFinal data counts (after cleanup):")
            final_counts = await get_counts(conn)
            for table, data in final_counts.items():
                if "error" not in data:
                    print(f"  {table}: {data['production']} prod, {data['test']} test remaining")

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "dry_run" if args.dry_run else ("archive_only" if args.archive_only else "archive_and_delete"),
            "before_counts": counts,
            "archive_results": archive_results,
            "delete_results": delete_results,
        }
        report_file = f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Cleanup report saved to: {report_file}")

        print(f"\n{'='*60}")
        print("Cleanup complete!")
        print(f"{'='*60}\n")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
