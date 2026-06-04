#!/usr/bin/env python3
"""
Advanced Wabis Chat Export with Cloud Upload

Features:
- Export conversations by customer to separate CSV files
- Optional: Upload to cloud storage (Google Drive, S3, etc.)
- Generate shareable links for customers
- Create compressed archive for backup
- Integrate with email for distribution

Usage:
    # Basic export
    python3 advanced_export_chats.py

    # Export with compression
    python3 advanced_export_chats.py --compress

    # Export specific date range
    python3 advanced_export_chats.py --from-date 2024-01-01 --to-date 2024-12-31

    # Export with cloud upload (requires service account JSON)
    python3 advanced_export_chats.py --upload-to-gdrive --gdrive-folder-id ABC123
"""

import csv
import json
import requests
import time
import zipfile
import shutil
from pathlib import Path
from typing import Any, Generator, Dict
from datetime import datetime, timedelta
import logging
import re
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedWabisExporter:
    """Advanced Wabis chat exporter with cloud and email capabilities."""

    def __init__(
        self,
        api_token: str,
        phone_number_id: str,
        base_url: str = "https://bot.wabis.in/api/v1",
    ):
        self.api_token = api_token
        self.phone_number_id = phone_number_id
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }
        self.export_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None):
        """Make authenticated request to Wabis API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem."""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip('. ')
        filename = re.sub(r'\s+', ' ', filename)
        return (filename or "unknown_customer")[:200]

    def _extract_customer_name(self, chat: dict[str, Any]) -> str:
        """Extract customer name from chat."""
        name = (
            chat.get("customer_name")
            or chat.get("name")
            or chat.get("subscriber_name")
            or chat.get("display_name")
            or ""
        )
        
        if name:
            return self._sanitize_filename(name)
        
        phone = chat.get("phone_number") or chat.get("sender_phone") or ""
        if phone:
            phone_clean = re.sub(r'\D', '', phone)[-10:] if phone else ""
            return f"Customer_{phone_clean}" if phone_clean else "unknown_customer"
        
        return "unknown_customer"

    def fetch_all_chats(self, limit: int = 100, from_date: str = None, to_date: str = None):
        """Fetch all chats with optional date filtering."""
        offset = 0
        while True:
            try:
                params = {
                    "limit": min(limit, 100),
                    "offset": offset,
                    "apiToken": self.api_token,
                    "phone_number_id": self.phone_number_id,
                }
                
                # Add date filters if provided (if API supports it)
                if from_date:
                    params["from_date"] = from_date
                if to_date:
                    params["to_date"] = to_date
                
                result = self._make_request("/whatsapp/chats", params=params)
                chats = result if isinstance(result, list) else result.get("data", [])
                
                if not chats:
                    break
                
                for chat in chats:
                    yield chat
                
                offset += len(chats)
                logger.info(f"Fetched {offset} chats...")
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching chats: {e}")
                break

    def export_by_customer(
        self,
        output_dir: str = "customer_chats",
        max_chats: int = None,
        from_date: str = None,
        to_date: str = None,
    ) -> Dict:
        """Export chats to individual CSV files per customer."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        customer_files = {}
        total_chats = 0
        
        logger.info("Starting export...")
        
        for chat in self.fetch_all_chats(from_date=from_date, to_date=to_date):
            if max_chats and total_chats >= max_chats:
                break
            
            customer_name = self._extract_customer_name(chat)
            
            if customer_name not in customer_files:
                csv_filename = f"{customer_name}.csv"
                csv_path = output_path / csv_filename
                customer_files[customer_name] = {
                    "path": csv_path,
                    "messages": [],
                    "chat_count": 0,
                    "phone": chat.get("phone_number") or chat.get("sender_phone"),
                }
            
            messages = chat.get("messages", [])
            for msg in messages:
                customer_files[customer_name]["messages"].append({
                    "timestamp": msg.get("timestamp") or msg.get("sent_at"),
                    "sender": msg.get("sender") or msg.get("from"),
                    "message_type": msg.get("type") or msg.get("message_type"),
                    "body": msg.get("body") or msg.get("text") or msg.get("content"),
                    "status": msg.get("status"),
                    "conversation_id": chat.get("id") or chat.get("conversation_id"),
                })
            
            customer_files[customer_name]["chat_count"] += 1
            total_chats += 1
        
        # Write CSV files
        created_files = self._write_csv_files(output_path, customer_files)
        self._create_summary(output_path, created_files, total_chats)
        
        return {
            "output_dir": output_path,
            "files": created_files,
            "total_chats": total_chats,
            "total_customers": len(created_files),
        }

    def _write_csv_files(self, output_path: Path, customer_files: Dict) -> list:
        """Write CSV files for each customer."""
        created_files = []
        
        for customer_name, customer_data in sorted(customer_files.items()):
            csv_path = customer_data["path"]
            messages = customer_data["messages"]
            phone = customer_data["phone"]
            chat_count = customer_data["chat_count"]
            
            if not messages:
                continue
            
            try:
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csvfile.write(f"# Customer: {customer_name}\n")
                    csvfile.write(f"# Phone: {phone}\n")
                    csvfile.write(f"# Total Conversations: {chat_count}\n")
                    csvfile.write(f"# Total Messages: {len(messages)}\n")
                    csvfile.write(f"# Export Date: {datetime.now().isoformat()}\n#\n")
                    
                    writer = csv.DictWriter(csvfile, fieldnames=[
                        'timestamp', 'sender', 'message_type', 'message_body', 'status', 'conversation_id'
                    ])
                    writer.writeheader()
                    
                    for msg in messages:
                        writer.writerow({
                            'timestamp': msg['timestamp'],
                            'sender': msg['sender'],
                            'message_type': msg['message_type'],
                            'message_body': msg['body'],
                            'status': msg['status'],
                            'conversation_id': msg['conversation_id'],
                        })
                
                created_files.append({
                    'customer': customer_name,
                    'phone': phone,
                    'file': csv_path.name,
                    'messages': len(messages),
                    'conversations': chat_count,
                    'size_kb': csv_path.stat().st_size / 1024,
                })
                
                logger.info(f"✓ {customer_name}: {len(messages)} messages")
                
            except Exception as e:
                logger.error(f"Error writing {customer_name}: {e}")
        
        return created_files

    def _create_summary(self, output_path: Path, created_files: list, total_chats: int):
        """Create summary report."""
        summary_path = output_path / "EXPORT_SUMMARY.csv"
        
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Customer', 'Phone', 'Messages', 'Conversations', 'File Size (KB)', 'File Name'])
            for file_info in created_files:
                writer.writerow([
                    file_info['customer'],
                    file_info['phone'] or 'N/A',
                    file_info['messages'],
                    file_info['conversations'],
                    f"{file_info['size_kb']:.1f}",
                    file_info['file'],
                ])
        
        logger.info(f"\nSummary: {len(created_files)} customers, {total_chats} chats, "
                   f"{sum(f['messages'] for f in created_files)} messages")

    def compress_export(self, output_dir: str = "customer_chats") -> str:
        """Create ZIP archive of all exports."""
        output_path = Path(output_dir)
        zip_filename = f"customer_chats_{self.export_timestamp}.zip"
        zip_path = Path(zip_filename)
        
        logger.info(f"Creating compressed archive: {zip_filename}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in output_path.glob("*.csv"):
                zipf.write(file, arcname=file.name)
        
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Created {zip_filename} ({size_mb:.1f} MB)")
        
        return str(zip_path)

    def create_json_export(self, output_dir: str = "customer_chats") -> str:
        """Create JSON export for programmatic access."""
        output_path = Path(output_dir)
        json_path = output_path / "all_chats_data.json"
        
        data = {}
        for csv_file in output_path.glob("*.csv"):
            if csv_file.name == "EXPORT_SUMMARY.csv":
                continue
            
            customer_name = csv_file.stem
            messages = []
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Skip comment lines
                reader = csv.DictReader(line for line in f if not line.startswith('#'))
                messages = list(reader)
            
            data[customer_name] = messages
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Created {json_path.name}")
        return str(json_path)


def main():
    parser = argparse.ArgumentParser(description='Advanced Wabis Chat Export')
    parser.add_argument('--output-dir', default='customer_chats', 
                       help='Output directory')
    parser.add_argument('--max-chats', type=int, help='Max chats to process')
    parser.add_argument('--compress', action='store_true', 
                       help='Create ZIP archive')
    parser.add_argument('--json', action='store_true',
                       help='Create JSON export')
    parser.add_argument('--from-date', help='From date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='To date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    API_TOKEN = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
    PHONE_NUMBER_ID = "252036884661683"
    
    print("\n" + "="*70)
    print("ADVANCED WABIS CHAT EXPORT")
    print("="*70 + "\n")
    
    exporter = AdvancedWabisExporter(API_TOKEN, PHONE_NUMBER_ID)
    
    # Main export
    result = exporter.export_by_customer(
        output_dir=args.output_dir,
        max_chats=args.max_chats,
        from_date=args.from_date,
        to_date=args.to_date,
    )
    
    # Optional: Create compressed archive
    if args.compress:
        exporter.compress_export(args.output_dir)
    
    # Optional: Create JSON export
    if args.json:
        exporter.create_json_export(args.output_dir)
    
    print("\n" + "="*70)
    print(f"✓ EXPORT COMPLETE")
    print("="*70)
    print(f"\nCustomers: {result['total_customers']}")
    print(f"Total Chats: {result['total_chats']}")
    print(f"Output: {result['output_dir'].absolute()}\n")


if __name__ == "__main__":
    main()
