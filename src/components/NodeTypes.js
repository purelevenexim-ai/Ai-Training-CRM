/**
 * Node Type Definitions & Editor Metadata
 * Defines canonical node types for React Flow builder
 * Used by FlowCanvas and NodeEditor
 */

export const NODE_TYPES = {
  EMAIL: 'email',
  WHATSAPP: 'whatsapp',
  DELAY: 'delay',
  CONDITION: 'condition',
  META_AUDIENCE: 'meta_audience',
  GOOGLE_AUDIENCE: 'google_audience',
  ADD_TAG: 'add_tag',
};

export const NODE_PALETTE = [
  {
    id: 'email',
    label: '📧 Email',
    icon: '📧',
    color: '#3B82F6',
    description: 'Send email via Plunk/SES',
    category: 'messaging',
  },
  {
    id: 'whatsapp',
    label: '💬 WhatsApp',
    icon: '💬',
    color: '#10B981',
    description: 'Send WhatsApp via Wabis',
    category: 'messaging',
  },
  {
    id: 'delay',
    label: '⏳ Delay',
    icon: '⏳',
    color: '#F59E0B',
    description: 'Wait N days before next action',
    category: 'timing',
  },
  {
    id: 'condition',
    label: '❓ Condition',
    icon: '❓',
    color: '#8B5CF6',
    description: 'Split journey based on attribute',
    category: 'logic',
  },
  {
    id: 'meta_audience',
    label: '📱 Meta Audience',
    icon: '📱',
    color: '#EC4899',
    description: 'Sync customer to Meta retargeting',
    category: 'sync',
  },
  {
    id: 'google_audience',
    label: '🔍 Google Audience',
    icon: '🔍',
    color: '#EA580C',
    description: 'Sync customer to Google Ads',
    category: 'sync',
  },
  {
    id: 'add_tag',
    label: '🏷️ Add Tag',
    icon: '🏷️',
    color: '#14B8A6',
    description: 'Tag customer for segmentation',
    category: 'segmentation',
  },
];

/**
 * Get node palette item by type
 */
export const getNodePaletteItem = (nodeType) => {
  return NODE_PALETTE.find((item) => item.id === nodeType);
};

/**
 * Default action_data schemas per node type
 */
export const DEFAULT_ACTION_DATA = {
  email: {
    template_id: 'email_welcome',
    subject_template: 'Welcome to Pure Leven',
    personalization: ['first_name', 'email'],
    retry_on_fail: true,
    max_retries: 3,
  },
  whatsapp: {
    template_id: 'wabis_product_offer',
    message_template: 'product_offer',
    body: 'Hi {{first_name}}, check out our latest products!',
    buttons: [],
    retry_on_fail: true,
    max_retries: 2,
  },
  delay: {
    unit: 'days',
    value: 1,
  },
  condition: {
    attribute: 'intent_level',
    operator: 'eq',
    value: 'high',
    true_node_id: null,
    false_node_id: null,
  },
  meta_audience: {
    audience_id: '',
    audience_name: 'Pure Leven Audience',
    sync_type: 'add',
    fields: ['email', 'phone'],
    hashing: 'sha256',
  },
  google_audience: {
    customer_list_id: '',
    list_name: 'Pure Leven Audience',
    sync_type: 'add',
    fields: ['email', 'phone'],
    hashing: 'sha256',
  },
  add_tag: {
    tag_name: 'engaged_customer',
    tag_value: null,
  },
};

/**
 * Create a new node with defaults
 */
export const createNode = (nodeType, position, id) => {
  const paletteItem = getNodePaletteItem(nodeType);
  return {
    id,
    type: nodeType,
    label: paletteItem.label,
    position,
    data: {
      action_type: nodeType,
      action_data: { ...DEFAULT_ACTION_DATA[nodeType] },
      condition: null,
      delay_days: nodeType === 'delay' ? 1 : 0,
      template_id: null,
    },
  };
};

/**
 * Validate node structure
 */
export const validateNode = (node) => {
  const errors = [];

  if (!node.id) errors.push('Node must have an id');
  if (!node.type || !NODE_TYPES[node.type.toUpperCase()]) {
    errors.push(`Invalid node type: ${node.type}`);
  }
  if (!node.position || typeof node.position.x !== 'number' || typeof node.position.y !== 'number') {
    errors.push('Node must have numeric position (x, y)');
  }
  if (!node.data) errors.push('Node must have data object');
  if (node.data.action_type !== node.type) {
    errors.push(`action_type (${node.data.action_type}) must match type (${node.type})`);
  }

  return { valid: errors.length === 0, errors };
};

/**
 * Validate edge structure
 */
export const validateEdge = (edge, nodeIds) => {
  const errors = [];

  if (!edge.id) errors.push('Edge must have an id');
  if (!edge.source || !nodeIds.includes(edge.source)) {
    errors.push(`Edge source node not found: ${edge.source}`);
  }
  if (!edge.target || !nodeIds.includes(edge.target)) {
    errors.push(`Edge target node not found: ${edge.target}`);
  }
  if (edge.source === edge.target) {
    errors.push('Self-loops not allowed');
  }

  return { valid: errors.length === 0, errors };
};

/**
 * Validate entire journey (DAG check)
 */
export const validateJourney = (nodes, edges) => {
  const errors = [];

  if (nodes.length === 0) errors.push('Journey must have at least 1 node');

  // Validate individual nodes
  nodes.forEach((node) => {
    const nodeValidation = validateNode(node);
    if (!nodeValidation.valid) {
      errors.push(`Node ${node.id}: ${nodeValidation.errors.join('; ')}`);
    }
  });

  // Validate individual edges
  const nodeIds = nodes.map((n) => n.id);
  edges.forEach((edge) => {
    const edgeValidation = validateEdge(edge, nodeIds);
    if (!edgeValidation.valid) {
      errors.push(`Edge ${edge.id}: ${edgeValidation.errors.join('; ')}`);
    }
  });

  // Check for orphaned nodes (not reachable from any starting node)
  if (nodes.length > 0 && edges.length > 0) {
    const reachable = new Set();
    const visited = new Set();

    const dfs = (nodeId) => {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);
      reachable.add(nodeId);

      const outgoing = edges.filter((e) => e.source === nodeId);
      outgoing.forEach((e) => dfs(e.target));
    };

    // Start from nodes with no incoming edges (entry points)
    const incomingMap = new Set(edges.map((e) => e.target));
    const entryNodes = nodes.filter((n) => !incomingMap.has(n.id));

    if (entryNodes.length === 0) {
      errors.push('No entry nodes found (all nodes have incoming edges)');
    } else {
      entryNodes.forEach((n) => dfs(n.id));
      const orphaned = nodes.filter((n) => !reachable.has(n.id));
      if (orphaned.length > 0) {
        errors.push(`Orphaned nodes (not reachable from start): ${orphaned.map((n) => n.id).join(', ')}`);
      }
    }
  }

  // Check for cycles (for DAG validation - not allowed)
  const hasCycle = () => {
    const visited = new Set();
    const recursionStack = new Set();

    const dfs = (nodeId) => {
      visited.add(nodeId);
      recursionStack.add(nodeId);

      const outgoing = edges.filter((e) => e.source === nodeId);
      for (const edge of outgoing) {
        if (!visited.has(edge.target)) {
          if (dfs(edge.target)) return true;
        } else if (recursionStack.has(edge.target)) {
          return true;
        }
      }

      recursionStack.delete(nodeId);
      return false;
    };

    for (const node of nodes) {
      if (!visited.has(node.id)) {
        if (dfs(node.id)) return true;
      }
    }

    return false;
  };

  if (hasCycle()) {
    errors.push('Journey contains a cycle (not a DAG)');
  }

  return { valid: errors.length === 0, errors };
};

/**
 * Serialize nodes + edges to template_json
 */
export const serializeToTemplate = (nodes, edges, metadata = {}) => {
  return {
    version: '1.0',
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type,
      label: n.label,
      position: {
        x: Math.round(n.position.x),
        y: Math.round(n.position.y),
      },
      data: n.data,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: e.type || 'smoothstep',
      animated: e.animated !== undefined ? e.animated : true,
    })),
    metadata: {
      created_at: new Date().toISOString(),
      modified_at: new Date().toISOString(),
      version: 1,
      author: metadata.author || 'user@pureleven.com',
      ...metadata,
    },
  };
};

/**
 * Deserialize template_json to nodes + edges
 */
export const deserializeFromTemplate = (template) => {
  if (!template || !template.nodes || !template.edges) {
    return { nodes: [], edges: [] };
  }

  return {
    nodes: template.nodes || [],
    edges: template.edges || [],
  };
};
