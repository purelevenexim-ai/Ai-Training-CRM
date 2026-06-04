#!/usr/bin/env python3
"""
Basil Commerce OS — Phase 5
automation/test_journey_cycle.py

15-minute automation script for marketing psychology journey demo.

Sends 15 WhatsApp messages to a test phone number every 15 minutes,
cycling through:
  - Lead journey (5 messages)
  - Abandoned cart journey (5 messages)  
  - Purchased customer journey (5 messages)

Each message includes comprehensive logging and psychology analysis.

Usage:
  python test_journey_cycle.py --phone +919447744583 --cycles 3
  
  --phone: Target phone number (E.164 format or 10-digit)
  --cycles: How many full cycles (3 cycles = 15 messages over 225 min)
  --interval: Seconds between sends (default 15min = 900 sec)
  --no-wait: Send all immediately (no delays)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests


# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_API_BASE = "http://localhost:8000"
JOURNEY_TYPES = ["lead", "abandoned", "purchased"]
MESSAGES_PER_JOURNEY = 5
DEFAULT_INTERVAL_SEC = 900  # 15 minutes


# ─── Logging ──────────────────────────────────────────────────────────────────

def log_message(msg: str, level: str = "INFO") -> None:
    """Pretty-print log messages."""
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] [{level}] {msg}")


def log_header(title: str) -> None:
    """Print section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


# ─── API Calls ────────────────────────────────────────────────────────────────

def send_journey_message(
    phone: str,
    journey_type: str,
    iteration: int,
    api_base: str = DEFAULT_API_BASE,
) -> dict:
    """
    Call the /api/test/journey/cycle endpoint.
    
    Returns response dict or raises exception.
    """
    
    url = f"{api_base}/api/test/journey/cycle"
    payload = {
        "phone": phone,
        "journey_type": journey_type,
        "iteration": iteration,
        "shop_domain": "pureleven.com",
    }
    
    log_message(f"Sending to {url}...", "DEBUG")
    log_message(f"Payload: {json.dumps(payload)}", "DEBUG")
    
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    return response.json()


def fetch_journey_log(phone: str, api_base: str = DEFAULT_API_BASE) -> list[dict]:
    """Fetch all sent messages for a phone."""
    
    url = f"{api_base}/api/test/journey/log"
    params = {"phone": phone, "limit": 50}
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    return response.json()


# ─── Main Automation ──────────────────────────────────────────────────────────

def run_journey_cycles(
    phone: str,
    cycles: int = 3,
    interval_sec: int = DEFAULT_INTERVAL_SEC,
    api_base: str = DEFAULT_API_BASE,
    no_wait: bool = False,
) -> None:
    """
    Send all journey messages, cycling through journey types.
    
    Timeline:
      Cycle 1: lead msgs 1-5 (every 20min)
      Cycle 2: abandoned msgs 1-5 (every 20min)
      Cycle 3: purchased msgs 1-5 (every 20min)
    """
    
    log_header("🎯 PURELEVEN MARKETING PSYCHOLOGY JOURNEY DEMO")
    log_message(f"Phone: {phone}")
    log_message(f"Cycles: {cycles}")
    log_message(f"Interval: {interval_sec}s ({interval_sec // 60}min)")
    log_message(f"Total Messages: {cycles * len(JOURNEY_TYPES) * MESSAGES_PER_JOURNEY}")
    log_message(f"Total Duration: ~{(cycles * len(JOURNEY_TYPES) * MESSAGES_PER_JOURNEY * interval_sec) // 60} minutes")
    
    if not no_wait:
        log_message("⏳ Starting in 5 seconds... (press Ctrl+C to cancel)", "WARN")
        time.sleep(5)
    
    start_time = datetime.now(timezone.utc)
    message_count = 0
    failed_count = 0
    
    log_header("📤 SENDING MESSAGES")
    
    for cycle_num in range(1, cycles + 1):
        for journey_idx, journey_type in enumerate(JOURNEY_TYPES):
            for msg_num in range(1, MESSAGES_PER_JOURNEY + 1):
                message_count += 1
                
                # Calculate timing
                elapsed = datetime.now(timezone.utc) - start_time
                elapsed_min = elapsed.total_seconds() / 60
                
                try:
                    log_message(
                        f"Message {message_count}/{ cycles * len(JOURNEY_TYPES) * MESSAGES_PER_JOURNEY} | "
                        f"Cycle {cycle_num}/{cycles} | "
                        f"{journey_type.upper()} Journey {msg_num}/{MESSAGES_PER_JOURNEY}",
                        "INFO"
                    )
                    
                    # Send message
                    result = send_journey_message(phone, journey_type, msg_num, api_base)
                    
                    # Log result
                    log_message(f"✅ SENT", "INFO")
                    log_message(f"   Template: {result.get('template_name')}", "INFO")
                    log_message(f"   Stage: {result.get('stage')}", "INFO")
                    log_message(f"   Psychology: {result.get('psychology_type')} "
                                f"(confidence: {result.get('psychology_confidence', 0):.0f}%)", "INFO")
                    log_message(f"   Conversion Probability: {result.get('conversion_probability', 0):.1f}%", "INFO")
                    log_message(f"   Timestamp: {result.get('timestamp')}", "DEBUG")
                    
                except Exception as e:
                    failed_count += 1
                    log_message(f"❌ FAILED: {str(e)}", "ERROR")
                
                # Wait before next message (unless it's the last one or no_wait is set)
                is_last_message = (cycle_num == cycles and 
                                  journey_idx == len(JOURNEY_TYPES) - 1 and 
                                  msg_num == MESSAGES_PER_JOURNEY)
                
                if not is_last_message and not no_wait:
                    log_message(f"⏳ Waiting {interval_sec}s ({interval_sec // 60}min) before next message...", "INFO")
                    for i in range(interval_sec):
                        if i % 60 == 0:
                            remaining = interval_sec - i
                            log_message(f"   {remaining}s remaining...", "DEBUG")
                        time.sleep(1)
    
    # Summary
    log_header("📊 JOURNEY COMPLETE")
    log_message(f"Total Messages Sent: {message_count - failed_count}/{message_count}")
    log_message(f"Success Rate: {((message_count - failed_count) / message_count * 100):.1f}%")
    log_message(f"Failed: {failed_count}")
    log_message(f"Duration: {(datetime.now(timezone.utc) - start_time).total_seconds() / 60:.1f}min")
    
    # Fetch and display log
    try:
        log_header("📋 MESSAGE LOG")
        messages = fetch_journey_log(phone, api_base)
        
        print(f"{'#':<3} {'Timestamp':<30} {'Journey':<12} {'Stage':<20} {'Template':<30} {'Status':<10} {'Psychology':<15}")
        print("-" * 130)
        
        for i, msg in enumerate(messages, 1):
            print(
                f"{i:<3} "
                f"{msg['timestamp'][-19:]:<30} "
                f"{msg['journey_type']:<12} "
                f"{msg['message_stage']:<20} "
                f"{msg['template_name']:<30} "
                f"{msg['status']:<10} "
                f"{msg['customer_psychology']:<15}"
            )
        
        log_message(f"Total logged messages: {len(messages)}", "INFO")
    
    except Exception as e:
        log_message(f"Could not fetch log: {e}", "ERROR")
    
    print()
    log_message("✅ Demo complete! Check your WhatsApp for all messages.", "INFO")
    log_message(f"Customer analytics available at: {api_base}/api/test/journey/log?phone={phone}", "INFO")
    print()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Parse args and run automation."""
    
    parser = argparse.ArgumentParser(
        description="Send test WhatsApp journey messages every 20 minutes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send 3 complete cycles (15 messages over 300 min)
  python test_journey_cycle.py --phone +919447744583 --cycles 3
  
  # Send 5 complete cycles with default 20min interval
  python test_journey_cycle.py --phone 9447744583 --cycles 5
  
  # Send all messages immediately (no waits)
  python test_journey_cycle.py --phone +919447744583 --cycles 3 --no-wait
  
  # Custom interval (10min between messages)
  python test_journey_cycle.py --phone +919447744583 --cycles 2 --interval 600
        """,
    )
    
    parser.add_argument(
        "--phone",
        required=True,
        help="Target phone number (E.164 or 10-digit format)",
    )
    
    parser.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="Number of complete journey cycles (default: 3 = 15 messages)",
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SEC,
        help=f"Seconds between messages (default: {DEFAULT_INTERVAL_SEC} = 15min)",
    )
    
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"API base URL (default: {DEFAULT_API_BASE})",
    )
    
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Send all messages immediately (no intervals)",
    )
    
    args = parser.parse_args()
    
    try:
        run_journey_cycles(
            phone=args.phone,
            cycles=args.cycles,
            interval_sec=args.interval,
            api_base=args.api_base,
            no_wait=args.no_wait,
        )
    except KeyboardInterrupt:
        print()
        log_message("Demo interrupted by user.", "WARN")
        sys.exit(0)
    except Exception as e:
        log_message(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
