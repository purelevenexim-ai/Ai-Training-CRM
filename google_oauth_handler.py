#!/usr/bin/env python3
"""
Google Ads OAuth handler - generates authorization URL and handles callback
"""
import os
import requests
from urllib.parse import urlencode

# Configuration
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "<GOOGLE_ADS_CLIENT_ID>")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
REDIRECT_URI = "https://track.pureleven.com/api/crm/auth/google-ads/callback"
SCOPES = [
    "https://www.googleapis.com/auth/adwords",  # Google Ads API
]
OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"


def get_authorization_url():
    """Generate the URL user needs to visit to authorize the app"""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "response_type": "code",
        "access_type": "offline",  # Required to get refresh token
        "prompt": "consent",  # Force consent screen to get refresh token
    }
    auth_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    return auth_url


def exchange_code_for_token(auth_code):
    """Exchange authorization code for access and refresh tokens"""
    token_data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    response = requests.post(OAUTH_TOKEN_URL, data=token_data)
    response.raise_for_status()
    
    token_response = response.json()
    return token_response


def update_env_with_refresh_token(refresh_token):
    """Update .env file with refresh token"""
    env_file = "/opt/pureleven/ai-engine/.env"
    
    # Read current .env
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    # Find or add GOOGLE_ADS_OAUTH_REFRESH_TOKEN line
    found = False
    for i, line in enumerate(lines):
        if line.startswith("GOOGLE_ADS_OAUTH_REFRESH_TOKEN="):
            lines[i] = f"GOOGLE_ADS_OAUTH_REFRESH_TOKEN={refresh_token}\n"
            found = True
            break
    
    if not found:
        lines.append(f"GOOGLE_ADS_OAUTH_REFRESH_TOKEN={refresh_token}\n")
    
    # Write back
    with open(env_file, "w") as f:
        f.writelines(lines)
    
    print(f"✅ Updated .env with refresh token")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "url":
        # Print authorization URL
        auth_url = get_authorization_url()
        print("🔗 Visit this URL to authorize:")
        print(auth_url)
        print("\nAfter authorization, you'll be redirected. Copy the 'code' parameter from the URL.")
        
    elif len(sys.argv) > 2 and sys.argv[1] == "exchange":
        # Exchange code for tokens
        auth_code = sys.argv[2]
        print(f"🔄 Exchanging code for tokens...")
        try:
            tokens = exchange_code_for_token(auth_code)
            print(f"✅ Success!")
            print(f"   Access Token: {tokens.get('access_token', 'N/A')[:50]}...")
            print(f"   Refresh Token: {tokens.get('refresh_token', 'N/A')}")
            print(f"   Expires In: {tokens.get('expires_in')} seconds")
            
            if 'refresh_token' in tokens:
                print(f"\n💾 Saving refresh token to .env...")
                update_env_with_refresh_token(tokens['refresh_token'])
            else:
                print("\n⚠️  No refresh token in response. Make sure you're using access_type=offline")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("Usage:")
        print("  python google_oauth_handler.py url                    # Get authorization URL")
        print("  python google_oauth_handler.py exchange <AUTH_CODE>   # Exchange code for tokens")
