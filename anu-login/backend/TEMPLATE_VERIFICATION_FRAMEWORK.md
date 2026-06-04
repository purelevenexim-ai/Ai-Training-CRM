# 🔍 AI TEMPLATE VERIFICATION FRAMEWORK

**Purpose:** Prevent AI hallucinations in marketing templates
**When to use:** BEFORE deploying ANY template
**Status:** Ready to implement

---

## ✅ VERIFICATION CHECKLIST (For Every Template)

Use this checklist BEFORE a template goes live:

### FACT-CHECK REQUIRED FIELDS

```
TEMPLATE: ________________

□ PRICING
  [ ] Product price verified on website
      Source URL: ________________
      Actual price: ________________
      Written price: ________________ (MUST MATCH)
  
  [ ] Discount percentage verified
      Original price: ________________
      Discount amount: ________________
      Calculation check: ☐ Correct ☐ Incorrect
  
  [ ] Free shipping threshold verified
      Claim: "Free shipping on ₹___"
      Website says: ________________

□ CONTACT INFORMATION
  [ ] Phone number verified (CALL IT to test)
      Number in template: ________________
      Expected number: +91 80755 19579
      Match: ☐ Yes ☐ No
  
  [ ] Email address verified (SEND TEST EMAIL)
      Email in template: ________________
      Expected: purelevenexim@gmail.com
      Match: ☐ Yes ☐ No
  
  [ ] WhatsApp verified (if mentioned)
      Number in template: ________________
      Expected: +91 88482 65849
      Match: ☐ Yes ☐ No

□ CUSTOMER TESTIMONIALS
  [ ] If customer quoted by name:
      Name in template: ________________
      Source: ☐ Google Reviews ☐ Social Media ☐ Other
      Verification link: ________________
      Exact quote match: ☐ Yes ☐ No ☐ Paraphrased
  
  [ ] If rating mentioned:
      Claim: "______ ⭐ rating"
      Current actual rating: ____ ⭐
      Match: ☐ Yes ☐ No

□ COMPANY CLAIMS
  [ ] FSSAI Licensed
      ☐ Verified on website
      ☐ Certificate link: ________________
  
  [ ] Farm-origin from [location]
      Location claimed: ________________
      Website says: ________________
      Match: ☐ Yes ☐ No
  
  [ ] Any other certification
      Claim: ________________
      Verified: ☐ Yes ☐ No
      Source: ________________

□ DELIVERY PROMISES
  [ ] Delivery time claimed
      Template says: _______ days
      Website policy: _______ days
      Match: ☐ Yes ☐ No
  
  [ ] Shipping cost (if applicable)
      Claimed: ________________
      Actual: ________________
      Match: ☐ Yes ☐ No

□ GUARANTEES & RETURN POLICIES
  [ ] Money-back guarantee period
      Template says: _______ days
      Policy says: _______ days
      Match: ☐ Yes ☐ No
  
  [ ] Return shipping (if applicable)
      Template claim: ________________
      Policy: ________________
      Match: ☐ Yes ☐ No

□ PRODUCTS & FEATURES
  [ ] Product names
      Each product mentioned verified on website: ☐ Yes ☐ No
  
  [ ] Product specifications (if mentioned)
      Example: "8mm cardamom pods"
      Verified: ☐ Yes ☐ No
  
  [ ] Product images (if linked)
      Link working: ☐ Yes ☐ No
      Correct product: ☐ Yes ☐ No

□ OFFERS & PROMOTIONS
  [ ] Coupon codes
      Code in template: ________________
      Does code exist: ☐ Yes ☐ No ☐ Unknown
      Discount: _________ %
      Verified working: ☐ Yes ☐ No
  
  [ ] Limited-time offers
      Claim: ________________
      Actually limited? ☐ Yes ☐ No ☐ Unknown
      If yes, expiry date: ________________

□ NO ARTIFICIAL URGENCY
  [ ] Does NOT claim fake scarcity
      ☐ Yes, template is honest
      ☐ No, template has false urgency
  
  [ ] Does NOT use fake deadlines
      ☐ Yes, template is realistic
      ☐ No, template has artificial deadline

□ LANGUAGE & TONE
  [ ] Tone matches PureLeven brand voice
      ☐ Yes - authentic, not generic
      ☐ No - sounds like generic marketing
  
  [ ] No competitor comparisons (unless verified)
      ☐ Correct - no competitors mentioned
      ☐ Issue - competitor claim needs verification
```

---

## 🚨 RED FLAGS - REJECT IF ANY APPLY

**IMMEDIATELY REJECT** if template contains:

- ❌ Pricing that doesn't match website (even close)
- ❌ Contact info that doesn't work
- ❌ Fake customer names or unverified quotes
- ❌ Rating/review numbers that differ from actual
- ❌ Certification claims not documented (FSSAI, organic, etc.)
- ❌ Delivery time promises beyond stated policy
- ❌ Guarantee period longer than policy
- ❌ "We personally verify each order" (overpromise)
- ❌ "Stock running out" (artificial urgency without proof)
- ❌ Coupon codes that don't exist
- ❌ "Limited time" without actual deadline
- ❌ Competitor comparisons without evidence
- ❌ Made-up testimonials with generic quotes
- ❌ "Best in industry" claims without sources

---

## ✅ GREEN FLAGS - APPROVE IF ALL APPLY

**APPROVE only if:**

- ✅ All prices match website exactly
- ✅ All contact info verified working
- ✅ All testimonials traced to real sources
- ✅ All ratings match current Google Reviews
- ✅ All certifications documented
- ✅ Delivery matches stated policy
- ✅ Guarantee matches actual policy
- ✅ Honest about stock/availability
- ✅ Real coupon codes only
- ✅ No false deadlines
- ✅ Authentic brand voice
- ✅ No unverified competitor claims
- ✅ Real customer stories only

---

## 📋 VERIFICATION PROCESS

### For Marketing Templates (WhatsApp, Email, etc.)

**Step 1: AI Draft (5 min)**
- AI generates template
- Include fact placeholders {{customer_name}}, etc.
- Do NOT include specific facts yet

**Step 2: Fact Research (15 min)**
- Visit pureleven.com
- Gather all facts needed
- Screenshot/document sources
- Create fact list

**Step 3: Fact Insertion (5 min)**
- Insert verified facts into template
- Use exact quotes for testimonials
- Do NOT paraphrase or change
- Check every number matches

**Step 4: Verification Checklist (10 min)**
- Use checklist above
- Check every box
- If any red flags: REJECT template
- If all green: APPROVE template

**Step 5: Approval (Sign-off)**
```
VERIFIED TEMPLATE: ________________
Verified by: ________________
Date: ________________
Source documents: ________________
Checked against: ☐ Website ☐ Google Reviews ☐ Policy ☐ Docs
All facts accurate: ☐ Yes
Ready for deployment: ☐ Yes
```

**Step 6: Deploy**
- Send verified template to Wabis/Email service
- Log verification date
- Monitor for customer feedback

---

## 🔄 TEMPLATE UPDATE PROCESS

When updating existing template:

1. **What's changing?** ________________
2. **Why is it changing?** ________________
3. **Is new info verified?** ☐ Yes ☐ No
4. **Check against:** ☐ Website ☐ Latest data ☐ Policy
5. **All facts still accurate?** ☐ Yes ☐ No
6. **Date of last verification:** ________________
7. **Ready to redeploy?** ☐ Yes ☐ No

---

## 📅 PERIODIC VERIFICATION

**Every 30 days:**
- [ ] Verify all active template facts still accurate
- [ ] Check prices haven't changed on website
- [ ] Verify contact info still works
- [ ] Confirm ratings/reviews still current
- [ ] Check guarantees/policies unchanged
- [ ] Document findings
- [ ] Update any outdated templates

**When facts change on website:**
- [ ] Update template immediately
- [ ] Re-verify all related templates
- [ ] Document date of change
- [ ] Test updated template
- [ ] Notify team of changes

---

## 📊 VERIFICATION SIGN-OFF SHEET

Keep this for each template:

```
TEMPLATE NAME: ________________
CREATION DATE: ________________
VERIFIER NAME: ________________

FACTS VERIFIED:
☐ Pricing (3-5 prices)
☐ Contact info (phone, email, WhatsApp)
☐ Customer testimonials (4-7 quotes)
☐ Ratings/reviews (dates, numbers)
☐ Certifications/guarantees
☐ Delivery promises
☐ Product info
☐ Offers/promotions

CHECKLIST SCORE: ___ / 50 boxes ✓

RED FLAGS FOUND: ☐ Yes ☐ No
If yes, list: ________________

APPROVAL STATUS:
☐ APPROVED - Ready for Wabis
☐ NEEDS REVISION - Details above
☐ REJECTED - See red flags

VERIFIER SIGNATURE: ________________
DATE: ________________
```

---

## 💡 KEY PRINCIPLE

**"If you can't verify it in 5 minutes, don't put it in the template"**

- Prices: 30 seconds on website ✓
- Contact: 30 seconds on footer ✓
- Testimonials: 1 minute in Google Reviews ✓
- Certifications: 1 minute on website ✓
- Policies: 2 minutes in docs ✓

If a fact takes longer than that to verify = probably doesn't exist.

---

## 🚀 TEMPLATE DEPLOYMENT CHECKLIST

Before ANY template goes to Wabis/production:

```
FINAL CHECKLIST
[ ] Verification checklist 100% complete
[ ] All boxes marked with green flag
[ ] No red flags present
[ ] Sign-off sheet filled out
[ ] Verifier signature present
[ ] All sources documented
[ ] Facts match current website
[ ] Tested with real links (if applicable)
[ ] Ready for Wabis deployment

DEPLOY TO WABIS
[ ] Template created in Wabis dashboard
[ ] Verification date added to notes
[ ] Status set to APPROVED
[ ] Tested with test API call
[ ] Monitor first 3 sends for errors

POST-DEPLOYMENT
[ ] Monitor customer responses
[ ] No complaints about accuracy
[ ] Track conversion metrics
[ ] Plan 30-day re-verification
```

---

## ✨ RESULT

**Every template deployed:**
- ✅ Verified against actual sources
- ✅ No hallucinations
- ✅ 100% accurate facts
- ✅ Customer trust established
- ✅ Legal compliance
- ✅ Ready for scale

**Time to verify: 30-45 minutes per template**
**Time saved from complaints: Priceless**
