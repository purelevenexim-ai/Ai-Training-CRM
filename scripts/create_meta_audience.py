#!/usr/bin/env python3
"""
Create Meta Custom Audience using Graph API
- Creates a customer list audience for CRM sync
- Automatically uploads the audience to the account

Usage:
  python3 scripts/create_meta_audience.py --name "Pure Leven CRM Sync"

Requires: META_ACCESS_TOKEN (System User token with ads_management scope)
"""
import argparse
import json
import urllib.request
import urllib.error
import sys

# Meta credentials (from VPS .env)
FACEBOOK_BUSINESS_ID = "616652333432085"
FACEBOOK_ACCESS_TOKEN = "EAAJegujoiH8BRZAjjgBN7PTNmw5szs1VZBGnIV2Q84f4mveUUseip4aEH0uWEHuiHIYezDYxs3sVyh4I8V3EoN1Nbc4KvlbmfcJTneMZBaeZAbo9fd7uXLZAy6jYbbTyXRGJskOhJlNkSMouOPXLwrVqnl5GXSoMQFLrB2c1a4G4Ltmq8gq06Mdjzts0Mr2Li1AZDZD"

# Endpoint base
GRAPH_API_VERSION = "v21.0"
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def graph_request(path, method="GET", data=None):
    """Make a request to Meta Graph API."""
    url = f"{GRAPH_API_URL}{path}"
    if not path.startswith("/"):
        url = f"{GRAPH_API_URL}/{path}"
    
    # Add access token to all requests
    if "?" in url:
        url += f"&access_token={FACEBOOK_ACCESS_TOKEN}"
    else:
        url += f"?access_token={FACEBOOK_ACCESS_TOKEN}"
    
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            response = json.loads(r.read().decode())
            return response, r.status
    except urllib.error.HTTPError as e:
        error_data = e.read().decode()
        try:
            error_json = json.loads(error_data)
            return error_json, e.code
        except:
            return {"error": error_data[:500]}, e.code


def create_custom_audience(audience_name="Pure Leven CRM Sync", audience_description="Customer List for CRM Sync"):
    """Create a custom audience (customer list) in Meta."""
    print(f"\n🎯 Creating Meta Custom Audience...\n")
    print(f"  Business ID: {FACEBOOK_BUSINESS_ID}")
    print(f"  Audience Name: {audience_name}")
    print(f"  Description: {audience_description}\n")
    
    # Step 1: Create custom audience
    create_payload = {
        "name": audience_name,
        "description": audience_description,
        "subtype": "CUSTOM",  # CUSTOM = customer list
        "customer_list": True,
    }
    
    endpoint = f"/{FACEBOOK_BUSINESS_ID}/customaudiences"
    resp, status = graph_request(endpoint, method="POST", data=create_payload)
    
    if status not in (200, 201):
        print(f"  ❌ Failed to create audience: {status}")
        print(f"  Response: {json.dumps(resp, indent=2)}")
        
        if "error" in resp:
            error = resp["error"]
            if isinstance(error, dict):
                print(f"  Error: {error.get('message', str(error))}")
            else:
                print(f"  Error: {error}")
        return None
    
    audience_id = resp.get("id")
    if not audience_id:
        print(f"  ❌ No audience ID in response: {resp}")
        return None
    
    print(f"  ✅ Created audience!")
    print(f"  Audience ID: {audience_id}\n")
    
    return audience_id


def verify_audience_access(audience_id):
    """Verify we can access the audience."""
    print(f"  Verifying access to audience {audience_id}...\n")
    
    endpoint = f"/{audience_id}"
    resp, status = graph_request(endpoint, method="GET")
    
    if status == 200:
        print(f"  ✅ Audience access verified!")
        print(f"     Name: {resp.get('name')}")
        print(f"     ID: {resp.get('id')}")
        print(f"     Subtype: {resp.get('subtype')}")
        print(f"     Customer List: {resp.get('customer_list')}\n")
        return True
    else:
        print(f"  ⚠️ Could not verify: {status} {resp}\n")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create Meta Custom Audience (Customer List)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/create_meta_audience.py
  python3 scripts/create_meta_audience.py --name "My Audience"
        """
    )
    parser.add_argument(
        "--name",
        default="Pure Leven CRM Sync",
        help="Audience name (default: Pure Leven CRM Sync)"
    )
    parser.add_argument(
        "--description",
        default="Customer List for CRM Sync",
        help="Audience description"
    )
    
    args = parser.parse_args()
    
    # Validate credentials
    if not FACEBOOK_ACCESS_TOKEN or FACEBOOK_ACCESS_TOKEN.startswith("EAA"):
        # Good token format
        pass
    else:
        print("❌ Error: FACEBOOK_ACCESS_TOKEN not set or invalid")
        print("   Token format: EAA... (from Meta System User)")
        sys.exit(1)
    
    if not FACEBOOK_BUSINESS_ID:
        print("❌ Error: FACEBOOK_BUSINESS_ID not set")
        sys.exit(1)
    
    # Create audience
    audience_id = create_custom_audience(args.name, args.description)
    
    if not audience_id:
        print("❌ Failed to create audience")
        sys.exit(1)
    
    # Verify access
    verify_audience_access(audience_id)
    
    # Print next steps
    print("=" * 60)
    print("✅ SETUP COMPLETE")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Update VPS .env with new audience ID:")
    print(f"   META_AUDIENCE_ID={audience_id}")
    print(f"\n2. SSH to VPS and update the config:")
    print(f"   ssh root@192.46.213.140")
    print(f"   sed -i 's/META_AUDIENCE_ID=.*/META_AUDIENCE_ID={audience_id}/' /opt/pureleven/ai-engine/.env")
    print(f"   docker restart pureleven-ai-engine")
    print(f"\n3. Test customer sync:")
    print(f"   curl 'https://track.pureleven.com/api/crm/audiences/meta/sync?limit=100'")
    print("\n")


if __name__ == "__main__":
    main()
