# Anu Login Backend Deployment

This folder contains the server-side deployment assets for the FastAPI backend in `anu-login/backend`.

## What This Deploys

- A `uvicorn` systemd service bound to `127.0.0.1:8000`
- An `nginx` site that proxies `/api/*` to the backend
- A persistent SQLite database path under `/var/lib/anu-login-backend`
- An optional Certbot step for HTTPS

## Important Constraints

1. `api.pureleven.com` does **not** currently resolve to `192.46.213.140`.
2. `adsapi.pureleven.com` **does** resolve to `192.46.213.140`, but it currently serves the reserved placeholder response for `pureleven-adsapi`.
3. The live theme snapshot still points `anu_login_api_url` at a temporary Cloudflare tunnel URL.
4. Do not update the Shopify theme setting until a real HTTPS hostname for this backend is live.

## Suggested Hostname

Use `adsapi.pureleven.com` for this deployment target.

## Server Bootstrap

Copy the `anu-login/backend` directory to the server, then run:

```bash
cd /path/to/anu-login/backend
sudo SERVER_NAME=adsapi.pureleven.com bash deploy/bootstrap-ubuntu.sh
```

If DNS is already correct and you want the script to obtain TLS automatically:

```bash
cd /path/to/anu-login/backend
sudo SERVER_NAME=adsapi.pureleven.com ENABLE_SSL=1 bash deploy/bootstrap-ubuntu.sh
```

## Environment File

The bootstrap script creates `/etc/anu-login-backend.env` from `.env.example` on first run.

At minimum, review these values:

- `ANU_LOGIN_ALLOWED_ORIGINS`
- `ANU_LOGIN_DEFAULT_COUPON`
- `ANU_LOGIN_ADMIN_SECRET`

## Post-Deploy Checks

Check the backend locally on the server:

```bash
curl http://127.0.0.1:8000/api/health
systemctl status anu-login-backend.service
journalctl -u anu-login-backend.service -n 100 --no-pager
```

Check the public route:

```bash
curl https://adsapi.pureleven.com/api/health
```

## Theme Update

After the public HTTPS hostname works, update the Shopify theme setting:

`Anu login > Lead API URL`

to:

```txt
https://adsapi.pureleven.com/api/leads
```

If you later run the separate Shopify embedded admin app against this backend, configure the admin app with:

- `ANU_LOGIN_API_BASE_URL=https://adsapi.pureleven.com`
- the same `ANU_LOGIN_ADMIN_SECRET` value used on the backend
