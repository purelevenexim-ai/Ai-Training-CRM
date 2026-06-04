================================================================================
WABIS AI CHATBOT TRAINING — MANUAL UPLOAD GUIDE
Generated: 2026-05-26
================================================================================

SITUATION
─────────
The cleaned and deduplicated training data has been prepared in JSON format
(546 Q&A pairs extracted from 41 intent×product categories). However:
  ✓ Training data file prepared: CHATBOT_TRAINING_DATA_CLEANED.json
  ✓ Formatted for API: 546 question-answer pairs ready
  ✗ Wabis API endpoints: Not responding to direct requests
  ✗ Browser UI: Cloudflare session validation required
  → Manual upload through UI is the recommended path forward

================================================================================
STEP 1 — LOG IN TO WABIS
================================================================================

1. Open browser and navigate to: https://bot.wabis.in/
2. Log in with your Wabis account credentials
3. If prompted with Cloudflare security check, wait for it to complete
   (may take 30-60 seconds)
4. Once logged in, you should see the dashboard/inbox view


================================================================================
STEP 2 — NAVIGATE TO SETTINGS
================================================================================

1. Look for a SETTINGS or ⚙️ icon in the top navigation bar
   (usually top-right corner)
2. Click on Settings
3. You should see a menu with options like:
   - Account
   - Team
   - Integrations
   - **AI & Knowledge Base** ← This is what we need
   - Billing
   - etc.


================================================================================
STEP 3 — ACCESS AI & KNOWLEDGE BASE
================================================================================

1. Click on "AI & Knowledge Base" section
2. You should see subsections like:
   - Knowledge Base
   - AI Training
   - AI Settings
   - Model Status
   
Look for an option labeled "Knowledge Base" or "AI Training"


================================================================================
STEP 4 — UPLOAD TRAINING DATA
================================================================================

Option A: If there's an "Import" or "Upload" button:
──────────────────────────────────────────────────────
1. Click the "Import" / "Upload" / "Add Training Data" button
2. Select format: JSON or CSV (if JSON is available, use that)
3. Browse to and select:
   📄 File: /Users/bthomas/Documents/pureleven_dev/WABIS_AI_TRAINING_FORMATTED.json
   📄 Location: Keep for CSV: /Users/bthomas/Documents/pureleven_dev/WABIS_AI_TRAINING_FORMATTED.csv
4. Click "Upload" and wait for processing
5. You should see a confirmation message

Option B: If there's a "Add FAQ" / "Add Q&A" button:
────────────────────────────────────────────────────
1. The platform may require adding training data manually or in bulk
2. Look for a bulk import option
3. Try uploading as CSV format
4. The CSV should have columns: question | answer | category

Option C: If there's a "Connect Data Source" option:
───────────────────────────────────────────────────
1. This might allow you to connect to external knowledge sources
2. You may be able to paste the JSON or upload the file directly


================================================================================
STEP 5 — TRIGGER AI MODEL TRAINING
================================================================================

After uploading the training data:

1. Look for a button labeled:
   - "Train Model"
   - "Start Training"
   - "Train AI"
   - "Process Data"

2. Click it to start the training process
3. The system will show:
   - Training progress (may take 5-30 minutes depending on data size)
   - Status updates
   - Completion confirmation

4. Monitor the "Model Status" section to see:
   - Training % complete
   - Last trained date
   - Model version


================================================================================
STEP 6 — VERIFY TRAINING STATUS
================================================================================

After training completes:

1. Return to Settings > AI & Knowledge Base
2. Look for "Model Status" or "Training Status" section
3. Verify:
   ✓ Model state: "Active" or "Ready"
   ✓ Last trained: Recent timestamp
   ✓ Training data count: Should show 546+ Q&A pairs (or similar)
   ✓ Model version: Should be incremented


================================================================================
TRAINING DATA SUMMARY
================================================================================

File: CHATBOT_TRAINING_DATA_CLEANED.json
Location: /Users/bthomas/Documents/pureleven_dev/

Content Overview:
  ✓ Total entries: 41 intent×product categories
  ✓ Q&A pairs: 546 (including original + variations)
  ✓ Languages: English + Malayalam
  ✓ Categories: price_check, delivery_query, order_placement, payment_query,
                complaint, product_inquiry, wholesale_inquiry, other
  ✓ Products: cardamom, cinnamon, pepper, clove, turmeric, combo, general

Sample Q&A pairs prepared:
  • "What's the price of cardamom?" → "100g ₹460+₹40, 200g ₹840 free..."
  • "Delivery time?" → "Dispatch 1-2 days, delivery 3-7 days..."
  • "How to order?" → [Complete order collection flow...]
  • "Wholesale rates?" → [Wholesale inquiry response...]
  • "Payment options?" → [Payment details with GPay/Bank/COD...]
  • "My order didn't arrive" → [Complaint handling response...]
  • And 540+ more Q&A pairs...

All data is bilingual (English + Malayalam script) and based on 10,000+ real
customer conversations from your WhatsApp chats.


================================================================================
FORMAT REFERENCE
================================================================================

The training data follows this JSON structure:

{
  "training_data": [
    {
      "question": "Customer's question",
      "answer": "Ideal response",
      "category": "price_check|delivery_query|order_placement|...",
      "product": "cardamom|cinnamon|pepper|clove|turmeric|combo|general",
      "language": "english|malayalam"
    },
    ...
  ],
  "model_type": "chatbot",
  "language": "en-ml",  // English + Malayalam
  "auto_train": true
}

If Wabis requires CSV format instead, use:
  Column 1: question
  Column 2: answer
  Column 3: category
  Column 4: product (optional)


================================================================================
TROUBLESHOOTING
================================================================================

❌ "Cannot find AI & Knowledge Base section"
   → Try clicking on different tabs in Settings
   → It might be under "Bot Settings" or "Advanced"
   → Or under a "Integrations" > "AI" submenu

❌ "Upload button doesn't work"
   → Try dragging and dropping the JSON file into the upload area
   → Or try uploading as CSV format instead
   → Make sure file size is reasonable (should be <10MB)

❌ "Training takes too long"
   → Large datasets (546 pairs) may take 15-30 minutes
   → Do not refresh the page or navigate away
   → Check back in 30 minutes to see if completed

❌ "No model improvement after training"
   → Verify that the training data was actually uploaded
   → Check model version number to ensure it changed
   → Try making a test query through the chatbot to see if it responds
   → Contact Wabis support if issue persists

❌ "Session expired / Cloudflare challenge keeps appearing"
   → Try logging out completely and logging in fresh
   → Clear browser cookies for bot.wabis.in
   → Try a different browser if possible
   → Wait 5-10 minutes and try again (rate limiting)


================================================================================
NEXT STEPS AFTER TRAINING
================================================================================

Once AI training is complete:

1. ✓ Test the bot with sample questions:
   - "What's the price of cardamom?"
   - "Can you help me place an order?"
   - "What's your delivery time?"
   - "എലക്ക വില?" (Malayalam: "What's the cardamom price?")

2. ✓ Monitor bot performance:
   - Track customer satisfaction
   - Review unanswered/unclear responses
   - Collect feedback from conversations

3. ✓ Iterate and improve:
   - Add more training data based on new conversations
   - Refine responses that customers complain about
   - Re-train model monthly with fresh data

4. ✓ Integrate with campaigns:
   - Use trained bot in automated flows
   - Deploy to FAQ channels
   - Use for customer support routing


================================================================================
SUPPORT & RESOURCES
================================================================================

Wabis Support:
  • Documentation: https://docs.wabis.com
  • Help: https://help.wabis.com
  • Support Email: support@wabis.in

Files prepared in /Users/bthomas/Documents/pureleven_dev/:
  • CHATBOT_TRAINING_DATA_CLEANED.json ← Main training data
  • PURELEVEN_CHATBOT_SYSTEM_PROMPT.txt ← System prompt for bot
  • wabis_ai_train.py ← Python script (for API attempts)

Contact: Basil Thomas (Owner, PureLeven Exim)
  • Phone: 8848265849
  • Email: basil@pureleven.com

================================================================================
