#!/bin/bash
# Export Wabis Chats Grouped by Customer - Quick Start

echo "=================================================="
echo "WABIS CHAT EXPORT BY CUSTOMER (CSV)"
echo "=================================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if requests library is installed
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required packages..."
    pip install requests
fi

echo ""
echo "Starting export of all Wabis conversations..."
echo "This will create a CSV file for each customer."
echo ""

# Run the export
python3 export_chats_by_customer.py --output-dir customer_chats

# Check if successful
if [ -d "customer_chats" ]; then
    echo ""
    echo "✓ Export successful!"
    echo ""
    echo "Output structure:"
    echo "  customer_chats/"
    echo "  ├── EXPORT_SUMMARY.csv      (List of all customers)"
    echo "  ├── Customer_Name_1.csv     (Each customer's conversation)"
    echo "  ├── Customer_Name_2.csv"
    echo "  ├── Customer_Name_3.csv"
    echo "  └── ..."
    echo ""
    echo "View summary:"
    echo "  cat customer_chats/EXPORT_SUMMARY.csv"
    echo ""
    echo "View specific customer chat:"
    echo "  cat customer_chats/Customer_Name.csv"
    echo ""
    
    # Show file count
    FILE_COUNT=$(ls customer_chats/*.csv 2>/dev/null | wc -l)
    echo "Total customer CSV files created: $FILE_COUNT"
else
    echo "❌ Export failed"
    exit 1
fi
