#!/usr/bin/env python3
"""Diagnose n8n and trigger Google Ads audience creation."""
import subprocess, json, sys

VPS = "root@192.46.213.140"
PWD = "QazPlm123!@#"

def ssh(cmd):
    r = subprocess.run(
        ["sshpass", "-p", PWD, "ssh", "-o", "StrictHostKeyChecking=no", VPS, cmd],
        capture_output=True, text=True, timeout=20
    )
    return (r.stdout + r.stderr).strip()

print("=" * 60)
print("N8N DIAGNOSTICS")
print("=" * 60)

print("\n1. CONTAINER STATUS:")
print(ssh('docker inspect pureleven-n8n --format "Running: {{.State.Running}} Status: {{.State.Status}} StartedAt: {{.State.StartedAt}}"'))

print("\n2. EXECUTION COUNTS IN DATABASE:")
print(ssh("sqlite3 /opt/pureleven/n8n/data/database.sqlite 'SELECT COUNT(*) FROM execution_entity;'"))

print("\n3. RECENT EXECUTIONS (last 5):")
print(ssh("sqlite3 /opt/pureleven/n8n/data/database.sqlite \"SELECT workflowId, status, datetime(createdAt) FROM execution_entity ORDER BY rowid DESC LIMIT 5;\""))

print("\n4. WORKFLOWS AND ACTIVE STATUS:")
print(ssh("sqlite3 /opt/pureleven/n8n/data/database.sqlite 'SELECT id, name, active FROM workflow_entity ORDER BY active DESC;'"))

print("\n5. SAVED CREDENTIALS:")
print(ssh("sqlite3 /opt/pureleven/n8n/data/database.sqlite 'SELECT id, name, type FROM credentials_entity;'"))

print("\n6. N8N LOGS (last 30 lines):")
print(ssh("docker logs pureleven-n8n --tail 30 2>&1"))

print("\n7. BACKEND CONNECTIVITY (n8n → FastAPI):")
result = ssh("docker exec pureleven-n8n wget -q -T5 -O- http://pureleven-ai-engine:8000/health 2>&1")
print(result if result else "TIMEOUT or no output")

print("\n8. N8N NETWORK:")
print(ssh('docker inspect pureleven-n8n --format "{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}"'))

print("\n9. BACKEND NETWORK:")
print(ssh('docker inspect pureleven-ai-engine --format "{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}"'))

print("\n10. N8N SETTINGS TABLE:")
print(ssh("sqlite3 /opt/pureleven/n8n/data/database.sqlite \"SELECT key, value FROM settings WHERE key LIKE '%user%' OR key LIKE '%owner%' OR key LIKE '%setup%';\""))

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
