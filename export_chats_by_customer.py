#!/usr/bin/env python3
"""
Wabis Chat Export by Customer

Exports all conversations from Wabis, grouped by customer.
Creates a separate CSV file for each customer with their name.

Output structure:
customer_chats/
├── Customer_Name_1.csv
├── Customer_Name_2.csv
├── Customer_Name_3.csv
└── ...
"""

import csv
import requests
import time
from pathlib import Path
from typing import Any, Generator, Dict
from datetime import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WabisChatByCustomerExporter:
    """Export Wabis chats grouped by customer with individual CSV files."""

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

    def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
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
        """Sanitize filename for use in filesystem."""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename or "unknown_customer"

    def _extract_customer_name(self, chat: dict[str, Any]) -> str:
        """Extract customer name/identifier from chat data."""
        # Try different fields for customer name
        name = (
            chat.get("customer_name")
            or chat.get("name")
            or chat.get("subscriber_name")
            or chat.get("display_name")
            or ""
        )
        
        if name:
            return self._sanitize_filename(name)
        
        # Fallback to phone number
        phone = chat.get("phone_number") or chat.get("sender_phone") or ""
        if phone:
            # Extract last 10 digits for cleaner filename
            phone_clean = re.sub(r'\D', '', phone)[-10:] if phone else ""
            return f"Customer_{phone_clean}" if phone_clean else "unknown_customer"
        
        return "unknown_customer"

    def fetch_all_chats(self, limit: int = 100) -> Generator[dict[str, Any], None, None]:
        """Paginate through all chats from Wabis API."""
        offset = 0
        while True:
            try:
                params = {
                    "limit": min(limit, 100),
                    "offset": offset,
                    "apiToken": self.api_token,
                    "phone_number_id": self.phone_number_id,
                }
                
                result = self._make_request("/whatsapp/chats", params=params)
                
                # Handle different response formats
                chats = result if isinstance(result, list) else result.get("data", [])
                
                if not chats:
                    logger.info(f"Reached end of chats at offset {offset}")
                    break
                
                for chat in chats:
                    yield chat
                
                offset += len(chats)
                logger.info(f"Fetched {offset} chats so far...")
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error fetching chats at offset {offset}: {e}")
                break

    def export_by_customer(self, output_dir: str = "customer_chats", max_chats: int = None):
        """
        Export chats to individual CSV files per customer.
        
        Returns:
            Dictionary with customer names and their file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Dictionary to track customer files
        customer_files: Dict[str, dict] = {}
        total_chats = 0
        
        logger.info("Starting export of all chats by customer...")
        
        for chat in self.fetch_all_chats():
            if max_chats and total_chats >= max_chats:
                logger.info(f"Reached max chats limit: {max_chats}")
                break
            
            customer_name = self._extract_customer_name(chat)
            
            # Initialize customer entry if new
            if customer_name not in customer_files:
                csv_filename = f"{customer_name}.csv"
                csv_path = output_path / csv_filename
                
                customer_files[customer_name] = {
                    "path": csv_path,
                    "messages": [],
                    "chat_count": 0,
                    "phone": chat.get("phone_number") or chat.get("sender_phone"),
                }
            
            # Collect messages from this chat
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
            
            if total_chats % 100 == 0:
                logger.info(f"Processed {total_chats} chats, {len(customer_files)} customers...")
        
        # Write CSV files for each customer
        logger.info(f"\nWriting CSV files for {len(customer_files)} customers...")
        created_files = []
        
        for customer_name, customer_data in sorted(customer_files.items()):
            csv_path = customer_data["path"]
            messages = customer_data["messages"]
            phone = customer_data["phone"]
            chat_count = customer_data["chat_count"]
            
            if not messages:
                logger.warning(f"No messages for {customer_name}, skipping")
                continue
            
            # Write CSV
            try:
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'timestamp',
                        'sender',
                        'message_type',
                        'message_body',
                        'status',
                        'conversation_id'
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    # Write header with customer info
                    csvfile.write(f"# Customer: {customer_name}\n")
                    csvfile.write(f"# Phone: {phone}\n")
                    csvfile.write(f"# Total Conversations: {chat_count}\n")
                    csvfile.write(f"# Total Messages: {len(messages)}\n")
                    csvfile.write(f"# Export Date: {datetime.now().isoformat()}\n")
                    csvfile.write("#\n")
                    
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
                    'file': csv_path,
                    'messages': len(messages),
                    'conversations': chat_count,
                })
                
                logger.info(
                    f"✓ {customer_name}: {len(messages)} messages across {chat_count} conversations"
                )
                
            except Exception as e:
                logger.error(f"Error writing CSV for {customer_name}: {e}")
                continue
        
        # Create summary report
        self._create_summary_report(output_path, created_files, total_chats)
        
        return created_files

    def _create_summary_report(self, output_dir: Path, created_files: list, total_chats: int):
        """Create a summary report of all exported files."""
        summary_path = output_dir / "EXPORT_SUMMARY.csv"
        
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Customer Name', 'Phone Number', 'Total Messages', 'Conversations', 'File Name'])
            
            for file_info in created_files:
                writer.writerow([
                    file_info['customer'],
                    file_info['phone'] or 'N/A',
                    file_info['messages'],
                    file_info['conversations'],
                    file_info['file'].name,
                ])
        
        logger.info(f"\n✓ Summary report created: {summary_path}")
        logger.info(f"\nExport Statistics:")
        logger.info(f"  Total chats processed: {total_chats}")
        logger.info(f"  Unique customers: {len(created_files)}")
        logger.info(f"  Total messages: {sum(f['messages'] for f in created_files)}")
        logger.info(f"  Output directory: {output_dir.absolute()}")


def main():
    """Export all Wabis chats by customer."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Export Wabis chats by customer')
    parser.add_argument('--output-dir', default='customer_chats', 
                       help='Output directory for customer CSV files')
    parser.add_argument('--max-chats', type=int, default=None,
                       help='Maximum chats to process (for testing)')
    parser.add_argument('--limit', type=int, default=100,
                       help='Chats per API request')
    
    args = parser.parse_args()
    
    # Configuration
    API_TOKEN = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
    PHONE_NUMBER_ID = "252036884661683"
    
    try:
        print("\n" + "="*70)
        print("WABIS CHAT EXPORT BY CUSTOMER")
        print("="*70 + "\n")
        
        exporter = WabisChatByCustomerExporter(API_TOKEN, PHONE_NUMBER_ID)
        
        created_files = exporter.export_by_customer(
            output_dir=args.output_dir,
            max_chats=args.max_chats
        )
        
        print("\n" + "="*70)
        print("EXPORT COMPLETE!")
        print("="*70)
        print(f"\n✓ Created {len(created_files)} customer CSV files")
        print(f"✓ Output directory: {Path(args.output_dir).absolute()}\n")
        
        # Show sample of created files
        print("Sample of created files:")
        for file_info in created_files[:10]:
            print(f"  • {file_info['file'].name}")
            print(f"    Messages: {file_info['messages']} | Conversations: {file_info['conversations']}")
        
        if len(created_files) > 10:
            print(f"  ... and {len(created_files) - 10} more files")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
