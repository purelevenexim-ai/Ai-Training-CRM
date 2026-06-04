# Wabis Chat Export by Customer (CSV)

Complete guide to export all Wabis conversations with individual CSV files for each customer.

## Overview

This solution exports all chat conversations from Wabis, grouped by customer, creating a **separate CSV file for each customer** with their full conversation history.

**Output Structure:**
```
customer_chats/
├── EXPORT_SUMMARY.csv          # Index of all customers
├── Alice Johnson.csv            # Alice's conversation
├── Rajesh Kumar.csv             # Rajesh's conversation
├── Priya Sharma.csv             # Priya's conversation
├── Customer_9876543210.csv      # If no name available, uses phone
└── ...
```

---

## Quick Start (3 Steps)

### **Step 1: Install Dependencies**
```bash
pip install requests
```

### **Step 2: Run Export**
```bash
python3 export_chats_by_customer.py
```

### **Step 3: Check Output**
```bash
ls -lh customer_chats/
cat customer_chats/EXPORT_SUMMARY.csv
```

---

## Usage Examples

### **Basic Export (All Conversations)**
```bash
python3 export_chats_by_customer.py
```

Creates CSV file for each customer with all their messages.

### **Export with Custom Output Directory**
```bash
python3 export_chats_by_customer.py --output-dir my_chats
```

### **Limit to First 1000 Conversations (For Testing)**
```bash
python3 export_chats_by_customer.py --max-chats 1000
```

### **Advanced: With Compression & JSON**
```bash
python3 advanced_export_chats.py --compress --json
```

Creates:
- Individual CSV files
- `customer_chats_TIMESTAMP.zip` (compressed backup)
- `all_chats_data.json` (machine-readable format)

### **Advanced: Date Range Export**
```bash
python3 advanced_export_chats.py \
  --from-date 2024-01-01 \
  --to-date 2024-12-31
```

*Note: Only works if Wabis API supports date filtering*

---

## CSV File Format

Each customer's CSV file includes:

**Header Section (Comments):**
```
# Customer: John Doe
# Phone: +91-9876543210
# Total Conversations: 5
# Total Messages: 23
# Export Date: 2024-05-25T14:30:00
```

**Data Columns:**
| Column | Example | Description |
|--------|---------|-------------|
| timestamp | 2024-05-25T10:30:00Z | When message was sent |
| sender | +919876543210 | Who sent the message |
| message_type | text | Message type (text, image, document, etc.) |
| message_body | Hello, I want to order... | Actual message content |
| status | delivered | Message delivery status |
| conversation_id | conv_xyz123 | Unique conversation identifier |

**Example Row:**
```csv
2024-05-25T10:30:00Z,+919876543210,text,Hello! I want to order spices,delivered,conv_xyz123
2024-05-25T10:31:15Z,+919999999999,text,Hi John! Sure I can help you. Which spices?,delivered,conv_xyz123
```

---

## EXPORT_SUMMARY.csv Format

Master index file listing all customers:

```csv
Customer Name,Phone Number,Total Messages,Conversations,File Size (KB),File Name
Alice Johnson,+91-9876543210,45,8,12.5,Alice Johnson.csv
Rajesh Kumar,+91-8765432109,23,4,8.3,Rajesh Kumar.csv
Priya Sharma,+91-7654321098,156,15,42.1,Priya Sharma.csv
Customer_1234567890,+91-6543210987,12,2,4.5,Customer_1234567890.csv
```

---

## File Details

### **Primary Script: `export_chats_by_customer.py`**

**Features:**
- ✅ Fetches all conversations from Wabis API
- ✅ Groups by customer name or phone number
- ✅ Creates individual CSV per customer
- ✅ Generates summary report
- ✅ Handles special characters in names
- ✅ Rate limiting (0.5s between requests)

**Output:**
- CSV files: One per customer
- Summary: EXPORT_SUMMARY.csv

**Time to Complete:**
- 10,000 chats: 15-30 minutes
- 100,000 chats: 2-4 hours

### **Advanced Script: `advanced_export_chats.py`**

**Additional Features:**
- ✅ All features from basic script
- ✅ **ZIP Compression** - Creates backup archive
- ✅ **JSON Export** - Machine-readable format for apps
- ✅ **Date Range Filtering** - Export specific time periods
- ✅ Detailed file size metrics

**Usage:**
```bash
python3 advanced_export_chats.py --compress --json
```

---

## Customer Name Resolution Logic

The exporter tries these fields in order to find customer name:

1. `customer_name` (preferred)
2. `name`
3. `subscriber_name`
4. `display_name`
5. Phone number (if name not found)
6. "unknown_customer" (fallback)

**Filename sanitization:**
- Removes invalid characters: `< > : " / \ | ? *`
- Limits to 200 characters
- Replaces multiple spaces with single space
- Example: `John Doe (Bulk Order)` → `John Doe (Bulk Order).csv`

---

## Output Examples

### Directory Structure
```
customer_chats/
├── EXPORT_SUMMARY.csv (4 KB)
├── Alice Johnson.csv (12.5 KB)
├── Rajesh Kumar.csv (8.3 KB)
├── Priya Sharma.csv (42.1 KB)
├── Amit Singh.csv (15.7 KB)
├── Neha Gupta.csv (9.2 KB)
├── Vikram Patel.csv (18.4 KB)
└── ... (50 more customer files)
```

### Sample Customer CSV
```csv
# Customer: Alice Johnson
# Phone: +91-9876543210
# Total Conversations: 8
# Total Messages: 45
# Export Date: 2024-05-25T14:30:00

timestamp,sender,message_type,message_body,status,conversation_id
2024-05-20T09:15:00Z,+919876543210,text,Hi! Do you have organic turmeric?,delivered,conv_001
2024-05-20T09:16:30Z,+919999999999,text,Hello Alice! Yes we do have organic turmeric in stock,delivered,conv_001
2024-05-20T09:17:45Z,+919876543210,text,Great! What's the price per kg?,delivered,conv_001
2024-05-20T09:18:20Z,+919999999999,text,₹450 per kg. Minimum order: 2 kg,delivered,conv_001
2024-05-20T09:19:00Z,+919876543210,text,Perfect! I'll take 5 kg,delivered,conv_001
2024-05-20T09:19:45Z,+919999999999,text,Wonderful! Your order ID is ORD-123456. Total: ₹2250,delivered,conv_001
2024-05-25T14:20:00Z,+919876543210,text,Hi! Checking order status,delivered,conv_002
2024-05-25T14:21:15Z,+919999999999,text,Your order has been shipped and will arrive by May 28,delivered,conv_002
```

---

## Processing Data After Export

### **1. Open in Excel/Google Sheets**
```bash
# On Mac
open customer_chats/*.csv

# On Linux
libreoffice customer_chats/*.csv &

# On Windows
start customer_chats
```

### **2. Search Across All Files**
```bash
# Find mentions of "return" or "refund"
grep -i "return\|refund" customer_chats/*.csv

# Find messages from specific customer
grep "Alice Johnson" customer_chats/*.csv

# Count total messages
wc -l customer_chats/*.csv
```

### **3. Merge All CSVs into One File**
```bash
# Unix/Mac
head -1 customer_chats/EXPORT_SUMMARY.csv > all_messages.csv
grep -h "^[0-9]" customer_chats/*.csv >> all_messages.csv

# Or use pandas (Python)
python3 << 'EOF'
import pandas as pd
from pathlib import Path
import os

dfs = []
for file in Path("customer_chats").glob("*.csv"):
    if file.name != "EXPORT_SUMMARY.csv":
        df = pd.read_csv(file, comment="#")
        dfs.append(df)

all_data = pd.concat(dfs, ignore_index=True)
all_data.to_csv("all_messages_merged.csv", index=False)
print(f"Merged {len(all_data)} messages")
EOF
```

### **4. Generate Statistics**
```python
import pandas as pd
from pathlib import Path

# Analyze all files
dfs = []
for file in Path("customer_chats").glob("*.csv"):
    if file.name != "EXPORT_SUMMARY.csv":
        df = pd.read_csv(file, comment="#")
        dfs.append(df)

all_data = pd.concat(dfs, ignore_index=True)

print(f"Total messages: {len(all_data)}")
print(f"Unique senders: {all_data['sender'].nunique()}")
print(f"Message types: {all_data['message_type'].value_counts()}")
print(f"Status distribution: {all_data['status'].value_counts()}")
print(f"Date range: {all_data['timestamp'].min()} to {all_data['timestamp'].max()}")
```

---

## Troubleshooting

### **Error: "API request failed"**
- ✗ Check API token is valid
- ✗ Verify phone_number_id is correct
- ✗ Check internet connection

**Solution:**
```bash
python3 wabis_test_export.sh  # Test connection first
```

### **Error: "Empty chats"**
- ✗ May have no messages in Wabis
- ✗ Date range filter may be too restrictive

**Solution:**
```bash
python3 export_chats_by_customer.py --max-chats 10  # Test with small set
```

### **Slow Export**
This is normal - API has rate limiting.
- For 10,000 chats: 15-30 minutes
- For 100,000 chats: 2-4 hours

**To speed up:** Increase batch size in code (modify `--limit`)

### **Special Characters in Filenames**
Some characters like `*`, `?`, `/` are invalid in filenames.
The script automatically removes them.

Example: `John/Sarah` → `JohnSarah.csv`

---

## Column Descriptions

### **timestamp**
ISO 8601 format with timezone (UTC)
```
2024-05-25T10:30:00Z
```

### **sender**
Phone number of who sent the message
```
+919876543210 (customer)
+919999999999 (business/bot)
```

### **message_type**
- `text` - Regular text message
- `image` - Photo/image sent
- `document` - PDF or file
- `audio` - Voice message
- `video` - Video message
- `location` - Location shared
- `template` - WhatsApp template message

### **message_body**
The actual message content. May be empty for:
- Media messages (image, video, audio)
- Location shares
- System messages

### **status**
- `sent` - Delivered to Wabis
- `delivered` - Reached recipient
- `read` - Customer read the message
- `failed` - Failed to deliver

### **conversation_id**
Unique identifier for each conversation thread
```
conv_123abc  or  unique_hash_string
```

---

## Best Practices

✅ **DO:**
- Export to external drive for backup
- Compress with ZIP for storage
- Review EXPORT_SUMMARY.csv first
- Use date ranges for large datasets
- Save with timestamp in filename

❌ **DON'T:**
- Export while actively receiving messages (may miss data)
- Edit CSV files manually (breaks relationships)
- Share raw files with customers
- Store credentials in code
- Run multiple exports simultaneously

---

## Next Steps

1. **Run the export:**
   ```bash
   python3 export_chats_by_customer.py
   ```

2. **Verify output:**
   ```bash
   cat customer_chats/EXPORT_SUMMARY.csv
   ```

3. **Use the data:**
   - Import to CRM
   - Analyze conversations
   - Share with customers (sanitized)
   - Backup in cloud storage
   - Generate reports

4. **Schedule regular exports:**
   ```bash
   # Add to crontab for daily backup
   0 2 * * * cd /path && python3 export_chats_by_customer.py
   ```

---

## Support

**Issue:** Files are created but empty
**Answer:** Check if conversations have messages

**Issue:** Can't find a specific customer
**Answer:** Search EXPORT_SUMMARY.csv for partial name

**Issue:** Timestamp format is different
**Answer:** It's ISO 8601 (2024-05-25T10:30:00Z)

---

## Related Files

- `export_chats_by_customer.py` - Main exporter
- `advanced_export_chats.py` - Advanced features (ZIP, JSON, dates)
- `export_by_customer.sh` - Bash wrapper
- `wabis_test_export.sh` - API connectivity test
