#!/usr/bin/env python3
"""
Create Google Ads Customer Match audience using the official google-ads library.
Run: python3 scripts/create_google_audience_v2.py
"""
import sys
import os

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
except ImportError:
    print("Install: pip3 install google-ads")
    sys.exit(1)

# Credentials. Keep real values in your private environment.
CONFIG = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", ""),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", ""),
    "refresh_token": os.getenv("GOOGLE_ADS_OAUTH_REFRESH_TOKEN", ""),
    "use_proto_plus": True,
}

CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")


def list_accessible_customers(client):
    """List all accessible Google Ads customer accounts."""
    service = client.get_service("CustomerService")
    accessible = service.list_accessible_customers()
    return accessible.resource_names


def check_existing_lists(client, customer_id):
    """Check for existing Customer Match lists."""
    service = client.get_service("GoogleAdsService")
    query = """
        SELECT user_list.id, user_list.name, user_list.membership_status,
               user_list.size_for_display
        FROM user_list
        WHERE user_list.type = 'CRM_BASED'
        ORDER BY user_list.name
    """
    try:
        response = service.search(customer_id=customer_id, query=query)
        lists = []
        for row in response:
            ul = row.user_list
            lists.append({
                "id": ul.id,
                "name": ul.name,
                "status": ul.membership_status.name,
            })
        return lists
    except GoogleAdsException as e:
        print(f"  Query error: {e.error.code().name}")
        for error in e.failure.errors:
            print(f"    {error.error_code}: {error.message}")
        return None


def create_customer_match_list(client, customer_id):
    """Create a Customer Match user list."""
    service = client.get_service("UserListService")

    user_list_operation = client.get_type("UserListOperation")
    user_list = user_list_operation.create

    user_list.name = "Pure Leven CRM Sync"
    user_list.description = "CRM customer segments from Pure Leven AI CRM"
    user_list.membership_status = client.enums.UserListMembershipStatusEnum.OPEN
    user_list.membership_life_span = 540  # max 540 days

    # Configure as CRM-based list
    user_list.crm_based_user_list.upload_key_type = (
        client.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO
    )
    user_list.crm_based_user_list.data_source_type = (
        client.enums.UserListCrmDataSourceTypeEnum.FIRST_PARTY
    )

    try:
        response = service.mutate_user_lists(
            customer_id=customer_id,
            operations=[user_list_operation],
        )
        resource_name = response.results[0].resource_name
        list_id = resource_name.split("/")[-1]
        return resource_name, list_id
    except GoogleAdsException as e:
        print(f"\n  Google Ads API Error: {e.error.code().name}")
        for error in e.failure.errors:
            error_code = error.error_code
            print(f"    Code: {error_code}")
            print(f"    Message: {error.message}")
        raise


def main():
    print("\n🔑 Initializing Google Ads client...")
    try:
        client = GoogleAdsClient.load_from_dict(CONFIG, version="v21")
        print("   ✓ Client initialized")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return

    print("\n👥 Listing accessible customers...")
    try:
        accounts = list_accessible_customers(client)
        print(f"   Found {len(accounts)} accessible accounts:")
        for acc in accounts:
            print(f"   - {acc}")
    except GoogleAdsException as e:
        print(f"   Error: {e.error.code().name}")
        for error in e.failure.errors:
            print(f"   {error.message}")
        # Try with login-customer-id
        print("   Retrying with login-customer-id...")
        try:
            client2 = GoogleAdsClient.load_from_dict(
                {**CONFIG, "login_customer_id": CUSTOMER_ID}, version="v21"
            )
            accounts = list_accessible_customers(client2)
            print(f"   Found {len(accounts)} accessible accounts (with login-customer-id):")
            for acc in accounts:
                print(f"   - {acc}")
            client = client2
        except Exception as e2:
            print(f"   Also failed: {e2}")

    print(f"\n🔍 Checking existing Customer Match lists for customer {CUSTOMER_ID}...")
    existing = check_existing_lists(client, CUSTOMER_ID)
    if existing is None:
        print("   Could not query — will try to create anyway")
    elif existing:
        for ul in existing:
            print(f"   ⚠️  Existing: '{ul['name']}' (ID: {ul['id']}, status: {ul['status']})")
            if "Pure Leven" in ul["name"]:
                print(f"\n✅ Audience already exists!")
                print(f"   GOOGLE_AUDIENCE_LIST_ID={ul['id']}")
                return
    else:
        print("   No existing Customer Match lists found")

    print("\n🎯 Creating 'Pure Leven CRM Sync' Customer Match audience...")
    try:
        resource_name, list_id = create_customer_match_list(client, CUSTOMER_ID)
        print(f"\n✅ SUCCESS!")
        print(f"   Resource name: {resource_name}")
        print(f"   List ID: {list_id}")
        print(f"\n📝 Update VPS .env:")
        print(f"   GOOGLE_AUDIENCE_LIST_ID={list_id}")
        print(f"\nRun to update VPS:")
        print(f"   ssh root@192.46.213.140 \"sed -i 's/GOOGLE_AUDIENCE_LIST_ID=.*/GOOGLE_AUDIENCE_LIST_ID={list_id}/' /opt/pureleven/ai-engine/.env && docker restart pureleven-ai-engine\"")
    except GoogleAdsException:
        print("\n   Try the alternative test account approach if developer token isn't approved yet")
    except Exception as e:
        print(f"\n   ✗ Unexpected error: {e}")


if __name__ == "__main__":
    main()
