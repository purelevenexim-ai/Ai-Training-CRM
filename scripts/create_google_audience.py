"""
Create Google Ads Customer Match audience list for Pure Leven CRM.
Run: python3 scripts/create_google_audience.py
"""
import os
import json
import urllib.request
import urllib.parse

# Google Ads credentials. Keep real values in your private environment.
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("GOOGLE_ADS_OAUTH_REFRESH_TOKEN", "")
DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")

API_VERSION = "v21"


def get_access_token():
    url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def create_customer_match_list(access_token):
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}/userLists:mutate"
    
    payload = {
        "operations": [
            {
                "create": {
                    "name": "Pure Leven CRM Sync",
                    "description": "CRM customer segments synced from Pure Leven AI CRM - https://ai.pureleven.com",
                    "membershipLifeSpan": 540,  # max 540 days
                    "membershipStatus": "OPEN",
                    "crmBasedUserList": {
                        "uploadKeyType": "CONTACT_INFO",
                        "dataSourceType": "FIRST_PARTY",
                    }
                }
            }
        ]
    }
    
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("developer-token", DEVELOPER_TOKEN)
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {error_body}")


def list_existing(access_token):
    """List existing user lists to check if audience already exists."""
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}/googleAds:searchStream"
    payload = {
        "query": "SELECT user_list.id, user_list.name, user_list.membership_status FROM user_list WHERE user_list.type = 'CRM_BASED' ORDER BY user_list.name"
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("developer-token", DEVELOPER_TOKEN)
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"error": f"HTTP {e.code}: {error_body}"}


def main():
    print("\n🔑 Getting Google Ads access token...")
    try:
        token = get_access_token()
        print("   ✓ Token obtained")
    except Exception as e:
        print(f"   ✗ Failed to get token: {e}")
        return

    print("\n🔍 Checking for existing Customer Match lists...")
    existing = list_existing(token)
    if "error" not in existing:
        results = existing if isinstance(existing, list) else [existing]
        for batch in results:
            for row in batch.get("results", []):
                ul = row.get("userList", {})
                name = ul.get("name", "")
                uid = ul.get("id", "")
                if "Pure Leven" in name:
                    print(f"   ⚠️  Audience already exists: '{name}' (ID: {uid})")
                    print(f"   → Add to .env: GOOGLE_AUDIENCE_LIST_ID={uid}")
                    return
    
    print("\n🎯 Creating 'Pure Leven CRM Sync' Customer Match audience...")
    try:
        result = create_customer_match_list(token)
        print(f"   ✓ Audience created!")
        print(f"\n📋 Response:")
        print(json.dumps(result, indent=2))
        
        # Extract the resource name / list ID
        results = result.get("results", [])
        if results:
            resource_name = results[0].get("resourceName", "")
            list_id = resource_name.split("/")[-1] if resource_name else "unknown"
            print(f"\n✅ SUCCESS!")
            print(f"   Resource name: {resource_name}")
            print(f"   List ID: {list_id}")
            print(f"\n📝 Add to .env:")
            print(f"   GOOGLE_AUDIENCE_LIST_ID={list_id}")
        else:
            print(f"\n📋 Full result: {json.dumps(result, indent=2)}")
    except RuntimeError as e:
        print(f"   ✗ Failed: {e}")
        if "CUSTOMER_NOT_ENABLED_FOR_CUSTOMER_MATCH" in str(e):
            print("\n⏳ Customer Match not yet enabled — this will work once Google approves your API tier.")
            print("   The audience list will be created automatically when approval is received.")
        elif "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
            print("\n⏳ Developer token not approved for standard access yet.")
            print("   This will work once Google approves your API tier upgrade (May 21-22).")
        else:
            print("\n🔍 Check error details above.")


if __name__ == "__main__":
    main()
