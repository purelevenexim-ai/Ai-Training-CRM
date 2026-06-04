#!/usr/bin/env python3
"""
Deploy a Shopify OAuth handler on the VPS to get a valid admin token.
This endpoint will be added to the CRM FastAPI app temporarily.
"""
import json
import os
import sys

oauth_code_to_add = '''
# Add this to /opt/pureleven/ai-engine/app/crm_routes.py
# Before the @app.get("/health") endpoint

@router.get("/shopify/oauth/callback")
async def shopify_oauth_callback(code: str, shop: str, state: str, hmac: str):
    """
    Shopify OAuth callback handler.
    After user authorizes, Shopify redirects here with an authorization code.
    We exchange it for an access token and save to .env
    """
    import hashlib
    import hmac as hmac_lib
    import urllib.parse
    import urllib.request
    import urllib.error
    
    # Verify HMAC (security)
    params = {"code": code, "shop": shop, "state": state}
    query_string = urllib.parse.urlencode(sorted(params.items()))
    computed_hmac = hmac_lib.new(
        SHOPIFY_CLIENT_SECRET.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if computed_hmac != hmac:
        return {"error": "Invalid HMAC"}, 401
    
    # Exchange code for access token
    try:
        store_url = f"https://{shop}"
        token_url = f"{store_url}/admin/oauth/access_token"
        data = urllib.parse.urlencode({
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "code": code
        }).encode()
        
        req = urllib.request.Request(token_url, data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            access_token = result.get("access_token")
            
            if access_token:
                # Save to .env file
                env_file = "/opt/pureleven/ai-engine/.env"
                with open(env_file, 'r') as f:
                    env_content = f.read()
                
                # Replace or add SHOPIFY_ADMIN_TOKEN
                if "SHOPIFY_ADMIN_TOKEN=" in env_content:
                    env_content = os.environ.get(
                        "SHOPIFY_ADMIN_TOKEN=",
                        f"SHOPIFY_ADMIN_TOKEN={access_token}"
                    )
                    env_content = env_content.replace(
                        f"SHOPIFY_ADMIN_TOKEN={os.environ.get('SHOPIFY_ADMIN_TOKEN', '')}",
                        f"SHOPIFY_ADMIN_TOKEN={access_token}"
                    ) if "SHOPIFY_ADMIN_TOKEN=" in env_content else env_content + f"\\nSHOPIFY_ADMIN_TOKEN={access_token}"
                else:
                    env_content += f"\\nSHOPIFY_ADMIN_TOKEN={access_token}"
                
                with open(env_file, 'w') as f:
                    f.write(env_content)
                
                # Return success page
                return {
                    "success": True,
                    "access_token": access_token,
                    "message": "Token saved! Restart the API service for changes to take effect."
                }
    
    except Exception as e:
        return {"error": str(e)}, 500


@router.get("/shopify/oauth/init")
async def shopify_oauth_init():
    """
    Initiate Shopify OAuth flow.
    User should visit this endpoint in browser.
    """
    from urllib.parse import urlencode
    import secrets
    
    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Build authorization URL
    auth_url = f"https://rwxtic-gz.myshopify.com/admin/oauth/authorize?" + urlencode({
        "client_id": SHOPIFY_CLIENT_ID,
        "scope": "read_orders,read_customers,write_webhooks,read_checkouts,read_carts",
        "redirect_uri": "https://track.pureleven.com/api/shopify/oauth/callback",
        "state": state
    })
    
    # Return HTML that redirects to authorization URL
    return {
        "status": "redirect",
        "auth_url": auth_url,
        "message": "Visiting authorization URL..."
    }
'''

print("""
╔═══════════════════════════════════════════════════════════════════════╗
║  SHOPIFY OAUTH VIA VPS                                                ║
╚═══════════════════════════════════════════════════════════════════════╝

The fastest solution is to add OAuth endpoints directly to the VPS API.

STEPS:

1. SSH to VPS and backup the file:
   ssh root@192.46.213.140
   cp /opt/pureleven/ai-engine/app/crm_routes.py{,.backup}

2. Open the file in an editor:
   nano /opt/pureleven/ai-engine/app/crm_routes.py

3. Find this line (around line 1250):
   @router.post("/events/micro")

4. Add these OAuth endpoints BEFORE that line:
   (See the code below)

5. Restart the API:
   docker restart pureleven-ai-engine

6. Then visit in browser:
   https://track.pureleven.com/api/shopify/oauth/init

7. Click "Authorize with Shopify", approve the app

8. The token will be saved automatically!

═══════════════════════════════════════════════════════════════════════

Here's the code to add:
""")

print(oauth_code_to_add)
