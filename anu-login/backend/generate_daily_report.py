#!/usr/bin/env python3
"""
Cron job to generate daily reports.

Run this every night (or in cron scheduler):
0 0 * * * /opt/pureleven/ai-engine/generate_daily_report.py

Generates: /app/data/reports/conversation_review_YYYY_MM_DD.md
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add app to path
sys.path.insert(0, '/app')

from app.ai.daily_report_generator import save_daily_report, ensure_reports_dir


def main():
    """Generate daily report for yesterday"""
    try:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Starting daily report generation...")
        
        ensure_reports_dir()
        report_path = save_daily_report()
        
        print(f"✅ Report saved: {report_path}")
        print(f"📊 Size: {report_path.stat().st_size} bytes")
        
        # Print first 30 lines
        content = report_path.read_text()
        lines = content.split('\n')[:30]
        print("\n" + "="*80)
        print('\n'.join(lines))
        if len(content.split('\n')) > 30:
            print(f"\n... ({len(content.split(chr(10))) - 30} more lines)")
        print("="*80)
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
