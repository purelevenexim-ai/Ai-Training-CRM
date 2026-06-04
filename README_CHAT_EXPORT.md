# Wabis Chat Export Toolkit - Complete Solution

**Extract all WhatsApp conversations from Wabis for analysis, backup, and AI training**

---

## 🎯 What This Does

Creates **separate CSV files for each customer** containing their complete conversation history.

**Example Output:**
```
customer_chats/
├── EXPORT_SUMMARY.csv (master index)
├── Alice Johnson.csv (45 messages)
├── Rajesh Kumar.csv (23 messages)
├── Priya Sharma.csv (156 messages)
└── 497 more customer files...
```

---

## ⚡ Quick Start (60 Seconds)

### **Method 1: One-Command Execution**
```bash
bash RUN_EXPORT.sh
```

### **Method 2: Direct Python**
```bash
python3 export_chats_by_customer.py
```

### **Method 3: With Advanced Features**
```bash
# Export + compress as ZIP + create JSON backup
python3 advanced_export_chats.py --compress --json
```

---

## 📊 What Gets Exported

| Item | Details |
|------|---------|
| **Files** | One CSV per customer (e.g., `John Doe.csv`) |
| **Format** | Timestamp, Sender, Type, Message Body, Status |
| **Data** | All WhatsApp conversations from Wabis |
| **Index** | `EXPORT_SUMMARY.csv` with all customer names |
| **Size** | 10,000 chats ≈ 50-150 MB |
| **Time** | 10,000 chats ≈ 15-30 minutes |

---

## 📁 File Structure After Export

```
customer_chats/
├── EXPORT_SUMMARY.csv
│   └── Master index: customer name, phone, message count, file name
│
├── Alice Johnson.csv
│   ├── Header with metadata (customer name, phone, date)
│   └── Data: timestamp, sender, message_type, body, status, conversation_id
│
├── Rajesh Kumar.csv
├── Priya Sharma.csv
├── Amit Singh.csv
└── ... (up to thousands of customer files)
```

### **Sample CSV Content:**
```csv
# Customer: Alice Johnson
# Phone: +91-9876543210
# Total Conversations: 8
# Total Messages: 45
# Export Date: 2024-05-25T14:30:00

timestamp,sender,message_type,message_body,status,conversation_id
2024-05-20T09:15:00Z,+919876543210,text,Hi! Do you have organic turmeric?,delivered,conv_001
2024-05-20T09:16:30Z,+919999999999,text,Hello Alice! Yes we do have organic turmeric in stock,delivered,conv_001
2024-05-20T09:17:45Z,+919876543210,text,What's the price per kg?,delivered,conv_001
2024-05-20T09:18:20Z,+919999999999,text,₹450 per kg. Minimum order: 2 kg,delivered,conv_001
```

---

## 🛠️ Available Scripts

### **Main Export Scripts**

| Script | Purpose | Output | Best For |
|--------|---------|--------|----------|
| `export_chats_by_customer.py` | Standard customer export | Individual CSVs | Default choice |
| `advanced_export_chats.py` | Advanced features | CSVs + ZIP + JSON | Backups + analytics |
| `RUN_EXPORT.sh` | One-command wrapper | CSVs | Quick execution |

### **Bulk Export Scripts** (For AI Training)

| Script | Purpose | Output | Best For |
|--------|---------|--------|----------|
| `wabis_chat_exporter.py` | Bulk format export | JSONL, SQLite, CSV, JSON | LLM fine-tuning |
| `preprocess_for_training.py` | Format converter | Platform-specific formats | OpenAI, Anthropic, HF |

### **Testing & Utilities**

| Script | Purpose | Output | Best For |
|--------|---------|--------|----------|
| `wabis_test_export.sh` | API connectivity test | JSON response sample | Debugging |
| `export_by_customer.sh` | Bash wrapper | CSVs | Shell preference |

### **Documentation**

| File | Content |
|------|---------|
| `CUSTOMER_CSV_EXPORT_GUIDE.md` | Detailed guide for customer CSV export |
| `WABIS_CHAT_EXPORT_GUIDE.md` | Guide for bulk export (AI training) |

---

## 🚀 Usage Scenarios

### **Scenario 1: I need each customer's chat history**
```bash
python3 export_chats_by_customer.py
# Creates: customer_chats/*.csv
```

### **Scenario 2: I need to backup everything as ZIP**
```bash
python3 advanced_export_chats.py --compress
# Creates: customer_chats_TIMESTAMP.zip
```

### **Scenario 3: I want to train an AI model**
```bash
python3 wabis_chat_exporter.py
python3 preprocess_for_training.py --format openai --input wabis_export/wabis_chats.jsonl
# Creates: training_data/openai_format.jsonl (ready for OpenAI fine-tuning)
```

### **Scenario 4: I need conversations from a specific date range**
```bash
python3 advanced_export_chats.py --from-date 2024-01-01 --to-date 2024-12-31
# Exports only chats from that period
```

### **Scenario 5: I want to search across all chats**
```bash
# After export:
grep -i "return\|refund" customer_chats/*.csv
# Shows all chats mentioning "return" or "refund"
```

---

## 📋 CSV Columns Explained

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| **timestamp** | DateTime | `2024-05-25T10:30:00Z` | When message was sent (ISO 8601) |
| **sender** | String | `+919876543210` | Phone number of sender |
| **message_type** | String | `text` | Type: text, image, document, video, audio, location, template |
| **message_body** | Text | `Hello, I want...` | Actual message content (may be empty for media) |
| **status** | String | `delivered` | Status: sent, delivered, read, failed |
| **conversation_id** | String | `conv_xyz123` | Unique conversation identifier |

---

## ⚙️ Configuration

All scripts use pre-configured credentials:
```
API Token: 18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95
Phone ID:  252036884661683
Base URL:  https://bot.wabis.in/api/v1
```

**To modify:** Edit the `API_TOKEN` and `PHONE_NUMBER_ID` variables in any script.

---

## ✅ Pre-requisites

- Python 3.6+
- `requests` library (auto-installs if missing)
- Internet connection
- Wabis API access

---

## 📈 Expected Results

### **For 10,000 Conversations:**
- **Customer files created:** 200-500 CSV files
- **Total messages:** 50,000-100,000
- **Total size:** 50-150 MB
- **Time to export:** 15-30 minutes
- **Messages per customer:** 50-500 (average 100-150)

### **Storage Requirements:**
- RAM: Minimal (streams data)
- Disk: ~500 MB for 10,000 chats
- Bandwidth: ~100 MB download

---

## 🔍 Post-Export Actions

### **1. View Summary**
```bash
cat customer_chats/EXPORT_SUMMARY.csv
```

### **2. Open in Excel/Google Sheets**
```bash
# Mac
open customer_chats/

# Windows
start customer_chats

# Linux
libreoffice customer_chats/
```

### **3. Search Across All Files**
```bash
# Find specific customer
grep "Alice Johnson" customer_chats/*.csv

# Find messages mentioning "order"
grep -i "order" customer_chats/*.csv | head -20

# Count total messages
wc -l customer_chats/*.csv
```

### **4. Generate Statistics (Python)**
```python
import pandas as pd
from pathlib import Path

dfs = [pd.read_csv(f, comment="#") for f in Path("customer_chats").glob("*.csv") if f.name != "EXPORT_SUMMARY.csv"]
all_data = pd.concat(dfs, ignore_index=True)

print(f"Total messages: {len(all_data)}")
print(f"Date range: {all_data['timestamp'].min()} to {all_data['timestamp'].max()}")
print(f"Message types: {all_data['message_type'].value_counts()}")
print(f"Status distribution: {all_data['status'].value_counts()}")
```

### **5. Merge All CSVs (Python)**
```python
import pandas as pd
from pathlib import Path

dfs = []
for file in Path("customer_chats").glob("*.csv"):
    if file.name != "EXPORT_SUMMARY.csv":
        dfs.append(pd.read_csv(file, comment="#"))

all_data = pd.concat(dfs, ignore_index=True)
all_data.to_csv("all_chats_combined.csv", index=False)
print(f"Created all_chats_combined.csv with {len(all_data)} messages")
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "ModuleNotFoundError: No module named 'requests'" | `pip install requests` |
| "API request failed" | Run `bash wabis_test_export.sh` to debug |
| "Empty chats" | Verify Wabis has messages, check date filters |
| "Slow export" | Normal - API rate limiting, takes 15-30 min for 10k |
| "Special characters in filenames" | Script auto-sanitizes, e.g., `John/Doe` → `JohnDoe` |

---

## 📚 Documentation Files

- **CUSTOMER_CSV_EXPORT_GUIDE.md** - Detailed guide for customer CSV export
- **WABIS_CHAT_EXPORT_GUIDE.md** - Guide for AI training data export
- **This file (README)** - Quick reference and overview

---

## 🔐 Security Notes

⚠️ **Important:**
- Store export files securely
- Don't commit credentials to git
- Consider encrypting sensitive data
- Set file permissions appropriately:
  ```bash
  chmod 600 customer_chats/*.csv
  ```

---

## 📞 Support

**Issue:** Files are created but empty
- Check if Wabis has messages
- Verify API token and phone ID

**Issue:** Export is very slow
- Normal for large datasets (10K+ chats)
- Takes 15-30 minutes, can take longer depending on data size

**Issue:** Can't find a customer
- Check EXPORT_SUMMARY.csv for correct name
- Filenames are sanitized (special chars removed)

---

## 🎓 Examples

### **Example 1: Export and search for order-related chats**
```bash
# Export
python3 export_chats_by_customer.py

# Find customers mentioning orders
grep -l "order" customer_chats/*.csv

# Get order-related messages
grep "order" customer_chats/*.csv | cut -d: -f2- | column -t -s,
```

### **Example 2: Generate customer engagement report**
```python
import pandas as pd
from pathlib import Path

# Load all data
dfs = []
for f in Path("customer_chats").glob("*.csv"):
    if f.name != "EXPORT_SUMMARY.csv":
        customer = f.stem
        df = pd.read_csv(f, comment="#")
        df['customer'] = customer
        dfs.append(df)

all_data = pd.concat(dfs, ignore_index=True)

# Top engaged customers
print("Top 10 customers by message count:")
print(all_data['customer'].value_counts().head(10))

# Messages by type
print("\nMessage types:")
print(all_data['message_type'].value_counts())
```

### **Example 3: Create daily conversation export**
```bash
# Schedule with cron (daily at 2 AM)
# 0 2 * * * cd /path/to/pureleven_dev && python3 export_chats_by_customer.py --output-dir "customer_chats_$(date +\%Y-\%m-\%d)"
```

---

## 📊 Output Size Reference

| Chats | Customers | Messages | Size |
|-------|-----------|----------|------|
| 100 | 10-20 | 500-1,000 | 1-2 MB |
| 1,000 | 100-200 | 5,000-10,000 | 10-20 MB |
| 10,000 | 500-1,000 | 50,000-100,000 | 50-150 MB |
| 100,000 | 2,000-5,000 | 500,000-1,000,000 | 500 MB - 1.5 GB |

---

## ✨ Features

✅ Separate CSV file per customer
✅ Auto-sanitizes customer names for filenames
✅ Handles special characters and emojis
✅ Rate limiting for API compliance
✅ Error handling and recovery
✅ Summary report generation
✅ Optional compression (ZIP)
✅ Optional JSON export
✅ Date range filtering (advanced)
✅ Streaming data processing (memory efficient)

---

## 🚀 Next Steps

1. **Quick start:**
   ```bash
   bash RUN_EXPORT.sh
   ```

2. **Monitor progress:**
   ```bash
   watch -n 2 'ls -1 customer_chats/*.csv | wc -l'  # See file count growing
   ```

3. **Analyze results:**
   ```bash
   cat customer_chats/EXPORT_SUMMARY.csv | column -t -s,
   ```

4. **Create backup:**
   ```bash
   python3 advanced_export_chats.py --compress
   zip -r customer_chats_backup.zip customer_chats/
   ```

5. **Use for analytics or AI training:**
   - Import CSVs to your CRM
   - Analyze customer interactions
   - Train chatbots with conversation data
   - Generate reports

---

**Happy exporting! 🎉**

Created: May 2026
Location: `/Users/bthomas/Documents/pureleven_dev/`
