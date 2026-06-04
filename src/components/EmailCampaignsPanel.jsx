/**
 * Email Workspace — lifecycle, transactional, and promotional email via /api/promo/*
 * Backend: https://track.pureleven.com/api
 * Auth: ?admin_secret= stored in localStorage
 */
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'https://track.pureleven.com/api/promo';
const CRM_API_BASE = 'https://track.pureleven.com/api';
const ADMIN_KEY = 'anu_admin_secret';

function getAdminSecret() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem(ADMIN_KEY) || window.__ADMIN_SECRET__ || '';
}

const TEMPLATES = [
  { id: 'flash_sale', label: '⚡ Flash Sale', desc: 'Limited time offer' },
  { id: 'seasonal', label: '🍂 Seasonal', desc: 'Seasonal promotions' },
  { id: 'bundle_offer', label: '📦 Bundle Offer', desc: 'Product bundles' },
  { id: 'vip_exclusive', label: '👑 VIP Exclusive', desc: 'VIP customer offer' },
  { id: 'restock_alert', label: '🔔 Restock Alert', desc: 'Back in stock' },
];

const EMAIL_LIFECYCLE_STAGES = [
  {
    key: 'order_confirmed',
    label: 'Order Confirmed',
    aliases: ['day1'],
    trigger: 'New Shopify order after the automation start date.',
    description: 'Sent immediately when a fresh order enters the journey.',
    tone: '#dbeafe',
  },
  {
    key: 'in_transit',
    label: 'Tracking / In Transit',
    aliases: ['day2'],
    trigger: 'Tracking is added or the carrier marks the shipment in transit.',
    description: 'Transactional dispatch update with tracking details when available.',
    tone: '#dcfce7',
  },
  {
    key: 'delivered',
    label: 'Delivered',
    aliases: ['day5'],
    trigger: 'Carrier delivered event reaches the CRM.',
    description: 'Delivery confirmation before later review and retention stages.',
    tone: '#fef3c7',
  },
  {
    key: 'review',
    label: 'Review Request',
    aliases: ['day15'],
    trigger: '10–16 days after delivery during the daily lifecycle run.',
    description: 'Asks for feedback once the customer has had time to use the products.',
    tone: '#ede9fe',
  },
  {
    key: 'upsell',
    label: 'Upsell / Replenishment',
    aliases: ['day30'],
    trigger: '28–33 days after delivery during the daily lifecycle run.',
    description: 'Suggests refills or next-best products based on the purchase.',
    tone: '#fee2e2',
  },
  {
    key: 'corporate',
    label: 'Corporate / Bulk',
    aliases: ['day60'],
    trigger: '58–63 days after delivery during the daily lifecycle run.',
    description: 'Introduces gifting and bulk-order options.',
    tone: '#ecfccb',
  },
  {
    key: 'loyalty',
    label: 'Loyalty / VIP',
    aliases: ['day75'],
    trigger: '73–78 days after delivery during the daily lifecycle run.',
    description: 'Rewards engaged customers with loyalty offers.',
    tone: '#fce7f3',
  },
  {
    key: 'rfm',
    label: 'Reactivation',
    aliases: ['day95'],
    trigger: '93–98 days after delivery during the daily lifecycle run.',
    description: 'Attempts a clean win-back for dormant customers.',
    tone: '#e5e7eb',
  },
];

const JOURNEY_STAGE_META = EMAIL_LIFECYCLE_STAGES.reduce((acc, stage) => {
  acc[stage.key] = stage;
  stage.aliases.forEach((alias) => {
    acc[alias] = stage;
  });
  return acc;
}, {});

function getJourneyStageMeta(stage) {
  return JOURNEY_STAGE_META[stage] || null;
}

function formatJourneyStageLabel(stage) {
  if (!stage) return '—';
  const meta = getJourneyStageMeta(stage);
  if (meta) return meta.label;
  return String(stage)
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatJourneyEventName(item) {
  if (item?.journey_stage) return formatJourneyStageLabel(item.journey_stage);
  return item?.campaign_name || '—';
}

function apiUrl(path, params = {}) {
  const secret = getAdminSecret();
  const qs = new URLSearchParams({ ...params });
  if (secret) qs.set('admin_secret', secret);
  return `${API_BASE}${path}?${qs}`;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const contentType = res.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await res.json().catch(() => null) : await res.text().catch(() => '');

  if (!res.ok) {
    const detail = payload?.detail || payload?.message || payload || `HTTP ${res.status}`;
    if (res.status === 401 || res.status === 403) {
      throw new Error(`Admin access denied. Check ${ADMIN_KEY} in this browser.`);
    }
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`);
  }

  return payload;
}

export default function EmailCampaignsPanel() {
  const [tab, setTab] = useState('dashboard');
  const [emailStatus, setEmailStatus] = useState(null);
  const [hasAdminAccess, setHasAdminAccess] = useState(() => Boolean(getAdminSecret()));

  // Dashboard stats
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState(null);

  // Customers
  const [customers, setCustomers] = useState([]);
  const [customersTotal, setCustomersTotal] = useState(0);
  const [customersLoading, setCustomersLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  // Campaigns
  const [campaigns, setCampaigns] = useState([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Create campaign form
  const [showCreate, setShowCreate] = useState(false);
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    template_type: 'flash_sale',
    subject: '',
    html_body: '',
    segment: 'all',
    send_interval_seconds: '1',
    discount_code: '',
    discount_percent: '',
    product_name: '',
    custom_message: '',
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  // Send campaign
  const [sendCampaignId, setSendCampaignId] = useState('');
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);
  const [progressByCampaign, setProgressByCampaign] = useState({});

  // Journey + Purchase + Engagement
  const [journeyFilters, setJourneyFilters] = useState({
    search: '',
    label: 'all',
    segment: 'all',
  });
  const [journeyCustomers, setJourneyCustomers] = useState([]);
  const [journeyTotal, setJourneyTotal] = useState(0);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [engagementSummary, setEngagementSummary] = useState(null);
  const [selectedJourneyEmail, setSelectedJourneyEmail] = useState('');
  const [journeyDetail, setJourneyDetail] = useState(null);
  const [journeyDetailLoading, setJourneyDetailLoading] = useState(false);

  // Logs / Bounces / Issues
  const [logsFilters, setLogsFilters] = useState({ campaign_id: '', status: '', email_search: '' });
  const [logs, setLogs] = useState([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsLoading, setLogsLoading] = useState(false);
  const [bounceSummary, setBounceSummary] = useState(null);
  const [suppressionList, setSuppressionList] = useState([]);
  const [suppressionTotal, setSuppressionTotal] = useState(0);
  const [retryingTransient, setRetryingTransient] = useState(false);
  const [retryResult, setRetryResult] = useState(null);
  const [suppressEmail, setSuppressEmail] = useState('');
  const [suppressReason, setSuppressReason] = useState('manual');
  const [suppressing, setSuppressing] = useState(false);

  // Segment preview
  const [segmentPreviewCount, setSegmentPreviewCount] = useState(null);
  const [segmentPreviewLoading, setSegmentPreviewLoading] = useState(false);

  const fetchEmailStatus = useCallback(async () => {
    try {
      const res = await fetch(`${CRM_API_BASE}/email/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setEmailStatus(data);
    } catch (e) {
      console.error('Email status fetch error', e);
      setEmailStatus(null);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    
    setStatsLoading(true);
    setStatsError(null);
    try {
      const data = await fetchJson(apiUrl('/dashboard/summary'));
      setStats(data);
      setHasAdminAccess(true);
    } catch (e) {
      setStatsError(e.message);
      if (/Admin access denied/.test(e.message)) setHasAdminAccess(false);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const fetchCustomers = useCallback(async () => {
    
    setCustomersLoading(true);
    try {
      const data = await fetchJson(apiUrl('/customers/list', { limit: 50, offset: 0 }));
      setCustomers(data.customers || []);
      setCustomersTotal(data.total || 0);
    } catch (e) {
      console.error('Customers fetch error', e);
    } finally {
      setCustomersLoading(false);
    }
  }, []);

  const fetchCampaigns = useCallback(async () => {
    
    setCampaignsLoading(true);
    try {
      const data = await fetchJson(apiUrl('/campaigns/list'));
      setCampaigns(data.campaigns || []);
    } catch (e) {
      console.error('Campaigns fetch error', e);
    } finally {
      setCampaignsLoading(false);
    }
  }, []);

  const fetchJourneyCustomers = useCallback(async () => {
    
    setJourneyLoading(true);
    try {
      const data = await fetchJson(
        apiUrl('/dashboard/journey/customers', {
          limit: 80,
          offset: 0,
          search: journeyFilters.search,
          label: journeyFilters.label,
          segment: journeyFilters.segment,
        })
      );
      setJourneyCustomers(data.customers || []);
      setJourneyTotal(data.total || 0);
    } catch (e) {
      console.error('Journey customers fetch error', e);
    } finally {
      setJourneyLoading(false);
    }
  }, [journeyFilters]);

  const fetchEngagementSummary = useCallback(async () => {
    
    try {
      const data = await fetchJson(apiUrl('/dashboard/engagement/summary', { segment: journeyFilters.segment }));
      setEngagementSummary(data);
    } catch (e) {
      console.error('Engagement summary fetch error', e);
    }
  }, [journeyFilters.segment]);

  const fetchJourneyDetail = useCallback(async (email) => {
    
    setSelectedJourneyEmail(email);
    setJourneyDetailLoading(true);
    try {
      const data = await fetchJson(apiUrl(`/dashboard/journey/${encodeURIComponent(email)}`));
      setJourneyDetail(data);
    } catch (e) {
      console.error('Journey detail fetch error', e);
      setJourneyDetail(null);
    } finally {
      setJourneyDetailLoading(false);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    
    setLogsLoading(true);
    try {
      const data = await fetchJson(apiUrl('/logs', { ...logsFilters, limit: 100, offset: 0 }));
      setLogs(data.logs || []);
      setLogsTotal(data.total || 0);
    } catch (e) { console.error('Logs fetch error', e); }
    finally { setLogsLoading(false); }
  }, [logsFilters]);

  const fetchBounceSummary = useCallback(async () => {
    
    try {
      const params = logsFilters.campaign_id ? { campaign_id: logsFilters.campaign_id } : {};
      const data = await fetchJson(apiUrl('/logs/bounces', params));
      setBounceSummary(data);
    } catch (e) { console.error('Bounce summary error', e); }
  }, [logsFilters.campaign_id]);

  const fetchSuppressionList = useCallback(async () => {
    
    try {
      const data = await fetchJson(apiUrl('/suppression/list', { limit: 100, offset: 0 }));
      setSuppressionList(data.suppressions || []);
      setSuppressionTotal(data.total || 0);
    } catch (e) { console.error('Suppression list error', e); }
  }, []);

  const handleRetryTransient = async () => {
    setRetryingTransient(true);
    setRetryResult(null);
    try {
      const data = await fetchJson(
        apiUrl('/logs/retry-transient', logsFilters.campaign_id ? { campaign_id: logsFilters.campaign_id } : {}),
        { method: 'POST' }
      );
      setRetryResult(data);
      await fetchLogs();
    } catch (e) { setRetryResult({ error: e.message }); }
    finally { setRetryingTransient(false); }
  };

  const handleSuppress = async (emailToSuppress, reason = 'manual') => {
    try {
      await fetchJson(apiUrl('/suppression/add'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailToSuppress, reason }),
      });
      await fetchSuppressionList();
    } catch (e) { console.error('Suppress error', e); }
  };

  const handleUnsuppress = async (emailToUnsuppress) => {
    try {
      await fetchJson(apiUrl('/suppression/remove', { email: emailToUnsuppress }), { method: 'DELETE' });
      await fetchSuppressionList();
    } catch (e) { console.error('Unsuppress error', e); }
  };

  const fetchSegmentPreview = useCallback(async (segment) => {
    
    setSegmentPreviewLoading(true);
    setSegmentPreviewCount(null);
    try {
      const data = await fetchJson(apiUrl('/segments/preview', { segment }));
      setSegmentPreviewCount(data.count ?? null);
    } catch (e) { console.error('Segment preview error', e); }
    finally { setSegmentPreviewLoading(false); }
  }, []);

  useEffect(() => {
    fetchEmailStatus();
    if (!getAdminSecret()) {
      setHasAdminAccess(false);
      setStatsError(`Admin access is not configured. Protected email data is paused until ${ADMIN_KEY} is available.`);
      return;
    }

    setHasAdminAccess(true);
    fetchStats();
    if (tab === 'customers') fetchCustomers();
    if (tab === 'campaigns') fetchCampaigns();
    if (tab === 'journey') {
      fetchJourneyCustomers();
      fetchEngagementSummary();
    }
    if (tab === 'logs') {
      fetchLogs();
      fetchBounceSummary();
      fetchSuppressionList();
    }
  }, [tab]); // eslint-disable-line

  useEffect(() => {
    const handleAdminUpdate = () => {
      const configured = Boolean(getAdminSecret());
      setHasAdminAccess(configured);
      if (!configured) {
        setStatsError(`Admin access is not configured. Protected email data is paused until ${ADMIN_KEY} is available.`);
        return;
      }
      setStatsError(null);
      fetchStats();
    };

    window.addEventListener('anu-admin-secret-updated', handleAdminUpdate);
    return () => window.removeEventListener('anu-admin-secret-updated', handleAdminUpdate);
  }, [fetchStats]);

  useEffect(() => {
    if (tab === 'logs') {
      fetchLogs();
      fetchBounceSummary();
    }
  }, [tab, logsFilters]); // eslint-disable-line

  useEffect(() => {
    if (tab === 'journey') {
      fetchJourneyCustomers();
      fetchEngagementSummary();
    }
  }, [tab, journeyFilters]); // eslint-disable-line

  useEffect(() => {
    if (tab !== 'campaigns' || !campaigns.length) return undefined;

    const queueingIds = campaigns
      .filter((c) => ['queued', 'sending', 'scheduled'].includes(c.queue_status || c.status))
      .map((c) => c.campaign_id);

    if (!queueingIds.length) return undefined;

    let cancelled = false;

    const pullProgress = async () => {
      const updates = {};
      for (const campaignId of queueingIds) {
        try {
          const res = await fetch(apiUrl(`/campaigns/${campaignId}/progress`));
          const data = await res.json();
          if (res.ok && data.ok) updates[campaignId] = data;
        } catch (e) {
          // ignore polling errors
        }
      }
      if (!cancelled && Object.keys(updates).length) {
        setProgressByCampaign((prev) => ({ ...prev, ...updates }));
      }
    };

    pullProgress();
    const id = window.setInterval(pullProgress, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [tab, campaigns]);

  const handleImport = async () => {
    setImporting(true);
    setImportResult(null);
    try {
      const data = await fetchJson(apiUrl('/import/shopify'), { method: 'POST' });
      setImportResult(data);
      await fetchCustomers();
      await fetchStats();
    } catch (e) {
      setImportResult({ error: e.message });
    } finally {
      setImporting(false);
    }
  };

  const handleCreateCampaign = async (e) => {
    e.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      const payload = {
        name: newCampaign.name,
        template_type: newCampaign.template_type,
        subject: newCampaign.subject || '',
        html_body: newCampaign.html_body || '',
        segment: newCampaign.segment || 'all',
        coupon_code: newCampaign.discount_code || '',
        discount_pct: Number(newCampaign.discount_percent || 0),
        send_interval_seconds: Number(newCampaign.send_interval_seconds || 1),
      };
      const data = await fetchJson(apiUrl('/campaigns/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setShowCreate(false);
      setNewCampaign({
        name: '',
        template_type: 'flash_sale',
        subject: '',
        html_body: '',
        segment: 'all',
        send_interval_seconds: '1',
        discount_code: '',
        discount_percent: '',
        product_name: '',
        custom_message: '',
      });
      await fetchCampaigns();
      setSendCampaignId(String(data.campaign_id));
    } catch (e) {
      setCreateError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleSendCampaign = async (campaignId) => {
    setSending(true);
    setSendCampaignId(String(campaignId));
    setSendResult(null);
    try {
      const data = await fetchJson(apiUrl('/campaigns/send'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign_id: String(campaignId),
          send_interval_seconds: Number(newCampaign.send_interval_seconds || 1),
        }),
      });
      setSendResult(data);
      await fetchCampaigns();
      await fetchStats();
    } catch (e) {
      setSendResult({ error: e.message });
    } finally {
      setSending(false);
    }
  };

  const fetchAnalytics = async (campaignId) => {
    setSelectedCampaign(campaignId);
    setAnalyticsLoading(true);
    setAnalytics(null);
    try {
      const data = await fetchJson(apiUrl(`/campaigns/${campaignId}/analytics`));
      setAnalytics(data);
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  // ── Main Panel ───────────────────────────────────────────────────────────────
  return (
    <div style={s.panel}>
      {/* Panel Header */}
      <div style={s.panelHeader}>
        <div>
          <h2 style={s.panelTitle}>📧 Email Workspace</h2>
          <p style={s.panelSubtitle}>Lifecycle, transactional, and promotional email aligned with the WhatsApp journey</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ ...s.statusPill, background: emailStatus?.configured ? '#dcfce7' : '#fee2e2', color: emailStatus?.configured ? '#166534' : '#991b1b' }}>
            {emailStatus?.configured ? 'Transactional email ready' : 'Email config needs attention'}
          </span>
          {emailStatus?.sender_email ? <span style={s.statusPillMuted}>{emailStatus.sender_email}</span> : null}
        </div>
      </div>

      {/* Internal Tabs */}
      <div style={s.tabRow}>
        {[
          { key: 'dashboard', label: '📊 Dashboard' },
          { key: 'customers', label: '👥 Customers' },
          { key: 'journey', label: '🧭 Lifecycle Journey' },
          { key: 'campaigns', label: '📨 Campaigns' },
          { key: 'logs', label: '🪵 Logs & Bounces' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{ ...s.tabBtn, ...(tab === key ? s.tabBtnActive : {}) }}
          >
            {label}
          </button>
        ))}
      </div>

      {!hasAdminAccess && (
        <div style={s.accessNotice}>
          <div>
            <strong>Email admin access is not active.</strong>
            <span style={{ marginLeft: '6px' }}>Protected email data is paused until {ADMIN_KEY} is available in this browser.</span>
          </div>
          <button
            style={{ ...s.btnSecondary, padding: '6px 10px', fontSize: '12px' }}
            onClick={() => {
              const configured = Boolean(getAdminSecret());
              setHasAdminAccess(configured);
              if (configured) {
                setStatsError(null);
                fetchStats();
              }
            }}
          >
            Recheck
          </button>
        </div>
      )}

      {/* Dashboard Tab */}
      {tab === 'dashboard' && (
        <div style={s.content}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
            <button style={s.btnSecondary} onClick={fetchStats} disabled={statsLoading}>
              {statsLoading ? '⟳ Refreshing…' : '🔄 Refresh'}
            </button>
          </div>

          {statsError && hasAdminAccess && <div style={s.errorBox}>Error: {statsError}</div>}

          {stats ? (
            <>
              {/* Stat Cards */}
              <div style={s.statsGrid}>
                <StatCard icon="👥" label="Total Customers" value={stats.total_customers ?? '—'} color="#3b82f6" />
                <StatCard icon="📨" label="Campaigns" value={stats.total_campaigns ?? '—'} color="#8b5cf6" />
                <StatCard icon="✉️" label="Emails Sent" value={stats.total_sent ?? '—'} color="#10b981" />
                <StatCard icon="👁️" label="Opened" value={stats.total_opened ?? '—'} color="#f59e0b" />
                <StatCard icon="🖱️" label="Clicks" value={stats.total_clicked ?? '—'} color="#ef4444" />
                <StatCard
                  icon="📈"
                  label="Open Rate"
                  value={stats.total_sent > 0 ? `${((stats.total_opened / stats.total_sent) * 100).toFixed(1)}%` : '—'}
                  color="#6366f1"
                />
              </div>

              {/* Recent Campaigns */}
              {stats.recent_campaigns?.length > 0 && (
                <div style={s.section}>
                  <h3 style={s.sectionTitle}>Recent Campaigns</h3>
                  <table style={s.table}>
                    <thead>
                      <tr style={s.tableHead}>
                        <th style={s.th}>Name</th>
                        <th style={s.th}>Template</th>
                        <th style={s.th}>Sent</th>
                        <th style={s.th}>Opens</th>
                        <th style={s.th}>Clicks</th>
                        <th style={s.th}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recent_campaigns.map((c) => (
                        <tr key={c.campaign_id} style={s.tableRow}>
                          <td style={s.td}>{c.name}</td>
                          <td style={s.td}><span style={s.badge}>{c.template_type}</span></td>
                          <td style={s.td}>{c.sent_count ?? 0}</td>
                          <td style={s.td}>{c.open_count ?? 0}</td>
                          <td style={s.td}>{c.click_count ?? 0}</td>
                          <td style={s.td}><StatusBadge status={c.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {stats.total_campaigns === 0 && (
                <div style={s.emptyState}>
                  <p>No campaigns yet.</p>
                  <button style={s.btnPrimary} onClick={() => setTab('campaigns')}>
                    Create First Campaign →
                  </button>
                </div>
              )}
            </>
          ) : (
            !statsLoading && <div style={s.emptyState}>Click Refresh to load stats</div>
          )}
        </div>
      )}

      {/* Customers Tab */}
      {tab === 'customers' && (
        <div style={s.content}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <p style={{ color: '#6b7280', margin: 0 }}>
              {customersTotal > 0 ? `${customersTotal} customers imported` : 'No customers yet'}
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button style={s.btnSecondary} onClick={fetchCustomers} disabled={customersLoading}>
                🔄 Refresh
              </button>
              <button style={s.btnPrimary} onClick={handleImport} disabled={importing}>
                {importing ? '⟳ Importing…' : '⬇️ Import from Shopify'}
              </button>
            </div>
          </div>

          {importResult && (
            <div style={importResult.error ? s.errorBox : s.successBox}>
              {importResult.error
                ? `Import failed: ${importResult.error}`
                : `✅ Imported ${importResult.imported ?? 0} new, ${importResult.updated ?? 0} updated, ${importResult.total ?? 0} total in Shopify`}
            </div>
          )}

          {customersLoading ? (
            <div style={s.loading}>Loading customers…</div>
          ) : customers.length > 0 ? (
            <table style={s.table}>
              <thead>
                <tr style={s.tableHead}>
                  <th style={s.th}>Email</th>
                  <th style={s.th}>Name</th>
                  <th style={s.th}>Phone</th>
                  <th style={s.th}>Orders</th>
                  <th style={s.th}>Total Spent</th>
                  <th style={s.th}>Segment</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id} style={s.tableRow}>
                    <td style={s.td}>{c.email}</td>
                    <td style={s.td}>{[c.first_name, c.last_name].filter(Boolean).join(' ') || '—'}</td>
                    <td style={s.td}>{c.phone || '—'}</td>
                    <td style={s.td}>{c.orders_count ?? 0}</td>
                    <td style={s.td}>₹{Number(c.total_spent || 0).toLocaleString('en-IN')}</td>
                    <td style={s.td}><span style={s.badge}>{c.segment || 'all'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={s.emptyState}>
              <p>No customers imported yet.</p>
              <p style={{ fontSize: '13px', color: '#9ca3af' }}>
                Click "Import from Shopify" to pull your customer list.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Campaigns Tab */}
      {tab === 'journey' && (
        <div style={s.content}>
          <div style={{ ...s.section, marginBottom: '16px' }}>
            <div style={{ display: 'grid', gap: '14px' }}>
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#111827' }}>Email journey is now synced to the WhatsApp lifecycle</div>
                <div style={{ marginTop: '6px', fontSize: '13px', color: '#4b5563', lineHeight: 1.7 }}>
                  WhatsApp and email now follow the same lifecycle story. The old <strong>day2/day5/day15</strong> labels are internal aliases only; the operator view below uses the cleaner business stages.
                </div>
              </div>
              <div style={{ padding: '12px 14px', borderRadius: '10px', background: '#eff6ff', border: '1px solid #bfdbfe', fontSize: '12px', color: '#1d4ed8', lineHeight: 1.7 }}>
                Automatic stages fire immediately on <strong>new order</strong>, <strong>tracking/in-transit</strong>, and <strong>delivered</strong> events. Review, upsell, corporate, loyalty, and reactivation are checked in the same daily lifecycle windows used by WhatsApp.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                {EMAIL_LIFECYCLE_STAGES.map((stage) => (
                  <div key={stage.key} style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '14px', background: 'white' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#111827' }}>{stage.label}</div>
                      <span style={{ fontSize: '10px', fontWeight: 700, color: '#475569', background: stage.tone, borderRadius: '999px', padding: '3px 8px' }}>
                        {stage.aliases.join(' / ')}
                      </span>
                    </div>
                    <div style={{ marginTop: '8px', fontSize: '11px', color: '#374151', lineHeight: 1.6 }}>{stage.trigger}</div>
                    <div style={{ marginTop: '6px', fontSize: '11px', color: '#6b7280', lineHeight: 1.6 }}>{stage.description}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', gap: '10px', flexWrap: 'wrap' }}>
            <p style={{ color: '#6b7280', margin: 0 }}>{journeyTotal} customer{journeyTotal !== 1 ? 's' : ''} in journey view</p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                style={{ ...s.input, width: '220px' }}
                value={journeyFilters.search}
                onChange={(e) => setJourneyFilters({ ...journeyFilters, search: e.target.value })}
                placeholder="Search email or name"
              />
              <select
                style={{ ...s.input, width: '140px' }}
                value={journeyFilters.label}
                onChange={(e) => setJourneyFilters({ ...journeyFilters, label: e.target.value })}
              >
                <option value="all">All labels</option>
                <option value="hot">Hot</option>
                <option value="warm">Warm</option>
                <option value="cold">Cold</option>
                <option value="inactive">Inactive</option>
              </select>
              <select
                style={{ ...s.input, width: '160px' }}
                value={journeyFilters.segment}
                onChange={(e) => setJourneyFilters({ ...journeyFilters, segment: e.target.value })}
              >
                <option value="all">All segments</option>
                <option value="purchased">Purchased</option>
                <option value="high_value">High value</option>
                <option value="new">New</option>
                <option value="general">General</option>
              </select>
              <button style={s.btnSecondary} onClick={() => { fetchJourneyCustomers(); fetchEngagementSummary(); }} disabled={journeyLoading}>
                🔄 Refresh
              </button>
              <a
                href={apiUrl('/dashboard/journey/customers/export', {
                  label: journeyFilters.label !== 'all' ? journeyFilters.label : '',
                  segment: journeyFilters.segment !== 'all' ? journeyFilters.segment : '',
                  search: journeyFilters.search,
                })}
                download="journey_customers.csv"
                style={{ ...s.btnSecondary, textDecoration: 'none', display: 'inline-block' }}
              >
                ⬇️ Export CSV
              </a>
            </div>
          </div>

          {engagementSummary && (
            <div style={{ ...s.statsGrid, gridTemplateColumns: 'repeat(4, 1fr)' }}>
              <StatCard icon="🔥" label="Hot" value={engagementSummary.hot ?? 0} color="#dc2626" />
              <StatCard icon="🌤" label="Warm" value={engagementSummary.warm ?? 0} color="#ea580c" />
              <StatCard icon="❄️" label="Cold" value={engagementSummary.cold ?? 0} color="#2563eb" />
              <StatCard icon="🌙" label="Inactive" value={engagementSummary.inactive ?? 0} color="#6b7280" />
            </div>
          )}

          {journeyLoading ? (
            <div style={s.loading}>Loading journey customers…</div>
          ) : journeyCustomers.length > 0 ? (
            <table style={s.table}>
              <thead>
                <tr style={s.tableHead}>
                  <th style={s.th}>Email</th>
                  <th style={s.th}>Name</th>
                  <th style={s.th}>Label</th>
                  <th style={s.th}>Sent</th>
                  <th style={s.th}>Opens</th>
                  <th style={s.th}>Clicks</th>
                  <th style={s.th}>Purchases</th>
                  <th style={s.th}>Total Spent</th>
                  <th style={s.th}>Action</th>
                </tr>
              </thead>
              <tbody>
                {journeyCustomers.map((c) => (
                  <tr key={c.email} style={s.tableRow}>
                    <td style={s.td}>{c.email}</td>
                    <td style={s.td}>{c.full_name || '—'}</td>
                    <td style={s.td}><StatusBadge status={c.engagement_label} /></td>
                    <td style={s.td}>{c.total_sent ?? 0}</td>
                    <td style={s.td}>{c.total_opened ?? 0}</td>
                    <td style={s.td}>{c.total_clicked ?? 0}</td>
                    <td style={s.td}>{c.purchase_count ?? 0}</td>
                    <td style={s.td}>₹{Number(c.total_spent || 0).toLocaleString('en-IN')}</td>
                    <td style={s.td}>
                      <button style={s.btnSmallBlue} onClick={() => fetchJourneyDetail(c.email)}>
                        View Journey
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={s.emptyState}>No customers found for current filters.</div>
          )}

          {(journeyDetailLoading || journeyDetail?.ok) && (
            <div style={{ ...s.section, marginTop: '16px' }}>
              {journeyDetailLoading ? (
                <div style={s.loading}>Loading journey timeline…</div>
              ) : journeyDetail?.ok ? (
                <>
                  <h3 style={{ margin: '0 0 10px', fontSize: '16px' }}>
                    {journeyDetail.customer?.full_name || journeyDetail.customer?.email || selectedJourneyEmail}
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '12px' }}>
                    <MiniStat label="Purchases" value={journeyDetail.purchase?.purchase_count ?? 0} />
                    <MiniStat label="Total Spent" value={`₹${Number(journeyDetail.purchase?.total_spent || 0).toLocaleString('en-IN')}`} />
                    <MiniStat label="Last Purchase" value={journeyDetail.purchase?.last_purchase_at ? new Date(journeyDetail.purchase.last_purchase_at).toLocaleDateString() : '—'} />
                    <MiniStat label="Timeline Events" value={journeyDetail.timeline_count ?? 0} />
                  </div>
                  <div style={{ maxHeight: '320px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
                    <table style={s.table}>
                      <thead>
                        <tr style={s.tableHead}>
                          <th style={s.th}>Time</th>
                          <th style={s.th}>Source</th>
                          <th style={s.th}>Name</th>
                          <th style={s.th}>Status</th>
                          <th style={s.th}>Opened</th>
                          <th style={s.th}>Clicked</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(journeyDetail.timeline || []).map((t, idx) => (
                          <tr key={`${t.event_at || idx}-${idx}`} style={s.tableRow}>
                            <td style={s.td}>{t.event_at ? new Date(t.event_at).toLocaleString() : '—'}</td>
                            <td style={s.td}>{t.source}</td>
                              <td style={s.td}>{formatJourneyEventName(t)}</td>
                            <td style={s.td}><StatusBadge status={t.status || 'draft'} /></td>
                            <td style={s.td}>{t.opened_at ? new Date(t.opened_at).toLocaleString() : '—'}</td>
                            <td style={s.td}>{t.clicked_at ? new Date(t.clicked_at).toLocaleString() : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Campaigns Tab */}
      {tab === 'campaigns' && (
        <div style={s.content}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <p style={{ color: '#6b7280', margin: 0 }}>{campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''}</p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button style={s.btnSecondary} onClick={fetchCampaigns} disabled={campaignsLoading}>
                🔄 Refresh
              </button>
              <button style={s.btnPrimary} onClick={() => setShowCreate(!showCreate)}>
                {showCreate ? '✕ Cancel' : '+ New Campaign'}
              </button>
            </div>
          </div>

          {/* Create Campaign Form */}
          {showCreate && (
            <form onSubmit={handleCreateCampaign} style={s.createForm}>
              <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600 }}>Create New Campaign</h3>
              <div style={s.formGrid}>
                <div style={s.formField}>
                  <label style={s.label}>Campaign Name *</label>
                  <input
                    style={s.input}
                    value={newCampaign.name}
                    onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                    placeholder="e.g. Diwali Flash Sale 2025"
                    required
                  />
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Template *</label>
                  <select
                    style={s.input}
                    value={newCampaign.template_type}
                    onChange={(e) => setNewCampaign({ ...newCampaign, template_type: e.target.value })}
                  >
                    {TEMPLATES.map((t) => (
                      <option key={t.id} value={t.id}>{t.label} — {t.desc}</option>
                    ))}
                  </select>
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Audience Segment</label>
                  <select
                    style={s.input}
                    value={newCampaign.segment}
                    onChange={(e) => {
                      setNewCampaign({ ...newCampaign, segment: e.target.value });
                      fetchSegmentPreview(e.target.value);
                    }}
                  >
                    <option value="all">All active customers</option>
                    <option value="purchased">Purchased</option>
                    <option value="high_value">High value</option>
                    <option value="new">New</option>
                  </select>
                  {segmentPreviewLoading && (
                    <span style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px', display: 'block' }}>Counting…</span>
                  )}
                  {!segmentPreviewLoading && segmentPreviewCount !== null && (
                    <span style={{ fontSize: '11px', color: '#059669', marginTop: '4px', display: 'block' }}>
                      ✓ {segmentPreviewCount.toLocaleString()} customers will receive this campaign
                    </span>
                  )}
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Send interval (seconds per email)</label>
                  <input
                    style={s.input}
                    type="number"
                    min="0.2"
                    step="0.1"
                    value={newCampaign.send_interval_seconds}
                    onChange={(e) => setNewCampaign({ ...newCampaign, send_interval_seconds: e.target.value })}
                    placeholder="e.g. 1"
                  />
                </div>
                <div style={{ ...s.formField, gridColumn: '1 / -1' }}>
                  <label style={s.label}>Email Subject (optional, uses template default if blank)</label>
                  <input
                    style={s.input}
                    value={newCampaign.subject}
                    onChange={(e) => setNewCampaign({ ...newCampaign, subject: e.target.value })}
                    placeholder="e.g. 🎉 Exclusive offer just for you!"
                  />
                </div>
                <div style={{ ...s.formField, gridColumn: '1 / -1' }}>
                  <label style={s.label}>HTML Email (optional)</label>
                  <textarea
                    style={{ ...s.input, minHeight: '140px', fontFamily: 'monospace' }}
                    value={newCampaign.html_body}
                    onChange={(e) => setNewCampaign({ ...newCampaign, html_body: e.target.value })}
                    placeholder="Paste HTML here, or leave blank to use auto-generated template"
                  />
                  {newCampaign.html_body && (
                    <details style={{ marginTop: '8px' }}>
                      <summary style={{ fontSize: '12px', color: '#6366f1', cursor: 'pointer' }}>👁 Preview HTML</summary>
                      <iframe
                        srcDoc={newCampaign.html_body}
                        style={{ width: '100%', height: '320px', border: '1px solid #e5e7eb', borderRadius: '6px', marginTop: '8px' }}
                        sandbox="allow-same-origin"
                        title="Email HTML preview"
                      />
                    </details>
                  )}
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Discount Code</label>
                  <input
                    style={s.input}
                    value={newCampaign.discount_code}
                    onChange={(e) => setNewCampaign({ ...newCampaign, discount_code: e.target.value })}
                    placeholder="e.g. DIWALI20"
                  />
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Discount %</label>
                  <input
                    style={s.input}
                    type="number"
                    value={newCampaign.discount_percent}
                    onChange={(e) => setNewCampaign({ ...newCampaign, discount_percent: e.target.value })}
                    placeholder="e.g. 20"
                  />
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Product Name</label>
                  <input
                    style={s.input}
                    value={newCampaign.product_name}
                    onChange={(e) => setNewCampaign({ ...newCampaign, product_name: e.target.value })}
                    placeholder="e.g. Organic Spice Bundle"
                  />
                </div>
                <div style={s.formField}>
                  <label style={s.label}>Custom Message</label>
                  <input
                    style={s.input}
                    value={newCampaign.custom_message}
                    onChange={(e) => setNewCampaign({ ...newCampaign, custom_message: e.target.value })}
                    placeholder="e.g. Limited stock — grab yours now!"
                  />
                </div>
              </div>
              {createError && <div style={{ ...s.errorBox, marginTop: '12px' }}>{createError}</div>}
              <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
                <button type="submit" style={s.btnPrimary} disabled={creating}>
                  {creating ? '⟳ Creating…' : '✅ Create Campaign'}
                </button>
                <button type="button" style={s.btnSecondary} onClick={() => setShowCreate(false)}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Send Result */}
          {sendResult && (
            <div style={sendResult.error ? s.errorBox : s.successBox}>
              {sendResult.error
                ? `Send failed: ${sendResult.error}`
                    : `✅ Campaign queued! ${sendResult.queued ?? 0} emails scheduled at ${sendResult.send_interval_seconds ?? 1}s interval.`}
            </div>
          )}

          {/* Campaigns List */}
          {campaignsLoading ? (
            <div style={s.loading}>Loading campaigns…</div>
          ) : campaigns.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {campaigns.map((c) => (
                <div key={c.campaign_id} style={s.campaignCard}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '15px', marginBottom: '4px' }}>{c.name}</div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={s.badge}>{c.template_type}</span>
                        <StatusBadge status={c.queue_status || c.status} />
                        {c.sent_count > 0 && (
                          <span style={{ fontSize: '12px', color: '#6b7280' }}>
                            {c.sent_count} sent · {c.open_count ?? 0} opens · {c.click_count ?? 0} clicks
                          </span>
                        )}
                        {progressByCampaign[c.campaign_id] && (
                          <span style={{ fontSize: '12px', color: '#6b7280' }}>
                            Progress: {progressByCampaign[c.campaign_id].sent}/{progressByCampaign[c.campaign_id].total} sent · {progressByCampaign[c.campaign_id].failed} failed
                          </span>
                        )}
                      </div>
                      {c.subject && (
                        <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
                          Subject: {c.subject}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                      <button
                        style={s.btnSmallBlue}
                        onClick={() => fetchAnalytics(c.campaign_id)}
                      >
                        📊 Analytics
                      </button>
                      {c.status !== 'sent' && c.queue_status !== 'completed' && (
                        <button
                          style={s.btnSmallGreen}
                          onClick={() => handleSendCampaign(c.campaign_id)}
                          disabled={sending}
                        >
                          {sending && sendCampaignId === String(c.campaign_id) ? '⟳ Queueing…' : '📤 Send'}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Analytics Drawer */}
                  {selectedCampaign === c.campaign_id && (
                    <div style={s.analyticsDrawer}>
                      {analyticsLoading ? (
                        <div style={s.loading}>Loading analytics…</div>
                      ) : analytics ? (
                        <>
                          <div style={s.analyticsGrid}>
                            <MiniStat label="Sent" value={analytics.total_sent ?? 0} />
                            <MiniStat label="Opened" value={analytics.total_opened ?? 0} />
                            <MiniStat label="Clicked" value={analytics.total_clicked ?? 0} />
                            <MiniStat
                              label="Open Rate"
                              value={analytics.total_sent > 0 ? `${((analytics.total_opened / analytics.total_sent) * 100).toFixed(1)}%` : '—'}
                            />
                          </div>

                          {analytics.recipients?.length > 0 && (
                            <div style={{ marginTop: '12px' }}>
                              <div style={{ fontSize: '12px', fontWeight: 600, color: '#374151', marginBottom: '6px' }}>Recipients</div>
                              <div style={s.recipientList}>
                                {analytics.recipients.slice(0, 20).map((r, i) => (
                                  <div key={i} style={s.recipientRow}>
                                    <span style={{ flex: 1, fontSize: '12px' }}>{r.email}</span>
                                    <span style={{ fontSize: '11px', color: r.opened_at ? '#10b981' : '#9ca3af' }}>
                                      {r.opened_at ? '👁 Opened' : 'Not opened'}
                                    </span>
                                    <span style={{ fontSize: '11px', color: r.clicked_at ? '#3b82f6' : '#9ca3af', marginLeft: '8px' }}>
                                      {r.clicked_at ? '🖱 Clicked' : ''}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        <div style={{ fontSize: '13px', color: '#9ca3af' }}>No analytics data</div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={s.emptyState}>
              <p>No campaigns yet.</p>
              <p style={{ fontSize: '13px', color: '#9ca3af' }}>
                Click "+ New Campaign" to create your first email campaign.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Logs & Bounces Tab ─────────────────────────────────────────────── */}
      {tab === 'logs' && (
        <div style={s.content}>
          {/* Bounce Summary Cards */}
          {bounceSummary && (
            <div style={{ ...s.statsGrid, marginBottom: '20px' }}>
              <StatCard icon="📤" label="Total Failed" value={bounceSummary.total_failed ?? 0} color="#ef4444" />
              <StatCard icon="🚫" label="Suppressed" value={bounceSummary.total_suppressed ?? 0} color="#f59e0b" />
              {(bounceSummary.by_type || []).map((bt) => (
                <StatCard
                  key={bt.error_type}
                  icon={bt.error_type === 'hard' ? '💀' : bt.error_type === 'soft' ? '📮' : '⚡'}
                  label={`${bt.error_type} bounces`}
                  value={bt.count}
                  color={bt.error_type === 'hard' ? '#dc2626' : bt.error_type === 'soft' ? '#d97706' : '#6366f1'}
                />
              ))}
            </div>
          )}

          {/* Filter bar */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '16px', alignItems: 'flex-end' }}>
            <div>
              <label style={{ ...s.label, display: 'block' }}>Campaign</label>
              <select
                style={{ ...s.input, width: '200px' }}
                value={logsFilters.campaign_id}
                onChange={(e) => setLogsFilters({ ...logsFilters, campaign_id: e.target.value })}
              >
                <option value="">All campaigns</option>
                {campaigns.map((c) => (
                  <option key={c.campaign_id} value={c.campaign_id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ ...s.label, display: 'block' }}>Status</label>
              <select
                style={{ ...s.input, width: '140px' }}
                value={logsFilters.status}
                onChange={(e) => setLogsFilters({ ...logsFilters, status: e.target.value })}
              >
                <option value="">All</option>
                <option value="sent">Sent</option>
                <option value="failed">Failed</option>
                <option value="suppressed">Suppressed</option>
              </select>
            </div>
            <div>
              <label style={{ ...s.label, display: 'block' }}>Email search</label>
              <input
                style={{ ...s.input, width: '200px' }}
                value={logsFilters.email_search}
                onChange={(e) => setLogsFilters({ ...logsFilters, email_search: e.target.value })}
                placeholder="e.g. @gmail.com"
              />
            </div>
            <button style={s.btnSecondary} onClick={() => { fetchLogs(); fetchBounceSummary(); }} disabled={logsLoading}>
              🔍 Filter
            </button>
            <button
              style={{ ...s.btnPrimary, background: retryResult?.ok ? '#10b981' : '#6366f1' }}
              onClick={handleRetryTransient}
              disabled={retryingTransient}
              title="Re-queue emails that failed with transient errors (network, timeout). Hard/soft bounces are skipped."
            >
              {retryingTransient ? '⟳ Retrying…' : '♻️ Retry Transient Failures'}
            </button>
          </div>

          {retryResult && (
            <div style={retryResult.ok ? s.successBox : s.errorBox}>
              {retryResult.ok
                ? `✅ ${retryResult.requeued} emails re-queued for retry`
                : `Error: ${retryResult.error}`}
            </div>
          )}

          {/* Send Logs Table */}
          {logsLoading ? (
            <div style={s.loading}>Loading logs…</div>
          ) : logs.length > 0 ? (
            <>
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '8px' }}>
                Showing {logs.length} of {logsTotal} log entries
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={s.table}>
                  <thead>
                    <tr>
                      {['Email', 'Campaign', 'Status', 'Error Type', 'Error', 'Attempt', 'Logged At', 'Actions'].map((h) => (
                        <th key={h} style={s.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((l) => (
                      <tr key={l.log_id}>
                        <td style={s.td}>{l.email}</td>
                        <td style={s.td}>{l.campaign_name || l.campaign_id?.slice(0, 12)}</td>
                        <td style={s.td}><StatusBadge status={l.status} /></td>
                        <td style={s.td}>
                          {l.error_type ? (
                            <StatusBadge status={l.error_type === 'hard' ? 'failed' : l.error_type === 'soft' ? 'warm' : 'cold'} />
                          ) : '—'}
                        </td>
                        <td style={{ ...s.td, maxWidth: '240px', fontSize: '11px', color: '#ef4444', wordBreak: 'break-all' }}>
                          {l.error_raw ? l.error_raw.slice(0, 120) : '—'}
                        </td>
                        <td style={s.td}>{l.attempt}</td>
                        <td style={s.td}>{l.logged_at ? new Date(l.logged_at).toLocaleString() : '—'}</td>
                        <td style={s.td}>
                          {l.status === 'failed' && (
                            <button
                              style={{ ...s.btnSmallGray, fontSize: '11px' }}
                              onClick={() => handleSuppress(l.email, l.error_type === 'hard' ? 'bounce' : 'manual')}
                              title="Add to suppression list"
                            >
                              🚫 Suppress
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div style={s.emptyState}>No send log entries match the current filter.</div>
          )}

          {/* Suppression List */}
          <div style={{ marginTop: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>
                🚫 Suppression List ({suppressionTotal})
              </h3>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  style={{ ...s.input, width: '200px' }}
                  value={suppressEmail}
                  onChange={(e) => setSuppressEmail(e.target.value)}
                  placeholder="email@example.com"
                />
                <select
                  style={{ ...s.input, width: '140px' }}
                  value={suppressReason}
                  onChange={(e) => setSuppressReason(e.target.value)}
                >
                  <option value="manual">Manual</option>
                  <option value="unsubscribed">Unsubscribed</option>
                  <option value="bounce">Bounce</option>
                  <option value="complaint">Complaint</option>
                </select>
                <button
                  style={s.btnPrimary}
                  disabled={suppressing || !suppressEmail}
                  onClick={async () => {
                    setSuppressing(true);
                    await handleSuppress(suppressEmail, suppressReason);
                    setSuppressEmail('');
                    setSuppressing(false);
                  }}
                >
                  {suppressing ? '⟳' : '+ Add'}
                </button>
              </div>
            </div>
            {suppressionList.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={s.table}>
                  <thead>
                    <tr>
                      {['Email', 'Reason', 'Bounce Type', 'Source', 'Suppressed At', 'Remove'].map((h) => (
                        <th key={h} style={s.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {suppressionList.map((sup) => (
                      <tr key={sup.id}>
                        <td style={s.td}>{sup.email}</td>
                        <td style={s.td}>{sup.reason}</td>
                        <td style={s.td}>{sup.bounce_type || '—'}</td>
                        <td style={s.td}>{sup.source}</td>
                        <td style={s.td}>{sup.created_at ? new Date(sup.created_at).toLocaleDateString() : '—'}</td>
                        <td style={s.td}>
                          <button
                            style={{ ...s.btnSmallGray, fontSize: '11px', color: '#dc2626' }}
                            onClick={() => handleUnsuppress(sup.email)}
                          >
                            ✕ Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ fontSize: '13px', color: '#9ca3af' }}>No suppressed emails.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div style={{ ...s.statCard, borderTop: `3px solid ${color}` }}>
      <div style={{ fontSize: '22px', marginBottom: '4px' }}>{icon}</div>
      <div style={{ fontSize: '24px', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>{label}</div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div style={{ textAlign: 'center', padding: '8px 12px', background: '#f9fafb', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
      <div style={{ fontSize: '18px', fontWeight: 700, color: '#111827' }}>{value}</div>
      <div style={{ fontSize: '11px', color: '#6b7280' }}>{label}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    draft: { bg: '#f3f4f6', text: '#6b7280' },
    scheduled: { bg: '#ede9fe', text: '#5b21b6' },
    queued: { bg: '#dbeafe', text: '#1d4ed8' },
    sent: { bg: '#d1fae5', text: '#065f46' },
    completed: { bg: '#d1fae5', text: '#065f46' },
    sending: { bg: '#dbeafe', text: '#1e40af' },
    failed: { bg: '#fee2e2', text: '#991b1b' },
    suppressed: { bg: '#fef3c7', text: '#92400e' },
    hot: { bg: '#fee2e2', text: '#991b1b' },
    warm: { bg: '#ffedd5', text: '#9a3412' },
    cold: { bg: '#dbeafe', text: '#1e3a8a' },
    inactive: { bg: '#f3f4f6', text: '#4b5563' },
  };
  const c = colors[status] || colors.draft;
  return (
    <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '99px', background: c.bg, color: c.text }}>
      {status}
    </span>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────
const s = {
  panel: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#f9fafb',
    overflow: 'hidden',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 28px 0',
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
    flexShrink: 0,
  },
  panelTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 700,
    color: '#111827',
  },
  panelSubtitle: {
    margin: '2px 0 0',
    fontSize: '13px',
    color: '#6b7280',
  },
  tabRow: {
    display: 'flex',
    gap: '4px',
    padding: '0 28px',
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
    flexShrink: 0,
  },
  tabBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    color: '#6b7280',
    transition: 'all 0.15s',
  },
  tabBtnActive: {
    color: '#3b82f6',
    borderBottom: '2px solid #3b82f6',
    fontWeight: 600,
  },
  statusPill: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 10px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: 700,
  },
  statusPillMuted: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 10px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: 600,
    background: '#f3f4f6',
    color: '#4b5563',
  },
  accessNotice: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    padding: '10px 28px',
    background: '#fffbeb',
    color: '#92400e',
    borderBottom: '1px solid #fde68a',
    fontSize: '12px',
    lineHeight: 1.5,
    flexShrink: 0,
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px 28px',
  },
  configBox: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    background: '#f9fafb',
  },
  configCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '36px',
    width: '360px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
    marginBottom: '24px',
  },
  statCard: {
    background: 'white',
    borderRadius: '10px',
    padding: '16px',
    textAlign: 'center',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  section: {
    background: 'white',
    borderRadius: '10px',
    padding: '20px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  sectionTitle: {
    margin: '0 0 12px',
    fontSize: '14px',
    fontWeight: 600,
    color: '#374151',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  tableHead: {
    background: '#f9fafb',
  },
  th: {
    padding: '8px 12px',
    textAlign: 'left',
    fontSize: '11px',
    fontWeight: 600,
    color: '#6b7280',
    textTransform: 'uppercase',
    borderBottom: '1px solid #e5e7eb',
  },
  tableRow: {
    borderBottom: '1px solid #f3f4f6',
  },
  td: {
    padding: '10px 12px',
    color: '#374151',
  },
  badge: {
    display: 'inline-block',
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '99px',
    background: '#eff6ff',
    color: '#3b82f6',
  },
  input: {
    width: '100%',
    padding: '9px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '13px',
    outline: 'none',
    boxSizing: 'border-box',
  },
  btnPrimary: {
    padding: '9px 20px',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnSecondary: {
    padding: '9px 16px',
    background: 'white',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  btnSmallBlue: {
    padding: '6px 12px',
    background: '#eff6ff',
    color: '#3b82f6',
    border: '1px solid #dbeafe',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnSmallGreen: {
    padding: '6px 12px',
    background: '#d1fae5',
    color: '#065f46',
    border: '1px solid #a7f3d0',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnSmallGray: {
    padding: '6px 12px',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  errorBox: {
    background: '#fee2e2',
    color: '#991b1b',
    padding: '10px 14px',
    borderRadius: '6px',
    fontSize: '13px',
    marginBottom: '12px',
  },
  successBox: {
    background: '#d1fae5',
    color: '#065f46',
    padding: '10px 14px',
    borderRadius: '6px',
    fontSize: '13px',
    marginBottom: '12px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '48px 24px',
    color: '#6b7280',
    fontSize: '14px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
  },
  loading: {
    textAlign: 'center',
    padding: '32px',
    color: '#9ca3af',
    fontSize: '13px',
  },
  createForm: {
    background: 'white',
    borderRadius: '10px',
    padding: '20px',
    marginBottom: '20px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
    border: '1px solid #e5e7eb',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  formField: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  label: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#374151',
  },
  campaignCard: {
    background: 'white',
    borderRadius: '10px',
    padding: '16px 20px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
    border: '1px solid #e5e7eb',
  },
  analyticsDrawer: {
    marginTop: '14px',
    paddingTop: '14px',
    borderTop: '1px solid #f3f4f6',
  },
  analyticsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '8px',
  },
  recipientList: {
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    overflow: 'hidden',
    maxHeight: '200px',
    overflowY: 'auto',
  },
  recipientRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '6px 10px',
    borderBottom: '1px solid #f3f4f6',
    fontSize: '12px',
  },
};
