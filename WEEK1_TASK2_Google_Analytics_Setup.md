# WEEK 1 - TASK 2: Google Analytics 4 Setup

**Status**: Configuration Guide Ready (Data collection pending - GA4 tag installation required)  
**Property ID**: 429219662  
**Account**: Pure Leven (pure-leven-otp)  
**Date**: June 3, 2026  

## GA4 Setup Status

### ✅ Completed
- Google Analytics 4 property verified: `pure-leven-otp` (ID: 429219662)
- Account settings verified
  - Property name: pure-leven-otp
  - Reporting timezone: India (GMT+05:30)
  - Currency: US Dollar ($)

### ⏳ Required Actions

#### 1. **Verify GA4 Web Data Stream**
- Navigate to: Admin → Data collection → Web streams
- Confirm web stream is active for pureleven.com
- Note Measurement ID (G-XXXXXXX) for GTM integration

#### 2. **Create Custom Dashboard: "SEO Traffic Dashboard"**

**Dashboard Name**: SEO Traffic Dashboard

**Cards to Add**:

**A. Overview Metrics (Row 1)**
1. **Organic Users** (Card 1)
   - Metric: Users
   - Dimension: Traffic Source
   - Filter: source = organic

2. **Organic Sessions** (Card 2)
   - Metric: Sessions
   - Dimension: Traffic Source
   - Filter: source = organic

3. **Organic Conversion Rate** (Card 3)
   - Metric: Conversion Rate
   - Filter: source = organic

**B. Engagement Metrics (Row 2)**
4. **Landing Pages (Organic)** (Card 4)
   - Metric: Users, Sessions
   - Dimension: Landing Page
   - Filter: source = organic
   - Sorting: Users (descending)
   - Top 10

5. **Engagement Rate** (Card 5)
   - Metric: Engagement Rate
   - Dimension: Traffic Source
   - Filter: source = organic

**C. Conversion Tracking (Row 3)**
6. **SEO Key Events** (Card 6)
   - Metric: Event Count
   - Dimension: Event Name
   - Filter: source = organic
   - Focus on custom events (product views, add-to-cart, form submissions)

7. **Source/Medium (Organic)** (Card 7)
   - Metric: Users, Sessions
   - Dimension: Source / Medium
   - Filter: source = organic
   - Top 20 sources

**D. Page Performance (Row 4)**
8. **Product Pages Performance** (Card 8)
   - Metric: Users, Average Session Duration, Bounce Rate
   - Dimension: Page Path + Title
   - Filter: Page Path contains "/products/"
   - Top 8 pages

#### 3. **Baseline Metrics Collection Template**

Create a spreadsheet tracking column in GA4 or local spreadsheet:

| Metric | Baseline (June 3) | Target (June 9) | Target (June 30) |
|--------|-------------------|-----------------|------------------|
| Organic Users (Week) | - | - | 50+ |
| Organic Sessions (Week) | - | - | 100+ |
| Avg Session Duration | - | - | 2+ min |
| Engagement Rate | - | - | 40%+ |
| Product Page Views | - | - | 200+ |
| Landing Pages (unique) | - | - | 5+ |
| Conversion Events | - | - | 10+ |

#### 4. **Enable Email Notifications** (Optional)
- Go to: Admin → Account settings → Notifications
- Enable: "Weekly summary emails"
- Set frequency: Weekly (Mondays at 9 AM)

## Implementation Steps

### Step 1: Verify Data Stream
1. Go to Admin → Property → Data collection → Data streams
2. Click on web data stream
3. Copy Measurement ID (should be G-XXXXXXX)
4. Verify implementation status

### Step 2: Set Up Custom Dashboard
1. From Home, look for "Create" button or Reports menu
2. Click "Create" → "Custom dashboard"
3. Name: "SEO Traffic Dashboard"
4. Follow the card additions listed above
5. Arrange cards in 2-column layout for optimal viewing
6. Save dashboard

### Step 3: Connect GTM (if not already done)
1. Copy GA4 Measurement ID
2. Verify in GTM:
   - Google Analytics: GA4 Configuration
   - Measurement ID: [Paste from Step 1]
   - Enable: All domains
3. Publish GTM container

### Step 4: Verify Data Collection
1. Install [Google Analytics Debugger](https://chrome.google.com/webstore/detail/google-analytics-debugger/jnkmfdileelhofjciceffmmehjcnhlfi) extension
2. Visit pureleven.com in incognito window
3. Open DevTools → "Events" in extension
4. Should see events like `page_view` and custom events
5. Check GA4 real-time report (Admin → Reporting → Real-time)

## Metrics to Monitor

### Primary Metrics (Daily)
- Organic users (from Google Search Console referrer)
- Product page pageviews
- Key event conversions

### Secondary Metrics (Weekly)
- Source/medium breakdown (focus on "google / organic")
- Landing page performance
- Session duration by source
- Bounce rate by source

### Target Metrics (Monthly)
- Organic traffic trend
- Conversion rate improvement
- Landing page ranking progress

## Expected Timeline

- **Week 1** (June 3-9): Dashboard setup, baseline metrics collection
- **Week 2-4** (June 10-30): Monitor organic growth, optimize high-performing pages
- **Month 2+** (July+): Analyze trends, adjust content strategy

## Notes

- Data won't appear immediately; allow 24-48 hours for GA4 to show organic traffic
- Ensure GTM is publishing GA4 events to the property
- Cross-reference with Google Search Console data for accuracy
- Product page optimization from Phase 0 should start showing results by Week 2

## Verification Checklist

- [ ] GA4 property created and verified
- [ ] Web data stream active
- [ ] Custom "SEO Traffic Dashboard" created
- [ ] All 8 dashboard cards added
- [ ] GTM integration verified
- [ ] Real-time data flowing
- [ ] Email notifications configured
- [ ] Baseline metrics documented

