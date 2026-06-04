#!/bin/bash
# QUICK START: Fetch 10,000 Wabis Chats for AI Training

echo "=================================================="
echo "WABIS CHAT EXPORT - QUICK START GUIDE"
echo "=================================================="

# ========== STEP 1: Setup ==========
echo -e "\n[STEP 1] Installing dependencies..."
pip install requests fastapi uvicorn

# ========== STEP 2: Test Connection ==========
echo -e "\n[STEP 2] Testing Wabis API connection..."
chmod +x wabis_test_export.sh
./wabis_test_export.sh

# ========== STEP 3: Export Chats ==========
echo -e "\n[STEP 3] Exporting 10,000 chats from Wabis..."
python3 wabis_chat_exporter.py

# This will create:
# ├── wabis_export/
# │   ├── wabis_chats.jsonl    ← For AI training
# │   ├── wabis_chats.db       ← For analysis
# │   ├── wabis_chats.csv      ← For spreadsheets
# │   └── wabis_chats.json     ← Full backup

# ========== STEP 4: Preprocess for Your AI Platform ==========
echo -e "\n[STEP 4] Preprocessing for AI training..."

# For OpenAI fine-tuning:
python3 preprocess_for_training.py --format openai --input wabis_export/wabis_chats.jsonl

# For Anthropic Claude:
python3 preprocess_for_training.py --format anthropic --input wabis_export/wabis_chats.jsonl

# For HuggingFace:
python3 preprocess_for_training.py --format huggingface --input wabis_export/wabis_chats.jsonl

# For all formats at once:
python3 preprocess_for_training.py --format all --input wabis_export/wabis_chats.jsonl --output-dir training_data

# ========== STEP 5: Validate Data Quality ==========
echo -e "\n[STEP 5] Validating data quality..."
python3 preprocess_for_training.py --validate --input wabis_export/wabis_chats.jsonl

# ========== STEP 6: Upload to Your AI Platform ==========
echo -e "\n[STEP 6] Upload to AI platform..."
echo ""
echo "OpenAI:"
echo "  openai api fine_tunes.create -t training_data/openai_format.jsonl"
echo ""
echo "Anthropic:"
echo "  Upload training_data/anthropic_format.jsonl via dashboard"
echo ""
echo "HuggingFace:"
echo "  Use training_data/huggingface_format.jsonl with transformers library"
echo ""

echo "=================================================="
echo "EXPORT COMPLETE!"
echo "=================================================="
