# WEEK 1 - TASK 3: Keyword Tracking Spreadsheet

**Status**: Template Ready for Import to Google Sheets  
**Date Created**: June 3, 2026  
**Total Keywords**: 16 (10 Tier 1 + 6 Tier 2)  

## Setup Instructions

### Option A: Import to Google Sheets (Recommended)
1. Go to [Google Sheets](https://sheets.google.com)
2. Click "New" → "Spreadsheet"
3. Name: `Pure Leven - SEO Keyword Tracking`
4. Copy the CSV data below (Tier 1 Keywords section)
5. Paste into Sheet1
6. Repeat for Tier 2 keywords in Sheet2

### Option B: Manual Data Entry
- Create 2 sheets in Google Sheets
- Sheet 1: "Tier 1 Keywords" (10 keywords)
- Sheet 2: "Tier 2 Keywords" (6 keywords)
- Follow the column structure below

---

## Sheet 1: TIER 1 KEYWORDS (Daily/2x Weekly Tracking)

**Tracking Frequency**: Daily or 2x weekly  
**Priority**: HIGH  
**Update Cadence**: Every morning & mid-week

### CSV Data (Import this to Google Sheets)

```
Keyword,Search Volume,Current Rank,Target Rank (Week 1),Target Rank (Week 4),Target Rank (Month 3),Product Pages,Content Type,Search Intent,Last Updated,Status
black pepper health benefits,4500,Not Indexed,60,30,15,Black Pepper,Blog + Product,Informational,6/3/26,Submitted
cardamom spice benefits,3200,Not Indexed,50,25,12,Cardamom,Blog + Product,Informational,6/3/26,Submitted
ceylon cinnamon vs cassia,2800,Not Indexed,40,20,10,Ceylon Cinnamon + Cassia,Comparison Post,Informational,6/3/26,Submitted
organic spices online,5600,Not Indexed,80,40,20,All Products,Product Hub,Commercial,6/3/26,Submitted
star anise uses,1900,Not Indexed,35,18,8,Star Anise,Blog + Product,Informational,6/3/26,Submitted
clove essential oil benefits,3400,Not Indexed,55,28,14,Clove,Blog + Product,Informational,6/3/26,Submitted
buy pure spices India,2200,Not Indexed,45,22,11,All Products,Product Hub,Commercial,6/3/26,Submitted
white pepper uses cooking,1400,Not Indexed,30,15,7,White Pepper,Blog + Product,Informational,6/3/26,Submitted
spice combo pack,890,Not Indexed,25,12,6,Combo Pack,Product,Commercial,6/3/26,Submitted
pure spices delivery Kerala,1600,Not Indexed,38,19,9,All Products,Service Page,Local,6/3/26,Submitted
```

### Column Definitions

| Column | Description | Example |
|--------|-------------|---------|
| **Keyword** | Primary search term | "black pepper health benefits" |
| **Search Volume** | Monthly search volume (GSC/Semrush estimate) | 4500 |
| **Current Rank** | Current ranking (GSC position) | "Not Indexed" or "65" |
| **Target Rank (Week 1)** | Goal for end of Week 1 (June 9) | 60-80 |
| **Target Rank (Week 4)** | Goal for end of Month (July 3) | 20-40 |
| **Target Rank (Month 3)** | Goal for end of Q2 (August) | 8-15 |
| **Product Pages** | Which products/pages target this keyword | "Black Pepper" or "All Products" |
| **Content Type** | Type of content addressing keyword | "Blog + Product", "Comparison Post" |
| **Search Intent** | Type of search: Informational/Commercial/Local | "Informational" |
| **Last Updated** | Date of last manual check | "6/3/26" |
| **Status** | Progress status | "Submitted", "Ranking", "Optimized" |

---

## Sheet 2: TIER 2 KEYWORDS (Weekly Tracking)

**Tracking Frequency**: Weekly (Mondays)  
**Priority**: MEDIUM  
**Update Cadence**: Every Monday

### CSV Data (Import this to Google Sheets)

```
Keyword,Search Volume,Current Rank,Target Rank (Week 1),Target Rank (Week 4),Target Rank (Month 3),Product Pages,Content Type,Search Intent,Last Updated,Status
best quality spices,1100,Not Indexed,70,35,18,All Products,Product Hub,Commercial,6/3/26,Submitted
organic black pepper,2300,Not Indexed,50,25,12,Black Pepper,Product,Commercial,6/3/26,Submitted
cardamom health uses,1800,Not Indexed,45,22,11,Cardamom,Blog,Informational,6/3/26,Submitted
premium cinnamon bark,950,Not Indexed,40,20,10,Cassia + Ceylon,Product,Commercial,6/3/26,Submitted
spice health benefits,2100,Not Indexed,55,28,14,All Products,Blog Hub,Informational,6/3/26,Submitted
authentic Kerala spices,1400,Not Indexed,50,25,12,All Products,Product Hub,Local,6/3/26,Submitted
```

---

## Tracking Workflow

### Daily/2x Weekly (Tier 1 - Monday, Wednesday, Friday)
1. Open Google Search Console
2. Go to Performance report
3. Check each keyword's ranking
4. Update "Current Rank" column
5. Note any position changes (+/- in adjacent column)
6. Check organic traffic for that keyword (clicks)

### Weekly (Tier 2 - Every Monday)
1. Same process as above for 6 Tier 2 keywords
2. Can be done in batch on Mondays

### Monthly Review (1st of each month)
1. Calculate average ranking across all keywords
2. Calculate organic traffic growth %
3. Update "Status" column
4. Identify keywords to optimize (still "Not Indexed" or ranking below 50)
5. Plan content/optimization for next month

---

## Formulas to Add (Optional)

### Column K: Ranking Progress
```
=IF(C2="Not Indexed", "—", 
    IF(C2<=F2, "✓ On Track", 
    IF(C2<=D2, "⚠ Slightly Behind", "❌ Off Track")))
```

### Column L: Average Week 1 Status
```
=AVERAGE(D2:D11)  [for Tier 1]
=AVERAGE(D13:D18) [for Tier 2]
```

### Add Conditional Formatting
- Red fill if "Current Rank" > 100
- Yellow fill if 50-100
- Green fill if < 50

---

## Expected Ranking Progress

### Week 1 (June 3-9)
- Most keywords: "Not Indexed" → 50-100 range
- Some competitive keywords may not rank yet

### Week 2-4 (June 10-July 3)
- Keywords trending upward: 40-50 range
- Tier 1 keywords showing organic traffic

### Month 2-3 (July-August)
- Tier 1 keywords: 15-30 range
- Tier 2 keywords: 25-40 range
- Consistent organic traffic growth

---

## Instructions for Sharing

1. **Create the Sheet**:
   - Go to Google Sheets → New Sheet
   - Name: "Pure Leven - SEO Keyword Tracking"

2. **Share with Team**:
   - Click "Share" (top right)
   - Add: purelevenexim@gmail.com
   - Add: seosages@pureleven.com (if team member)
   - Permission: "Editor"

3. **Link to Save**:
   - Copy the Google Sheets link
   - Save to bookmark/wiki
   - Example: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`

4. **Add to Workflow**:
   - Monday: Check Tier 2 keywords
   - Mon/Wed/Fri: Check Tier 1 keywords
   - 1st of month: Monthly review & reporting

---

## Keyword Selection Rationale

### Tier 1 - High Priority Keywords (10)
- **Search Volume**: 1,400 - 5,600 monthly searches
- **Competition**: Medium-High
- **Intent**: Mix of Informational + Commercial + Local
- **Connection to Products**: Direct (each addresses 1-2 main products)

**Focus Areas**:
- Health benefits (SEO-friendly + evergreen content)
- Spice buying intent (commercial - drives sales)
- Product comparisons (addresses buyer confusion)
- Location-based (Kerala spices = local advantage)

### Tier 2 - Supporting Keywords (6)
- **Search Volume**: 950 - 2,300 monthly searches
- **Competition**: Lower
- **Intent**: Long-tail variants & supporting content
- **Connection**: Complements Tier 1 keywords

**Focus Areas**:
- Quality/premium positioning
- Health angle (continuing from Tier 1)
- Specific product attributes
- Regional advantage

---

## Success Metrics

| Milestone | Timeline | Target |
|-----------|----------|--------|
| Keywords indexed | Week 1-2 | 8/10 Tier 1 visible in SERPs |
| Keywords ranking | Week 2-4 | 5/10 Tier 1 in top 100 |
| Organic traffic | Week 4+ | 20+ organic visits/week |
| Rankings improve | Month 2 | Avg position improves 30+ places |
| Top 20 position | Month 3 | 3/10 Tier 1 keywords in top 20 |

---

## Notes

- Rankings shown are estimates based on keyword competition
- Actual rankings depend on domain authority, content quality, and backlinks
- "Not Indexed" status means Google hasn't crawled/indexed the pages for this keyword yet
- Expect 2-4 weeks before seeing meaningful ranking data
- Focus on Tier 1 first; Tier 2 can be added later if bandwidth allows

