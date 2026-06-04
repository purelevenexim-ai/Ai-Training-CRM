# Phase 2 Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install Dependencies
```bash
npm install zustand recharts
```

### 2. Copy Environment Variable
```bash
# Add to your .env file:
REACT_APP_CRM_API=https://track.pureleven.com/api/crm
```

### 3. Update Your App
Replace your main app component:

**Before:**
```jsx
import CRMDashboard from './CRMDashboard';
export default App() { return <CRMDashboard />; }
```

**After:**
```jsx
import CRMDashboard from './CRMDashboard_V2';
export default App() { return <CRMDashboard />; }
```

### 4. Start Your App
```bash
npm run dev    # Vite
# or
npm start      # Create React App
```

### 5. Verify Backend Connection
```bash
curl https://track.pureleven.com/api/crm/health
# Should return: {"status": "ok"}
```

---

## 📍 File Locations

```
your-project/
├── src/
│   ├── crmApi.js                        (5.3 KB) - API layer
│   ├── crmStore.js                      (7.2 KB) - State management
│   ├── JourneyAnalyticsDashboard.jsx    (10 KB) - Metrics dashboard
│   ├── CustomerTimelineView.jsx         (13 KB) - Timeline view
│   ├── JourneyBuilderUI.jsx             (15 KB) - Journey editor
│   └── CRMDashboard_V2.jsx              (8.0 KB) - Main dashboard
│
└── .env
    └── REACT_APP_CRM_API=https://track.pureleven.com/api/crm
```

---

## 🎯 Three Main Views

### View 1: Analytics Dashboard 📊
**Path**: Click "📊 Journeys" tab

Shows:
- Active journey instances
- Completed journeys  
- Conversion rates
- Channel breakdown (email vs WhatsApp)
- Funnel chart
- Performance table per journey

Data refreshes every 30 seconds automatically.

### View 2: Customer Timeline 👤
**Path**: Click "👤 Timeline" tab

Shows:
1. Search for customer by email
2. View customer profile (orders, spent, etc)
3. See active journeys with progress bars
4. Check next scheduled action
5. Review message history (email/WhatsApp)

Actions:
- Pause/Resume journeys
- Enroll in new journeys

### View 3: Journey Builder 🎨
**Path**: Click "🎨 Builder" tab

Build journeys by:
1. Drag nodes from left palette (7 types)
2. Set journey name
3. Choose trigger (customer_create, order_complete, etc)
4. Click Deploy to create journey

Node types:
- 📧 Email
- 💬 WhatsApp
- ⏳ Delay
- ❓ Condition
- 📱 Meta Audience
- 🔍 Google Audience
- 🏷️ Add Tag

---

## 🔌 API Endpoints Used

All these endpoints are already deployed on VPS:

```
GET    /api/crm/journeys                          - List journeys
GET    /api/crm/journeys/analytics                - Get metrics
POST   /api/crm/journeys                          - Create journey
PATCH  /api/crm/journeys/{id}                     - Update journey
DELETE /api/crm/journeys/{id}                     - Delete journey

GET    /api/crm/customers/{email}/timeline        - Get timeline
GET    /api/crm/customers/{email}                 - Get customer
GET    /api/crm/customers?skip=0&limit=100        - List customers

POST   /api/crm/journey-instances                 - Enroll customer
PATCH  /api/crm/journey-instances/{id}            - Pause/Resume/Exit
```

---

## 🐛 Debugging

### Problem: No data showing in Analytics

**Check 1**: Backend is running
```bash
curl https://track.pureleven.com/api/crm/health
```

**Check 2**: Env variable set
```bash
echo $REACT_APP_CRM_API
# Should print: https://track.pureleven.com/api/crm
```

**Check 3**: Browser console
```javascript
// Open DevTools > Console
// Try manually:
fetch('https://track.pureleven.com/api/crm/journeys')
  .then(r => r.json())
  .then(d => console.log(d))
```

### Problem: Customer search not working

**Solution**: Check if customers exist in database
```bash
ssh root@192.46.213.140
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT COUNT(*) FROM crm_customers;"
```

### Problem: Deploy journey fails

**Check**: Journey name and trigger are selected
```javascript
// In builder, verify:
builderJourneyName !== ''
builderJourneyTrigger !== ''
nodes.length > 0
```

---

## 📦 Package Dependencies

```json
{
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "zustand": "^4.4.0",
    "recharts": "^2.10.0"
  },
  "devDependencies": {
    "vite": "^4.0.0"
  }
}
```

### Installation Command
```bash
npm install zustand@^4.4.0 recharts@^2.10.0
```

---

## 🎨 Customization

### Change Colors
In each component, edit the `styles` object:
```jsx
const styles = {
  ...
  someElement: {
    background: '#3B82F6'  // Change to any hex color
  }
}
```

Color palette used:
- Blue: #3B82F6 (primary)
- Green: #10B981 (success)
- Amber: #F59E0B (warning)
- Purple: #8B5CF6 (accent)
- Red: #EF4444 (error)

### Change Refresh Interval
In `JourneyAnalyticsDashboard.jsx`:
```jsx
const [refreshInterval, setRefreshInterval] = useState(30000); // milliseconds
// Change 30000 to any value (60000 = 1 minute)
```

### Add New Node Types
In `JourneyBuilderUI.jsx`, add to `nodeTypes` array:
```jsx
{ id: 'sms', label: '📱 SMS', icon: '📱', color: '#06B6D4' },
```

---

## 📈 Performance Notes

- **File Sizes**: Total ~58 KB (gzipped ~15 KB)
- **Load Time**: <200ms for components (depends on API)
- **Memory**: Zustand store is lightweight (~5 KB)
- **Network**: ~4-5 API calls per view load

---

## ✅ Deployment Checklist

- [ ] npm install zustand recharts
- [ ] .env file updated with REACT_APP_CRM_API
- [ ] All 6 component files copied to src/
- [ ] CRMDashboard_V2 imported in main app
- [ ] npm run build completes successfully
- [ ] Test analytics view loads
- [ ] Test customer search works
- [ ] Test journey creation in builder
- [ ] Deploy to production

---

## 🆘 Need Help?

Check these first:
1. **Backend Status**: curl https://track.pureleven.com/api/crm/health
2. **VPS Containers**: ssh root@192.46.213.140 && docker ps
3. **Database**: ssh root@192.46.213.140 && docker exec pureleven-postgres psql -U pureleven -d pureleven -c "SELECT COUNT(*) FROM crm_journeys;"
4. **Browser DevTools**: Check Console for errors

---

**Phase 2 Status**: ✅ Ready to Deploy
**Backend (Phase 1)**: ✅ Live & Tested
**Database**: ✅ 3 Tables Created

Start building! 🚀
