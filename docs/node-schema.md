# Journey Node Schema Specification

**Phase 3 Documentation**

## Overview
This document defines the canonical node model used by React Flow builder and backend journey templates. It ensures consistency between visual editing and stored `template_json`.

---

## Node Model (Canonical)

### Structure
```javascript
{
  id: "node_unique_id",           // Unique within journey (e.g., node_0, node_1)
  type: "email|whatsapp|delay|condition|meta_audience|google_audience|add_tag",
  label: "Human readable label",
  position: { x: 100, y: 50 },    // Canvas coordinates (React Flow)
  data: {
    action_type: "email|whatsapp|delay|etc",
    action_data: { ... },          // Type-specific config
    condition: null,               // For conditional nodes
    delay_days: 0,
    template_id: null,
  }
}
```

---

## Node Types & Schemas

### 1. Email Node
**Trigger a Plunk/AWS SES email campaign.**

```javascript
{
  type: "email",
  data: {
    action_type: "email",
    template_id: "email_welcome_series",  // Reference to email template (Plunk/SES)
    action_data: {
      email_template: "welcome",
      subject_template: "Welcome to Pure Leven, {{first_name}}!",
      personalization: ["first_name", "email", "location"],
      retry_on_fail: true,
      max_retries: 3,
    },
  }
}
```

**Backend mapping:** Triggers N8N webhook → N8N calls Plunk/SES API.

---

### 2. WhatsApp Node
**Trigger a Wabis WhatsApp message.**

```javascript
{
  type: "whatsapp",
  data: {
    action_type: "whatsapp",
    template_id: "wabis_product_offer",
    action_data: {
      message_template: "product_offer",
      body: "Hi {{first_name}}, check out our Kerala Cardamom →",
      buttons: [
        { text: "View Product", action: "link", value: "https://pureleven.com/..." }
      ],
      personalization: ["first_name", "phone"],
      retry_on_fail: true,
      max_retries: 2,
    },
  }
}
```

**Backend mapping:** Triggers N8N webhook → N8N calls Wabis WhatsApp API.

---

### 3. Delay Node
**Wait before next action (email, pause engagement).**

```javascript
{
  type: "delay",
  data: {
    action_type: "delay",
    delay_days: 3,            // Number of days to wait
    action_data: {
      unit: "days",           // or "hours", "minutes"
      value: 3,
      scheduled_at: null,     // Computed by backend
    },
  }
}
```

**Backend mapping:** Sets `journey_steps.scheduled_at`, backend cron/APScheduler triggers next step.

---

### 4. Condition Node
**Split journey based on customer attribute or event.**

```javascript
{
  type: "condition",
  data: {
    action_type: "condition",
    action_data: {
      attribute: "intent_level",     // or "email_opens", "cart_value", etc
      operator: "eq|gt|lt|in",       // Equals, greater, less, in array
      value: "high",                 // Comparison value
      true_node_id: "node_2",        // Next node if true
      false_node_id: "node_3",       // Next node if false (else)
    },
  }
}
```

**Backend mapping:** Evaluates condition in `journey_instances` step processor; routes to `true_node_id` or `false_node_id`.

---

### 5. Meta Audience Node
**Sync customer to Meta Custom Audience for retargeting.**

```javascript
{
  type: "meta_audience",
  data: {
    action_type: "meta_audience",
    template_id: "meta_high_intent_audience",
    action_data: {
      audience_id: "123456789",      // Meta Custom Audience ID
      audience_name: "High Intent Users",
      sync_type: "add",              // "add" or "remove"
      fields: ["email", "phone"],    // Customer fields to hash & sync
      hashing: "sha256",
    },
  }
}
```

**Backend mapping:** Triggers N8N → N8N calls Meta Conversions API.

---

### 6. Google Audience Node
**Sync customer to Google Ads audience.**

```javascript
{
  type: "google_audience",
  data: {
    action_type: "google_audience",
    template_id: "google_high_intent_audience",
    action_data: {
      customer_list_id: "987654321",
      list_name: "High Intent Users",
      sync_type: "add",              // "add" or "remove"
      fields: ["email", "phone"],
      hashing: "sha256",
    },
  }
}
```

**Backend mapping:** Triggers N8N → N8N calls Google Ads API.

---

### 7. Add Tag Node
**Assign customer tag (for segmentation).**

```javascript
{
  type: "add_tag",
  data: {
    action_type: "add_tag",
    action_data: {
      tag_name: "high_intent_customer",
      tag_value: null,                // Optional: e.g., "vip" or "10k+"
    },
  }
}
```

**Backend mapping:** Adds tag to `customer_tags` table (if it exists) or customer metadata.

---

## Edge Model

Edges connect nodes in the flow. Standard React Flow edges:

```javascript
{
  id: "edge_node0_node1",
  source: "node_0",
  target: "node_1",
  type: "smoothstep",           // Visual style
  animated: true,               // Show animation
}
```

**For conditional nodes:** Two edges from condition node (true → node_2, false → node_3).

---

## Template JSON (Backend Storage)

The full journey is serialized to `Journey.template_json`:

```json
{
  "version": "1.0",
  "nodes": [
    {
      "id": "node_0",
      "type": "email",
      "label": "Welcome Email",
      "position": { "x": 100, "y": 50 },
      "data": {
        "action_type": "email",
        "template_id": "email_welcome",
        "action_data": { "subject": "Welcome" }
      }
    },
    {
      "id": "node_1",
      "type": "delay",
      "label": "Wait 3 Days",
      "position": { "x": 300, "y": 50 },
      "data": {
        "action_type": "delay",
        "delay_days": 3
      }
    }
  ],
  "edges": [
    {
      "id": "edge_0_1",
      "source": "node_0",
      "target": "node_1"
    }
  ],
  "metadata": {
    "created_at": "2026-05-19T12:00:00Z",
    "modified_at": "2026-05-19T12:00:00Z",
    "version": 1,
    "author": "user@pureleven.com"
  }
}
```

---

## Serialization Rules (Builder → Backend)

When user deploys a flow:

1. **Extract nodes & edges** from React Flow canvas state
2. **Validate each node**:
   - Required fields present
   - Type is valid
   - Data schema matches type
3. **Build adjacency map** (for execution order)
4. **Serialize to template_json**:
   - Set `metadata.created_at` and `metadata.author`
   - Convert positions to safe integers (no floats)
5. **POST /journeys** with `template_json` payload
6. **Backend creates Journey** record with `status=DRAFT`

---

## Deserialization Rules (Backend → Builder)

When user edits existing journey:

1. **GET /journeys/{id}** → returns journey with `template_json`
2. **Parse template_json**:
   - Extract `nodes` array
   - Extract `edges` array
   - Restore canvas positions
3. **Populate builder state**:
   - `builderNodes = nodes`
   - `builderEdges = edges`
   - `builderJourneyName = journey.name`
4. **Render on canvas** using React Flow

---

## Node Palette (UI Reference)

Left sidebar in builder shows available node types:

| Icon | Type | Color | Action |
|------|------|-------|--------|
| 📧 | Email | Blue (#3B82F6) | Send email via Plunk/SES |
| 💬 | WhatsApp | Green (#10B981) | Send WhatsApp via Wabis |
| ⏳ | Delay | Amber (#F59E0B) | Wait N days |
| ❓ | Condition | Purple (#8B5CF6) | Split based on attribute |
| 📱 | Meta Audience | Pink (#EC4899) | Sync to Meta |
| 🔍 | Google Audience | Orange (#EA580C) | Sync to Google |
| 🏷️ | Add Tag | Teal (#14B8A6) | Tag customer |

---

## Execution Order (Backend)

Once journey is ACTIVE and customer enrolled:

1. **Instantiate** `JourneyInstance` (customer + journey mapping)
2. **Start from first node** (topological sort of nodes by edges)
3. **Execute node action**:
   - Email: trigger N8N webhook → Plunk/SES
   - WhatsApp: trigger N8N webhook → Wabis
   - Delay: schedule `journey_steps` row with `scheduled_at`
   - Condition: evaluate, pick true or false branch
   - Audience: trigger N8N webhook → Meta/Google
   - Tag: write to database
4. **Persist step result** in `journey_steps` table
5. **Proceed to next node** (follow edges)
6. **Complete when no outgoing edges** from current node

---

## Example Journey: "Welcome + Upsell"

**Nodes:**
1. node_0: Email (Welcome)
2. node_1: Delay (3 days)
3. node_2: Condition (intent_level == "high")
4. node_3: Email (Upsell for High Intent)
5. node_4: Email (Retention for Low Intent)
6. node_5: Meta Audience (High Intent)

**Edges:**
- node_0 → node_1
- node_1 → node_2
- node_2 → node_3 (true)
- node_2 → node_4 (false)
- node_3 → node_5
- node_4 → (end)

**Execution:**
1. Send welcome email → node_0 ✓
2. Wait 3 days → node_1 ✓
3. Check intent_level → node_2 ✓
4. If high: send upsell → node_3 ✓ → sync to Meta → node_5 ✓
5. If low: send retention → node_4 ✓
6. End

---

## Future Extensions

- **A/B Testing** (Phase 5): Add `variant_id` and traffic split to nodes
- **Delay Scheduling** (Phase 4): Add cron expressions (e.g., "9am every Monday")
- **Multi-branch** (Phase 6): Condition nodes with >2 branches (switch/case)
- **Loop** (Phase 6): Support loops with max iteration limits
- **Webhook** (Phase 6): Custom HTTP webhook actions
- **Human Review** (Phase 6): Pause for manual approval before sending

---

## API Endpoints (Phase 3 & 4)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/journeys` | POST | Create journey from template_json |
| `/journeys/{id}` | GET | Retrieve journey with template_json |
| `/journeys/{id}` | PATCH | Update journey (edit DRAFT only) |
| `/journeys/{id}/deploy` | POST | Activate journey (DRAFT → ACTIVE) |
| `/journey-instances` | POST | Enroll customer in active journey |
| `/journey-steps/{id}/log` | POST | Log N8N step result |
| `/ws/metrics` | WS | Real-time analytics stream |
| `/ws/steps` | WS | Real-time step log stream |

---

## Validation Rules

### Node Validation
- ✅ `id` must be unique within journey
- ✅ `type` must be one of 7 types
- ✅ `data.action_type` must match `type`
- ✅ `data.action_data` must have required fields per type
- ✅ `position` must have numeric x, y

### Edge Validation
- ✅ `source` and `target` must exist as node ids
- ✅ No self-loops (source != target)
- ✅ For condition nodes: exactly 2 outgoing edges (true + false)
- ✅ For other nodes: 0 or 1 outgoing edge

### Journey Validation
- ✅ At least 1 node
- ✅ Nodes form a DAG (directed acyclic graph)
- ✅ No orphaned nodes (all reachable from start)
- ✅ End nodes have no outgoing edges

---

## Implementation Checklist (Phase 3)

- [ ] Create `FlowCanvas.jsx` (React Flow wrapper)
- [ ] Create `NodeTypes.js` (node definitions + editor config)
- [ ] Create `NodeEditor.jsx` (property panel)
- [ ] Implement serializer: nodes+edges → template_json
- [ ] Implement deserializer: template_json → nodes+edges
- [ ] Update `JourneyBuilderUI.jsx` to use FlowCanvas
- [ ] Add node validation logic
- [ ] Add edge validation logic
- [ ] Write unit tests (serializer, validator)
- [ ] Manual E2E test: create flow → deploy → verify stored template_json

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-19  
**Author:** Pure Leven CRM Team
