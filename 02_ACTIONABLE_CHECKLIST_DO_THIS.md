# ☑️ ACTIONABLE CHECKLIST - DO THIS NOW

**Date**: May 17, 2026  
**Session**: Live Testing Activation  
**Time Required**: 45-60 minutes total  
**Goal**: Get real customer orders flowing into the CRM

---

## 🎯 PART 1: WEBHOOK REGISTRATION (15 minutes)

### Step 1: Go to Shopify Admin
- [ ] Open: https://admin.shopify.com
- [ ] Make sure you're logged into the Pureleven store
- [ ] Store URL should be: admin.shopify.com/store/rwxtic-gz

### Step 2: Navigate to Webhooks
- [ ] Click: Settings (bottom left)
- [ ] Click: Notifications
- [ ] Scroll down to: Webhooks section

### Step 3: Create Webhook #1 (Customer Created)
- [ ] Click: "Create webhook" button
- [ ] Event: Select "customer created"
- [ ] Endpoint: `https://track.pureleven.com/api/crm/webhooks/shopify`
- [ ] Format: JSON
- [ ] Click: "Save"
- [ ] Verify: Shows ✅ Active (green status)

### Step 4: Create Webhook #2 (Customer Updated)
- [ ] Click: "Create webhook" button
- [ ] Event: Select "customer updated"
- [ ] Endpoint: `https://track.pureleven.com/api/crm/webhooks/shopify`
- [ ] Format: JSON
- [ ] Click: "Save"
- [ ] Verify: Shows ✅ Active

### Step 5: Create Webhook #3 (Order Created)
- [ ] Click: "Create webhook" button
- [ ] Event: Select "order created"
- [ ] Endpoint: `https://track.pureleven.com/api/crm/webhooks/shopify`
- [ ] Format: JSON
- [ ] Click: "Save"
- [ ] Verify: Shows ✅ Active

### Step 6: Create Webhook #4 (Order Paid)
- [ ] Click: "Create webhook" button
- [ ] Event: Select "order paid"
- [ ] Endpoint: `https://track.pureleven.com/api/crm/webhooks/shopify`
- [ ] Format: JSON
- [ ] Click: "Save"
- [ ] Verify: Shows ✅ Active

### Step 7: Create Webhook #5 (Checkout Abandoned)
- [ ] Click: "Create webhook" button
- [ ] Event: Select "checkout abandoned"
- [ ] Endpoint: `https://track.pureleven.com/api/crm/webhooks/shopify`
- [ ] Format: JSON
- [ ] Click: "Save"
- [ ] Verify: Shows ✅ Active

### Step 8: Final Verification
- [ ] List all 5 webhooks should show:
  - ✅ customer created → Active
  - ✅ customer updated → Active
  - ✅ order created → Active
  - ✅ order paid → Active
  - ✅ checkout abandoned → Active

**Status**: ✅ All webhooks registered and active

---

## 🎯 PART 2: PREPARATION FOR TESTING (5 minutes)

### Step 1: Prepare Monitoring (Terminal 1)
- [ ] Open Terminal/SSH
- [ ] Run: `ssh root@192.46.213.140`
- [ ] Enter password: `QazPlm123!@#`
- [ ] Run: `docker logs -f pureleven-ai-engine`
- [ ] Keep this window open - you'll watch for webhook calls here

### Step 2: Prepare Database Query (Terminal 2)
- [ ] Open another Terminal/SSH window
- [ ] Run: `ssh root@192.46.213.140`
- [ ] Run: `docker exec -it pureleven-postgres psql -U pureleven -d pureleven`
- [ ] Keep this ready - you'll query after placing order

### Step 3: Open Dashboard
- [ ] Open browser tab: https://ai.pureleven.com/static/dashboard.html
- [ ] Refresh page
- [ ] Keep open to watch for customer appearing

### Step 4: Open Pureleven Store
- [ ] Open another browser tab: https://pureleven.com
- [ ] Ready to place test order

**Status**: ✅ All windows and tabs ready

---

## 🎯 PART 3: TEST SCENARIO #1 - BASIC ORDER (15 minutes)

### Step 1: Add Product to Cart
- [ ] On pureleven.com
- [ ] Find product: "Kerala Cardamom" (₹449)
- [ ] Click: "Add +"
- [ ] Verify: Cart count increased

### Step 2: Proceed to Checkout
- [ ] Click: Cart icon (top right)
- [ ] Click: "Proceed to Checkout"
- [ ] Continue to checkout page

### Step 3: Enter Customer Details
- [ ] First Name: `Test`
- [ ] Last Name: `Customer1`
- [ ] Email: `testing-scenario1@example.com`
- [ ] Phone: `9876543210` (or any 10-digit number)
- [ ] Address: Any valid address
- [ ] City: `Kochi`
- [ ] State: `Kerala`
- [ ] ZIP: `682001`

### Step 4: Select Payment Method
- [ ] Select: **Cash on Delivery (COD)**
- [ ] Do NOT select credit card/UPI

### Step 5: Review Order
- [ ] Verify items: Kerala Cardamom × 1
- [ ] Verify amount: ₹449
- [ ] Verify payment: Cash on Delivery

### Step 6: Place Order
- [ ] Click: "Place Order" or "Complete Order"
- [ ] Wait for confirmation page
- [ ] Note down: Order number
- [ ] Take screenshot of order confirmation

### Step 7: Record Details
```
Order Details:
Order Number: ________________
Email: testing-scenario1@example.com
Product: Kerala Cardamom
Amount: ₹449
Payment: COD
Time Placed: ________________
```

**Status**: ✅ Order placed

---

## 🎯 PART 4: MONITOR WEBHOOK (5 minutes)

### Step 1: Check API Logs
- [ ] Look at Terminal 1 (docker logs window)
- [ ] Watch for: `POST /api/crm/webhooks/shopify`
- [ ] Should see: `200 OK`
- [ ] Usually appears within 2-5 seconds
- [ ] Take screenshot of the log

### Step 2: If You See 200 OK
- ✅ Great! Webhook fired successfully
- ✅ Data is flowing to CRM API
- ✅ Continue to next step

### Step 3: If You Don't See Webhook Call
- ❌ Webhook may not have fired
- ❌ Check: Is endpoint URL correct?
- ❌ Check: Are webhooks actually active?
- ❌ Go back to Part 1 and verify

**Status**: ✅ Webhook verified

---

## 🎯 PART 5: CHECK DATABASE (5 minutes)

### Step 1: Query Customers Table
- [ ] In Terminal 2 (psql prompt)
- [ ] Run:
```sql
SELECT * FROM crm_customers WHERE email = 'testing-scenario1@example.com';
```
- [ ] Should return 1 row with customer data
- [ ] Take screenshot

### Step 2: Expected Customer Fields
- [ ] id: (UUID value)
- [ ] email: `testing-scenario1@example.com`
- [ ] first_name: `Test`
- [ ] last_name: `Customer1`
- [ ] phone: (should be populated)
- [ ] total_spent: 449.00
- [ ] orders_count: 1
- [ ] created_at: (recent timestamp)

### Step 3: Query Orders Table
- [ ] In Terminal 2
- [ ] Run:
```sql
SELECT * FROM crm_orders WHERE email = 'testing-scenario1@example.com';
```
- [ ] Should return 1 row with order data
- [ ] Take screenshot

### Step 4: Expected Order Fields
- [ ] id: (UUID value)
- [ ] customer_id: (matches customer id)
- [ ] email: `testing-scenario1@example.com`
- [ ] order_date: (recent timestamp)
- [ ] total_amount: 449.00
- [ ] status: `pending` (for COD)
- [ ] currency: `INR`
- [ ] items: (should list products)

### Step 5: Record Findings
```
Customer Query Result:
Found: ☐ Yes ☐ No
Fields populated: ☐ All ☐ Some ☐ None
Missing fields: ________________

Order Query Result:
Found: ☐ Yes ☐ No
Fields populated: ☐ All ☐ Some ☐ None
Missing fields: ________________
```

**Status**: ✅ Database verified

---

## 🎯 PART 6: CHECK DASHBOARD (5 minutes)

### Step 1: Refresh Dashboard
- [ ] Go to browser tab: https://ai.pureleven.com/static/dashboard.html
- [ ] Press: Ctrl+Shift+R (hard refresh)
- [ ] Wait for page to fully load

### Step 2: Look for Customer
- [ ] In "Customer List" section
- [ ] Search for: `testing-scenario1@example.com`
- [ ] Should appear in list
- [ ] Take screenshot

### Step 3: Verify Customer Details
- [ ] Email: `testing-scenario1@example.com` ✓
- [ ] Orders: 1 ✓
- [ ] Total Spent: ₹449 ✓
- [ ] Click customer row - should show details

### Step 4: Check Analytics
- [ ] Look for: "Total Customers" metric
- [ ] Should increment by 1
- [ ] Look for: "Total Orders" metric
- [ ] Should increment by 1

### Step 5: Record Dashboard Findings
```
Dashboard Status:
Customer visible: ☐ Yes ☐ No
Order visible: ☐ Yes ☐ No
Data accuracy: ☐ Correct ☐ Incorrect
Response time: ______ seconds
Issues: ________________
```

**Status**: ✅ Dashboard verified

---

## ✅ TEST RESULT: SCENARIO #1

### If All Above Worked:
```
✅ Webhook registered and active
✅ Order placed successfully
✅ Webhook fired (200 OK in logs)
✅ Customer data in database
✅ Order data in database
✅ Dashboard showing data

RESULT: SYSTEM IS WORKING! 🎉
```

### If Any Failed:
```
❌ Document which step failed
❌ Check corresponding section in docs
❌ Fix issue
❌ Re-test
```

---

## 🎯 PART 7: TEST SCENARIO #2 - MULTIPLE PRODUCTS (Optional)

Once Scenario 1 is verified, repeat with:

### Order Details:
- [ ] Products: Add 3 different spices
- [ ] Email: `testing-scenario2@example.com`
- [ ] Amount: ₹1000+ (different total)
- [ ] Follow same steps as Part 3-6

### Verify:
- [ ] All 3 products recorded in items JSON
- [ ] Total amount is correct
- [ ] Customer created with correct totals
- [ ] Dashboard shows updated data

---

## 🎯 PART 8: TEST SCENARIO #3 - WITH COUPON (Optional)

Once Scenario 2 is verified, repeat with coupon:

### Order Details:
- [ ] Product: Any single product
- [ ] Apply coupon code at checkout
- [ ] Email: `testing-scenario3@example.com`
- [ ] Amount: After discount
- [ ] Follow same steps as Part 3-6

### Verify:
- [ ] Coupon code recorded
- [ ] Discount amount correct
- [ ] Final total after discount recorded
- [ ] Database shows coupon_code field (if exists)

---

## 📊 SUMMARY OF FINDINGS

After all tests, fill in:

### What Worked:
```
✅ _________________________________
✅ _________________________________
✅ _________________________________
✅ _________________________________
```

### What's Missing:
```
❌ _________________________________
❌ _________________________________
❌ _________________________________
```

### What Needs Fixing:
```
🔧 _________________________________
🔧 _________________________________
```

### Next Steps:
```
→ _________________________________
→ _________________________________
```

---

## 📞 IF SOMETHING FAILS

### If Webhook Doesn't Fire:
1. Check endpoint URL exactly: `https://track.pureleven.com/api/crm/webhooks/shopify`
2. Verify webhook shows "Active" status
3. Try placing order again
4. If still fails: Check CRM API is running

### If Customer Not in Database:
1. Check API logs for errors
2. Verify database connection
3. Run: `docker exec -it pureleven-postgres psql -U pureleven -d pureleven`
4. Check tables exist: `\dt crm_*`

### If Dashboard Not Updating:
1. Hard refresh: Ctrl+Shift+R
2. Check if database query returned data
3. Open browser DevTools (F12)
4. Check for JavaScript errors

### If Completely Stuck:
1. Check: COMPREHENSIVE_README.md (troubleshooting section)
2. Check: WEBHOOK_REGISTRATION_MANUAL.md (verification steps)
3. Review: CRM_API_DOCUMENTATION.md (endpoint details)

---

## ⏱️ TIME ESTIMATE

```
Part 1: Webhook Registration        15 minutes ✓
Part 2: Preparation                  5 minutes ✓
Part 3: Place Order                  5 minutes ✓
Part 4: Monitor Webhook              5 minutes ✓
Part 5: Check Database               5 minutes ✓
Part 6: Check Dashboard              5 minutes ✓
─────────────────────────────────────────────
Part 1-6 (First Complete Test):     40 minutes

Part 7: Second Order Test            10 minutes ✓
Part 8: Coupon Test                  10 minutes ✓
─────────────────────────────────────────────
All Tests Complete:                 60 minutes
```

---

## 🎯 SUCCESS CHECKLIST

When all tests are done, you should have:

- [ ] 5 Shopify webhooks registered and active
- [ ] At least 1 successful order placed
- [ ] Order data appeared in CRM database
- [ ] Customer data appeared in CRM database
- [ ] Dashboard displaying data correctly
- [ ] API logs showing 200 OK responses
- [ ] No errors in logs
- [ ] Response times < 500ms
- [ ] All field data populated
- [ ] Coupon test (if attempted) working

---

## 🚀 NEXT STEPS AFTER TESTING

### If All Tests Pass:
```
→ System is operational!
→ You can now proceed to GA4 integration (optional)
→ You can proceed to Google Ads setup (optional)
→ You can proceed to Meta setup (optional)
```

### If Issues Found:
```
→ Document all issues
→ Fix data parsing if needed
→ Re-run tests
→ Verify fixes work
```

### Go Live Checklist:
```
✅ Webhook registration complete
✅ Orders tested and flowing
✅ Database populated
✅ Dashboard working
✅ No errors in logs
✅ Performance acceptable
→ System ready for live use!
```

---

## 📝 NOTES

```
Test Date: ________________
Tester: ________________
Environment: Production (https://ai.pureleven.com)
Test Duration: ________________ minutes
Overall Result: ✅ Pass / ❌ Fail

Issues Found:
1. ____________________________
2. ____________________________
3. ____________________________

Fixes Applied:
1. ____________________________
2. ____________________________

Final Status: ✅ Ready for production / ❌ Needs more work
```

---

**READY? LET'S GO! 🚀**

Start with **PART 1: Webhook Registration**

Once done, come back and report results!

---

**Good luck! You've got this!** 💪
