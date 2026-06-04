# Google Ads OAuth Setup Guide

## Status: 90% Ready ✅

You have:
- ✅ Customer ID: 7225234563
- ✅ Client ID: <GOOGLE_ADS_CLIENT_ID>
- ⏳ Developer Token: PENDING
- ⏳ Client Secret: PENDING
- ⏳ Refresh Token: PENDING (generated via OAuth)

---

## Step 1: Get Developer Token

**Location**: Google Ads API Center  
**Time**: 2 minutes

### A. Navigate to API Center
1. Go to: https://ads.google.com/aw/apicenter
2. You should already have this tab open (Annaseo account)

### B. Find & Copy Developer Token
1. Look for "Development Settings" or "API Settings" section
2. Find the field labeled **"Developer Token"**
3. **Copy the token** (should be 20-40 characters)
4. Paste it below or tell me the value

**Expected format**: Alphanumeric string like `abc123def456ghi789jkl`

```
Your Developer Token: ___________________________________
```

---

## Step 2: Get Client Secret from Google Cloud

**Location**: Google Cloud Console → Credentials  
**Time**: 2 minutes

### A. Navigate to Credentials
1. Go to: https://console.cloud.google.com/auth/clients?project=pure-leven
2. Or: Google Cloud Console → APIs & Services → Credentials

### B. Find Your OAuth 2.0 Client ID
1. Look for the client ID: `<GOOGLE_ADS_CLIENT_ID>`
2. Click on it to open details

### C. Copy Client Secret
1. You should see a **"Client Secret"** field
2. Click the **eye icon** or "Show" button to reveal it
3. **Copy the secret** (should be 24+ characters)
4. Paste it below or tell me the value

**Expected format**: Something like `<GOOGLE_ADS_CLIENT_SECRET>`

```
Your Client Secret: ___________________________________
```

---

## Step 3: Generate Refresh Token (One-Time OAuth Flow)

**Time**: 5 minutes  
**Method**: Via Python script or browser

### Option A: Automated Python Script
```bash
# This will generate a refresh token interactively
python3 /Users/bthomas/Documents/pureleven_dev/generate_google_oauth_token.py
```

### Option B: Manual OAuth Flow
1. Use this URL in your browser (replace CLIENT_ID):
```
https://accounts.google.com/o/oauth2/v2/auth?
  client_id=<GOOGLE_ADS_CLIENT_ID>&
  redirect_uri=urn:ietf:wg:oauth:2.0:oob&
  response_type=code&
  scope=https://www.googleapis.com/auth/adwords&
  access_type=offline
```

2. Google will give you an **Authorization Code**
3. Exchange it for Refresh Token (Python):
```python
import requests

code = "YOUR_AUTH_CODE"  # From step 2
client_id = "<GOOGLE_ADS_CLIENT_ID>"
client_secret = "YOUR_CLIENT_SECRET"  # From Step 2

response = requests.post('https://oauth2.googleapis.com/token', data={
    'code': code,
    'client_id': client_id,
    'client_secret': client_secret,
    'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
    'grant_type': 'authorization_code'
})

data = response.json()
print(f"Refresh Token: {data['refresh_token']}")
```

---

## All Required Credentials Checklist

| Credential | Value | Source |
|-----------|-------|--------|
| GOOGLE_ADS_CUSTOMER_ID | 7225234563 | ✅ Already have |
| GOOGLE_ADS_DEVELOPER_TOKEN | ❓ NEED | Google Ads API Center |
| GOOGLE_ADS_CLIENT_ID | <GOOGLE_ADS_CLIENT_ID> | ✅ Already have |
| GOOGLE_ADS_CLIENT_SECRET | ❓ NEED | Google Cloud Console |
| GOOGLE_ADS_OAUTH_REFRESH_TOKEN | ❓ NEED | OAuth 2.0 flow |

---

## Final VPS Configuration

Once you have all three missing credentials, I'll run:

```bash
sshpass -p 'QazPlm123!@#' ssh -o StrictHostKeyChecking=no root@192.46.213.140 << 'EOF'
cat >> /opt/pureleven/ai-engine/.env << 'ENDENV'

# Google Ads Configuration (COMPLETE)
GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_DEVELOPER_TOKEN
GOOGLE_ADS_CLIENT_ID=<GOOGLE_ADS_CLIENT_ID>
GOOGLE_ADS_CLIENT_SECRET=YOUR_CLIENT_SECRET
GOOGLE_ADS_OAUTH_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
GOOGLE_ADS_CUSTOMER_ID=7225234563
ENDENV

docker restart pureleven-ai-engine
EOF
```

---

## What Happens After Setup

✅ **Email Service**: AWS SES will send transactional emails  
✅ **Meta Audience Sync**: CAPI will add customers to Meta audiences  
✅ **Google Ads Sync**: Customer Match will add customers to Google Ads audiences  
✅ **Live Feed**: WebSocket shows all step executions in real-time  
✅ **N8N Integration**: Webhooks will trigger all customer journeys  

---

## Quick Extraction Command

If you can access the pages and just need to copy the values, use these commands:

**For Google Ads Developer Token** (copy from https://ads.google.com/aw/apicenter):
```
Select → Copy → Paste below
```

**For Google Cloud Client Secret** (copy from GCP credentials page):
```
Click eye icon → Copy → Paste below
```

---

## Next: Tell Me the Values

Once you have Developer Token and Client Secret, just provide them and I'll complete the VPS configuration immediately.

**Format**:
```
Developer Token: abc123def456...
Client Secret: <GOOGLE_ADS_CLIENT_SECRET>...
```

Or just say "Got them!" and I'll walk you through pasting them into the VPS via SSH.
