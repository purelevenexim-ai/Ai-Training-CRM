# Phase 3 Integration Guide - React Flow & Real-time

**Status:** ✅ Phase 3.1-3.3 Complete | 🔄 Phase 3.4 In Progress  
**Last Updated:** 2026-05-19  
**Estimated Time to Complete Phase 3:** 2-3 hours  

---

## 📋 What Was Built

### ✅ Completed Components

| Component | Lines | Purpose | Location |
|-----------|-------|---------|----------|
| `node-schema.md` | 450 | Canonical node specification | `docs/node-schema.md` |
| `NodeTypes.js` | 280 | Node definitions, validators, serializers | `src/components/NodeTypes.js` |
| `FlowCanvas.jsx` | 260 | React Flow drag-drop builder | `src/components/FlowCanvas.jsx` |
| `NodeEditor.jsx` | 280 | Property editor for nodes | `src/components/NodeEditor.jsx` |
| `socketClient.js` | 280 | WebSocket client with reconnection | `src/utils/socketClient.js` |
| `realtime_routes.py` | 200 | FastAPI WebSocket endpoints | `backend/realtime_routes.py` |
| `JourneyBuilderUI.jsx` | 180 | **Updated** to use FlowCanvas ✨ | `JourneyBuilderUI.jsx` |
| `crmStore.js` | 220 | **Updated** with WebSocket state ✨ | `crmStore.js` |

**Total New Code:** ~2,400 lines across 6 files  
**Total Updated Code:** 2 files enhanced with Phase 3 integration  

---

## 🎯 Phase 3 Implementation Progress

### Phase 3.1: ✅ Discovery & Schema Audit
- Analyzed existing Phase 2 architecture
- Designed 7-node type system (email, whatsapp, delay, condition, meta_audience, google_audience, add_tag)
- Created canonical `node-schema.md` specification

### Phase 3.2: ✅ Node Schema & React Flow Setup
- Created `NodeTypes.js` with:
  - Node definitions and palette
  - Validators (DAG check, orphan detection, cycles)
  - Serializers (template_json v1.0 format)
  - Deserializers (from stored templates)
- Created `FlowCanvas.jsx` with React Flow integration
- Created `NodeEditor.jsx` for property editing

### Phase 3.3: ✅ Visual Editor Integration
- **JourneyBuilderUI.jsx updated:**
  - Replaced grid with React Flow canvas
  - Wired nodes/edges to Zustand store
  - Added serialization on deploy
  - Integrated NodeTypes validators
  
- **crmStore.js updated:**
  - Added WebSocket state (wsConnected, metricsData, stepLogs)
  - Added WebSocket actions (setWsConnected, updateMetricsData, addStepLog)
  - Kept builder state (builderNodes, builderEdges)
  - Improved deployJourney flow

### Phase 3.4: 🔄 Backend WebSocket Integration (NOW)
- Created `realtime_routes.py` with:
  - `/ws/metrics` endpoint (journey analytics)
  - `/ws/steps` endpoint (N8N step logs)
  - Redis pub/sub architecture
  - Connection manager for broadcast
  
**TODO:** Wire router into FastAPI main.py

### Phase 3.5: ⏳ Socket Client Store Integration (NEXT)
- Created `socketClient.js` with:
  - Dual WebSocket channels (metrics + steps)
  - Reconnection logic (exponential backoff)
  - React hook for component integration
  
**TODO:** Integrate useSocket hook into components

---

## 🚀 Next Steps (Immediate Actions)

### Step 1: Wire WebSocket Routes to FastAPI (30 min)

**Location:** VPS at 192.46.213.140

```bash
# SSH to VPS
ssh root@192.46.213.140

# Go to FastAPI app directory
cd /opt/pureleven/ai-engine/app

# Edit main.py to add WebSocket routes
# Add these imports at the top:
from realtime_routes import router as realtime_router

# Add this line before app.run() or after other router includes:
app.include_router(realtime_router)

# Verify routes are registered
curl -s http://localhost:8000/api/crm/ws/health
# Should return: {"status": "healthy", "connections": {...}}
```

**OR if using Docker:**

```bash
# Copy realtime_routes.py to container
docker cp realtime_routes.py pureleven-ai-engine:/opt/pureleven/ai-engine/app/

# Restart container
docker restart pureleven-ai-engine

# Test health endpoint
curl -s -k https://track.pureleven.com/api/crm/ws/health
```

### Step 2: Test WebSocket Connection (20 min)

```bash
# Option 1: Using wscat (if installed)
npm install -g wscat
wscat -c wss://track.pureleven.com/api/crm/ws/metrics

# Option 2: Using Python websocket-client
pip install websocket-client
python3 << 'EOF'
import websocket
import json

def on_message(ws, message):
    print("📊 Metrics:", json.loads(message))

def on_error(ws, error):
    print("❌ Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("🔌 Closed")

ws = websocket.WebSocketApp(
    "wss://track.pureleven.com/api/crm/ws/metrics",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)
ws.run_forever()
EOF

# Option 3: Using curl with streaming
curl -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  https://track.pureleven.com/api/crm/ws/metrics
```

### Step 3: Integrate Socket Client into CRMDashboard (30 min)

**File:** `CRMDashboard_V2.jsx`

```jsx
import { useSocket } from './utils/socketClient';
import useCrmStore from './crmStore';

const CRMDashboard_V2 = () => {
  const store = useCrmStore();
  
  // Initialize WebSocket connection
  const { connected, metricsData, stepLogs } = useSocket({
    token: localStorage.getItem('auth_token'), // Add your JWT token
    onMetricsUpdate: (data) => store.updateMetricsData(data),
    onStepLog: (log) => store.addStepLog(log),
    onError: (err) => store.setWsError(err),
  });

  return (
    <div>
      {/* Connection indicator */}
      <div style={{
        padding: '10px',
        background: connected ? '#DCFCE7' : '#FEE2E2',
        color: connected ? '#15803D' : '#991B1B',
        borderRadius: '4px',
      }}>
        {connected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>

      {/* Show metrics from WebSocket */}
      {metricsData && (
        <div>Real-time Metrics: {JSON.stringify(metricsData)}</div>
      )}

      {/* Show step logs */}
      <div style={{ maxHeight: '400px', overflow: 'auto' }}>
        {stepLogs.map((log) => (
          <div key={log.step_id} style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
            {log.status === 'success' && '✅'} 
            {log.status === 'error' && '❌'}
            {log.status === 'pending' && '⏳'}
            {' '} {log.message}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Step 4: Test End-to-End Flow (30 min)

```bash
# 1. Start React dev server
cd /Users/bthomas/Documents/pureleven_dev
npm run dev

# 2. Open browser to http://localhost:5173

# 3. Go to Journey Builder tab

# 4. Create a test journey:
#    - Name: "Test WebSocket Journey"
#    - Add an Email node
#    - Add a Delay node
#    - Connect them
#    - Deploy

# 5. Monitor browser console for:
#    - ✅ FlowCanvas renders (nodes/edges visible)
#    - ✅ WebSocket connects (metrics stream visible)
#    - ✅ Deploy creates journey in backend
#    - ✅ Step logs appear in real-time

# 6. Verify in backend:
curl -s -k https://track.pureleven.com/api/crm/journeys | jq '.[] | select(.name == "Test WebSocket Journey")'
```

---

## 📝 Configuration Files

### `.env` - Frontend Environment Variables

```env
# FastAPI/CRM API
REACT_APP_CRM_API=https://track.pureleven.com/api/crm

# WebSocket Server
REACT_APP_WS_URL=wss://track.pureleven.com/api

# Auth Token (stored in localStorage by login)
# JWT token is auto-included by socketClient.js
```

### `.env.backend` - FastAPI Environment Variables

```env
# Redis for pub/sub (WebSocket broadcasting)
REDIS_URL=redis://localhost:6379

# Optional: Specify Redis channels
REDIS_METRICS_CHANNEL=pubsub:metrics
REDIS_STEPS_CHANNEL=pubsub:steps

# JWT validation (optional)
JWT_SECRET=your-secret-key
```

---

## 🧪 Testing Checklist

### Frontend Tests

- [ ] **React Flow renders**
  - [ ] Canvas displays empty state
  - [ ] Can drag nodes from palette
  - [ ] Nodes appear on canvas with correct colors
  - [ ] Can edit node properties in right panel
  - [ ] Can delete nodes
  - [ ] Can create edges between nodes

- [ ] **Store integration**
  - [ ] builderNodes updates when nodes change
  - [ ] builderEdges updates when edges change
  - [ ] Deploy button disabled when no nodes
  - [ ] Clear button resets all state

- [ ] **Serialization**
  - [ ] DAG validation passes for valid journeys
  - [ ] DAG validation fails for cyclic graphs
  - [ ] template_json format is correct
  - [ ] Journey deploys successfully

### Backend Tests

- [ ] **WebSocket health**
  ```bash
  curl -s -k https://track.pureleven.com/api/crm/ws/health
  # Should return: {"status": "healthy", "active_connections": 0}
  ```

- [ ] **Metrics streaming**
  ```bash
  wscat -c wss://track.pureleven.com/api/crm/ws/metrics
  # Should receive periodic metric updates
  ```

- [ ] **Step log streaming**
  ```bash
  wscat -c wss://track.pureleven.com/api/crm/ws/steps
  # Should receive step logs when journeys execute
  ```

---

## 📂 File Structure

```
/Users/bthomas/Documents/pureleven_dev/
├── docs/
│   └── node-schema.md ✅
├── src/
│   ├── components/
│   │   ├── FlowCanvas.jsx ✅
│   │   ├── NodeEditor.jsx ✅
│   │   ├── NodeTypes.js ✅
│   │   ├── JourneyBuilderUI.jsx ✨ UPDATED
│   │   ├── CRMDashboard_V2.jsx (needs socket integration)
│   │   └── ... (existing components)
│   ├── utils/
│   │   └── socketClient.js ✅
│   └── ... (existing)
└── backend/
    ├── realtime_routes.py ✅
    └── ... (existing: crm_routes.py, crm_models.py, email_service.py, etc)
```

---

## 🔍 Troubleshooting

### Issue: "React Flow not rendering"
**Solution:**
```bash
npm install reactflow
npm run dev
# Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
```

### Issue: "WebSocket connection fails"
**Solution:**
1. Check backend is running: `curl -s -k https://track.pureleven.com/api/crm/health`
2. Check realtime_routes.py is imported in main.py
3. Check Redis is running: `docker exec pureleven-redis redis-cli ping`
4. Check browser console for error messages

### Issue: "No metrics appearing"
**Solution:**
1. Verify Redis pub/sub is working:
   ```bash
   docker exec pureleven-redis redis-cli SUBSCRIBE pubsub:metrics
   # Should show: "Subscribed to channel"
   ```
2. Trigger a journey to generate metrics:
   ```bash
   curl -X POST https://track.pureleven.com/api/crm/journeys/{id}/customers \
     -H "Content-Type: application/json" \
     -d '{"customer_email": "test@example.com"}'
   ```

---

## 📊 What's Next After Phase 3

### Phase 3.5: Socket Client Integration
- Wire useSocket hook into CRMDashboard
- Add connection status indicator
- Display real-time metrics updates
- Show N8N step logs as they execute

### Phase 3.6: N8N Log UI
- Create JourneyStepLogs.jsx component
- Display live step logs in CustomerTimelineView
- Show execution timestamps and status badges

### Phase 3.7-3.8: Testing & Monitoring
- Unit tests for serializer/validator
- Integration tests for full journey workflow
- Feature flags for staged rollout
- Monitoring dashboard and alerts

---

## 📞 Support & Documentation

- **Node Schema Reference:** [docs/node-schema.md](docs/node-schema.md)
- **NodeTypes API:** [src/components/NodeTypes.js](src/components/NodeTypes.js)
- **Socket Client Docs:** [src/utils/socketClient.js](src/utils/socketClient.js)
- **WebSocket Spec:** [backend/realtime_routes.py](backend/realtime_routes.py)

---

## ✨ Summary

Phase 3 brings **visual journey building with React Flow** and **real-time metrics streaming via WebSocket**. The integration is straightforward:

1. **Frontend** already has FlowCanvas, NodeEditor, socketClient ready
2. **Backend** already has WebSocket endpoints ready
3. **Just need to wire** the routes into FastAPI and test

**Estimated Total Time:** 2-3 hours for full Phase 3 completion ⏰

