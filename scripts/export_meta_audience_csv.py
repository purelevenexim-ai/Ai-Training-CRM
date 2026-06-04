#!/usr/bin/env python3
"""
Export Shopify customers as Meta-compatible Customer List CSV
- Fetches all customers from Shopify Admin API
- Formats as Meta audience CSV (email, phone, fn, ln, value)
- Saves to meta_audience_customers.csv for upload to Meta Ads Manager

Usage:
  python3 scripts/export_meta_audience_csv.py --token <SHOPIFY_ADMIN_TOKEN>
"""
import argparse
import csv
import json
import urllib.request
import urllib.error
import urllib.parse
import sys
import os

STORE = "rwxtic-gz.myshopify.com"
API_VERSION = "2024-10"
OUTPUT_FILE = "meta_audience_customers.csv"


def shopify_request(token, path):
    url = f"https://{STORE}/admin/api/{API_VERSION}/{path}"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()), r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:500]}, e.code, {}


def format_phone(phone):
    """Ensure phone has country code (assume India +91 if no country code)."""
    if not phone:
        return ""
    phone = phone.strip()
    # Remove spaces/dashes/parens for basic check
    digits_only = "".join(c for c in phone if c.isdigit())
    if phone.startswith("+"):
        return phone  # Already has country code
    if phone.startswith("00"):
        return "+" + phone[2:]  # 00-prefixed international
    if len(digits_only) == 10:
        return "+91" + digits_only  # Indian mobile without country code
    return phone


def fetch_all_customers(token):
    """Fetch all customers with pagination."""
    customers = []
    path = "customers.json?limit=250&fields=id,email,phone,first_name,last_name,orders_count,total_spent,created_at"
    page = 0

    while path:
        page += 1
        print(f"  Fetching page {page}...", end="", flush=True)
        result, status, headers = shopify_request(token, path)

        if status != 200:
            print(f"\n  ❌ Error {status}: {result}")
            break

        batch = result.get("customers", [])
        customers.extend(batch)
        print(f" {len(batch)} customers (total: {len(customers)})")

        # Handle cursor-based pagination via Link header
        link_header = headers.get("Link", "") or headers.get("link", "")
        next_path = None
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    # Extract URL from <url>; rel="next"
                    start = part.find("<") + 1
                    end = part.find(">")
                    next_url = part[start:end].strip()
                    # Convert absolute URL to path+query
                    parsed = urllib.parse.urlparse(next_url)
                    next_path = parsed.path.lstrip("/").replace(
                        f"admin/api/{API_VERSION}/", ""
                    ) + ("?" + parsed.query if parsed.query else "")
                    break

        path = next_path
        if not batch:
            break

    return customers


def export_csv(customers, output_file):
    """Export customers as Meta-compatible CSV."""
    # Meta CSV columns: email, phone, fn, ln, value
    written = 0
    skipped = 0

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header row - Meta required format
        writer.writerow(["email", "phone", "fn", "ln", "value"])

        for c in customers:
            email = (c.get("email") or "").strip().lower()
            phone = format_phone(c.get("phone") or "")
            fn = (c.get("first_name") or "").strip()
            ln = (c.get("last_name") or "").strip()

            # Customer value = total amount spent (numeric only)
            try:
                value = float(c.get("total_spent") or 0)
            except (ValueError, TypeError):
                value = 0.0

            # Skip if no email AND no phone (Meta needs at least one identifier)
            if not email and not phone:
                skipped += 1
                continue

            writer.writerow([email, phone, fn, ln, round(value, 2)])
            written += 1

    return written, skipped


def convert_shopify_csv(shopify_csv_path, output_file):
    """Convert a Shopify Admin UI customer export CSV to Meta audience format.
    
    Shopify export columns include: First Name, Last Name, Email, Phone, Total Spent, etc.
    """
    written = 0
    skipped = 0

    with open(shopify_csv_path, newline="", encoding="utf-8-sig") as infile, \
         open(output_file, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        writer = csv.writer(outfile)
        writer.writerow(["email", "phone", "fn", "ln", "value"])

        for row in reader:
            # Shopify export uses these column names
            email = (row.get("Email") or row.get("email") or "").strip().lower()
            phone = format_phone(row.get("Phone") or row.get("phone") or "")
            fn = (row.get("First Name") or row.get("first_name") or "").strip()
            ln = (row.get("Last Name") or row.get("last_name") or "").strip()
            try:
                value = float(row.get("Total Spent") or row.get("total_spent") or 0)
            except (ValueError, TypeError):
                value = 0.0

            if not email and not phone:
                skipped += 1
                continue

            writer.writerow([email, phone, fn, ln, round(value, 2)])
            written += 1

    return written, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Export Shopify customers as Meta audience CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a Shopify Admin-exported CSV (from email) to Meta format:
  python3 scripts/export_meta_audience_csv.py --shopify-csv customers_export.csv

  # Fetch via API (Basic plan stores return no PII — use --shopify-csv instead):
  python3 scripts/export_meta_audience_csv.py --token <SHOPIFY_ADMIN_TOKEN>
        """
    )
    parser.add_argument("--token", help="Shopify Admin API token (shpat_...)")
    parser.add_argument("--shopify-csv", help="Path to Shopify Admin UI customer export CSV (emailed by Shopify)")
    parser.add_argument("--output", default=OUTPUT_FILE, help=f"Output CSV path (default: {OUTPUT_FILE})")
    args = parser.parse_args()

    if args.shopify_csv:
        # Mode: convert Shopify Admin UI export CSV
        if not os.path.exists(args.shopify_csv):
            print(f"❌ File not found: {args.shopify_csv}")
            sys.exit(1)
        print(f"\n📋 Converting Shopify CSV: {args.shopify_csv}")
        print(f"📄 Exporting to {args.output}...\n")
        written, skipped = convert_shopify_csv(args.shopify_csv, args.output)
    elif args.token:
        # Mode: fetch via API
        if not args.token.startswith("shpat_") and not args.token.startswith("shpca_"):
            print("⚠️  Warning: Token doesn't look like a Shopify admin token (expected shpat_...)")

        print(f"\n📋 Fetching customers from {STORE}...\n")
        customers = fetch_all_customers(args.token)

        if not customers:
            print("\n❌ No customers found. Check your token and store URL.")
            sys.exit(1)

        print(f"\n✅ Fetched {len(customers)} total customers")
        print(f"\n📄 Exporting to {args.output}...\n")
        written, skipped = export_csv(customers, args.output)
    else:
        print("❌ Provide either --token (API) or --shopify-csv (Shopify Admin export).")
        print("\nNote: Basic Shopify plan stores return null PII via API.")
        print("To get customer emails/phones, use --shopify-csv with the CSV emailed by Shopify.")
        sys.exit(1)

    output_path = os.path.abspath(args.output)
    print(f"✅ Exported {written} customers ({skipped} skipped — no email or phone)")
    print(f"\n📁 File saved to:")
    print(f"   {output_path}")
    print(f"\n{'='*60}")
    print(f"NEXT STEPS:")
    print(f"{'='*60}")
    print(f"1. Go to Meta Ads Manager Audiences page")
    print(f"2. Create Audience → Customer List → choose file")
    print(f"3. Select: {output_path}")
    print(f"4. Click 'Next' → Map identifiers → Upload → Confirm")
    print(f"5. Copy the Audience ID → update META_AUDIENCE_ID in VPS .env")
    print()


if __name__ == "__main__":
    main()
