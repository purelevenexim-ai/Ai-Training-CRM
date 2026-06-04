# Wabis Chat Export for AI Training

Complete guide to fetch 10,000+ chat conversations from Wabis for AI model training.

## Quick Start

### Option 1: Bulk API Export (Fastest for Historical Data)

```bash
# 1. Install dependencies
pip install requests

# 2. Set your credentials in wabis_chat_exporter.py
API_TOKEN="your_token_here"
PHONE_NUMBER_ID="your_phone_id_here"

# 3. Run exporter
python3 wabis_chat_exporter.py

# Output files created:
# ├── wabis_chats.json       # Full nested structure
# ├── wabis_chats.csv        # Flattened for spreadsheets
# ├── wabis_chats.jsonl      # For LLM fine-tuning (1 line per conversation)
# └── wabis_chats.db         # SQLite database (queryable)
```

## Detailed Approaches

### **Approach 1: Bulk Export via API (RECOMMENDED)**

**Best for:** Initial 10,000 chat export

**File:** `wabis_chat_exporter.py`

**How it works:**
1. Authenticates with Wabis API
2. Paginates through `/whatsapp/chats` endpoint (100 items per request)
3. Exports to 4 formats simultaneously

**Formats:**
- **JSONL** - One JSON object per line (best for ML training)
- **SQLite** - Queryable database (best for analysis)
- **CSV** - Spreadsheet format (best for Excel)
- **JSON** - Raw nested structure

**Usage:**
```bash
python3 wabis_chat_exporter.py
```

**Configuration:**
```python
API_TOKEN = "18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
PHONE_NUMBER_ID = "252036884661683"
MAX_CHATS = 10000
```

**Expected output for 10,000 chats:**
- JSONL: ~50-200 MB (depending on message length)
- SQLite: ~30-100 MB
- CSV: ~40-150 MB

---

### **Approach 2: Quick Test with cURL**

**File:** `wabis_test_export.sh`

**How it works:**
1. Tests API connection
2. Verifies pagination works
3. Shows response structure

**Usage:**
```bash
chmod +x wabis_test_export.sh
./wabis_test_export.sh
```

**Manual cURL command:**
```bash
API_TOKEN="18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95"
PHONE_NUMBER_ID="252036884661683"

# Fetch first 100 chats
curl -s -X GET \
  "https://bot.wabis.in/api/v1/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=100&offset=0" \
  -H "Authorization: Bearer ${API_TOKEN}" | jq '.' > chats_page_0.json

# Fetch with offset (pagination)
curl -s -X GET \
  "https://bot.wabis.in/api/v1/whatsapp/chats?apiToken=${API_TOKEN}&phone_number_id=${PHONE_NUMBER_ID}&limit=100&offset=100" \
  -H "Authorization: Bearer ${API_TOKEN}" | jq '.' > chats_page_1.json
```

---

### **Approach 3: Webhook Streaming (For Continuous Ingestion)**

**File:** `wabis_webhook_receiver.py`

**Best for:** Ongoing chat capture while maintaining backlog

**How it works:**
1. Runs FastAPI server listening for webhooks
2. Captures messages as they arrive
3. Stores in SQLite database
4. Can export JSONL on demand

**Setup:**

```bash
# 1. Install dependencies
pip install fastapi uvicorn

# 2. Start webhook receiver
python3 wabis_webhook_receiver.py
# Server runs on http://localhost:8000

# 3. In Wabis Dashboard:
#    - Go to Webhook Workflow
#    - Create new workflow
#    - URL: https://your-domain.com:8000/webhook/wabis
#    - Test with sample message

# 4. Check stats
curl http://localhost:8000/stats

# 5. Export when ready
curl http://localhost:8000/export/jsonl > training_data.jsonl
```

**For production (with tunneling):**
```bash
# Using ngrok to expose local server
ngrok http 8000
# Use provided URL in Wabis webhook config
```

---

## API Endpoints Reference

### Get Chats (Bulk)
```
GET /whatsapp/chats
Parameters:
  - apiToken: Your API token
  - phone_number_id: Your WhatsApp phone ID
  - limit: 1-100 (default 100)
  - offset: pagination offset
  
Response:
[
  {
    "id": "conv_123",
    "phone_number": "+91XXXXXXXXXX",
    "messages": [
      {
        "id": "msg_123",
        "sender": "+91XXXXXXXXXX",
        "body": "Hello",
        "timestamp": "2024-05-25T10:30:00Z",
        "status": "delivered"
      }
    ],
    "created_at": "2024-05-20T10:00:00Z"
  }
]
```

### Get Inbox (Alternative)
```
GET /whatsapp/inbox
Parameters:
  - apiToken: Your API token
  - limit: pagination limit
  - offset: pagination offset
  
Useful if /chats endpoint structure differs
```

---

## Data Formats Explained

### JSONL (For LLM Fine-tuning)
```jsonl
{"conversation_id": "conv_1", "messages": [{"timestamp": "...", "sender": "+91...", "content": "Hi"}], "metadata": {...}}
{"conversation_id": "conv_2", "messages": [{"timestamp": "...", "sender": "+91...", "content": "Hello"}], "metadata": {...}}
```

**Why JSONL?**
- One conversation per line (streaming-friendly)
- Exact format needed by OpenAI, Anthropic, etc.
- Memory efficient for large datasets
- Easy to filter/preprocess

### SQLite (For Analysis)
```sql
-- Query all messages from a customer
SELECT * FROM messages WHERE conversation_id = 'conv_123';

-- Find conversations with >10 messages
SELECT conversation_id, COUNT(*) as count 
FROM messages 
GROUP BY conversation_id 
HAVING COUNT(*) > 10;

-- Messages by date
SELECT DATE(timestamp), COUNT(*) 
FROM messages 
GROUP BY DATE(timestamp);
```

### CSV (For Spreadsheets)
```csv
timestamp,sender,recipient,message_type,body,status,conversation_id
2024-05-25T10:30:00Z,+918075930331,+919876543210,text,Hello there,delivered,conv_123
```

---

## Processing Data for AI Training

### 1. Preprocess JSONL

```python
import json
import re

# Clean and format messages
with open('wabis_chats.jsonl') as f:
    for line in f:
        conv = json.loads(line)
        
        # Extract user-bot pairs
        messages = conv['messages']
        for i in range(len(messages)-1):
            user_msg = messages[i]
            bot_msg = messages[i+1]
            
            # Save as training pair
            print({
                "input": clean_text(user_msg['content']),
                "output": clean_text(bot_msg['content'])
            })

def clean_text(text):
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special chars
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower()
```

### 2. Filter by Quality

```python
# Remove very short messages
conversations = [c for c in conversations if all(len(m['content']) > 3 for m in c['messages'])]

# Remove conversations with spam keywords
spam_keywords = ['unsubscribe', 'click here', 'limited time']
conversations = [c for c in conversations 
                 if not any(keyword in m['content'].lower() 
                           for m in c['messages'] 
                           for keyword in spam_keywords)]
```

### 3. Split for Training/Testing

```python
import random

# 80/20 split
random.shuffle(conversations)
split = int(len(conversations) * 0.8)

train_data = conversations[:split]
test_data = conversations[split:]

# Save in JSONL format
with open('train.jsonl', 'w') as f:
    for conv in train_data:
        f.write(json.dumps(conv) + '\n')

with open('test.jsonl', 'w') as f:
    for conv in test_data:
        f.write(json.dumps(conv) + '\n')
```

---

## Troubleshooting

### Error: "API connection failed"
- Check token is valid: `echo $API_TOKEN`
- Verify phone_number_id is correct
- Check internet connection
- Ensure Wabis account is active

### Error: "Empty chats"
- Verify you have messages in Wabis
- Check timestamp range (may need to query from specific date)
- Try `/inbox` endpoint instead

### Slow Export
- This is normal for 10,000 chats (can take 10-30 minutes)
- Each API call takes 0.5s (rate limiting)
- You can modify `time.sleep(0.5)` to `time.sleep(0.1)` if Wabis allows

### Need Specific Date Range?
Modify exporter to add date filters:
```python
params = {
    "limit": 100,
    "offset": offset,
    "apiToken": self.api_token,
    "from_date": "2024-01-01",  # Add if API supports
    "to_date": "2024-05-31"
}
```

---

## Next Steps for AI Training

1. **Choose format:**
   - Use JSONL for OpenAI/Anthropic fine-tuning
   - Use SQLite for preprocessing and analysis

2. **Clean data:**
   - Remove duplicates, spam, gibberish
   - Anonymize personal information
   - Standardize timestamps

3. **Split data:**
   - 80% training, 20% validation
   - Balance conversation types if possible

4. **Upload to platform:**
   - OpenAI: `openai api fine_tunes.create -t train.jsonl`
   - Anthropic: Upload via dashboard
   - Local: Use for Hugging Face transformers

---

## Files Summary

| File | Purpose | Format |
|------|---------|--------|
| `wabis_chat_exporter.py` | Main bulk exporter | Python |
| `wabis_test_export.sh` | Quick API test | Bash |
| `wabis_webhook_receiver.py` | Streaming receiver | FastAPI |
| `wabis_chats.jsonl` | AI training data | JSONL |
| `wabis_chats.db` | Queryable database | SQLite |

---

## Support

- **Wabis API Issues:** Check `wabis_test_export.sh` output
- **Export Errors:** Run with `--verbose` (add to exporter)
- **Database Issues:** Ensure disk space for 10,000 chats
