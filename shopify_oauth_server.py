#!/usr/bin/env python3
"""
Simple OAuth 2.0 server to get a valid Shopify Admin API access token.
Run this, visit the auth URL in browser, approve the app, and get your shpat_ token.
"""
import os
import sys
import json
import hashlib
import hmac
import secrets
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

# Shopify config (from private environment)
STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")
SCOPES = ["read_orders", "read_customers", "write_webhooks"]
REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI", "http://localhost:8765/callback")

# Temp storage for state
oauth_state = {}

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        if path == "/auth":
            # Step 1: Redirect user to Shopify authorization
            state = secrets.token_urlsafe(32)
            oauth_state['state'] = state
            
            auth_url = f"https://{STORE_URL}/admin/oauth/authorize?" + urlencode({
                "client_id": CLIENT_ID,
                "scope": ",".join(SCOPES),
                "redirect_uri": REDIRECT_URI,
                "state": state
            })
            
            self.send_response(302)
            self.send_header("Location", auth_url)
            self.end_headers()
            print(f"[*] Redirecting to Shopify authorization URL")
            
        elif path == "/callback":
            # Step 2: Handle callback with authorization code
            code = query.get('code', [None])[0]
            state = query.get('state', [None])[0]
            error = query.get('error', [None])[0]
            
            if error:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h1>Error: {error}</h1>".encode())
                print(f"[!] OAuth error: {error}")
                return
            
            if not code or state != oauth_state.get('state'):
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Invalid state or missing code</h1>")
                print("[!] Invalid state or missing code")
                return
            
            # Step 3: Exchange code for access token
            print(f"[*] Got authorization code: {code[:20]}...")
            token = self._exchange_code_for_token(code)
            
            if token:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                html = f"""
                <html>
                <head><title>Shopify OAuth Success</title></head>
                <body>
                <h1>✅ Success!</h1>
                <p>Your Shopify Admin API access token:</p>
                <code style="background: #f0f0f0; padding: 15px; display: block; font-family: monospace; word-break: break-all;">
                {token}
                </code>
                <p><strong>Copy this token and update:</strong></p>
                <code>SHOPIFY_ADMIN_TOKEN={token}</code>
                <p>in your VPS <code>.env</code> file</p>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
                print(f"[✓] Token obtained: {token[:30]}...")
            else:
                self.send_response(500)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Failed to get access token</h1>")
                print("[!] Failed to exchange code for token")
        
        elif path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = f"""
            <html>
            <head><title>Shopify OAuth</title></head>
            <body>
            <h1>Shopify Admin API OAuth</h1>
            <p>Click the button below to authorize the Pure Leven CRM Sync app:</p>
            <a href="/auth" style="padding: 10px 20px; background: #0088e6; color: white; text-decoration: none; border-radius: 5px;">
                Authorize with Shopify
            </a>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def _exchange_code_for_token(self, code: str) -> str | None:
        """Exchange authorization code for access token"""
        try:
            token_url = f"https://{STORE_URL}/admin/oauth/access_token"
            data = urlencode({
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code
            }).encode()
            
            req = urllib.request.Request(token_url, data=data)
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            
            with urllib.request.urlopen(req, timeout=10) as r:
                result = json.loads(r.read())
                return result.get('access_token')
        
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"[!] HTTP {e.code}: {body}")
        except Exception as e:
            print(f"[!] Error exchanging code: {e}")
        
        return None
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  SHOPIFY OAUTH 2.0 AUTHORIZATION SERVER")
    print("="*70)
    print(f"\n[*] Starting server on http://localhost:8765")
    print(f"\n[*] STEP 1: Open your browser and visit:")
    print(f"    👉  http://localhost:8765/")
    print(f"\n[*] STEP 2: Click 'Authorize with Shopify'")
    print(f"\n[*] STEP 3: Approve the Pure Leven CRM Sync app in Shopify")
    print(f"\n[*] STEP 4: Copy the shpat_ token from the success page")
    print(f"\n[*] STEP 5: Update VPS .env with the new token")
    print("\n" + "="*70 + "\n")
    
    server = HTTPServer(('localhost', 8765), OAuthHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped")
        sys.exit(0)
