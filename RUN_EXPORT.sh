#!/bin/bash
# One-Command Export: All Customer Chats to Separate CSV Files

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   WABIS CUSTOMER CHAT EXPORT - INSTANT EXECUTION              ║"
echo "║   Each customer gets their own CSV file                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure we're in the right directory
if [ ! -f "export_chats_by_customer.py" ]; then
    echo -e "${YELLOW}⚠ Script not found. Please run from pureleven_dev directory${NC}"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠ Python 3 not found. Installing...${NC}"
    exit 1
fi

# Check requests library
python3 -c "import requests" 2>/dev/null || {
    echo -e "${BLUE}📦 Installing requests library...${NC}"
    pip install requests > /dev/null 2>&1
}

# Step 1: Run export
echo -e "${BLUE}[1/5] Exporting conversations from Wabis...${NC}"
echo "     (This may take 10-30 minutes for 10,000+ chats)"
echo ""

python3 export_chats_by_customer.py

# Step 2: Show results
echo ""
echo -e "${GREEN}[2/5] Export Complete!${NC}"
echo ""

if [ -d "customer_chats" ]; then
    FILE_COUNT=$(find customer_chats -maxdepth 1 -name "*.csv" -type f ! -name "EXPORT_SUMMARY.csv" | wc -l)
    TOTAL_SIZE=$(du -sh customer_chats | cut -f1)
    
    echo -e "${GREEN}✓ Customer CSV files created: $FILE_COUNT${NC}"
    echo -e "${GREEN}✓ Total size: $TOTAL_SIZE${NC}"
    echo ""
    
    # Step 3: Show summary
    echo -e "${BLUE}[3/5] Summary of exported customers:${NC}"
    echo ""
    head -20 customer_chats/EXPORT_SUMMARY.csv | column -t -s',' | sed 's/^/    /'
    
    SUMMARY_LINES=$(wc -l < customer_chats/EXPORT_SUMMARY.csv)
    if [ $SUMMARY_LINES -gt 21 ]; then
        REMAINING=$((SUMMARY_LINES - 21))
        echo "    ... and $REMAINING more customers"
    fi
    
    echo ""
    echo -e "${BLUE}[4/5] Sample customer file:${NC}"
    FIRST_CUSTOMER=$(ls customer_chats/*.csv | grep -v EXPORT_SUMMARY | head -1)
    if [ -f "$FIRST_CUSTOMER" ]; then
        echo "    File: $(basename $FIRST_CUSTOMER)"
        head -5 "$FIRST_CUSTOMER" | sed 's/^/    /'
        TOTAL_LINES=$(wc -l < "$FIRST_CUSTOMER")
        echo "    ... ($((TOTAL_LINES - 6)) more rows)"
    fi
    
    echo ""
    echo -e "${GREEN}[5/5] Next Steps:${NC}"
    echo ""
    echo -e "  ${GREEN}✓ View all customers:${NC}"
    echo "    $ cat customer_chats/EXPORT_SUMMARY.csv"
    echo ""
    echo -e "  ${GREEN}✓ View specific customer:${NC}"
    echo "    $ cat customer_chats/Customer_Name.csv"
    echo ""
    echo -e "  ${GREEN}✓ List all customer files:${NC}"
    echo "    $ ls -lh customer_chats/"
    echo ""
    echo -e "  ${GREEN}✓ Search for a phrase across all chats:${NC}"
    echo "    $ grep -i 'keyword' customer_chats/*.csv"
    echo ""
    echo -e "  ${GREEN}✓ Import to Excel/Sheets:${NC}"
    echo "    $ open customer_chats/  # On Mac"
    echo ""
    echo -e "  ${GREEN}✓ Advanced: Compress all files:${NC}"
    echo "    $ python3 advanced_export_chats.py --compress"
    echo ""
    
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo -e "${GREEN}🎉 EXPORT SUCCESSFUL!${NC}"
    echo ""
    echo "Location: $(pwd)/customer_chats/"
    echo "Files: $FILE_COUNT customers"
    echo ""
    
else
    echo -e "${YELLOW}⚠ Output directory not created${NC}"
    exit 1
fi
