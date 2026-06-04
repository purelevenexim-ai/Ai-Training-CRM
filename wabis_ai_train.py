#!/usr/bin/env python3
"""
Wabis AI Model Training — Upload cleaned chatbot training data

Uses Wabis API to:
1. Check available AI training endpoints
2. Upload cleaned training data from CHATBOT_TRAINING_DATA_CLEANED.json
3. Trigger AI model training

Training data structure (from cleaning pipeline):
  - 41 deduplicated intent×product entries
  - Each with: category, product, customer_input, input_variations[], ideal_response
  - Mixed English/Malayalam, ready for Wabis bot learning
"""

import os
import json
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ─── Configuration ─────────────────────────────────────────────────────────────
PHONE_ID = "252036884661683"
BASE_URL = "https://bot.wabis.in"


def resolve_token() -> str:
    """Read the Wabis token from the environment instead of hard-coding it."""
    token = (
        os.getenv("WABIS_API_TOKEN")
        or os.getenv("WABIS_API_KEY")
        or os.getenv("WABIS_TRAINING_TOKEN")
        or ""
    ).strip()

    if not token:
        raise RuntimeError(
            "Missing WABIS token. Set WABIS_API_TOKEN, WABIS_API_KEY, or WABIS_TRAINING_TOKEN."
        )

    return token


def resolve_training_file() -> Path:
    """Find the cleaned training artifact in both local and server layouts."""
    env_path = (os.getenv("WABIS_TRAINING_FILE") or os.getenv("PURELEVEN_TRAINING_FILE") or "").strip()
    candidates = []

    if env_path:
        candidates.append(Path(env_path).expanduser())

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir

    candidates.extend(
        [
            repo_root / "training_artifacts" / "current" / "wabis_training_upload.json",
            repo_root / "training_artifacts" / "wabis_training_upload.json",
            repo_root / "CHATBOT_TRAINING_DATA_CLEANED.json",
            repo_root / "app" / "CHATBOT_TRAINING_DATA_CLEANED.json",
            Path.cwd() / "CHATBOT_TRAINING_DATA_CLEANED.json",
            Path.cwd() / "app" / "CHATBOT_TRAINING_DATA_CLEANED.json",
            Path.cwd() / "training_artifacts" / "current" / "wabis_training_upload.json",
            Path.cwd() / "training_artifacts" / "wabis_training_upload.json",
            Path("/opt/pureleven/ai-engine/training_artifacts/wabis_training_upload.json"),
            Path("/opt/anu-login-backend/backend/training_artifacts/current/wabis_training_upload.json"),
            Path("/opt/anu-login-backend/backend/training_artifacts/wabis_training_upload.json"),
            Path("/opt/pureleven/ai-engine/CHATBOT_TRAINING_DATA_CLEANED.json"),
            Path("/opt/pureleven/ai-engine/app/CHATBOT_TRAINING_DATA_CLEANED.json"),
            Path.home() / "Documents" / "pureleven_dev" / "CHATBOT_TRAINING_DATA_CLEANED.json",
        ]
    )

    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.resolve() if candidate.exists() else candidate
        key = str(normalized)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    searched = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(f"Training file not found. Searched:\n{searched}")

def curl_post(endpoint: str, payload: dict = None, show_request: bool = False) -> dict:
    """POST JSON via curl."""
    token = resolve_token()
    headers = [
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
    ]
    
    cmd = ["curl", "-s", "-X", "POST"]
    cmd.extend(headers)
    
    if payload:
        body = json.dumps(payload)
        cmd.extend(["-d", body])
    
    cmd.append(f"{BASE_URL}{endpoint}")
    
    if show_request:
        print(f"  → POST {endpoint}")
        if payload:
            print(f"    Payload: {json.dumps(payload, indent=2)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        else:
            return {"error": f"curl error: {result.stderr}"}
    except Exception as e:
        return {"error": str(e)}

def load_training_data() -> list:
    """Load cleaned training data."""
    training_file = resolve_training_file()

    with open(training_file) as f:
        data = json.load(f)
    
    print(f"✅ Loaded {len(data)} training entries from {training_file}")
    return data

def format_training_data(data: list) -> list:
    """Format training data for Wabis API."""
    if data and isinstance(data[0], dict) and {"question", "answer", "category", "product"}.issubset(data[0].keys()):
        print(f"📊 Using curated Wabis-ready dataset with {len(data)} Q&A pairs")
        return data

    formatted = []
    
    for entry in data:
        # Convert to Q&A pairs format
        questions = [entry['customer_input']] + entry.get('input_variations', [])
        answer = entry['ideal_response']
        
        for q in questions:
            if q and q.strip():  # Skip empty questions
                formatted.append({
                    "question": q.strip(),
                    "answer": answer.strip(),
                    "category": entry.get('category', 'general'),
                    "product": entry.get('product', 'general'),
                    "language": entry.get('language', 'en'),
                })
    
    print(f"📊 Formatted {len(formatted)} Q&A pairs from {len(data)} entries")
    return formatted

def discover_endpoints():
    """Try to discover available Wabis AI endpoints."""
    print("\n🔍 Discovering Wabis AI endpoints...")
    
    endpoints_to_try = [
        "/api/v1/ai/knowledge-base/upload",
        "/api/v1/ai/training/upload",
        "/api/v1/ai/train",
        "/api/v1/bot/ai/knowledge",
        "/api/v1/whatsapp/ai/train",
        "/api/v1/ai/knowledge-base/add",
        "/api/v1/knowledge/add",
    ]
    
    for endpoint in endpoints_to_try:
        print(f"\n  Trying: {endpoint}")
        resp = curl_post(endpoint, {"test": "discovery"})
        
        # Check if endpoint exists (error codes other than 404/not found)
        if "error" not in resp and resp:
            print(f"    ✓ Response: {resp}")
        elif resp.get("error"):
            if "404" not in str(resp.get("error")):
                print(f"    → {resp.get('error')}")

def upload_to_knowledge_base(data: list):
    """Upload training data to Wabis knowledge base."""
    print("\n📤 Uploading training data to Wabis knowledge base...")
    
    # Try different API formats
    endpoints = [
        ("/api/v1/ai/knowledge-base/upload", "knowledge_base_upload"),
        ("/api/v1/ai/training/upload", "training_upload"),
        ("/api/v1/bot/ai/knowledge", "bot_ai_knowledge"),
    ]
    
    for endpoint, name in endpoints:
        print(f"\n  Attempting: {endpoint}")
        
        payload = {
            "training_data": data,
            "model_type": "chatbot",
            "language": "en-ml",  # English-Malayalam
            "auto_train": True,
        }
        
        resp = curl_post(endpoint, payload, show_request=True)
        
        if "error" not in resp and resp.get("status") in ["success", "uploaded", "queued"]:
            print(f"  ✅ {resp}")
            return True
        elif resp.get("error"):
            print(f"  ⚠️  {resp.get('error')}")
    
    print("\n  ⚠️  Could not find working upload endpoint")
    return False

def trigger_training():
    """Trigger AI model training."""
    print("\n🤖 Triggering AI model training...")
    
    endpoints = [
        "/api/v1/ai/train",
        "/api/v1/ai/model/train",
        "/api/v1/bot/train",
    ]
    
    for endpoint in endpoints:
        print(f"\n  Attempting: {endpoint}")
        resp = curl_post(endpoint, {"start": True}, show_request=True)
        
        if "error" not in resp and resp.get("status") in ["started", "running", "queued"]:
            print(f"  ✅ Training started: {resp}")
            return True
        elif resp.get("error"):
            print(f"  ⚠️  {resp.get('error')}")
    
    print("\n  ⚠️  Could not trigger training via API")
    return False

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload curated or cleaned training data to Wabis.")
    parser.add_argument("--training-file", help="Explicit training file path")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip endpoint discovery requests")
    parser.add_argument("--dry-run", action="store_true", help="Load and format data without calling Wabis")
    parser.add_argument("--fail-on-upload-error", action="store_true", help="Exit non-zero if upload or trigger fails")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 80)
    print("Wabis AI Model Training — Upload Cleaned Chatbot Data")
    print("=" * 80)
    print(f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.training_file:
        os.environ["WABIS_TRAINING_FILE"] = args.training_file
    training_file = resolve_training_file()
    token = resolve_token()
    print(f"📄 Training file: {training_file}")
    print(f"🔑 Using API token: {token[:10]}...")
    
    # 1. Load training data
    data = load_training_data()
    if not data:
        return
    
    # 2. Format for API
    formatted_data = format_training_data(data)

    if args.dry_run:
        print("🧪 Dry run enabled. Skipping Wabis API calls.")
        print("\n" + "=" * 80)
        return 0
    
    # 3. Discover endpoints
    if not args.skip_discovery:
        discover_endpoints()
    
    # 4. Try to upload
    uploaded = upload_to_knowledge_base(formatted_data)
    
    # 5. Trigger training if upload succeeded
    triggered = False
    if uploaded:
        triggered = trigger_training()
    
    print("\n" + "=" * 80)
    print("Note: For final verification, log in to https://bot.wabis.in/settings")
    print("      and check Settings > AI & Knowledge Base > Training Status")
    print("=" * 80)
    if args.fail_on_upload_error and (not uploaded or not triggered):
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
