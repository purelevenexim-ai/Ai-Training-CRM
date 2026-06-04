/**
 * CRM API Client
 * Calls the FastAPI backend at track.pureleven.com/api
 */

const API_BASE = 'https://track.pureleven.com/api';

function getAdminSecret() {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem('anu_admin_secret') || window.__ADMIN_SECRET__ || '';
}

function buildUrl(path, params = null) {
  const url = new URL(`${API_BASE}${path}`);
  if (params && Object.keys(params).length > 0) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      url.searchParams.set(key, String(value));
    });
  }
  return url.toString();
}

async function request(method, path, body, params = null) {
  const requestParams = { ...(params || {}) };
  const adminSecret = getAdminSecret();
  if (adminSecret && requestParams.admin_secret === undefined) {
    requestParams.admin_secret = adminSecret;
  }
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (adminSecret) {
    opts.headers['x-anu-admin-secret'] = adminSecret;
  }
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(buildUrl(path, requestParams), opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

const crmApi = {
  get: (path, params = {}) => request('GET', path, undefined, params),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  delete: (path, params = {}) => request('DELETE', path, undefined, params),

  // Journey Management
  listJourneys: (activeOnly = false) => 
    request('GET', `/crm/journeys${activeOnly ? '?status=active' : ''}`),
  
  getJourney: (id) => 
    request('GET', `/crm/journeys/${id}`),
  
  createJourney: (data) => 
    request('POST', '/crm/journeys', data),
  
  updateJourney: (id, data) => 
    request('PATCH', `/crm/journeys/${id}`, data),
  
  // Journey Analytics - aggregate metrics across all journeys
  getJourneyAnalytics: (journeyId) => {
    if (journeyId) {
      return request('GET', `/crm/journeys/${journeyId}/analytics`);
    }
    // Use aggregate analytics endpoint
    return request('GET', '/crm/journeys/analytics').catch(() =>
      // Fallback: build analytics from journey list
      request('GET', '/crm/journeys').then((resp) => {
        const list = Array.isArray(resp) ? resp : (resp.journeys || []);
        return {
          total_active_instances: 0,
          total_completed: 0,
          total_journeys: list.length,
          journeys: list.map((j) => ({
            id: j.id,
            name: j.name,
            status: j.status || 'DRAFT',
            conversion_rate: 0,
            email_sent: 0,
            whatsapp_sent: 0,
          })),
        };
      })
    );
  },

  // Customer Timeline
  getCustomerTimeline: (email) =>
    request('GET', `/customers/${encodeURIComponent(email)}/intelligence`),

  // Lead Management
  listLeads: (params = {}) => request('GET', '/leads', undefined, params),
  createLead: (data) => request('POST', '/leads', data),
  captureLeadEmail: (leadId, payload) => request('PUT', `/leads/${leadId}/email`, payload),

  // Journey Enrollment
  enrollCustomerInJourney: (journeyId, data) =>
    request('POST', `/crm/journeys/${journeyId}/enroll`, data),
  
  getJourneyEnrollments: (journeyId, status = null) =>
    request('GET', `/crm/journeys/${journeyId}/enrollments${status ? `?status=${status}` : ''}`),

  // Journey Instance Management
  updateJourneyInstance: (instanceId, data) =>
    request('PUT', `/journey-instances/${instanceId}`, data),
  
  // Journey Controls
  stopJourney: (journeyId) =>
    request('POST', `/crm/journeys/${journeyId}/stop`, {}),
  
  cloneJourney: (journeyId) =>
    request('POST', `/crm/journeys/${journeyId}/clone`, {}),

  // A/B Variant Management (Phase 5)
  listVariants: (journeyId) =>
    request('GET', `/crm/journeys/${journeyId}/variants`),

  createVariant: (journeyId, data) =>
    request('POST', `/crm/journeys/${journeyId}/variants`, data),

  updateVariant: (journeyId, variantId, data) =>
    request('PUT', `/crm/journeys/${journeyId}/variants/${variantId}`, data),

  // Phase 5: Promote winning variant
  promoteVariant: (journeyId, variantId) =>
    request('POST', `/crm/journeys/${journeyId}/variants/${variantId}/promote`, {}),

  // Bulk Enrollment (Phase 5)
  bulkEnroll: (journeyId, emails) =>
    request('POST', `/crm/journeys/${journeyId}/enroll-bulk`, { emails }),

  getJobStatus: (jobId) =>
    request('GET', `/jobs/${jobId}/status`),

  // Attribution (Phase 4)
  getJourneyAttribution: (journeyId) =>
    request('GET', `/journeys/${journeyId}/attribution`),

  // Sync triggers (Phase 4)
  triggerMetaSync: () =>
    request('POST', '/sync/meta/now', {}),

  triggerGoogleSync: () =>
    request('POST', '/sync/google/now', {}),

  getSyncStatus: () =>
    request('GET', '/sync/status'),

  // Full health check (Phase 4)
  fullHealthCheck: () =>
    request('GET', '/health/full'),

  // Tracking operations
  getTrackingHealth: (hours = 24) =>
    request('GET', '/crm/admin/tracking/health', undefined, { hours }),

  getTrackingAlerts: (hours = 6) =>
    request('GET', '/crm/admin/tracking/alerts', undefined, { hours }),

  getTrackingEvents: (params = {}) =>
    request('GET', '/crm/admin/tracking/events', undefined, params),

  replayTrackingOrder: (orderId, destinations = ['meta', 'google', 'ga4'], force = false) =>
    request('POST', '/crm/admin/tracking/replay', {
      order_id: orderId,
      destinations,
      force,
    }),

  retryTracking: (statuses = ['failed', 'skipped'], destinations = ['meta', 'google', 'ga4'], lookbackHours = 72, limit = 50) =>
    request('POST', '/crm/admin/tracking/retry', {
      statuses,
      destinations,
      lookback_hours: lookbackHours,
      limit,
    }),
};

export default crmApi;
