/**
 * WhatsApp workspace with dashboard, customers, journey, templates, and logs.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = 'https://track.pureleven.com/api';
const SYNC_INTERVAL = 30 * 60 * 1000;
const MAIN_TABS = [
  ['dashboard', 'Dashboard'],
  ['customers', 'Customers'],
  ['journey', 'Journey'],
  ['campaigns', 'Templates'],
  ['logs', 'Logs'],
];
const CAMPAIGN_TABS = [
  ['send', 'Send Message'],
  ['create', 'Create Template'],
];
const AUDIENCE_TYPE_OPTIONS = [
  ['all', 'All audience types'],
  ['purchased', 'Purchased'],
  ['interested', 'Interested'],
  ['abandoned', 'Abandoned'],
  ['whatsapp_lead', 'WhatsApp leads'],
  ['promotional_lead', 'Promotional Lead Numbers'],
];
const STATUS_OPTIONS = [
  ['interested', 'Interested'],
  ['purchased', 'Purchased'],
  ['lead', 'Lead'],
  ['active', 'Active'],
  ['cold', 'Cold'],
  ['warm', 'Warm'],
  ['hot', 'Hot'],
  ['abandoned', 'Abandoned'],
];
const DELIVERY_CHANNEL_OPTIONS = [
  ['whatsapp', 'WhatsApp'],
  ['email', 'Email'],
];
const SCORE_BUCKET_OPTIONS = [
  { id: 'buyers', label: 'Buyers', range: '90-100', min: 90, max: 100, tone: 'amber' },
  { id: 'purchase_intent', label: 'Intent', range: '80-89', min: 80, max: 89, tone: 'green' },
  { id: 'warm', label: 'Warm', range: '50-79', min: 50, max: 79, tone: 'blue' },
  { id: 'behavioral', label: 'Behavioral', range: '10-49', min: 10, max: 49, tone: 'indigo' },
  { id: 'cold', label: 'Cold', range: '0-9', min: 0, max: 9, tone: 'slate' },
];
const CURATED_LABEL_OPTIONS = [
  'interested',
  'interest',
  'intent',
  'purchased',
  'purchase',
  'abandoned',
  'whatsapp_lead',
  'promotional_lead',
  'eng_customer',
  'mal_customer',
];

function countdownStr(nextSyncAt) {
  const diff = Math.max(0, nextSyncAt - Date.now());
  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function highlightVars(text) {
  if (!text) return null;
  const parts = text.split(/(\{\{\d+\}\})/g);
  return parts.map((part, index) => (
    /^\{\{\d+\}\}$/.test(part)
      ? (
        <mark
          key={`${part}-${index}`}
          style={{
            background: '#fef9c3',
            borderRadius: '3px',
            padding: '0 2px',
            fontWeight: 700,
            color: '#854d0e',
          }}
        >
          {part}
        </mark>
        )
      : part
  ));
}

function formatDateTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatMoney(value) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

async function readJson(res) {
  try {
    return await res.json();
  } catch {
    return {};
  }
}

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

function audienceTypeLabel(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'purchased') return 'Purchased';
  if (normalized === 'interested') return 'Interested';
  if (normalized === 'abandoned') return 'Abandoned';
  if (normalized === 'whatsapp_lead') return 'WhatsApp lead';
  if (normalized === 'promotional_lead') return 'Promotional lead';
  return 'General';
}

function audienceTypeTone(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'purchased') return 'amber';
  if (normalized === 'interested') return 'green';
  if (normalized === 'abandoned') return 'red';
  if (normalized === 'whatsapp_lead') return 'green';
  if (normalized === 'promotional_lead') return 'indigo';
  return 'slate';
}

function toggleListValue(values, value) {
  const list = Array.isArray(values) ? values : [];
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value];
}

function normalizePhoneLookup(value) {
  return String(value || '').replace(/\D/g, '');
}

function scoreBucketFor(score) {
  const numericScore = Number(score || 0);
  return SCORE_BUCKET_OPTIONS.find((bucket) => numericScore >= bucket.min && numericScore <= bucket.max)?.id || 'cold';
}

function toneColors(tone) {
  const palette = {
    green: { background: '#f0fdf4', border: '#bbf7d0', text: '#166534' },
    blue: { background: '#eff6ff', border: '#bfdbfe', text: '#1d4ed8' },
    amber: { background: '#fffbeb', border: '#fde68a', text: '#92400e' },
    slate: { background: '#f8fafc', border: '#e2e8f0', text: '#334155' },
    red: { background: '#fef2f2', border: '#fecaca', text: '#b91c1c' },
    indigo: { background: '#eef2ff', border: '#c7d2fe', text: '#4338ca' },
  };
  return palette[tone] || palette.slate;
}

function PanelSection({ title, subtitle, actions, children }) {
  return (
    <div style={{ background: 'white', borderRadius: '14px', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)' }}>
      <div style={{ padding: '18px 20px 16px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#111827' }}>{title}</div>
          {subtitle ? <div style={{ marginTop: '4px', fontSize: '12px', color: '#6b7280', lineHeight: 1.6 }}>{subtitle}</div> : null}
        </div>
        {actions ? <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>{actions}</div> : null}
      </div>
      <div style={{ padding: '18px 20px' }}>{children}</div>
    </div>
  );
}

function StatCard({ label, value, tone = 'slate', caption }) {
  const colors = toneColors(tone);
  return (
    <div style={{ background: colors.background, border: `1px solid ${colors.border}`, borderRadius: '14px', padding: '16px' }}>
      <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
      <div style={{ marginTop: '8px', fontSize: '28px', fontWeight: 800, color: colors.text, lineHeight: 1.1 }}>{value}</div>
      {caption ? <div style={{ marginTop: '8px', fontSize: '12px', color: '#64748b' }}>{caption}</div> : null}
    </div>
  );
}

function Badge({ label, tone = 'slate' }) {
  const colors = toneColors(tone);
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '999px', fontSize: '11px', fontWeight: 700, color: colors.text, background: colors.background, border: `1px solid ${colors.border}` }}>
      {label}
    </span>
  );
}

function StatusPill({ status }) {
  const normalized = String(status || 'unknown').toLowerCase();
  const tone = normalized === 'read'
    ? 'indigo'
    : normalized === 'delivered'
      ? 'green'
      : normalized === 'failed'
        ? 'red'
        : normalized === 'sent'
          ? 'blue'
          : 'slate';
  return <Badge label={normalized.replace(/_/g, ' ')} tone={tone} />;
}

function templatePreviewText(template) {
  return template?.body?.meta_text
    || template?.body?.text
    || template?.header?.text
    || template?.footer?.text
    || 'No preview available';
}

function campaignExecutionSummary(item) {
  const queue = item?.queue || {};
  const sends = item?.sends || {};
  const total = Number(item?.total_recipients || queue.total || sends.total || 0);
  const sent = Math.max(Number(item?.sent_count || 0), Number(queue.sent || 0), Number(sends.sent || 0));
  const failed = Math.max(Number(item?.error_count || 0), Number(queue.failed || 0), Number(sends.failed || 0));
  const suppressed = Number(queue.suppressed || 0);
  const completed = Math.min(total || (sent + failed + suppressed), sent + failed + suppressed);
  return {
    total,
    sent,
    failed,
    suppressed,
    pending: Number(queue.pending || 0) + Number(queue.queued || 0),
    sending: Number(queue.sending || 0),
    progress: total ? Math.round((completed / total) * 100) : 0,
  };
}

function EmptyState({ title, body }) {
  return (
    <div style={{ padding: '36px 18px', border: '1px dashed #cbd5e1', borderRadius: '12px', textAlign: 'center', color: '#64748b', background: '#f8fafc' }}>
      <div style={{ fontSize: '14px', fontWeight: 700, color: '#334155' }}>{title}</div>
      <div style={{ marginTop: '6px', fontSize: '12px', lineHeight: 1.6 }}>{body}</div>
    </div>
  );
}

export default function WhatsAppWorkspace() {
  const [mainTab, setMainTab] = useState('dashboard');
  const [campaignTab, setCampaignTab] = useState('send');
  const [channel, setChannel] = useState('meta');
  const [phone, setPhone] = useState('919447744583');
  const [wabisTemplates, setWabisTemplates] = useState([]);
  const [metaTemplates, setMetaTemplates] = useState([]);
  const [metaConfigured, setMetaConfigured] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState(null);
  const [lastSynced, setLastSynced] = useState(null);
  const [nextSyncAt, setNextSyncAt] = useState(null);
  const [countdown, setCountdown] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [params, setParams] = useState([]);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [sendHistory, setSendHistory] = useState([]);
  const [headerImageUrl, setHeaderImageUrl] = useState('');
  const [newTpl, setNewTpl] = useState({ name: '', category: 'MARKETING', language: 'en_US', body: '', header: '', footer: '' });
  const [templateDraft, setTemplateDraft] = useState({ name: '', category: 'MARKETING', language: 'en_US', body: '', header: '', footer: '' });
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState(null);

  const [dashboard, setDashboard] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState(null);
  const [salesOs, setSalesOs] = useState(null);
  const [salesOsLoading, setSalesOsLoading] = useState(false);
  const [salesOsAction, setSalesOsAction] = useState('');
  const [salesOsResult, setSalesOsResult] = useState(null);

  const [audienceSearch, setAudienceSearch] = useState('');
  const [audienceLeadType, setAudienceLeadType] = useState('all');
  const [audienceScoreMin, setAudienceScoreMin] = useState(0);
  const [audienceScoreMax, setAudienceScoreMax] = useState(100);
  const [audienceLanguage, setAudienceLanguage] = useState('all');
  const [audiencePage, setAudiencePage] = useState(1);
  const [audiencePageSize] = useState(50);
  const [audienceRows, setAudienceRows] = useState([]);
  const [audienceTotal, setAudienceTotal] = useState(0);
  const [audienceSummary, setAudienceSummary] = useState(null);
  const [audienceLoading, setAudienceLoading] = useState(false);
  const [importing, setImporting] = useState('');
  const [importResult, setImportResult] = useState(null);

  // ── Campaign Builder ─────────────────────────────────────────────────────
  const [campaignStep, setCampaignStep] = useState(0); // 0=idle, 1-4=steps
  const [campaignName, setCampaignName] = useState('');
  const [campaignFilters, setCampaignFilters] = useState({
    score_min: 70,
    score_max: 100,
    score_buckets: [],
    lead_types: [],
    labels: [],
    statuses: [],
    engagement_labels: [],
    language: 'all',
    date_field: 'updated_at',
    date_from: '',
    date_to: '',
    delivery_channels: ['whatsapp'],
  });
  const [campaignTemplate, setCampaignTemplate] = useState(null);
  const [emailSubject, setEmailSubject] = useState('');
  const [emailHtml, setEmailHtml] = useState('');
  const [campaignScheduleType, setCampaignScheduleType] = useState('now');
  const [campaignScheduledAt, setCampaignScheduledAt] = useState('');
  const [campaignSyncMeta, setCampaignSyncMeta] = useState(false);
  const [campaignEstimate, setCampaignEstimate] = useState(null);
  const [campaignEstimateError, setCampaignEstimateError] = useState(null);
  const [campaignEstimating, setCampaignEstimating] = useState(false);
  const [campaignCreating, setCampaignCreating] = useState(false);
  const [campaignResult, setCampaignResult] = useState(null);
  const [aiSuggestion, setAiSuggestion] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiExpanded, setAiExpanded] = useState(false);
  const [availableLabels, setAvailableLabels] = useState([]);
  const [labelSearch, setLabelSearch] = useState('');
  const [labelsLoading, setLabelsLoading] = useState(false);
  const campaignDeliveryChannels = useMemo(() => new Set(campaignFilters.delivery_channels || ['whatsapp']), [campaignFilters.delivery_channels]);
  const campaignUsesWhatsApp = campaignDeliveryChannels.has('whatsapp');
  const campaignUsesEmail = campaignDeliveryChannels.has('email');

  const [journeyFilters, setJourneyFilters] = useState({ search: '', stage: 'all', segment: 'all', subscription: 'all' });
  const [journeyPhoneSearch, setJourneyPhoneSearch] = useState('');
  const [journeyRows, setJourneyRows] = useState([]);
  const [journeyTotal, setJourneyTotal] = useState(0);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [selectedJourneyId, setSelectedJourneyId] = useState('');
  const [journeyDetail, setJourneyDetail] = useState(null);
  const [journeyDetailLoading, setJourneyDetailLoading] = useState(false);
  const [journeyCampaignRows, setJourneyCampaignRows] = useState([]);
  const [journeyCampaignTotal, setJourneyCampaignTotal] = useState(0);
  const [journeyCampaignLoading, setJourneyCampaignLoading] = useState(false);
  const [journeyPipeline, setJourneyPipeline] = useState(null);
  const [journeyPipelineLoading, setJourneyPipelineLoading] = useState(false);
  const [orchestrating, setOrchestrating] = useState(false);
  const [orchestrateResult, setOrchestrateResult] = useState(null);
  const [lifecycleStageConfigs, setLifecycleStageConfigs] = useState([]);
  const [lifecycleStageLoading, setLifecycleStageLoading] = useState(false);
  const [selectedLifecycleStage, setSelectedLifecycleStage] = useState('');
  const [selectedLifecycleTemplateName, setSelectedLifecycleTemplateName] = useState('');
  const [lifecycleTemplateSearch, setLifecycleTemplateSearch] = useState('');
  const [lifecycleTemplateSaving, setLifecycleTemplateSaving] = useState(false);
  const [lifecycleTemplateResult, setLifecycleTemplateResult] = useState(null);
  const [lifecycleCreateOpen, setLifecycleCreateOpen] = useState(false);

  const [logsFilters, setLogsFilters] = useState({ search: '', status: 'all', template_name: '' });
  const [logRows, setLogRows] = useState([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logSummary, setLogSummary] = useState({});
  const [logsLoading, setLogsLoading] = useState(false);

  const syncTimerRef = useRef(null);
  const countdownRef = useRef(null);
  const csvInputRef = useRef(null);
  const xmlInputRef = useRef(null);
  const xlsxInputRef = useRef(null);

  const syncTemplates = useCallback(async (showSpinner = true, forceRefresh = false) => {
    if (showSpinner) setSyncing(true);
    setSyncError(null);

    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/templates${forceRefresh ? '?refresh=true' : ''}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      const wabis = Array.isArray(data.wabis) ? data.wabis : [];
      const meta = Array.isArray(data.meta) ? data.meta : [];
      const nextChannel = channel === 'meta'
        ? (meta.length > 0 ? 'meta' : 'wabis')
        : (wabis.length > 0 ? 'wabis' : 'meta');
      const visibleTemplates = nextChannel === 'meta' ? meta : wabis;
      const nextSelected = visibleTemplates.some((item) => String(item.id) === String(selectedId))
        ? selectedId
        : (visibleTemplates[0]?.id ?? null);
      const nextTemplate = visibleTemplates.find((item) => String(item.id) === String(nextSelected));

      setWabisTemplates(wabis);
      setMetaTemplates(meta);
      setMetaConfigured(Boolean(data.meta_configured));
      setChannel(nextChannel);
      setSelectedId(nextSelected);
      setParams(Array(nextTemplate?.total_vars || 0).fill(''));
      setLastSynced(new Date());
      setNextSyncAt(Date.now() + SYNC_INTERVAL);
    } catch (error) {
      setSyncError(error.message);
    } finally {
      setSyncing(false);
    }
  }, [channel, selectedId]);

  const loadDashboard = useCallback(async () => {
    setDashboardLoading(true);
    setDashboardError(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/dashboard`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setDashboard(data);
    } catch (error) {
      setDashboardError(error.message);
    } finally {
      setDashboardLoading(false);
    }
  }, []);

  const loadSalesOs = useCallback(async () => {
    setSalesOsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/sales-os`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setSalesOs(data);
    } catch (error) {
      setSalesOsResult({ ok: false, detail: error.message });
    } finally {
      setSalesOsLoading(false);
    }
  }, []);

  const retryLifecycle = useCallback(async (eventType, dryRun = false) => {
    setSalesOsAction(`${dryRun ? 'preview' : 'retry'}-${eventType}`);
    setSalesOsResult(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/orders/retry-lifecycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: eventType, limit: 50, dry_run: dryRun }),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setSalesOsResult({ ok: true, title: dryRun ? 'Lifecycle preview complete' : 'Lifecycle retry complete', data, eventType, dryRun });
      if (!dryRun) await Promise.all([loadSalesOs(), loadDashboard()]);
    } catch (error) {
      setSalesOsResult({ ok: false, detail: error.message });
    } finally {
      setSalesOsAction('');
    }
  }, [loadDashboard, loadSalesOs]);

  const syncRetargetingAudience = useCallback(async (audienceKey, platforms = ['meta', 'google']) => {
    setSalesOsAction(`retarget-${audienceKey}`);
    setSalesOsResult(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/retargeting/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audience_key: audienceKey, platforms }),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setSalesOsResult({ ok: data.ok, title: `${data.audience_name} sync`, data });
      await loadSalesOs();
    } catch (error) {
      setSalesOsResult({ ok: false, detail: error.message });
    } finally {
      setSalesOsAction('');
    }
  }, [loadSalesOs]);

  const startFunnelForAudience = useCallback((audienceKey, goalLabel) => {
    const presets = {
      purchased: { lead_types: ['purchased'], score_min: 60, score_max: 100, score_buckets: ['buyers'], labels: ['purchased'], statuses: ['purchased'], engagement_labels: [], delivery_channels: ['whatsapp', 'email'] },
      interested: { lead_types: ['interested', 'whatsapp_lead'], score_min: 50, score_max: 100, score_buckets: ['warm', 'purchase_intent'], labels: ['interested'], statuses: ['interested'], engagement_labels: ['warm', 'hot'] },
      non_purchased: { lead_types: ['interested', 'whatsapp_lead'], score_min: 40, score_max: 100, score_buckets: ['warm', 'purchase_intent'], labels: ['interested'], statuses: [], engagement_labels: [] },
      abandoned: { lead_types: ['abandoned'], score_min: 20, score_max: 100, score_buckets: ['warm', 'purchase_intent'], labels: ['abandoned'], statuses: ['abandoned'], engagement_labels: [] },
      whatsapp_leads: { lead_types: ['whatsapp_lead'], score_min: 30, score_max: 100, score_buckets: ['warm', 'purchase_intent'], labels: [], statuses: [], engagement_labels: [] },
      hot_leads: { lead_types: [], score_min: 80, score_max: 100, score_buckets: ['purchase_intent', 'buyers'], labels: [], statuses: ['hot'], engagement_labels: ['hot'] },
      all: { lead_types: [], score_min: 0, score_max: 100, score_buckets: [], labels: [], statuses: [], engagement_labels: [] },
    };
    const preset = presets[audienceKey] || presets.all;
    setCampaignStep(1);
    setCampaignName(goalLabel || `AI Funnel - ${audienceKey.replace(/_/g, ' ')}`);
    setCampaignFilters((prev) => ({ ...prev, ...preset, language: 'all', date_field: 'updated_at', date_from: '', date_to: '', delivery_channels: preset.delivery_channels || prev.delivery_channels || ['whatsapp'] }));
    setCampaignTemplate(null);
    setEmailSubject(goalLabel ? `${goalLabel} from Pureleven` : 'Pureleven update');
    setEmailHtml('');
    setCampaignEstimate(null);
    setCampaignEstimateError(null);
    setCampaignResult(null);
    setAiSuggestion(null);
    setAiExpanded(true);
    setMainTab('journey');
  }, []);

  const loadAudience = useCallback(async () => {
    setAudienceLoading(true);
    try {
      const offset = (audiencePage - 1) * audiencePageSize;
      const params = {
        search: audienceSearch,
        lead_type: audienceLeadType,
        min_score: audienceScoreMin,
        max_score: audienceScoreMax,
        language: audienceLanguage,
        limit: audiencePageSize,
        offset,
      };
      const res = await fetch(`${API_BASE}/crm/whatsapp/customers${buildQuery(params)}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setAudienceRows(Array.isArray(data.customers) ? data.customers : []);
      setAudienceTotal(data.total || 0);
      setAudienceSummary(data.summary || null);
    } catch (error) {
      setImportResult({ ok: false, detail: error.message });
    } finally {
      setAudienceLoading(false);
    }
  }, [audienceLeadType, audienceSearch, audienceScoreMin, audienceScoreMax, audienceLanguage, audiencePage, audiencePageSize]);

  const loadCampaignEstimate = useCallback(async (filters) => {
    setCampaignEstimating(true);
    setCampaignEstimateError(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/campaigns/estimate-cost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setCampaignEstimate(data);
    } catch (error) {
      setCampaignEstimate(null);
      setCampaignEstimateError(error.message);
    } finally {
      setCampaignEstimating(false);
    }
  }, []);

  const loadAvailableLabels = useCallback(async (search = '') => {
    setLabelsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/labels${buildQuery({ search, limit: 80 })}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setAvailableLabels(Array.isArray(data.labels) ? data.labels : []);
    } catch {
      setAvailableLabels([]);
    } finally {
      setLabelsLoading(false);
    }
  }, []);

  const loadAiSuggestion = useCallback(async (filters) => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/ai/suggest-campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setAiSuggestion(data);
      setAiExpanded(true);
    } catch {
      setAiSuggestion(null);
    } finally {
      setAiLoading(false);
    }
  }, []);

  const loadJourneyCampaignHistory = useCallback(async () => {
    setJourneyCampaignLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/journey/campaigns${buildQuery({ limit: 8, offset: 0 })}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setJourneyCampaignRows(Array.isArray(data.items) ? data.items : []);
      setJourneyCampaignTotal(data.total || 0);
    } catch {
      setJourneyCampaignRows([]);
      setJourneyCampaignTotal(0);
    } finally {
      setJourneyCampaignLoading(false);
    }
  }, []);

  const loadJourneyPipeline = useCallback(async () => {
    setJourneyPipelineLoading(true);
    try {
      const res = await fetch(`${API_BASE}/journey/orchestrate/pipeline?shop_domain=rwxtic-gz.myshopify.com`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setJourneyPipeline(data);
    } catch {
      setJourneyPipeline(null);
    } finally {
      setJourneyPipelineLoading(false);
    }
  }, []);

  const loadLifecycleStageTemplates = useCallback(async () => {
    setLifecycleStageLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/lifecycle-templates`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setLifecycleStageConfigs(Array.isArray(data.stages) ? data.stages : []);
    } catch (error) {
      setLifecycleStageConfigs([]);
      setLifecycleTemplateResult({ ok: false, text: error.message });
    } finally {
      setLifecycleStageLoading(false);
    }
  }, []);

  const runOrchestration = useCallback(async () => {
    setOrchestrating(true);
    setOrchestrateResult(null);
    try {
      const res = await fetch(`${API_BASE}/journey/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shop_domain: 'rwxtic-gz.myshopify.com', dry_run: false }),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setOrchestrateResult(data);
      await loadJourneyPipeline();
    } catch (error) {
      setOrchestrateResult({ error: error.message });
    } finally {
      setOrchestrating(false);
    }
  }, [loadJourneyPipeline]);

  const submitCampaign = useCallback(async () => {
    if (!campaignName.trim() || (campaignUsesWhatsApp && !campaignTemplate)) return;
    setCampaignCreating(true);
    try {
      const payload = {
        name: campaignName.trim(),
        audience_filters: campaignFilters,
        template_id: campaignTemplate ? String(campaignTemplate.id) : '',
        template_name: campaignTemplate?.name || '',
        channel: campaignTemplate?._channel || channel,
        delivery_channels: campaignFilters.delivery_channels || ['whatsapp'],
        email_subject: emailSubject,
        email_html: emailHtml,
        schedule_type: campaignScheduleType,
        scheduled_at: campaignScheduleType === 'scheduled' ? campaignScheduledAt : null,
        sync_meta_audiences: campaignSyncMeta,
      };
      const res = await fetch(`${API_BASE}/crm/whatsapp/journey/create-campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setCampaignResult(data);
      await loadJourneyCampaignHistory();
      setCampaignStep(4);
    } catch (error) {
      setCampaignResult({ error: error.message });
    } finally {
      setCampaignCreating(false);
    }
  }, [campaignTemplate, campaignName, campaignFilters, campaignUsesWhatsApp, channel, emailHtml, emailSubject, campaignScheduleType, campaignScheduledAt, campaignSyncMeta, loadJourneyCampaignHistory]);

  const loadJourney = useCallback(async (overrides = {}) => {
    setJourneyLoading(true);
    try {
      const params = {
        ...journeyFilters,
        phone: overrides.phone !== undefined ? overrides.phone : journeyPhoneSearch,
        limit: 120,
        offset: 0,
      };
      const res = await fetch(`${API_BASE}/crm/whatsapp/journey/customers${buildQuery(params)}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      const rows = Array.isArray(data.customers) ? data.customers : [];
      setJourneyRows(rows);
      setJourneyTotal(data.total || 0);
    } catch (error) {
      setJourneyRows([]);
      setJourneyTotal(0);
    } finally {
      setJourneyLoading(false);
    }
  }, [journeyFilters, journeyPhoneSearch]);

  const loadJourneyDetail = useCallback(async (customerId) => {
    if (!customerId) {
      setSelectedJourneyId('');
      setJourneyDetail(null);
      return;
    }
    setSelectedJourneyId(customerId);
    setJourneyDetailLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/journey/${encodeURIComponent(customerId)}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setJourneyDetail(data);
    } catch {
      setJourneyDetail(null);
    } finally {
      setJourneyDetailLoading(false);
    }
  }, []);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/logs${buildQuery({ ...logsFilters, limit: 150, offset: 0 })}`);
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setLogRows(Array.isArray(data.logs) ? data.logs : []);
      setLogsTotal(data.total || 0);
      setLogSummary(data.summary || {});
    } catch {
      setLogRows([]);
      setLogsTotal(0);
      setLogSummary({});
    } finally {
      setLogsLoading(false);
    }
  }, [logsFilters]);

  useEffect(() => {
    syncTemplates();
    syncTimerRef.current = setInterval(() => syncTemplates(false), SYNC_INTERVAL);
    return () => window.clearInterval(syncTimerRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    countdownRef.current = setInterval(() => {
      if (nextSyncAt) setCountdown(countdownStr(nextSyncAt));
    }, 1000);
    return () => window.clearInterval(countdownRef.current);
  }, [nextSyncAt]);

  useEffect(() => {
    if (mainTab === 'dashboard') {
      loadDashboard();
      loadSalesOs();
    }
    if (mainTab === 'customers') {
      loadAudience();
      loadSalesOs();
      loadAvailableLabels(labelSearch);
    }
    if (mainTab === 'journey') {
      loadJourney();
      loadJourneyCampaignHistory();
      loadJourneyPipeline();
      loadSalesOs();
      loadLifecycleStageTemplates();
    }
    if (mainTab === 'logs') loadLogs();
  }, [mainTab, loadAudience, loadAvailableLabels, loadDashboard, loadJourney, loadJourneyCampaignHistory, loadJourneyPipeline, loadLifecycleStageTemplates, loadLogs, loadSalesOs]);

  useEffect(() => {
    if (mainTab !== 'journey' || (campaignStep !== 1 && campaignStep !== 3)) return undefined;
    const timeoutId = window.setTimeout(() => {
      loadCampaignEstimate(campaignFilters);
    }, 250);
    return () => window.clearTimeout(timeoutId);
  }, [mainTab, campaignFilters, campaignStep, loadCampaignEstimate]);

  useEffect(() => {
    if (mainTab !== 'journey' || campaignStep !== 1) return undefined;
    const timeoutId = window.setTimeout(() => {
      loadAvailableLabels(labelSearch);
    }, 250);
    return () => window.clearTimeout(timeoutId);
  }, [campaignStep, labelSearch, loadAvailableLabels, mainTab]);

  useEffect(() => {
    if (mainTab !== 'customers') return undefined;
    const timeoutId = window.setTimeout(() => {
      loadAvailableLabels(labelSearch);
    }, 250);
    return () => window.clearTimeout(timeoutId);
  }, [labelSearch, loadAvailableLabels, mainTab]);

  useEffect(() => {
    if (mainTab !== 'journey' || !journeyRows.length) return;
    if (journeyPhoneSearch && journeyRows[0]?.id !== selectedJourneyId) {
      loadJourneyDetail(journeyRows[0].id);
      return;
    }
    const exists = journeyRows.some((row) => row.id === selectedJourneyId);
    if (!exists) {
      loadJourneyDetail(journeyRows[0].id);
    }
  }, [mainTab, journeyRows, selectedJourneyId, loadJourneyDetail, journeyPhoneSearch]);

  const templates = channel === 'wabis' ? wabisTemplates : metaTemplates;
  const activeTpl = templates.find((item) => String(item.id) === String(selectedId)) || null;

  const varSlots = useMemo(() => {
    if (!activeTpl) return [];
    const slots = [];
    let index = 0;
    const addSlots = (component, labelPrefix) => {
      if (!component) return;
      for (let num = 1; num <= (component.vars || 0); num += 1) {
        const example = component.examples?.[num - 1] || '';
        const label = activeTpl.var_labels?.[String(index + 1)] || example || `Param ${index + 1}`;
        slots.push({ index, labelPrefix, num, example, label });
        index += 1;
      }
    };
    addSlots(activeTpl.header, 'Header');
    addSlots(activeTpl.body, 'Body');
    (activeTpl.buttons || []).forEach((button, buttonIndex) => addSlots(button, `Button ${buttonIndex + 1}`));
    return slots;
  }, [activeTpl]);

  useEffect(() => {
    if (!activeTpl) return;
    setParams((prev) => {
      const size = activeTpl.total_vars || 0;
      if (prev.length === size) return prev;
      return Array(size).fill('').map((_, index) => prev[index] || '');
    });
    setTemplateDraft({
      name: `${activeTpl.name || 'template'}_edit`,
      category: activeTpl.category || 'MARKETING',
      language: activeTpl.locale || 'en_US',
      header: activeTpl.header?.text || '',
      body: activeTpl.body?.meta_text || activeTpl.body?.text || '',
      footer: activeTpl.footer?.text || '',
    });
  }, [activeTpl]);

  useEffect(() => {
    if (!selectedLifecycleStage) return;
    const stageConfig = lifecycleStageConfigs.find((item) => item.stage === selectedLifecycleStage);
    if (!stageConfig) return;
    setSelectedLifecycleTemplateName(stageConfig.active_template_name || stageConfig.default_template_names?.[0] || '');
  }, [lifecycleStageConfigs, selectedLifecycleStage]);

  const journeyStages = useMemo(() => Array.from(new Set(journeyRows.map((row) => row.journey_stage).filter(Boolean))), [journeyRows]);
  const journeySegments = useMemo(() => Array.from(new Set(journeyRows.map((row) => row.customer_segment).filter(Boolean))), [journeyRows]);
  const logStatuses = useMemo(() => Object.keys(logSummary || {}), [logSummary]);
  const selectedScoreBuckets = useMemo(() => new Set(campaignFilters.score_buckets || []), [campaignFilters.score_buckets]);
  const labelOptions = useMemo(() => {
    const merged = new Map();
    CURATED_LABEL_OPTIONS.forEach((label) => merged.set(label.toLowerCase(), { label, count: null }));
    availableLabels.forEach((item) => {
      const label = String(item.label || '').trim();
      if (!label) return;
      merged.set(label.toLowerCase(), { label, count: item.count || 0 });
    });
    return Array.from(merged.values());
  }, [availableLabels]);
  const selectedLabelSet = useMemo(() => new Set((campaignFilters.labels || []).map((label) => String(label).toLowerCase())), [campaignFilters.labels]);
  const selectedStatusSet = useMemo(() => new Set((campaignFilters.statuses || []).map((status) => String(status).toLowerCase())), [campaignFilters.statuses]);
  const selectedEngagementSet = useMemo(() => new Set((campaignFilters.engagement_labels || []).map((label) => String(label).toLowerCase())), [campaignFilters.engagement_labels]);
  const campaignSelectedLeadTypes = useMemo(() => new Set(campaignFilters.lead_types || []), [campaignFilters.lead_types]);
  const journeyPhoneNeedle = useMemo(() => normalizePhoneLookup(journeyPhoneSearch), [journeyPhoneSearch]);
  const templateLibrary = useMemo(() => {
    const merged = new Map();
    wabisTemplates.forEach((template) => {
      if (!template?.name) return;
      merged.set(template.name, { ...template, _channel: 'wabis' });
    });
    metaTemplates.forEach((template) => {
      if (!template?.name) return;
      merged.set(template.name, { ...template, _channel: 'meta' });
    });
    return Array.from(merged.values()).sort((left, right) => String(left.name || '').localeCompare(String(right.name || '')));
  }, [metaTemplates, wabisTemplates]);
  const lifecycleStageMap = useMemo(() => Object.fromEntries(lifecycleStageConfigs.map((item) => [item.stage, item])), [lifecycleStageConfigs]);
  const lifecycleStageCards = useMemo(() => ([
    { key: 'day1_sent', stage: 'order_confirmed', defaultLabel: 'Day 1 — Order Confirmed' },
    { key: 'day2_sent', stage: 'in_transit', defaultLabel: 'Day 2 — In Transit' },
    { key: 'day5_sent', stage: 'delivered', defaultLabel: 'Day 5 — Delivered' },
    { key: 'day15_sent', stage: 'review', defaultLabel: 'Day 15 — Review Request' },
    { key: 'day30_sent', stage: 'upsell', defaultLabel: 'Day 30 — Upsell' },
    { key: 'day60_sent', stage: 'corporate', defaultLabel: 'Day 60 — Corporate / Gifting' },
    { key: 'day75_sent', stage: 'loyalty', defaultLabel: 'Day 75 — Loyalty' },
    { key: 'day95_sent', stage: 'rfm', defaultLabel: 'Day 95 — Re-engagement' },
  ]), []);
  const selectedLifecycleStageConfig = selectedLifecycleStage ? (lifecycleStageMap[selectedLifecycleStage] || null) : null;
  const selectedLifecycleTemplate = selectedLifecycleTemplateName
    ? (templateLibrary.find((template) => template.name === selectedLifecycleTemplateName) || null)
    : null;
  const lifecycleTemplateLibrary = useMemo(() => {
    const needle = lifecycleTemplateSearch.trim().toLowerCase();
    const recommendedCategory = String(selectedLifecycleStageConfig?.recommended_category || '').toUpperCase();
    return templateLibrary
      .filter((template) => {
        if (!needle) return true;
        return String(template.name || '').toLowerCase().includes(needle)
          || String(templatePreviewText(template) || '').toLowerCase().includes(needle);
      })
      .sort((left, right) => {
        const leftScore = (left.name === selectedLifecycleTemplateName ? -30 : 0)
          + (String(left.category || '').toUpperCase() === recommendedCategory ? -10 : 0)
          + (String(left.status || '').toUpperCase() === 'APPROVED' ? -5 : 0);
        const rightScore = (right.name === selectedLifecycleTemplateName ? -30 : 0)
          + (String(right.category || '').toUpperCase() === recommendedCategory ? -10 : 0)
          + (String(right.status || '').toUpperCase() === 'APPROVED' ? -5 : 0);
        if (leftScore !== rightScore) return leftScore - rightScore;
        return String(left.name || '').localeCompare(String(right.name || ''));
      });
  }, [lifecycleTemplateSearch, selectedLifecycleStageConfig, selectedLifecycleTemplateName, templateLibrary]);
  const lifecycleTemplateDirty = Boolean(selectedLifecycleStageConfig && selectedLifecycleTemplateName && selectedLifecycleTemplateName !== selectedLifecycleStageConfig.active_template_name);

  const handleChannelSwitch = (nextChannel) => {
    setChannel(nextChannel);
    const list = nextChannel === 'wabis' ? wabisTemplates : metaTemplates;
    const nextTemplate = list[0] || null;
    setSelectedId(nextTemplate?.id ?? null);
    setParams(Array(nextTemplate?.total_vars || 0).fill(''));
    setResult(null);
    setHeaderImageUrl('');
  };

  const selectTemplate = useCallback((id) => {
    const template = templates.find((item) => String(item.id) === String(id));
    setSelectedId(id);
    setParams(Array(template?.total_vars || 0).fill(''));
    setResult(null);
    setHeaderImageUrl('');
  }, [templates]);

  const handleSend = async () => {
    if (!phone.trim() || !activeTpl) return;
    setSending(true);
    setResult(null);
    try {
      let url = '';
      let body = '';
      if (channel === 'wabis') {
        url = `${API_BASE}/crm/wabis/send`;
        const payload = {
          phone: phone.replace(/\D/g, ''),
          template_id: activeTpl.id,
          template_name: activeTpl.name,
          params: params.filter(Boolean),
        };
        if (headerImageUrl.trim()) payload.header_image_url = headerImageUrl.trim();
        body = JSON.stringify(payload);
      } else {
        url = `${API_BASE}/crm/meta-wa/send`;
        body = JSON.stringify({
          phone: phone.replace(/\D/g, ''),
          template: activeTpl.name,
          params: params.filter(Boolean),
          phone_number_id: '',
          language_code: activeTpl.locale || 'en_US',
        });
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      const data = await readJson(res);
      setResult({ ok: res.ok, data, channel, name: activeTpl.name });
      setSendHistory((prev) => [
        {
          id: Date.now(),
          channel,
          phone: phone.replace(/\D/g, ''),
          template: activeTpl.name,
          params: [...params],
          ok: res.ok,
          ts: new Date().toLocaleTimeString(),
          response: data,
        },
        ...prev.slice(0, 49),
      ]);
      loadLogs();
      loadDashboard();
    } catch (error) {
      setResult({ ok: false, data: { detail: error.message }, channel, name: activeTpl?.name });
    } finally {
      setSending(false);
    }
  };

  const handleCreateTemplate = async () => {
    if (!newTpl.name.trim() || !newTpl.body.trim()) {
      setCreateMsg({ ok: false, text: 'Template name and body are required.' });
      return;
    }

    setCreating(true);
    setCreateMsg(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/create-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTpl),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      setCreateMsg({ ok: true, text: `Submitted "${data.name}" to Meta. Current status: ${data.status || 'PENDING'}.` });
      setNewTpl({ name: '', category: 'MARKETING', language: 'en_US', body: '', header: '', footer: '' });
      syncTemplates(false, true);
      loadLifecycleStageTemplates();
      loadDashboard();
    } catch (error) {
      setCreateMsg({ ok: false, text: error.message });
    } finally {
      setCreating(false);
    }
  };

  const openLifecycleStageStudio = useCallback((stageKey) => {
    setSelectedLifecycleStage(stageKey);
    setLifecycleTemplateSearch('');
    setLifecycleCreateOpen(false);
    setLifecycleTemplateResult(null);
  }, []);

  const prefillLifecycleStageComposer = useCallback((stageConfig) => {
    if (!stageConfig?.create_preset) return;
    const preset = stageConfig.create_preset;
    setNewTpl({
      name: preset.name || `${stageConfig.stage}_template_v1`,
      category: preset.category || stageConfig.recommended_category || 'MARKETING',
      language: 'en_US',
      header: preset.header || '',
      body: preset.body || '',
      footer: preset.footer || '',
    });
    setCreateMsg(null);
    setLifecycleCreateOpen(true);
  }, []);

  const saveLifecycleStageTemplate = useCallback(async (stageKey, templateName = '') => {
    if (!stageKey) return;
    setLifecycleTemplateSaving(true);
    setLifecycleTemplateResult(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/lifecycle-templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: stageKey, template_name: templateName }),
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

      setLifecycleStageConfigs((prev) => prev.map((item) => (item.stage === stageKey ? data.stage : item)));
      setSelectedLifecycleTemplateName(data.stage?.active_template_name || '');
      setLifecycleTemplateResult({ ok: true, text: templateName ? `Saved ${templateName} for ${data.stage?.label || stageKey}.` : `Reset ${data.stage?.label || stageKey} to the backend default.` });
    } catch (error) {
      setLifecycleTemplateResult({ ok: false, text: error.message });
    } finally {
      setLifecycleTemplateSaving(false);
    }
  }, []);

  const handleManualSync = async () => {
    await syncTemplates(true, true);
    if (mainTab === 'dashboard') loadDashboard();
    if (mainTab === 'logs') loadLogs();
  };

  const handleImportShopify = async () => {
    setImporting('shopify');
    setImportResult(null);
    try {
      const res = await fetch(`${API_BASE}/crm/whatsapp/customers/import/shopify`, { method: 'POST' });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setImportResult(data);
      loadAudience();
      loadDashboard();
    } catch (error) {
      setImportResult({ ok: false, detail: error.message });
    } finally {
      setImporting('');
    }
  };

  const handleFileImport = async (kind, file) => {
    if (!file) return;
    setImporting(kind);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/crm/whatsapp/customers/import/${kind}`, {
        method: 'POST',
        body: formData,
      });
      const data = await readJson(res);
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setImportResult(data);
      loadAudience();
      loadDashboard();
    } catch (error) {
      setImportResult({ ok: false, detail: error.message });
    } finally {
      setImporting('');
    }
  };

  const handleFileChosen = (kind, event) => {
    const file = event.target.files?.[0];
    handleFileImport(kind, file);
    event.target.value = '';
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1280px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '24px', alignItems: 'flex-start', marginBottom: '22px', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ margin: '0 0 6px', fontSize: '24px', fontWeight: 800, color: '#111827' }}>WhatsApp Workspace</h2>
          <p style={{ margin: 0, fontSize: '13px', color: '#6b7280', lineHeight: 1.7 }}>Audience import, journey visibility, template sync every 30 minutes, direct Meta submission, and live send logs.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {lastSynced ? <Badge label={`Synced ${lastSynced.toLocaleTimeString()} · next ${countdown || '0:00'}`} tone="slate" /> : null}
          <Badge label={`Wabis ${wabisTemplates.length}`} tone="green" />
          <Badge label={`Meta ${metaTemplates.length}`} tone="blue" />
          <button onClick={handleManualSync} disabled={syncing} style={secondaryButtonStyle(syncing)}>
            {syncing ? 'Syncing…' : 'Sync Now'}
          </button>
        </div>
      </div>

      {syncError ? (
        <div style={{ marginBottom: '16px', padding: '12px 14px', background: '#fef2f2', borderRadius: '10px', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '13px' }}>
          Sync error: {syncError}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        {MAIN_TABS.map(([id, label]) => (
          <button key={id} onClick={() => setMainTab(id)} style={mainTabButtonStyle(mainTab === id)}>
            {label}
          </button>
        ))}
      </div>

      {mainTab === 'dashboard' ? (
        dashboardLoading ? (
          <PanelSection title="Overview" subtitle="Reading message, audience, and journey stats.">
            <EmptyState title="Loading dashboard" body="Pulling template counts, journey mix, and the last 30 days of WhatsApp activity." />
          </PanelSection>
        ) : dashboardError ? (
          <PanelSection title="Overview" subtitle="Dashboard request failed.">
            <EmptyState title="Dashboard unavailable" body={dashboardError} />
          </PanelSection>
        ) : (
          <div style={{ display: 'grid', gap: '18px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px' }}>
              <StatCard label="Audience" value={dashboard?.totals?.audience_customers || 0} tone="blue" caption={`${dashboard?.totals?.opted_in_customers || 0} opted in`} />
              <StatCard label="Journey Customers" value={dashboard?.totals?.journey_customers || 0} tone="indigo" caption="Customers currently represented in lifecycle data" />
              <StatCard label="Active Sessions" value={dashboard?.totals?.active_sessions || 0} tone="slate" caption="Live conversation sessions" />
              <StatCard label="Messages 30d" value={dashboard?.totals?.messages_30d || 0} tone="green" caption={`${dashboard?.totals?.delivered_30d || 0} delivered · ${dashboard?.totals?.read_30d || 0} read`} />
              <StatCard label="Failed 30d" value={dashboard?.totals?.failed_30d || 0} tone="red" caption={`${dashboard?.totals?.sent_30d || 0} latest status = sent`} />
              <StatCard label="Template Sources" value={`${dashboard?.template_sources?.wabis || 0}/${dashboard?.template_sources?.meta || 0}`} tone="amber" caption={dashboard?.template_sources?.meta_configured ? 'Wabis / Meta configured' : 'Meta still not configured'} />
            </div>

            <PanelSection
              title="Sales Command Center"
              subtitle="Daily control room for orders, lifecycle automation, retargeting sync, and failed-message recovery."
              actions={<button onClick={loadSalesOs} disabled={salesOsLoading} style={secondaryButtonStyle(salesOsLoading)}>{salesOsLoading ? 'Refreshing…' : 'Refresh'}</button>}
            >
              {salesOsResult ? (
                <div style={{ marginBottom: '14px', padding: '12px 14px', borderRadius: '10px', border: `1px solid ${salesOsResult.ok ? '#bbf7d0' : '#fecaca'}`, background: salesOsResult.ok ? '#f0fdf4' : '#fef2f2', color: salesOsResult.ok ? '#166534' : '#991b1b', fontSize: '12px', lineHeight: 1.7 }}>
                  <div>{salesOsResult.ok ? `${salesOsResult.title || 'Action complete'}.` : (salesOsResult.detail || 'Action failed')}</div>
                  {salesOsResult.ok && salesOsResult.dryRun && (salesOsResult.data?.results || []).some((item) => item.dry_run > 0) ? (
                    <div style={{ marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                      {(salesOsResult.data.results || []).map((item) => <Badge key={item.event_type} label={`${item.event_type}: ${item.dry_run} eligible`} tone="amber" />)}
                      <button onClick={() => retryLifecycle(salesOsResult.eventType, false)} disabled={salesOsAction === `retry-${salesOsResult.eventType}`} style={primaryButtonStyle(salesOsAction === `retry-${salesOsResult.eventType}`)}>
                        {salesOsAction === `retry-${salesOsResult.eventType}` ? 'Sending…' : 'Send Eligible Now'}
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginBottom: '16px' }}>
                <div style={miniMetricStyle('blue')}><div style={miniMetricValueStyle('#1d4ed8')}>{salesOs?.orders?.shopify_today ?? '—'}</div><div style={miniMetricLabelStyle}>Orders Today</div></div>
                <div style={miniMetricStyle('amber')}><div style={miniMetricValueStyle('#92400e')}>{salesOs?.orders?.missing_tracking ?? '—'}</div><div style={miniMetricLabelStyle}>Missing Tracking</div></div>
                <div style={miniMetricStyle('green')}><div style={miniMetricValueStyle('#166534')}>{salesOs?.orders?.delivered ?? '—'}</div><div style={miniMetricLabelStyle}>Delivered</div></div>
                <div style={miniMetricStyle('red')}><div style={miniMetricValueStyle('#b91c1c')}>{salesOs?.lifecycle?.pending_total ?? '—'}</div><div style={miniMetricLabelStyle}>Lifecycle Pending</div></div>
                <div style={miniMetricStyle('indigo')}><div style={miniMetricValueStyle('#4338ca')}>{salesOs?.retargeting?.attribution?.meta ?? '—'}</div><div style={miniMetricLabelStyle}>Meta Attributed</div></div>
                <div style={miniMetricStyle('slate')}><div style={miniMetricValueStyle('#374151')}>{salesOs?.retargeting?.attribution?.google ?? '—'}</div><div style={miniMetricLabelStyle}>Google Attributed</div></div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.08fr) minmax(320px, 0.92fr)', gap: '14px' }}>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {(salesOs?.action_cards || []).map((card) => {
                    const busy = salesOsAction === `preview-${String(card.action || '').split(':')[1]}`;
                    return (
                      <div key={card.key} style={{ padding: '13px 14px', borderRadius: '12px', background: '#f8fafc', border: `1px solid ${toneColors(card.tone).border}`, display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '10px', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>{card.title}</div>
                          <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{Number(card.count || 0) === 0 ? 'Clear' : 'Needs attention'}</div>
                        </div>
                        <Badge label={`${card.count || 0}`} tone={card.tone} />
                        {String(card.action || '').startsWith('retry_lifecycle:') ? (
                          <button onClick={() => retryLifecycle(String(card.action).split(':')[1], true)} disabled={busy || Number(card.count || 0) === 0} style={secondaryButtonStyle(busy || Number(card.count || 0) === 0)}>{busy ? 'Checking…' : 'Preview'}</button>
                        ) : (
                          <button onClick={() => { if (card.action === 'open_logs_failed') { setMainTab('logs'); setLogsFilters((prev) => ({ ...prev, status: 'failed' })); } else { setMainTab('journey'); } }} style={secondaryButtonStyle(false)}>Open</button>
                        )}
                      </div>
                    );
                  })}
                </div>

                <div style={softPanelStyle('blue')}>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Retargeting Sync</div>
                  <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Push sales audiences to Meta and prepare Google customer-match uploads from the same customer state.</div>
                  <div style={{ marginTop: '12px', display: 'grid', gap: '8px' }}>
                    {(salesOs?.retargeting?.audiences || []).slice(0, 5).map((audience) => {
                      const busy = salesOsAction === `retarget-${audience.key}`;
                      return (
                        <div key={audience.key} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '8px', alignItems: 'center', padding: '9px 10px', borderRadius: '10px', background: 'white', border: '1px solid #dbeafe' }}>
                          <div>
                            <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>{audience.label}</div>
                            <div style={{ marginTop: '2px', fontSize: '10px', color: '#64748b' }}>Meta + Google retargeting set</div>
                          </div>
                          <Badge label={`${audience.count}`} tone="blue" />
                          <button onClick={() => syncRetargetingAudience(audience.key)} disabled={busy || !audience.count} style={secondaryButtonStyle(busy || !audience.count)}>{busy ? 'Syncing…' : 'Sync'}</button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </PanelSection>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(320px, 0.9fr)', gap: '18px' }}>
              <PanelSection title="Top Templates" subtitle="Most frequently logged template traffic in the last 30 days.">
                {!dashboard?.top_templates?.length ? (
                  <EmptyState title="No template activity yet" body="Send a template or wait for journey/webhook traffic to populate usage." />
                ) : (
                  <div style={{ display: 'grid', gap: '10px' }}>
                    {dashboard.top_templates.map((item) => (
                      <div key={`${item.template_name}-${item.last_seen_at}`} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '12px', alignItems: 'center', padding: '12px 14px', borderRadius: '10px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: '#111827' }}>{item.template_name}</div>
                          <div style={{ marginTop: '3px', fontSize: '11px', color: '#64748b' }}>Last seen {formatDateTime(item.last_seen_at)}</div>
                        </div>
                        <Badge label={`${item.cnt} events`} tone="blue" />
                        <button onClick={() => { setMainTab('campaigns'); setCampaignTab('send'); }} style={inlineActionStyle}>Open</button>
                      </div>
                    ))}
                  </div>
                )}
              </PanelSection>

              <div style={{ display: 'grid', gap: '18px' }}>
                <PanelSection title="Audience Buckets" subtitle="Purchased, abandoned, WhatsApp leads, and promotional numbers in the current WhatsApp audience.">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
                    <StatCard label="Purchased" value={dashboard?.audience_breakdown?.purchased || 0} tone="amber" caption="Contacts with order history" />
                    <StatCard label="Abandoned" value={dashboard?.audience_breakdown?.abandoned || 0} tone="red" caption="Open or cancelled order prospects" />
                    <StatCard label="WhatsApp Leads" value={dashboard?.audience_breakdown?.whatsapp_leads || 0} tone="green" caption="Captured from WhatsApp-native lead sources" />
                    <StatCard label="Promotional Numbers" value={dashboard?.audience_breakdown?.promotional_leads || 0} tone="indigo" caption="Promo audience contacts with phones" />
                  </div>
                </PanelSection>

                <PanelSection title="Score Tiers" subtitle="Lead score distribution across all customers. Use these to target the right audience for your campaigns.">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px' }}>
                    <StatCard label="Buyers" value={dashboard?.score_breakdown?.buyers || 0} tone="amber" caption="Score 90–100" />
                    <StatCard label="Purchase Intent" value={dashboard?.score_breakdown?.purchase_intent || 0} tone="green" caption="Score 80–89" />
                    <StatCard label="Warm" value={dashboard?.score_breakdown?.warm || 0} tone="blue" caption="Score 50–79" />
                    <StatCard label="Behavioral" value={dashboard?.score_breakdown?.behavioral || 0} tone="indigo" caption="Score 10–49" />
                    <StatCard label="Cold" value={dashboard?.score_breakdown?.cold || 0} tone="slate" caption="Score 0–9" />
                  </div>
                </PanelSection>

                <PanelSection title="Journey Mix" subtitle="Current stage and segment distribution from journey customers.">
                  <div style={{ display: 'grid', gap: '14px' }}>
                    <div>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#64748b', marginBottom: '8px' }}>Stages</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {(dashboard?.stages || []).map((item) => <Badge key={item.label} label={`${item.label} · ${item.count}`} tone="indigo" />)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#64748b', marginBottom: '8px' }}>Segments</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {(dashboard?.segments || []).map((item) => <Badge key={item.label} label={`${item.label} · ${item.count}`} tone="slate" />)}
                      </div>
                    </div>
                  </div>
                </PanelSection>

                <PanelSection title="Engagement Events" subtitle="Tracked clicks, replies, calls, and other events in the last 30 days.">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {(dashboard?.engagement || []).length ? (
                      dashboard.engagement.map((item) => <Badge key={item.label} label={`${item.label} · ${item.count}`} tone="green" />)
                    ) : (
                      <Badge label="No engagement events yet" tone="slate" />
                    )}
                  </div>
                </PanelSection>
              </div>
            </div>
          </div>
        )
      ) : null}

      {mainTab === 'customers' ? (
        <div style={{ display: 'grid', gap: '18px' }}>
          <PanelSection
            title="Customer 360 Audience Builder"
            subtitle="Choose a sales audience, sync it for retargeting, or turn it into an AI-assisted WhatsApp funnel."
            actions={<button onClick={loadSalesOs} disabled={salesOsLoading} style={secondaryButtonStyle(salesOsLoading)}>{salesOsLoading ? 'Refreshing…' : 'Refresh Audiences'}</button>}
          >
            {salesOsResult ? (
              <div style={{ marginBottom: '14px', padding: '12px 14px', borderRadius: '10px', border: `1px solid ${salesOsResult.ok ? '#bbf7d0' : '#fecaca'}`, background: salesOsResult.ok ? '#f0fdf4' : '#fef2f2', color: salesOsResult.ok ? '#166534' : '#991b1b', fontSize: '12px' }}>
                {salesOsResult.ok ? `${salesOsResult.title || 'Action complete'} — ${salesOsResult.data?.matched ?? 0} customers matched.` : (salesOsResult.detail || 'Action failed')}
              </div>
            ) : null}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
              {(salesOs?.retargeting?.audiences || []).map((audience) => {
                const busy = salesOsAction === `retarget-${audience.key}`;
                const funnelNames = {
                  purchased: 'Repeat Purchase Funnel',
                  interested: 'Interested Customer Conversion Funnel',
                  non_purchased: 'First Order Conversion Funnel',
                  abandoned: 'Abandoned Recovery Funnel',
                  whatsapp_leads: 'WhatsApp Lead Nurture Funnel',
                  hot_leads: 'Hot Lead Closing Funnel',
                  all: 'Full Audience Broadcast Funnel',
                };
                return (
                  <div key={audience.key} style={{ padding: '14px 15px', borderRadius: '12px', background: 'white', border: '1px solid #e2e8f0', display: 'grid', gap: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>{audience.label}</div>
                        <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Use for Meta/Google retargeting or build a WhatsApp journey.</div>
                      </div>
                      <Badge label={`${audience.count}`} tone={audience.key === 'hot_leads' ? 'red' : audience.key === 'purchased' ? 'amber' : audience.key === 'interested' ? 'green' : 'blue'} />
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button onClick={() => syncRetargetingAudience(audience.key)} disabled={busy || !audience.count} style={secondaryButtonStyle(busy || !audience.count)}>{busy ? 'Syncing…' : 'Sync Meta + Google'}</button>
                      <button onClick={() => startFunnelForAudience(audience.key, funnelNames[audience.key] || `${audience.label} Funnel`)} disabled={!audience.count} style={primaryButtonStyle(!audience.count)}>Create Journey</button>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: '16px', padding: '15px 16px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', display: 'grid', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Custom Audience Builder</div>
                  <div style={{ marginTop: '4px', fontSize: '12px', color: '#64748b', lineHeight: 1.6 }}>Filter by type, label, status, score, date, and channel. The same rules open directly in Journey for template selection.</div>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button onClick={() => loadCampaignEstimate(campaignFilters)} disabled={campaignEstimating} style={secondaryButtonStyle(campaignEstimating)}>{campaignEstimating ? 'Calculating…' : 'Preview Audience'}</button>
                  <button onClick={() => { setCampaignStep(1); setCampaignName(campaignName || 'Custom AI Journey'); setMainTab('journey'); }} style={primaryButtonStyle(false)}>Open in Journey</button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                <div style={softPanelStyle('slate')}>
                  <label style={labelStyle}>Delivery Channel</label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {DELIVERY_CHANNEL_OPTIONS.map(([value, label]) => (
                      <button key={value} onClick={() => setCampaignFilters((f) => {
                        const next = toggleListValue(f.delivery_channels || [], value);
                        return { ...f, delivery_channels: next.length ? next : [value] };
                      })} style={multiSelectChipStyle(campaignDeliveryChannels.has(value), value === 'email' ? 'blue' : 'green')}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <div style={softPanelStyle('slate')}>
                  <label style={labelStyle}>Type</label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {AUDIENCE_TYPE_OPTIONS.filter(([value]) => value !== 'all').map(([value, label]) => (
                      <button key={value} onClick={() => setCampaignFilters((f) => ({ ...f, lead_types: toggleListValue(f.lead_types || [], value) }))} style={multiSelectChipStyle(campaignSelectedLeadTypes.has(value), audienceTypeTone(value))}>{label}</button>
                    ))}
                  </div>
                </div>
                <div style={softPanelStyle('slate')}>
                  <label style={labelStyle}>Status</label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {STATUS_OPTIONS.map(([value, label]) => (
                      <button key={value} onClick={() => setCampaignFilters((f) => ({ ...f, statuses: toggleListValue(f.statuses || [], value) }))} style={multiSelectChipStyle(selectedStatusSet.has(value), value === 'purchased' ? 'amber' : value === 'abandoned' ? 'red' : 'slate')}>{label}</button>
                    ))}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '12px' }}>
                <div>
                  <label style={labelStyle}>Score Min</label>
                  <input type="number" min={0} max={100} value={campaignFilters.score_min} onChange={(event) => setCampaignFilters((f) => ({ ...f, score_min: Number(event.target.value) }))} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Score Max</label>
                  <input type="number" min={0} max={100} value={campaignFilters.score_max} onChange={(event) => setCampaignFilters((f) => ({ ...f, score_max: Number(event.target.value) }))} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Date Field</label>
                  <select value={campaignFilters.date_field || 'updated_at'} onChange={(event) => setCampaignFilters((f) => ({ ...f, date_field: event.target.value }))} style={inputStyle}>
                    <option value="updated_at">Updated</option>
                    <option value="created_at">Created</option>
                    <option value="last_order_date">Last order</option>
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>From Date</label>
                  <input type="date" value={campaignFilters.date_from || ''} onChange={(event) => setCampaignFilters((f) => ({ ...f, date_from: event.target.value }))} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>To Date</label>
                  <input type="date" value={campaignFilters.date_to || ''} onChange={(event) => setCampaignFilters((f) => ({ ...f, date_to: event.target.value }))} style={inputStyle} />
                </div>
              </div>

              <div style={softPanelStyle('slate')}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                  <label style={{ ...labelStyle, marginBottom: 0 }}>Labels</label>
                  {labelsLoading ? <Badge label="Loading labels" tone="blue" /> : <Badge label={`${(campaignFilters.labels || []).length} selected`} tone="slate" />}
                </div>
                <input value={labelSearch} onChange={(event) => setLabelSearch(event.target.value)} placeholder="Search labels like purchased, interested, mal_customer" style={inputStyle} />
                <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap', maxHeight: '120px', overflowY: 'auto' }}>
                  {labelOptions.slice(0, 40).map((item) => {
                    const active = selectedLabelSet.has(String(item.label).toLowerCase());
                    return <button key={item.label} onClick={() => setCampaignFilters((f) => ({ ...f, labels: toggleListValue(f.labels || [], item.label) }))} style={multiSelectChipStyle(active, 'indigo')}>{item.label}{item.count ? ` · ${item.count}` : ''}</button>;
                  })}
                </div>
              </div>

              {campaignEstimate ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
                  <div style={miniMetricStyle('slate')}><div style={miniMetricValueStyle('#111827')}>{campaignEstimate.matched || 0}</div><div style={miniMetricLabelStyle}>Matched</div></div>
                  <div style={miniMetricStyle('green')}><div style={miniMetricValueStyle('#166534')}>{campaignEstimate.whatsapp_sendable || 0}</div><div style={miniMetricLabelStyle}>WhatsApp Ready</div></div>
                  <div style={miniMetricStyle('blue')}><div style={miniMetricValueStyle('#1d4ed8')}>{campaignEstimate.email_sendable || 0}</div><div style={miniMetricLabelStyle}>Email Ready</div></div>
                  <div style={miniMetricStyle('amber')}><div style={miniMetricValueStyle('#92400e')}>₹{campaignEstimate.cost?.inr || 0}</div><div style={miniMetricLabelStyle}>WA Cost</div></div>
                </div>
              ) : null}
            </div>
          </PanelSection>

          <PanelSection
            title="Audience"
            subtitle="Import phone-ready contacts from Shopify, CSV, XML, or XLSX into the WhatsApp audience view."
            actions={(
              <>
                <button onClick={handleImportShopify} disabled={importing !== ''} style={secondaryButtonStyle(importing !== '')}>{importing === 'shopify' ? 'Importing…' : 'Import Shopify'}</button>
                <button onClick={() => csvInputRef.current?.click()} disabled={importing !== ''} style={secondaryButtonStyle(importing !== '')}>Upload CSV</button>
                <button onClick={() => xmlInputRef.current?.click()} disabled={importing !== ''} style={secondaryButtonStyle(importing !== '')}>Upload XML</button>
                <button onClick={() => xlsxInputRef.current?.click()} disabled={importing !== ''} style={secondaryButtonStyle(importing !== '')}>Upload XLSX</button>
                <button onClick={loadAudience} disabled={audienceLoading} style={secondaryButtonStyle(audienceLoading)}>{audienceLoading ? 'Refreshing…' : 'Refresh'}</button>
              </>
            )}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', marginBottom: '16px' }}>
              <StatCard label="Audience Total" value={audienceSummary?.total || 0} tone="blue" caption="Contacts with a WhatsApp phone number" />
              <StatCard label="Opted In" value={audienceSummary?.opted_in || 0} tone="green" caption="Customers flagged as WhatsApp opted-in" />
              <StatCard label="Purchased" value={audienceSummary?.purchased || 0} tone="amber" caption="Audience contacts with order history" />
              <StatCard label="Abandoned" value={audienceSummary?.abandoned || 0} tone="red" caption="Open or cancelled order prospects" />
              <StatCard label="WhatsApp Leads" value={audienceSummary?.whatsapp_leads || 0} tone="green" caption="Rows attributed to WhatsApp lead sources" />
              <StatCard label="Promotional Numbers" value={audienceSummary?.promotional_leads || 0} tone="indigo" caption="Promo audience contacts with phone numbers" />
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap' }}>
              <input
                value={audienceSearch}
                onChange={(event) => setAudienceSearch(event.target.value)}
                placeholder="Search by name, email, or phone"
                style={{ ...inputStyle, maxWidth: '280px' }}
              />
              <select value={audienceLeadType} onChange={(event) => setAudienceLeadType(event.target.value)} style={{ ...inputStyle, maxWidth: '200px' }}>
                {AUDIENCE_TYPE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <select value={audienceLanguage} onChange={(event) => setAudienceLanguage(event.target.value)} style={{ ...inputStyle, maxWidth: '160px' }}>
                <option value="all">All languages</option>
                <option value="mal">Malayalam</option>
                <option value="eng">English</option>
              </select>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>Score Filter</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '10px' }}>
                <button
                  onClick={() => { setAudienceScoreMin(0); setAudienceScoreMax(100); }}
                  style={scoreSelectorCardStyle(audienceScoreMin === 0 && audienceScoreMax === 100, 'slate')}
                >
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>All Scores</div>
                  <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>0-100</div>
                </button>
                {SCORE_BUCKET_OPTIONS.map((bucket) => (
                  <button
                    key={bucket.id}
                    onClick={() => { setAudienceScoreMin(bucket.min); setAudienceScoreMax(bucket.max); }}
                    style={scoreSelectorCardStyle(audienceScoreMin === bucket.min && audienceScoreMax === bucket.max, bucket.tone)}
                  >
                    <div style={{ fontSize: '12px', fontWeight: 800, color: toneColors(bucket.tone).text }}>{bucket.label}</div>
                    <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{bucket.range}</div>
                    <div style={{ marginTop: '8px', fontSize: '18px', fontWeight: 800, color: toneColors(bucket.tone).text }}>{dashboard?.score_breakdown?.[bucket.id] || 0}</div>
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 12px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#374151', whiteSpace: 'nowrap' }}>Custom</span>
                  <input
                    type="number" min={0} max={100} value={audienceScoreMin}
                    onChange={(event) => setAudienceScoreMin(Number(event.target.value))}
                    style={{ ...inputStyle, width: '72px', padding: '8px 10px' }}
                  />
                  <span style={{ fontSize: '12px', color: '#6b7280' }}>to</span>
                  <input
                    type="number" min={0} max={100} value={audienceScoreMax}
                    onChange={(event) => setAudienceScoreMax(Number(event.target.value))}
                    style={{ ...inputStyle, width: '72px', padding: '8px 10px' }}
                  />
                </div>
                <button onClick={() => { setAudiencePage(1); loadAudience(); }} disabled={audienceLoading} style={primaryButtonStyle(audienceLoading)}>
                  {audienceLoading ? 'Searching…' : 'Search'}
                </button>
                <Badge label={`${audienceTotal} matched`} tone="slate" />
              </div>
            </div>

            {importResult ? (
              <div style={{ marginBottom: '16px', padding: '12px 14px', borderRadius: '10px', border: `1px solid ${importResult.ok === false ? '#fecaca' : '#bbf7d0'}`, background: importResult.ok === false ? '#fef2f2' : '#f0fdf4', color: importResult.ok === false ? '#b91c1c' : '#166534', fontSize: '12px', lineHeight: 1.7 }}>
                {importResult.ok === false ? (
                  <strong>{importResult.detail || 'Import failed'}</strong>
                ) : (
                  <>
                    <strong>{importResult.source?.toUpperCase() || 'IMPORT'} complete.</strong>
                    {' '}
                    Created {importResult.created || 0}, updated {importResult.updated || 0}, skipped {importResult.skipped || 0}.
                    {importResult.normalized_contacts ? ` ${importResult.normalized_contacts} contact groups were resolved from the file.` : ''}
                    {importResult.skipped_no_phone ? ` ${importResult.skipped_no_phone} skipped because no phone number was available.` : ''}
                  </>
                )}
              </div>
            ) : null}

            {audienceLoading ? (
              <EmptyState title="Loading audience" body="Fetching WhatsApp-ready customers from the unified customer table." />
            ) : !audienceRows.length ? (
              <EmptyState title="No audience contacts" body="Run a Shopify import or upload a file with phone numbers to populate the WhatsApp audience." />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      {['Name', 'Phone', 'Email', 'Types', 'Source', 'Orders', 'Spend', 'Updated'].map((heading) => (
                        <th key={heading} style={thStyle}>{heading}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {audienceRows.map((row) => (
                      <tr key={row.id} style={trStyle}>
                        <td style={tdStyle}>
                          <div style={{ fontWeight: 700, color: '#111827' }}>{row.full_name || 'Unnamed contact'}</div>
                          <div style={{ marginTop: '3px', fontSize: '11px', color: '#64748b' }}>{row.tags?.length ? row.tags.join(', ') : 'No tags'}</div>
                        </td>
                        <td style={tdStyle}><span style={monoStyle}>{row.phone || '—'}</span></td>
                        <td style={tdStyle}>{row.email || '—'}</td>
                        <td style={tdStyle}>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {(row.lead_types?.length ? row.lead_types : ['general']).map((item) => (
                              <Badge key={`${row.id}-${item}`} label={audienceTypeLabel(item)} tone={audienceTypeTone(item)} />
                            ))}
                          </div>
                        </td>
                        <td style={tdStyle}><Badge label={row.source || 'manual'} tone="slate" /></td>
                        <td style={tdStyle}>{row.total_orders || 0}</td>
                        <td style={tdStyle}>{formatMoney(row.total_spent || 0)}</td>
                        <td style={tdStyle}>{formatDateTime(row.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {audienceTotal > audiencePageSize ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', flexWrap: 'wrap', gap: '10px' }}>
                <span style={{ fontSize: '12px', color: '#64748b' }}>
                  Page {audiencePage} of {Math.ceil(audienceTotal / audiencePageSize)} · {audienceTotal} total
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    disabled={audiencePage <= 1 || audienceLoading}
                    onClick={() => setAudiencePage((p) => Math.max(1, p - 1))}
                    style={secondaryButtonStyle(audiencePage <= 1 || audienceLoading)}
                  >← Prev</button>
                  <button
                    disabled={audiencePage >= Math.ceil(audienceTotal / audiencePageSize) || audienceLoading}
                    onClick={() => setAudiencePage((p) => p + 1)}
                    style={secondaryButtonStyle(audiencePage >= Math.ceil(audienceTotal / audiencePageSize) || audienceLoading)}
                  >Next →</button>
                </div>
              </div>
            ) : null}
          </PanelSection>

          <input ref={csvInputRef} type="file" accept=".csv,text/csv" style={{ display: 'none' }} onChange={(event) => handleFileChosen('csv', event)} />
          <input ref={xmlInputRef} type="file" accept=".xml,text/xml,application/xml" style={{ display: 'none' }} onChange={(event) => handleFileChosen('xml', event)} />
          <input ref={xlsxInputRef} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" style={{ display: 'none' }} onChange={(event) => handleFileChosen('xlsx', event)} />
        </div>
      ) : null}

      {mainTab === 'journey' ? (
        <div style={{ display: 'grid', gap: '18px' }}>

          <PanelSection
            title="When Does a Journey Start?"
            subtitle="Use this as the operating map: automatic order journeys are event-driven, while interested/custom journeys start only when you launch a filtered campaign."
            actions={salesOs?.automation?.old_manual_orders_ignored ? <Badge label="Old manual orders ignored" tone="green" /> : null}
          >
            <div style={{ display: 'grid', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                {[
                  {
                    step: '1',
                    title: 'New Shopify order',
                    body: `Starts the purchased/order journey when a new order arrives after ${salesOs?.automation?.start_label || '23 May 2026, 12:00 AM IST'} and the customer has a phone number. Sends order confirmation immediately.`,
                    tone: 'amber',
                  },
                  {
                    step: '2',
                    title: 'Tracking is added',
                    body: 'Moves the same order to the tracking stage when Shopify fulfillment or carrier tracking appears. Sends the in-transit message once for that order.',
                    tone: 'blue',
                  },
                  {
                    step: '3',
                    title: 'Delivered event arrives',
                    body: 'Moves the order to delivered when the carrier/status webhook marks it delivered. Sends the delivered message once, then later review/upsell stages can qualify by date window.',
                    tone: 'green',
                  },
                  {
                    step: '4',
                    title: 'Interested/custom audience',
                    body: 'Does not start automatically. Pick Purchased, Interested, or Custom AI Journey below, choose filters/template/channel, then Create Campaign to queue WhatsApp and/or email.',
                    tone: 'indigo',
                  },
                ].map((item) => {
                  const colors = toneColors(item.tone);
                  return (
                    <div key={item.step} style={{ padding: '15px 16px', borderRadius: '12px', border: `1px solid ${colors.border}`, background: colors.background, display: 'grid', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ width: '26px', height: '26px', borderRadius: '999px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'white', border: `1px solid ${colors.border}`, color: colors.text, fontSize: '12px', fontWeight: 900 }}>{item.step}</span>
                        <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>{item.title}</div>
                      </div>
                      <div style={{ fontSize: '12px', color: '#475569', lineHeight: 1.65 }}>{item.body}</div>
                    </div>
                  );
                })}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px', alignItems: 'stretch' }}>
                <div style={{ padding: '14px 16px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>Start gate currently active</div>
                  <div style={{ marginTop: '7px', fontSize: '12px', color: '#475569', lineHeight: 1.7 }}>
                    The system starts considering orders from <strong>{salesOs?.automation?.start_label || '23 May 2026, 12:00 AM IST'}</strong>. Anything before that is treated as already handled manually and is excluded from lifecycle counts, retries, and daily orchestration.
                  </div>
                </div>
                <div style={{ padding: '14px 16px', borderRadius: '12px', background: '#ecfdf5', border: '1px solid #bbf7d0' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#166534' }}>What happens next?</div>
                  <div style={{ marginTop: '7px', fontSize: '12px', color: '#14532d', lineHeight: 1.7 }}>
                    New order/tracking/delivered events send immediately. Daily review, upsell, corporate, loyalty, and reactivation stages are checked at <strong>10:00 AM IST</strong> using the date windows below.
                  </div>
                </div>
              </div>
            </div>
          </PanelSection>

          {/* ── Journey Orchestration Engine ──────────────────────────── */}
          <PanelSection
            title="Automatic Order Journey Monitor"
            subtitle={`Today-forward lifecycle only. Automation starts ${salesOs?.automation?.start_label || '23 May 2026, 12:00 AM IST'} and watches new order, tracking, and delivered events from that point onward.`}
            actions={(
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button onClick={loadJourneyPipeline} disabled={journeyPipelineLoading} style={secondaryButtonStyle(journeyPipelineLoading)}>
                  {journeyPipelineLoading ? 'Refreshing…' : 'Refresh'}
                </button>
                <button onClick={() => retryLifecycle('all', true)} disabled={salesOsAction === 'preview-all'} style={primaryButtonStyle(salesOsAction === 'preview-all')}>
                  {salesOsAction === 'preview-all' ? 'Checking…' : 'Preview Run Now'}
                </button>
              </div>
            )}
          >
            <div style={{ marginBottom: '14px', padding: '12px 14px', borderRadius: '12px', background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1d4ed8', fontSize: '12px', lineHeight: 1.7 }}>
              Preview Run Now is safe: it only checks rows from the start gate above. If eligible rows appear, the send button is shown after the preview.
            </div>
            {salesOsResult?.dryRun ? (
              <div style={{ marginBottom: '14px', padding: '12px 14px', borderRadius: '12px', background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', fontSize: '12px', lineHeight: 1.7 }}>
                {(salesOsResult.data?.results || []).map((item) => `${item.event_type}: ${item.dry_run || 0} eligible`).join(' · ') || 'No eligible rows'}
                {(salesOsResult.data?.results || []).some((item) => item.dry_run > 0) ? (
                  <button onClick={() => retryLifecycle(salesOsResult.eventType, false)} disabled={salesOsAction === `retry-${salesOsResult.eventType}`} style={{ marginLeft: '10px', ...primaryButtonStyle(salesOsAction === `retry-${salesOsResult.eventType}`) }}>{salesOsAction === `retry-${salesOsResult.eventType}` ? 'Sending…' : 'Send Eligible Now'}</button>
                ) : null}
              </div>
            ) : null}
            {orchestrateResult ? (
              <div style={{ marginBottom: '16px', padding: '14px 16px', borderRadius: '12px', border: `1px solid ${orchestrateResult.error ? '#fecaca' : '#bbf7d0'}`, background: orchestrateResult.error ? '#fef2f2' : '#f0fdf4' }}>
                {orchestrateResult.error ? (
                  <div style={{ fontSize: '13px', color: '#991b1b' }}>Error: {orchestrateResult.error}</div>
                ) : (
                  <div style={{ display: 'grid', gap: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#166534' }}>Orchestration complete — {orchestrateResult.total_sent || 0} messages sent across {orchestrateResult.stages_run || 0} stages</div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {(orchestrateResult.stages || []).filter((s) => s.eligible > 0).map((s) => (
                        <Badge key={s.stage} label={`${s.stage}: ${s.sent} sent / ${s.eligible} eligible`} tone={s.sent > 0 ? 'green' : 'slate'} />
                      ))}
                      {!(orchestrateResult.stages || []).some((s) => s.eligible > 0) ? <Badge label="No eligible customers today" tone="slate" /> : null}
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '16px' }}>
              <div style={miniMetricStyle('indigo')}>
                <div style={miniMetricValueStyle('#4338ca')}>{salesOs?.orders?.automation_orders ?? journeyPipeline?.total_journey_customers ?? '—'}</div>
                <div style={miniMetricLabelStyle}>Automation Orders</div>
              </div>
              <div style={miniMetricStyle('amber')}>
                <div style={miniMetricValueStyle('#92400e')}>{salesOs?.lifecycle?.order_confirmations_pending ?? journeyPipeline?.stage_breakdown?.order_confirmed ?? '—'}</div>
                <div style={miniMetricLabelStyle}>Confirmations Pending</div>
              </div>
              <div style={miniMetricStyle('blue')}>
                <div style={miniMetricValueStyle('#1d4ed8')}>{salesOs?.lifecycle?.tracking_messages_pending ?? journeyPipeline?.stage_breakdown?.in_transit ?? '—'}</div>
                <div style={miniMetricLabelStyle}>Tracking Pending</div>
              </div>
              <div style={miniMetricStyle('green')}>
                <div style={miniMetricValueStyle('#166534')}>{salesOs?.lifecycle?.delivery_messages_pending ?? journeyPipeline?.stage_breakdown?.delivered ?? '—'}</div>
                <div style={miniMetricLabelStyle}>Delivered Pending</div>
              </div>
              <div style={miniMetricStyle('slate')}>
                <div style={miniMetricValueStyle('#374151')}>{journeyPipeline ? Object.values(journeyPipeline.send_flags || {}).reduce((a, b) => a + b, 0) : '—'}</div>
                <div style={miniMetricLabelStyle}>Total Msgs Sent</div>
              </div>
            </div>

            {journeyPipeline ? (
              <div style={{ display: 'grid', gap: '8px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>Lifecycle Stage Progress</div>
                {lifecycleStageCards.map(({ key, defaultLabel, stage }) => {
                  const sentCount = journeyPipeline.send_flags?.[key] ?? 0;
                  const stageCount = journeyPipeline.stage_breakdown?.[stage] ?? 0;
                  const total = journeyPipeline.total_journey_customers || 1;
                  const pct = Math.round((sentCount / total) * 100);
                  const recent7d = Object.values(journeyPipeline.recent_7d?.[stage] || {}).reduce((a, b) => a + b, 0);
                  const stageConfig = lifecycleStageMap[stage];
                  const isSelected = selectedLifecycleStage === stage;
                  const activeTemplateName = stageConfig?.active_template_name || stageConfig?.default_template_names?.[0] || 'Template not configured';
                  return (
                    <button
                      type="button"
                      key={key}
                      onClick={() => openLifecycleStageStudio(stage)}
                      style={{
                        padding: '10px 14px',
                        borderRadius: '10px',
                        background: isSelected ? '#ecfeff' : '#f8fafc',
                        border: `1px solid ${isSelected ? '#67e8f9' : '#e2e8f0'}`,
                        display: 'grid',
                        gap: '6px',
                        textAlign: 'left',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: '#111827' }}>{stageConfig?.label || defaultLabel}</div>
                          <div style={{ marginTop: '4px', fontSize: '10px', color: '#64748b' }}>Template: {activeTemplateName}</div>
                        </div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          {recent7d > 0 ? <Badge label={`+${recent7d} last 7d`} tone="green" /> : null}
                          {stageConfig?.override ? <Badge label="Override active" tone="indigo" /> : null}
                          <Badge label={`${sentCount} sent`} tone={sentCount > 0 ? 'blue' : 'slate'} />
                          {stageCount > 0 ? <Badge label={`${stageCount} at stage`} tone="indigo" /> : null}
                        </div>
                      </div>
                      <div style={{ height: '5px', borderRadius: '999px', background: '#e2e8f0', overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: sentCount > 0 ? '#0f766e' : '#e2e8f0', minWidth: sentCount > 0 ? '3px' : '0' }} />
                      </div>
                      <div style={{ fontSize: '10px', color: '#94a3b8' }}>{pct}% of total journey customers have received this stage</div>
                    </button>
                  );
                })}

                {selectedLifecycleStageConfig ? (
                  <div style={{ marginTop: '10px', padding: '16px', borderRadius: '14px', border: '1px solid #cbd5e1', background: 'white', display: 'grid', gap: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontSize: '15px', fontWeight: 800, color: '#111827' }}>Stage Template Studio</div>
                        <div style={{ marginTop: '5px', fontSize: '12px', color: '#475569', lineHeight: 1.7 }}>
                          <strong>{selectedLifecycleStageConfig.label}</strong> · {selectedLifecycleStageConfig.trigger}
                        </div>
                        <div style={{ marginTop: '5px', fontSize: '12px', color: '#64748b', lineHeight: 1.7 }}>{selectedLifecycleStageConfig.description}</div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <Badge label={selectedLifecycleStageConfig.override ? 'Override saved' : 'Backend default'} tone={selectedLifecycleStageConfig.override ? 'indigo' : 'slate'} />
                        <Badge label={`Recommended ${selectedLifecycleStageConfig.recommended_category}`} tone={selectedLifecycleStageConfig.recommended_category === 'UTILITY' ? 'blue' : 'amber'} />
                      </div>
                    </div>

                    {selectedLifecycleStageConfig.uses_segment_defaults ? (
                      <div style={{ padding: '12px 14px', borderRadius: '12px', border: '1px solid #fde68a', background: '#fffbeb', color: '#92400e', fontSize: '12px', lineHeight: 1.7 }}>
                        This stage currently has segment-aware defaults: {selectedLifecycleStageConfig.default_template_names.join(' · ')}. Saving an override here replaces that branching with one universal template for this stage.
                      </div>
                    ) : null}

                    {lifecycleTemplateResult ? (
                      <div style={{ padding: '12px 14px', borderRadius: '12px', border: `1px solid ${lifecycleTemplateResult.ok ? '#bbf7d0' : '#fecaca'}`, background: lifecycleTemplateResult.ok ? '#f0fdf4' : '#fef2f2', color: lifecycleTemplateResult.ok ? '#166534' : '#b91c1c', fontSize: '12px', lineHeight: 1.7 }}>
                        {lifecycleTemplateResult.text}
                      </div>
                    ) : null}

                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 0.95fr) minmax(0, 1.05fr)', gap: '16px', alignItems: 'start' }}>
                      <div style={{ display: 'grid', gap: '12px' }}>
                        <div style={softPanelStyle('slate')}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
                            <div>
                              <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>Live Review</div>
                              <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{selectedLifecycleTemplate?.name || selectedLifecycleTemplateName || 'Choose a template from the right'}</div>
                            </div>
                            {selectedLifecycleTemplate ? <Badge label={`${selectedLifecycleTemplate._channel} · ${selectedLifecycleTemplate.status || 'unknown'}`} tone={selectedLifecycleTemplate._channel === 'meta' ? 'blue' : 'green'} /> : null}
                          </div>
                          <div style={{ marginTop: '12px', background: '#e5ddd5', borderRadius: '14px', padding: '14px', minHeight: '220px' }}>
                            {selectedLifecycleTemplate ? (
                              <div style={{ background: '#dcf8c6', borderRadius: '10px 10px 10px 0', padding: '14px 16px', boxShadow: '0 1px 2px rgba(15, 23, 42, 0.08)' }}>
                                {selectedLifecycleTemplate.header?.text ? <div style={{ marginBottom: '6px', fontSize: '13px', fontWeight: 700, color: '#111827' }}>{highlightVars(selectedLifecycleTemplate.header.text)}</div> : null}
                                <div style={{ fontSize: '13px', color: '#111827', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{highlightVars(templatePreviewText(selectedLifecycleTemplate))}</div>
                                {selectedLifecycleTemplate.footer?.text ? <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>{selectedLifecycleTemplate.footer.text}</div> : null}
                              </div>
                            ) : (
                              <EmptyState title="No template selected" body="Pick a template on the right to preview exactly what this stage would use." />
                            )}
                          </div>
                          {selectedLifecycleTemplate ? (
                            <div style={{ fontSize: '11px', color: '#64748b', lineHeight: 1.8 }}>
                              Active now: <strong>{selectedLifecycleStageConfig.active_template_name}</strong><br />
                              Default route: {selectedLifecycleStageConfig.default_template_names.join(' · ')}
                            </div>
                          ) : null}
                        </div>
                      </div>

                      <div style={{ display: 'grid', gap: '12px' }}>
                        <div style={softPanelStyle('blue')}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                            <div>
                              <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>Choose Different Template</div>
                              <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>Search synced Wabis and Meta templates, preview one, then save it for this lifecycle stage.</div>
                            </div>
                            {lifecycleStageLoading ? <Badge label="Loading" tone="blue" /> : <Badge label={`${lifecycleTemplateLibrary.length} templates`} tone="slate" />}
                          </div>
                          <input value={lifecycleTemplateSearch} onChange={(event) => setLifecycleTemplateSearch(event.target.value)} placeholder="Search templates by name or preview text" style={inputStyle} />
                          <div style={{ marginTop: '10px', display: 'grid', gap: '8px', maxHeight: '280px', overflowY: 'auto', paddingRight: '4px' }}>
                            {lifecycleTemplateLibrary.length ? lifecycleTemplateLibrary.map((template) => {
                              const selected = selectedLifecycleTemplateName === template.name;
                              const unsupported = (template.header?.vars || 0) > 0;
                              return (
                                <button
                                  type="button"
                                  key={template.name}
                                  onClick={() => setSelectedLifecycleTemplateName(template.name)}
                                  style={{ ...templateListItemStyle(selected), opacity: unsupported ? 0.72 : 1 }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>{template.name}</div>
                                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>{templatePreviewText(template).slice(0, 110)}{templatePreviewText(template).length > 110 ? '…' : ''}</div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                                      <Badge label={template.category || 'Unknown'} tone={String(template.category || '').toUpperCase() === 'UTILITY' ? 'blue' : 'amber'} />
                                      <Badge label={template.status || 'unknown'} tone={String(template.status || '').toUpperCase() === 'APPROVED' ? 'green' : 'slate'} />
                                    </div>
                                  </div>
                                  {unsupported ? <div style={{ marginTop: '6px', fontSize: '10px', color: '#b91c1c' }}>Dynamic header variables are not supported for lifecycle stage overrides yet.</div> : null}
                                </button>
                              );
                            }) : <EmptyState title="No templates found" body="Try a different search, or create a fresh template for this stage below." />}
                          </div>

                          <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            <button
                              onClick={() => saveLifecycleStageTemplate(selectedLifecycleStageConfig.stage, selectedLifecycleTemplateName)}
                              disabled={lifecycleTemplateSaving || !selectedLifecycleTemplateName || !selectedLifecycleTemplate || (selectedLifecycleTemplate.header?.vars || 0) > 0 || !lifecycleTemplateDirty}
                              style={primaryButtonStyle(lifecycleTemplateSaving || !selectedLifecycleTemplateName || !selectedLifecycleTemplate || (selectedLifecycleTemplate.header?.vars || 0) > 0 || !lifecycleTemplateDirty)}
                            >
                              {lifecycleTemplateSaving ? 'Saving…' : 'Save for This Stage'}
                            </button>
                            <button
                              onClick={() => saveLifecycleStageTemplate(selectedLifecycleStageConfig.stage, '')}
                              disabled={lifecycleTemplateSaving || !selectedLifecycleStageConfig.override}
                              style={secondaryButtonStyle(lifecycleTemplateSaving || !selectedLifecycleStageConfig.override)}
                            >
                              Reset to Default
                            </button>
                            <button onClick={() => prefillLifecycleStageComposer(selectedLifecycleStageConfig)} style={secondaryButtonStyle(false)}>
                              {lifecycleCreateOpen ? 'Update Draft Below' : 'Create New Template for This Stage'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>

                    {lifecycleCreateOpen ? (
                      <div style={{ display: 'grid', gap: '12px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>Create New Template for {selectedLifecycleStageConfig.label}</div>
                        <CreateTemplatePane newTpl={newTpl} onChange={setNewTpl} onSubmit={handleCreateTemplate} creating={creating} createMsg={createMsg} />
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div style={{ marginTop: '8px', padding: '14px 16px', borderRadius: '12px', background: '#f8fafc', border: '1px dashed #cbd5e1', fontSize: '12px', color: '#64748b', lineHeight: 1.7 }}>
                    Click any lifecycle stage row to inspect the current template, preview it live, choose a different template, or create a new one for that stage.
                  </div>
                )}

                <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>
                  Next auto-run: daily at <strong>10:00 AM IST</strong>. Counts and sends here exclude orders before the automation start date.
                </div>
              </div>
            ) : (
              <EmptyState title={journeyPipelineLoading ? 'Loading pipeline…' : 'No pipeline data'} body="Click Refresh to load the lifecycle stage progress." />
            )}
          </PanelSection>

          {/* ── Campaign Builder ──────────────────────────────────────── */}
          {campaignStep === 0 ? (
            <PanelSection
              title="Audience Campaign Journeys"
              subtitle="Use these for purchased follow-up, interested non-purchased leads, or a custom AI-defined audience. These journeys begin when you create the campaign."
              actions={
                <button onClick={() => {
                  setCampaignStep(1);
                  setCampaignName('');
                  setCampaignFilters({ score_min: 70, score_max: 100, score_buckets: [], lead_types: [], labels: [], statuses: [], engagement_labels: [], language: 'all', date_field: 'updated_at', date_from: '', date_to: '', delivery_channels: ['whatsapp'] });
                  setCampaignTemplate(null);
                  setEmailSubject('');
                  setEmailHtml('');
                  setCampaignEstimate(null);
                  setCampaignEstimateError(null);
                  setCampaignResult(null);
                  setAiSuggestion(null);
                  setAiExpanded(false);
                  setLabelSearch('');
                }} style={primaryButtonStyle(false)}>
                  + New Campaign
                </button>
              }
            >
              <div style={{ display: 'grid', gap: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                  {[
                    { key: 'purchased', title: 'Purchased Customer Journey', body: 'Review, repeat purchase, cross-sell, loyalty, gifting, and replenishment.', tone: 'amber' },
                    { key: 'interested', title: 'Interested Non-purchased Journey', body: 'For interested labels, warm scores, and WhatsApp leads who have not ordered.', tone: 'green' },
                    { key: 'all', title: 'Custom AI Journey', body: 'Define type, status, label, score, date, channel, and template with AI help.', tone: 'indigo' },
                    { key: 'abandoned', title: 'Abandoned Recovery Journey', body: 'Recover abandoned or open order prospects with urgency and proof.', tone: 'red' },
                  ].map((goal) => (
                    <button
                      key={goal.key}
                      onClick={() => startFunnelForAudience(goal.key, `${goal.title} Funnel`)}
                      style={{ ...scoreSelectorCardStyle(false, goal.tone), textAlign: 'left', padding: '15px 16px' }}
                    >
                      <div style={{ fontSize: '13px', fontWeight: 800, color: toneColors(goal.tone).text }}>{goal.title}</div>
                      <div style={{ marginTop: '7px', fontSize: '12px', lineHeight: 1.6, color: '#475569' }}>{goal.body}</div>
                      <div style={{ marginTop: '12px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <Badge label="AI audience" tone={goal.tone} />
                        <Badge label="Template pick" tone="slate" />
                      </div>
                    </button>
                  ))}
                </div>
                <div style={{ padding: '14px 16px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Need a specific set of customers?</div>
                    <div style={{ marginTop: '4px', fontSize: '12px', color: '#64748b', lineHeight: 1.6 }}>Use labels, score, type, language, and status in the campaign builder. AI will recommend when to send and which template to use.</div>
                  </div>
                  <button onClick={() => startFunnelForAudience('all', 'Custom Audience Funnel')} style={primaryButtonStyle(false)}>Build Custom Funnel</button>
                </div>
              </div>
            </PanelSection>
          ) : campaignStep === 4 ? (
            <PanelSection title="Campaign Created" subtitle="Your campaign has been saved and queued for send.">
              <div style={{ padding: '24px', borderRadius: '12px', background: '#f0fdf4', border: '1px solid #bbf7d0', textAlign: 'center' }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>✓</div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: '#166534', marginBottom: '8px' }}>{campaignResult?.name || 'Campaign'} created</div>
                <div style={{ fontSize: '13px', color: '#14532d', lineHeight: 1.8 }}>
                  {campaignResult?.recipients || 0} recipients queued · Status: {campaignResult?.status || 'pending'}
                  {campaignResult?.whatsapp_recipients !== undefined ? ` · WhatsApp ${campaignResult.whatsapp_recipients}` : ''}
                  {campaignResult?.email_recipients !== undefined ? ` · Email ${campaignResult.email_recipients}` : ''}
                  {campaignResult?.schedule_type === 'scheduled' ? ` · Scheduled for ${campaignResult.scheduled_at}` : ''}
                </div>
                <button onClick={() => {
                  setCampaignStep(0);
                  setCampaignName('');
                  setCampaignFilters({ score_min: 70, score_max: 100, score_buckets: [], lead_types: [], labels: [], statuses: [], engagement_labels: [], language: 'all', date_field: 'updated_at', date_from: '', date_to: '', delivery_channels: ['whatsapp'] });
                  setCampaignTemplate(null);
                  setEmailSubject('');
                  setEmailHtml('');
                  setCampaignEstimate(null);
                  setCampaignEstimateError(null);
                  setCampaignResult(null);
                  setAiSuggestion(null);
                  setAiExpanded(false);
                  setLabelSearch('');
                }} style={{ marginTop: '16px', ...primaryButtonStyle(false) }}>
                  Back to Journey
                </button>
              </div>
            </PanelSection>
          ) : (
            <PanelSection
              title={`Campaign Builder — Step ${campaignStep} of 3`}
              subtitle={['', 'Select audience filters', 'Choose a WhatsApp template', 'Review cost & schedule'][campaignStep]}
              actions={
                <button onClick={() => setCampaignStep(0)} style={secondaryButtonStyle(false)}>Cancel</button>
              }
            >
              {/* Step indicator */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
                {[1, 2, 3].map((s) => (
                  <div key={s} style={{
                    flex: 1, height: '6px', borderRadius: '999px',
                    background: s <= campaignStep ? '#0f766e' : '#e5e7eb',
                    transition: 'background 0.2s',
                  }} />
                ))}
              </div>

              {/* Step 1 — Audience */}
              {campaignStep === 1 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.12fr) minmax(320px, 0.88fr)', gap: '20px', alignItems: 'start' }}>
                  <div style={{ display: 'grid', gap: '18px' }}>
                    <div>
                      <label style={labelStyle}>Campaign Name</label>
                      <input value={campaignName} onChange={(e) => setCampaignName(e.target.value)} placeholder="e.g. Onam Offer 2025" style={inputStyle} />
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <label style={labelStyle}>Delivery Channel</label>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {DELIVERY_CHANNEL_OPTIONS.map(([value, label]) => (
                          <button
                            key={value}
                            onClick={() => setCampaignFilters((f) => {
                              const next = toggleListValue(f.delivery_channels || [], value);
                              return { ...f, delivery_channels: next.length ? next : [value] };
                            })}
                            style={multiSelectChipStyle(campaignDeliveryChannels.has(value), value === 'email' ? 'blue' : 'green')}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <label style={labelStyle}>Audience Types</label>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button
                          onClick={() => setCampaignFilters((f) => ({ ...f, lead_types: [] }))}
                          style={multiSelectChipStyle(campaignFilters.lead_types.length === 0, 'slate')}
                        >
                          All audience types
                        </button>
                        {AUDIENCE_TYPE_OPTIONS.filter(([value]) => value !== 'all').map(([value, label]) => (
                          <button
                            key={value}
                            onClick={() => setCampaignFilters((f) => ({ ...f, lead_types: toggleListValue(f.lead_types, value) }))}
                            style={multiSelectChipStyle(campaignSelectedLeadTypes.has(value), audienceTypeTone(value))}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                        <label style={{ ...labelStyle, marginBottom: 0 }}>Status</label>
                        <Badge label={`${(campaignFilters.statuses || []).length + (campaignFilters.engagement_labels || []).length} selected`} tone="slate" />
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {STATUS_OPTIONS.map(([value, label]) => (
                          <button
                            key={value}
                            onClick={() => setCampaignFilters((f) => ({ ...f, statuses: toggleListValue(f.statuses || [], value) }))}
                            style={multiSelectChipStyle(selectedStatusSet.has(value), value === 'purchased' ? 'amber' : value === 'abandoned' ? 'red' : value === 'interested' ? 'green' : 'slate')}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {['cold', 'warm', 'hot', 'inactive'].map((value) => (
                          <button
                            key={value}
                            onClick={() => setCampaignFilters((f) => ({ ...f, engagement_labels: toggleListValue(f.engagement_labels || [], value) }))}
                            style={multiSelectChipStyle(selectedEngagementSet.has(value), value === 'hot' ? 'red' : value === 'warm' ? 'green' : 'slate')}
                          >
                            Engagement: {value}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div style={softPanelStyle('slate')}>
                        <label style={labelStyle}>Language</label>
                        <select value={campaignFilters.language} onChange={(e) => setCampaignFilters((f) => ({ ...f, language: e.target.value }))} style={inputStyle}>
                          <option value="all">All languages</option>
                          <option value="mal">Malayalam only</option>
                          <option value="eng">English only</option>
                        </select>
                      </div>
                      <div style={softPanelStyle('slate')}>
                        <label style={labelStyle}>Custom Score Range</label>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '8px', alignItems: 'center' }}>
                          <input type="number" min={0} max={100} value={campaignFilters.score_min} onChange={(e) => setCampaignFilters((f) => ({ ...f, score_min: Number(e.target.value) }))} style={inputStyle} />
                          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 700 }}>to</span>
                          <input type="number" min={0} max={100} value={campaignFilters.score_max} onChange={(e) => setCampaignFilters((f) => ({ ...f, score_max: Number(e.target.value) }))} style={inputStyle} />
                        </div>
                      </div>
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <label style={labelStyle}>Date Window</label>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                        <select value={campaignFilters.date_field || 'updated_at'} onChange={(e) => setCampaignFilters((f) => ({ ...f, date_field: e.target.value }))} style={inputStyle}>
                          <option value="updated_at">Updated date</option>
                          <option value="created_at">Created date</option>
                          <option value="last_order_date">Last order date</option>
                        </select>
                        <input type="date" value={campaignFilters.date_from || ''} onChange={(e) => setCampaignFilters((f) => ({ ...f, date_from: e.target.value }))} style={inputStyle} />
                        <input type="date" value={campaignFilters.date_to || ''} onChange={(e) => setCampaignFilters((f) => ({ ...f, date_to: e.target.value }))} style={inputStyle} />
                      </div>
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: '#374151' }}>Score Targeting</div>
                          <div style={{ marginTop: '3px', fontSize: '11px', color: '#64748b' }}>Select one or more score buckets. Custom range narrows the final audience.</div>
                        </div>
                        <Badge label={`${campaignFilters.score_min}-${campaignFilters.score_max}`} tone="slate" />
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(135px, 1fr))', gap: '10px' }}>
                        {SCORE_BUCKET_OPTIONS.map((bucket) => {
                          const active = selectedScoreBuckets.has(bucket.id);
                          const count = campaignEstimate?.score_breakdown?.[bucket.id] ?? dashboard?.score_breakdown?.[bucket.id] ?? 0;
                          return (
                            <button
                              key={bucket.id}
                              onClick={() => setCampaignFilters((f) => ({ ...f, score_buckets: toggleListValue(f.score_buckets, bucket.id) }))}
                              style={scoreSelectorCardStyle(active, bucket.tone)}
                            >
                              <div style={{ fontSize: '12px', fontWeight: 800, color: toneColors(bucket.tone).text }}>{bucket.label}</div>
                              <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{bucket.range}</div>
                              <div style={{ marginTop: '10px', fontSize: '20px', fontWeight: 800, color: toneColors(bucket.tone).text }}>{count}</div>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: '#374151' }}>Labels</div>
                          <div style={{ marginTop: '3px', fontSize: '11px', color: '#64748b' }}>Use curated campaign-safe tags or search the full tag list from the audience.</div>
                        </div>
                        {labelsLoading ? <Badge label="Loading labels" tone="blue" /> : <Badge label={`${campaignFilters.labels.length} selected`} tone="slate" />}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                        <button onClick={() => setCampaignFilters((f) => ({ ...f, labels: [] }))} style={multiSelectChipStyle(campaignFilters.labels.length === 0, 'slate')}>
                          Clear labels
                        </button>
                        {CURATED_LABEL_OPTIONS.map((label) => (
                          <button
                            key={label}
                            onClick={() => setCampaignFilters((f) => ({ ...f, labels: toggleListValue(f.labels, label) }))}
                            style={multiSelectChipStyle(selectedLabelSet.has(label.toLowerCase()), 'indigo')}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      <input value={labelSearch} onChange={(e) => setLabelSearch(e.target.value)} placeholder="Search all audience labels" style={inputStyle} />
                      <div style={{ marginTop: '10px', display: 'grid', gap: '8px', maxHeight: '190px', overflowY: 'auto', paddingRight: '4px' }}>
                        {labelOptions.length ? labelOptions.map((item) => {
                          const active = selectedLabelSet.has(String(item.label).toLowerCase());
                          return (
                            <button
                              key={item.label}
                              onClick={() => setCampaignFilters((f) => ({ ...f, labels: toggleListValue(f.labels, item.label) }))}
                              style={{
                                ...templateListItemStyle(active),
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}
                            >
                              <span style={{ fontSize: '12px', fontWeight: 700, color: '#111827' }}>{item.label}</span>
                              <span style={{ fontSize: '11px', color: '#64748b' }}>{item.count ?? 'preset'}</span>
                            </button>
                          );
                        }) : <EmptyState title="No labels found" body="Try another search to load audience tags." />}
                      </div>
                    </div>

                    <div style={{ borderRadius: '12px', border: '1px solid #c7d2fe', background: '#eef2ff', overflow: 'hidden' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', cursor: 'pointer' }} onClick={() => setAiExpanded((v) => !v)}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: '#4338ca' }}>AI Campaign Recommendation</div>
                          <div style={{ marginTop: '3px', fontSize: '11px', color: '#6366f1' }}>Analyzes hot customers from the current filters and pre-fills a template.</div>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <button onClick={(e) => { e.stopPropagation(); loadAiSuggestion(campaignFilters); }} disabled={aiLoading} style={aiActionButtonStyle(aiLoading)}>
                            {aiLoading ? 'Analyzing…' : aiSuggestion ? 'Refresh AI' : 'Analyze Hot Customers'}
                          </button>
                          <span style={{ fontSize: '12px', color: '#6366f1' }}>{aiExpanded ? '▲' : '▼'}</span>
                        </div>
                      </div>
                      {aiExpanded && aiSuggestion ? (
                        <div style={{ padding: '0 16px 16px', display: 'grid', gap: '12px' }}>
                          <div style={{ fontSize: '13px', color: '#312e81', lineHeight: 1.6 }}>{aiSuggestion.recommendation || 'AI found a promising audience from the current filters.'}</div>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
                            <div style={miniMetricStyle('indigo')}>
                              <div style={miniMetricValueStyle('#4338ca')}>{aiSuggestion.summary?.total_hot || 0}</div>
                              <div style={miniMetricLabelStyle}>Hot Customers</div>
                            </div>
                            <div style={miniMetricStyle('amber')}>
                              <div style={miniMetricValueStyle('#d97706')}>{aiSuggestion.summary?.top_20_buyers || 0}</div>
                              <div style={miniMetricLabelStyle}>Top 20 Buyers</div>
                            </div>
                            <div style={miniMetricStyle('green')}>
                              <div style={miniMetricValueStyle('#166534')}>{aiSuggestion.summary?.estimated_conversion_pct || 0}%</div>
                              <div style={miniMetricLabelStyle}>Est. Conversion</div>
                            </div>
                            <div style={miniMetricStyle('blue')}>
                              <div style={miniMetricValueStyle('#1d4ed8')}>{aiSuggestion.summary?.recommended_language === 'mal' ? 'Malayalam' : 'English'}</div>
                              <div style={miniMetricLabelStyle}>Recommended Language</div>
                            </div>
                          </div>
                          {aiSuggestion.recommended_template ? (
                            <div style={{ padding: '12px 14px', borderRadius: '12px', background: 'white', border: '1px solid #c7d2fe' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
                                <div>
                                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>{aiSuggestion.recommended_template.name}</div>
                                  <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{aiSuggestion.recommended_template.channel} · {aiSuggestion.recommended_template.category || 'template'}</div>
                                </div>
                                <Badge label={aiSuggestion.recommended_template.locale || 'default'} tone="slate" />
                              </div>
                              <div style={{ marginTop: '8px', fontSize: '12px', color: '#475569', lineHeight: 1.6 }}>
                                {aiSuggestion.recommended_template.body?.meta_text || aiSuggestion.recommended_template.body?.text || 'No preview available'}
                              </div>
                            </div>
                          ) : null}
                          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                            <button
                              onClick={() => {
                                const nextTemplate = aiSuggestion.recommended_template
                                  ? { ...aiSuggestion.recommended_template, _channel: aiSuggestion.recommended_template.channel }
                                  : null;
                                if (!campaignName.trim()) setCampaignName('AI Campaign');
                                setCampaignFilters((f) => ({
                                  ...f,
                                  ...(aiSuggestion.filters || {}),
                                  language: aiSuggestion.summary?.recommended_language || aiSuggestion.filters?.language || f.language,
                                }));
                                if (nextTemplate) {
                                  setCampaignTemplate(nextTemplate);
                                  setChannel(nextTemplate._channel || channel);
                                }
                                setCampaignStep(2);
                              }}
                              style={aiActionButtonStyle(false)}
                            >
                              Use AI Audience + Template
                            </button>
                          </div>
                          <div>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Top Hot Customers</div>
                            <div style={{ display: 'grid', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                              {(aiSuggestion.top_customers || []).slice(0, 8).map((c) => (
                                <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 10px', borderRadius: '8px', background: 'white', fontSize: '12px' }}>
                                  <span style={{ fontWeight: 700, color: '#111827' }}>{c.name}</span>
                                  <span style={{ color: '#64748b' }}>Score {c.lead_score} · Hot {c.hot_score}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                      <button
                        disabled={!campaignName.trim()}
                        onClick={() => { loadCampaignEstimate(campaignFilters); setCampaignStep(2); }}
                        style={primaryButtonStyle(!campaignName.trim())}
                      >
                        Next: Choose Template →
                      </button>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gap: '14px', position: 'sticky', top: '12px' }}>
                    <div style={softPanelStyle('blue')}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Audience Snapshot</div>
                          <div style={{ marginTop: '3px', fontSize: '11px', color: '#64748b' }}>Live audience size and cost preview for the current filters.</div>
                        </div>
                        <button onClick={() => loadCampaignEstimate(campaignFilters)} disabled={campaignEstimating} style={secondaryButtonStyle(campaignEstimating)}>
                          {campaignEstimating ? 'Refreshing…' : 'Recalculate'}
                        </button>
                      </div>
                      {campaignEstimateError ? (
                        <div style={{ marginBottom: '10px', padding: '10px 12px', borderRadius: '10px', background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '12px' }}>
                          {campaignEstimateError}
                        </div>
                      ) : null}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
                        <div style={miniMetricStyle('slate')}>
                          <div style={miniMetricValueStyle('#111827')}>{campaignEstimate?.matched || 0}</div>
                          <div style={miniMetricLabelStyle}>Matched</div>
                        </div>
                        <div style={miniMetricStyle('green')}>
                          <div style={miniMetricValueStyle('#166534')}>{campaignEstimate?.opted_in || 0}</div>
                          <div style={miniMetricLabelStyle}>Will Receive</div>
                        </div>
                        <div style={miniMetricStyle('amber')}>
                          <div style={miniMetricValueStyle('#92400e')}>₹{campaignEstimate?.cost?.inr || 0}</div>
                          <div style={miniMetricLabelStyle}>Meta Cost INR</div>
                        </div>
                        <div style={miniMetricStyle('blue')}>
                          <div style={miniMetricValueStyle('#1d4ed8')}>${campaignEstimate?.cost?.usd || 0}</div>
                          <div style={miniMetricLabelStyle}>Meta Cost USD</div>
                        </div>
                      </div>
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827', marginBottom: '10px' }}>Selected Filters</div>
                      <div style={{ display: 'grid', gap: '10px' }}>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Delivery</div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {(campaignFilters.delivery_channels || ['whatsapp']).map((value) => <Badge key={value} label={value === 'email' ? 'Email' : 'WhatsApp'} tone={value === 'email' ? 'blue' : 'green'} />)}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Audience Types</div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {campaignFilters.lead_types.length ? campaignFilters.lead_types.map((value) => <Badge key={value} label={audienceTypeLabel(value)} tone={audienceTypeTone(value)} />) : <Badge label="All audience types" tone="slate" />}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Score Selection</div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {campaignFilters.score_buckets.length ? campaignFilters.score_buckets.map((bucketId) => {
                              const bucket = SCORE_BUCKET_OPTIONS.find((item) => item.id === bucketId);
                              return bucket ? <Badge key={bucketId} label={`${bucket.label} ${bucket.range}`} tone={bucket.tone} /> : null;
                            }) : <Badge label="No score buckets selected" tone="slate" />}
                            <Badge label={`Range ${campaignFilters.score_min}-${campaignFilters.score_max}`} tone="slate" />
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Labels</div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {campaignFilters.labels.length ? campaignFilters.labels.map((label) => <Badge key={label} label={label} tone="indigo" />) : <Badge label="No label filter" tone="slate" />}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Status / Date</div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {(campaignFilters.statuses || []).length ? campaignFilters.statuses.map((status) => <Badge key={status} label={status} tone="slate" />) : <Badge label="Any status" tone="slate" />}
                            {(campaignFilters.engagement_labels || []).map((label) => <Badge key={label} label={`Engagement ${label}`} tone={label === 'hot' ? 'red' : label === 'warm' ? 'green' : 'slate'} />)}
                            {campaignFilters.date_from || campaignFilters.date_to ? <Badge label={`${campaignFilters.date_from || 'Start'} to ${campaignFilters.date_to || 'Now'}`} tone="blue" /> : <Badge label="Any date" tone="slate" />}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <Badge label={campaignFilters.language === 'all' ? 'All languages' : campaignFilters.language === 'mal' ? 'Malayalam' : 'English'} tone="blue" />
                          {campaignTemplate ? <Badge label={`Template ready: ${campaignTemplate.name}`} tone="green" /> : <Badge label="No template selected yet" tone="slate" />}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Step 2 — Template */}
              {campaignStep === 2 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.08fr) minmax(320px, 0.92fr)', gap: '18px', alignItems: 'start' }}>
                  <div style={{ display: 'grid', gap: '16px' }}>
                    <div style={softPanelStyle('slate')}>
                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Template Library</div>
                      <div style={{ marginTop: '4px', fontSize: '12px', color: '#64748b', lineHeight: 1.7 }}>{campaignUsesWhatsApp ? 'Choose the WhatsApp template that best fits the audience you just built.' : 'Email-only journey selected. You can continue without a WhatsApp template.'}</div>
                      <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <Badge label={`${wabisTemplates.length + metaTemplates.length} templates loaded`} tone="slate" />
                        {campaignEstimate ? <Badge label={`${campaignEstimate.opted_in || 0} recipients ready`} tone="green" /> : null}
                        {aiSuggestion?.recommended_template ? <Badge label={`AI suggested ${aiSuggestion.recommended_template.name}`} tone="indigo" /> : null}
                      </div>
                    </div>

                    {!campaignUsesWhatsApp ? (
                      <EmptyState title="No WhatsApp template needed" body="This campaign is set to Email only. Continue to review, edit the email content, and queue the audience." />
                    ) : !wabisTemplates.length && !metaTemplates.length ? (
                      <EmptyState title="No templates loaded" body="Go to the Campaigns tab and sync templates first." />
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px', maxHeight: '560px', overflowY: 'auto', paddingRight: '4px' }}>
                        {[...wabisTemplates.map((t) => ({ ...t, _ch: 'wabis' })), ...metaTemplates.map((t) => ({ ...t, _ch: 'meta' }))].map((tpl) => {
                          const isSelected = campaignTemplate?.id === tpl.id && (campaignTemplate?._channel || campaignTemplate?.channel) === tpl._ch;
                          const isRecommended = aiSuggestion?.recommended_template?.id === tpl.id && aiSuggestion?.recommended_template?.channel === tpl._ch;
                          return (
                            <button
                              key={`${tpl._ch}-${tpl.id}`}
                              onClick={() => setCampaignTemplate({ ...tpl, _channel: tpl._ch })}
                              style={{
                                ...templateListItemStyle(isSelected),
                                padding: '14px 15px',
                                background: isSelected ? '#ecfdf5' : 'white',
                                boxShadow: isSelected ? '0 10px 28px rgba(15, 118, 110, 0.08)' : 'none',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                                <div>
                                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>{tpl.name}</div>
                                  <div style={{ marginTop: '5px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                    <Badge label={tpl._ch} tone={tpl._ch === 'wabis' ? 'green' : 'blue'} />
                                    {tpl.category ? <Badge label={tpl.category} tone="slate" /> : null}
                                    {tpl.locale ? <Badge label={tpl.locale} tone="slate" /> : null}
                                    {tpl.total_vars > 0 ? <Badge label={`${tpl.total_vars} vars`} tone="indigo" /> : null}
                                  </div>
                                </div>
                                {isSelected ? <Badge label="Selected" tone="green" /> : (isRecommended ? <Badge label="AI pick" tone="indigo" /> : null)}
                              </div>
                              <div style={{ marginTop: '12px', padding: '12px 13px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0', fontSize: '12px', color: '#334155', lineHeight: 1.7, minHeight: '92px' }}>
                                {highlightVars(templatePreviewText(tpl))}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                      <button onClick={() => setCampaignStep(1)} style={secondaryButtonStyle(false)}>← Back</button>
                      <button disabled={campaignUsesWhatsApp && !campaignTemplate} onClick={() => setCampaignStep(3)} style={primaryButtonStyle(campaignUsesWhatsApp && !campaignTemplate)}>
                        Next: Review & Schedule →
                      </button>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gap: '14px', position: 'sticky', top: '12px' }}>
                    <div style={softPanelStyle('blue')}>
                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Selected Template Preview</div>
                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Lock in the creative and tone before you move to cost and scheduling.</div>
                      {!campaignTemplate ? (
                        <div style={{ marginTop: '14px' }}>
                          <EmptyState title={campaignUsesWhatsApp ? 'Choose a template' : 'Email only'} body={campaignUsesWhatsApp ? 'Select any card from the library to preview the exact template content here.' : 'No WhatsApp template is required for this journey.'} />
                        </div>
                      ) : (
                        <div style={{ marginTop: '14px', display: 'grid', gap: '12px' }}>
                          <div style={{ padding: '14px 15px', borderRadius: '14px', background: 'white', border: '1px solid #bfdbfe' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                              <div>
                                <div style={{ fontSize: '14px', fontWeight: 800, color: '#111827' }}>{campaignTemplate.name}</div>
                                <div style={{ marginTop: '6px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                  <Badge label={campaignTemplate._channel || campaignTemplate.channel || 'template'} tone={(campaignTemplate._channel || campaignTemplate.channel) === 'wabis' ? 'green' : 'blue'} />
                                  {campaignTemplate.category ? <Badge label={campaignTemplate.category} tone="slate" /> : null}
                                  {campaignTemplate.locale ? <Badge label={campaignTemplate.locale} tone="slate" /> : null}
                                </div>
                              </div>
                              {campaignTemplate.total_vars > 0 ? <Badge label={`${campaignTemplate.total_vars} vars`} tone="indigo" /> : null}
                            </div>
                            <div style={{ marginTop: '14px', padding: '12px 13px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #dbeafe', fontSize: '12px', color: '#334155', lineHeight: 1.8 }}>
                              {highlightVars(templatePreviewText(campaignTemplate))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    <div style={softPanelStyle('slate')}>
                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Audience Ready for This Template</div>
                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Quick recap of the audience and cost before you commit to review.</div>
                      <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
                        <div style={miniMetricStyle('slate')}>
                          <div style={miniMetricValueStyle('#111827')}>{campaignEstimate?.matched || 0}</div>
                          <div style={miniMetricLabelStyle}>Matched</div>
                        </div>
                        <div style={miniMetricStyle('green')}>
                          <div style={miniMetricValueStyle('#166534')}>{campaignEstimate?.whatsapp_sendable ?? campaignEstimate?.opted_in ?? 0}</div>
                          <div style={miniMetricLabelStyle}>WhatsApp Ready</div>
                        </div>
                        <div style={miniMetricStyle('blue')}>
                          <div style={miniMetricValueStyle('#1d4ed8')}>{campaignEstimate?.email_sendable || 0}</div>
                          <div style={miniMetricLabelStyle}>Email Ready</div>
                        </div>
                        <div style={miniMetricStyle('amber')}>
                          <div style={miniMetricValueStyle('#92400e')}>₹{campaignEstimate?.cost?.inr || 0}</div>
                          <div style={miniMetricLabelStyle}>Meta Cost</div>
                        </div>
                        <div style={miniMetricStyle('indigo')}>
                          <div style={miniMetricValueStyle('#4338ca')}>{campaignFilters.language === 'all' ? 'All' : campaignFilters.language.toUpperCase()}</div>
                          <div style={miniMetricLabelStyle}>Language</div>
                        </div>
                      </div>
                      <div style={{ marginTop: '12px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {campaignFilters.lead_types.length ? campaignFilters.lead_types.map((value) => <Badge key={value} label={audienceTypeLabel(value)} tone={audienceTypeTone(value)} />) : <Badge label="All audience types" tone="slate" />}
                        {campaignFilters.score_buckets.length ? campaignFilters.score_buckets.map((bucketId) => {
                          const bucket = SCORE_BUCKET_OPTIONS.find((item) => item.id === bucketId);
                          return bucket ? <Badge key={bucketId} label={bucket.label} tone={bucket.tone} /> : null;
                        }) : <Badge label={`Range ${campaignFilters.score_min}-${campaignFilters.score_max}`} tone="slate" />}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Step 3 — Review + Cost + Schedule */}
              {campaignStep === 3 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.08fr) minmax(320px, 0.92fr)', gap: '18px', alignItems: 'start' }}>
                  <div style={{ display: 'grid', gap: '18px' }}>
                    <div style={{ borderRadius: '14px', border: '1px solid #e2e8f0', background: '#f8fafc', padding: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Audience & Cost Estimate</div>
                          <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Final audience size, score mix, and Meta delivery cost before launch.</div>
                        </div>
                        <button onClick={() => loadCampaignEstimate(campaignFilters)} disabled={campaignEstimating} style={secondaryButtonStyle(campaignEstimating)}>
                          {campaignEstimating ? 'Recalculating…' : 'Recalculate Estimate'}
                        </button>
                      </div>
                      {campaignEstimateError ? (
                        <div style={{ marginBottom: '12px', padding: '10px 12px', borderRadius: '10px', background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '12px' }}>
                          {campaignEstimateError}
                        </div>
                      ) : null}
                      {campaignEstimate ? (
                        <>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px' }}>
                            <div style={miniMetricStyle('slate')}>
                              <div style={miniMetricValueStyle('#111827')}>{campaignEstimate.matched}</div>
                              <div style={miniMetricLabelStyle}>Matched</div>
                            </div>
                            <div style={miniMetricStyle('green')}>
                              <div style={miniMetricValueStyle('#166534')}>{campaignEstimate.whatsapp_sendable ?? campaignEstimate.opted_in}</div>
                              <div style={miniMetricLabelStyle}>WhatsApp Ready</div>
                            </div>
                            <div style={miniMetricStyle('blue')}>
                              <div style={miniMetricValueStyle('#1d4ed8')}>{campaignEstimate.email_sendable || 0}</div>
                              <div style={miniMetricLabelStyle}>Email Ready</div>
                            </div>
                            <div style={miniMetricStyle('amber')}>
                              <div style={miniMetricValueStyle('#92400e')}>₹{campaignEstimate.cost?.inr || 0}</div>
                              <div style={miniMetricLabelStyle}>Meta Cost INR</div>
                            </div>
                            <div style={miniMetricStyle('blue')}>
                              <div style={miniMetricValueStyle('#1d4ed8')}>${campaignEstimate.cost?.usd || 0}</div>
                              <div style={miniMetricLabelStyle}>Meta Cost USD</div>
                            </div>
                            <div style={miniMetricStyle('indigo')}>
                              <div style={miniMetricValueStyle('#4338ca')}>{campaignEstimate.language_split?.mal || 0}</div>
                              <div style={miniMetricLabelStyle}>Malayalam</div>
                            </div>
                            <div style={miniMetricStyle('green')}>
                              <div style={miniMetricValueStyle('#0f766e')}>{campaignEstimate.language_split?.eng || 0}</div>
                              <div style={miniMetricLabelStyle}>English</div>
                            </div>
                          </div>
                          <div style={{ marginTop: '14px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
                            {SCORE_BUCKET_OPTIONS.map((bucket) => (
                              <div key={bucket.id} style={{ padding: '10px 12px', borderRadius: '12px', border: `1px solid ${toneColors(bucket.tone).border}`, background: toneColors(bucket.tone).background }}>
                                <div style={{ fontSize: '11px', fontWeight: 700, color: toneColors(bucket.tone).text }}>{bucket.label}</div>
                                <div style={{ marginTop: '6px', fontSize: '18px', fontWeight: 800, color: toneColors(bucket.tone).text }}>{campaignEstimate.score_breakdown?.[bucket.id] || 0}</div>
                              </div>
                            ))}
                          </div>
                        </>
                      ) : (
                        <div style={{ fontSize: '12px', color: '#64748b' }}>{campaignEstimating ? 'Calculating…' : 'No estimate available yet.'}</div>
                      )}
                    </div>

                    <div style={softPanelStyle('blue')}>
                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Schedule & Sync</div>
                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Choose when this campaign should go live and whether the audience should also sync to Meta.</div>
                      {campaignUsesEmail ? (
                        <div style={{ marginTop: '14px', padding: '12px', borderRadius: '12px', background: 'white', border: '1px solid #bfdbfe', display: 'grid', gap: '10px' }}>
                          <div style={{ fontSize: '12px', fontWeight: 800, color: '#111827' }}>Email Campaign</div>
                          <div>
                            <label style={labelStyle}>Subject</label>
                            <input value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} placeholder={`${campaignName || 'Pureleven'} update`} style={inputStyle} />
                          </div>
                          <div>
                            <label style={labelStyle}>HTML Body</label>
                            <textarea value={emailHtml} onChange={(e) => setEmailHtml(e.target.value)} placeholder="Leave blank to use a clean Pureleven offer email, or paste/edit HTML here." rows={5} style={{ ...inputStyle, minHeight: '120px', resize: 'vertical', lineHeight: 1.6 }} />
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>{campaignEstimate?.email_sendable || 0} email-ready customers match this audience.</div>
                        </div>
                      ) : null}
                      <div style={{ marginTop: '14px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        {[['now', 'Send Now'], ['scheduled', 'Schedule Later']].map(([value, label]) => (
                          <button
                            key={value}
                            onClick={() => setCampaignScheduleType(value)}
                            style={{
                              padding: '9px 16px',
                              borderRadius: '10px',
                              fontSize: '13px',
                              fontWeight: 700,
                              cursor: 'pointer',
                              border: `1px solid ${campaignScheduleType === value ? '#93c5fd' : '#d1d5db'}`,
                              background: campaignScheduleType === value ? '#dbeafe' : 'white',
                              color: campaignScheduleType === value ? '#1d4ed8' : '#374151',
                            }}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      {campaignScheduleType === 'scheduled' ? (
                        <div style={{ marginTop: '12px' }}>
                          <label style={labelStyle}>Scheduled Time</label>
                          <input type="datetime-local" value={campaignScheduledAt} onChange={(e) => setCampaignScheduledAt(e.target.value)} style={{ ...inputStyle, maxWidth: '320px' }} />
                        </div>
                      ) : null}
                      <label style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                        <input type="checkbox" checked={campaignSyncMeta} onChange={(e) => setCampaignSyncMeta(e.target.checked)} />
                        <span style={{ fontSize: '13px', color: '#374151' }}>Also sync this audience to Meta Custom Audiences after campaign creation</span>
                      </label>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gap: '14px', position: 'sticky', top: '12px' }}>
                    <div style={softPanelStyle('slate')}>
                      <div style={{ fontSize: '13px', fontWeight: 800, color: '#111827' }}>Launch Review</div>
                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>Final confirmation of the audience, template, and execution settings.</div>
                      <div style={{ marginTop: '14px', display: 'grid', gap: '12px' }}>
                        <div style={{ padding: '13px 14px', borderRadius: '12px', background: 'white', border: '1px solid #e2e8f0' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Campaign</div>
                          <div style={{ marginTop: '8px', fontSize: '15px', fontWeight: 800, color: '#111827' }}>{campaignName}</div>
                          <div style={{ marginTop: '8px', fontSize: '12px', color: '#475569', lineHeight: 1.7 }}>
                            Template: {campaignTemplate?.name || (campaignUsesWhatsApp ? '—' : 'Email only')}<br />
                            Channel: {(campaignFilters.delivery_channels || ['whatsapp']).join(' + ')}<br />
                            Schedule: {campaignScheduleType === 'scheduled' ? formatDateTime(campaignScheduledAt) : 'Send immediately'}
                          </div>
                        </div>

                        <div style={{ padding: '13px 14px', borderRadius: '12px', background: 'white', border: '1px solid #e2e8f0' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Template Preview</div>
                          <div style={{ marginTop: '10px', fontSize: '12px', color: '#334155', lineHeight: 1.8 }}>
                            {campaignTemplate ? highlightVars(templatePreviewText(campaignTemplate)) : (campaignUsesEmail ? (emailSubject || 'Email draft will use the default Pureleven email template.') : '—')}
                          </div>
                        </div>

                        <div style={{ padding: '13px 14px', borderRadius: '12px', background: 'white', border: '1px solid #e2e8f0' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Audience Rules</div>
                          <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {campaignFilters.lead_types.length ? campaignFilters.lead_types.map((type) => <Badge key={type} label={audienceTypeLabel(type)} tone={audienceTypeTone(type)} />) : <Badge label="All audience types" tone="slate" />}
                            {campaignFilters.score_buckets.length ? campaignFilters.score_buckets.map((bucketId) => {
                              const bucket = SCORE_BUCKET_OPTIONS.find((item) => item.id === bucketId);
                              return bucket ? <Badge key={bucketId} label={bucket.label} tone={bucket.tone} /> : null;
                            }) : <Badge label="No score bucket" tone="slate" />}
                            <Badge label={`Range ${campaignFilters.score_min}-${campaignFilters.score_max}`} tone="slate" />
                            <Badge label={campaignFilters.language === 'all' ? 'All languages' : campaignFilters.language === 'mal' ? 'Malayalam' : 'English'} tone="blue" />
                            {campaignFilters.labels.length ? campaignFilters.labels.slice(0, 4).map((label) => <Badge key={label} label={label} tone="indigo" />) : <Badge label="No labels" tone="slate" />}
                            {campaignFilters.labels.length > 4 ? <Badge label={`+${campaignFilters.labels.length - 4} more labels`} tone="slate" /> : null}
                          </div>
                        </div>
                      </div>
                    </div>

                    {campaignResult?.error ? (
                      <div style={{ padding: '12px 14px', borderRadius: '10px', border: '1px solid #fecaca', background: '#fef2f2', color: '#b91c1c', fontSize: '12px' }}>
                        Error: {campaignResult.error}
                      </div>
                    ) : null}

                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                      <button onClick={() => setCampaignStep(2)} style={secondaryButtonStyle(false)}>← Back</button>
                      <button
                        disabled={campaignCreating || (campaignUsesWhatsApp && !campaignTemplate) || (campaignScheduleType === 'scheduled' && !campaignScheduledAt)}
                        onClick={submitCampaign}
                        style={primaryButtonStyle(campaignCreating || (campaignUsesWhatsApp && !campaignTemplate) || (campaignScheduleType === 'scheduled' && !campaignScheduledAt))}
                      >
                        {campaignCreating ? 'Creating…' : 'Create Campaign'}
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </PanelSection>
          )}

          <PanelSection
            title="Campaign History"
            subtitle="Recent Journey campaign launches with queue progress and send-state rollups."
            actions={(
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <Badge label={`${journeyCampaignTotal} total`} tone="slate" />
                <button onClick={loadJourneyCampaignHistory} disabled={journeyCampaignLoading} style={secondaryButtonStyle(journeyCampaignLoading)}>
                  {journeyCampaignLoading ? 'Refreshing…' : 'Refresh'}
                </button>
              </div>
            )}
          >
            {journeyCampaignLoading ? (
              <EmptyState title="Loading campaign history" body="Reading recent Journey campaigns, queue states, and send outcomes." />
            ) : !journeyCampaignRows.length ? (
              <EmptyState title="No campaign history yet" body="Create a Journey campaign to start tracking queue status and send progress here." />
            ) : (
              <div style={{ display: 'grid', gap: '12px' }}>
                {journeyCampaignRows.map((item) => {
                  const summary = campaignExecutionSummary(item);
                  return (
                    <div key={item.id} style={{ padding: '15px 16px', borderRadius: '14px', border: '1px solid #e5e7eb', background: 'white', display: 'grid', gap: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: 800, color: '#111827' }}>{item.name}</div>
                          <div style={{ marginTop: '6px', fontSize: '12px', color: '#64748b', lineHeight: 1.7 }}>
                            Created {formatDateTime(item.created_at)}
                            {item.schedule_type === 'scheduled' && item.scheduled_at ? ` · Scheduled ${formatDateTime(item.scheduled_at)}` : ' · Send now'}
                            {item.last_activity_at ? ` · Last activity ${formatDateTime(item.last_activity_at)}` : ''}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                          <StatusPill status={item.status} />
                          <Badge label={`${summary.progress}% complete`} tone={summary.progress >= 100 ? 'green' : 'blue'} />
                        </div>
                      </div>

                      <div style={{ height: '8px', borderRadius: '999px', background: '#e2e8f0', overflow: 'hidden' }}>
                        <div style={{ width: `${summary.progress}%`, height: '100%', background: summary.progress >= 100 ? '#16a34a' : '#0f766e' }} />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '8px' }}>
                        <div style={miniMetricStyle('slate')}>
                          <div style={miniMetricValueStyle('#111827')}>{summary.total}</div>
                          <div style={miniMetricLabelStyle}>Audience</div>
                        </div>
                        <div style={miniMetricStyle('amber')}>
                          <div style={miniMetricValueStyle('#92400e')}>{summary.pending}</div>
                          <div style={miniMetricLabelStyle}>Pending</div>
                        </div>
                        <div style={miniMetricStyle('blue')}>
                          <div style={miniMetricValueStyle('#1d4ed8')}>{summary.sending}</div>
                          <div style={miniMetricLabelStyle}>Sending</div>
                        </div>
                        <div style={miniMetricStyle('green')}>
                          <div style={miniMetricValueStyle('#166534')}>{summary.sent}</div>
                          <div style={miniMetricLabelStyle}>Sent</div>
                        </div>
                        <div style={miniMetricStyle('red')}>
                          <div style={miniMetricValueStyle('#b91c1c')}>{summary.failed}</div>
                          <div style={miniMetricLabelStyle}>Failed</div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {item.filters?.lead_types?.length ? item.filters.lead_types.map((type) => <Badge key={`${item.id}-${type}`} label={audienceTypeLabel(type)} tone={audienceTypeTone(type)} />) : <Badge label="All audience types" tone="slate" />}
                        {item.filters?.score_buckets?.length ? item.filters.score_buckets.map((bucketId) => {
                          const bucket = SCORE_BUCKET_OPTIONS.find((entry) => entry.id === bucketId);
                          return bucket ? <Badge key={`${item.id}-${bucketId}`} label={bucket.label} tone={bucket.tone} /> : null;
                        }) : null}
                        {item.filters?.language && item.filters.language !== 'all' ? <Badge label={item.filters.language === 'mal' ? 'Malayalam' : 'English'} tone="blue" /> : null}
                        {item.filters?.labels?.length ? <Badge label={`${item.filters.labels.length} labels`} tone="indigo" /> : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </PanelSection>

          <PanelSection
            title="Journey Customers"
            subtitle="Delivery-stage WhatsApp lifecycle customers, engagement score, purchase context, and timeline drill-down."
            actions={<button onClick={loadJourney} disabled={journeyLoading} style={secondaryButtonStyle(journeyLoading)}>{journeyLoading ? 'Refreshing…' : 'Refresh'}</button>}
          >
            <div style={{ padding: '14px 16px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#f8fafc', marginBottom: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) auto auto', gap: '10px', alignItems: 'end' }}>
                <div>
                  <label style={labelStyle}>Find by Phone</label>
                  <input value={journeyPhoneSearch} onChange={(event) => setJourneyPhoneSearch(event.target.value)} placeholder="+91 94477 44583 or 9447744583" style={inputStyle} />
                  <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>Exact or partial digits work. The best match is pushed to the top and auto-selected.</div>
                </div>
                <button onClick={loadJourney} disabled={journeyLoading} style={primaryButtonStyle(journeyLoading)}>{journeyLoading ? 'Finding…' : 'Find Phone'}</button>
                <button onClick={() => { setJourneyPhoneSearch(''); loadJourney({ phone: '' }); }} disabled={journeyLoading || !journeyPhoneSearch} style={secondaryButtonStyle(journeyLoading || !journeyPhoneSearch)}>Clear</button>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1.2fr) repeat(3, minmax(150px, 0.6fr)) auto', gap: '10px', marginBottom: '16px' }}>
              <input value={journeyFilters.search} onChange={(event) => setJourneyFilters((prev) => ({ ...prev, search: event.target.value }))} placeholder="Search name, email, order" style={inputStyle} />
              <select value={journeyFilters.stage} onChange={(event) => setJourneyFilters((prev) => ({ ...prev, stage: event.target.value }))} style={inputStyle}>
                <option value="all">All stages</option>
                {journeyStages.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <select value={journeyFilters.segment} onChange={(event) => setJourneyFilters((prev) => ({ ...prev, segment: event.target.value }))} style={inputStyle}>
                <option value="all">All segments</option>
                {journeySegments.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <select value={journeyFilters.subscription} onChange={(event) => setJourneyFilters((prev) => ({ ...prev, subscription: event.target.value }))} style={inputStyle}>
                <option value="all">All subscriptions</option>
                <option value="subscribed">Subscribed</option>
                <option value="unsubscribed">Unsubscribed</option>
              </select>
              <button onClick={loadJourney} disabled={journeyLoading} style={primaryButtonStyle(journeyLoading)}>{journeyLoading ? 'Loading…' : 'Apply'}</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(340px, 0.8fr)', gap: '18px' }}>
              <div>
                <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Badge label={`${journeyTotal} customers`} tone="slate" />
                </div>
                {journeyLoading ? (
                  <EmptyState title="Loading journey customers" body="Reading lifecycle customers, message counts, and engagement totals." />
                ) : !journeyRows.length ? (
                  <EmptyState title="No journey customers" body="Journey rows appear once orders and delivery lifecycle data start flowing in." />
                ) : (
                  <div style={{ overflow: 'hidden', border: '1px solid #e5e7eb', borderRadius: '12px' }}>
                    {journeyRows.map((row) => (
                      <button
                        key={row.id}
                        onClick={() => loadJourneyDetail(row.id)}
                        title={journeyPhoneNeedle && normalizePhoneLookup(row.phone).includes(journeyPhoneNeedle) ? 'Phone match' : ''}
                        style={{
                          width: '100%',
                          padding: '14px 16px',
                          border: 'none',
                          borderBottom: '1px solid #f1f5f9',
                          background: row.id === selectedJourneyId ? '#eff6ff' : (journeyPhoneNeedle && normalizePhoneLookup(row.phone).includes(journeyPhoneNeedle) ? '#f8fafc' : 'white'),
                          textAlign: 'left',
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start' }}>
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 700, color: '#111827' }}>{row.name || row.phone}</div>
                            <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{row.phone} · {row.customer_segment} · {row.journey_stage}</div>
                          </div>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                            {journeyPhoneNeedle && normalizePhoneLookup(row.phone).includes(journeyPhoneNeedle) ? <Badge label="Phone match" tone="amber" /> : null}
                            <Badge label={`Score ${Number(row.engagement_score || 0).toFixed(1)}`} tone="green" />
                          </div>
                        </div>
                        <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <Badge label={`${row.total_messages || 0} messages`} tone="blue" />
                          <Badge label={`${row.total_events || 0} events`} tone="indigo" />
                          <Badge label={`${row.whatsapp_subscription_status || 'unknown'}`} tone="slate" />
                          {row.failed_count ? <Badge label={`${row.failed_count} failed`} tone="red" /> : null}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <PanelSection title="Customer Timeline" subtitle="Template sends, engagement signals, and live conversation turns for the selected journey customer.">
                {journeyDetailLoading ? (
                  <EmptyState title="Loading customer timeline" body="Building the message, engagement, and conversation timeline." />
                ) : !journeyDetail?.customer ? (
                  <EmptyState title="Select a customer" body="Choose a journey customer from the list to inspect their lifecycle timeline." />
                ) : (
                  <div style={{ display: 'grid', gap: '16px' }}>
                    <div style={{ padding: '14px', borderRadius: '12px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#111827' }}>{journeyDetail.customer.name || journeyDetail.customer.phone}</div>
                      <div style={{ marginTop: '6px', fontSize: '12px', color: '#64748b', lineHeight: 1.7 }}>
                        {journeyDetail.customer.phone || '—'}<br />
                        {journeyDetail.customer.email || 'No email'}<br />
                        Stage: {journeyDetail.customer.journey_stage || '—'} · Segment: {journeyDetail.customer.customer_segment || '—'}
                      </div>
                      <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <Badge label={`Score ${Number(journeyDetail.customer.engagement_score || 0).toFixed(1)}`} tone="green" />
                        <Badge label={`Purchases ${journeyDetail.customer.purchase_count || 0}`} tone="amber" />
                        <Badge label={`Spent ${formatMoney(journeyDetail.customer.total_spent || 0)}`} tone="blue" />
                      </div>
                    </div>

                    {!journeyDetail.timeline?.length ? (
                      <EmptyState title="No timeline activity" body="This customer exists in the journey table but has no visible message or engagement timeline yet." />
                    ) : (
                      <div style={{ display: 'grid', gap: '10px', maxHeight: '720px', overflowY: 'auto', paddingRight: '4px' }}>
                        {journeyDetail.timeline.map((item, index) => (
                          <div key={`${item.source}-${item.event_at}-${index}`} style={{ padding: '12px 14px', borderRadius: '12px', border: '1px solid #e5e7eb', background: 'white' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                                <Badge label={item.source} tone={item.source === 'message' ? 'blue' : item.source === 'engagement' ? 'green' : 'indigo'} />
                                <Badge label={item.event_type} tone="slate" />
                                {item.status ? <StatusPill status={item.status} /> : null}
                              </div>
                              <div style={{ fontSize: '11px', color: '#64748b' }}>{formatDateTime(item.event_at)}</div>
                            </div>
                            {item.template_name ? <div style={{ marginTop: '10px', fontSize: '13px', fontWeight: 700, color: '#111827' }}>{item.template_name}</div> : null}
                            {item.journey_stage ? <div style={{ marginTop: '6px', fontSize: '12px', color: '#64748b' }}>Journey stage: {item.journey_stage}</div> : null}
                            {item.customer_text ? <div style={{ marginTop: '10px', fontSize: '13px', color: '#111827', whiteSpace: 'pre-wrap' }}>{item.customer_text}</div> : null}
                            {item.message_rendered ? <div style={{ marginTop: '10px', fontSize: '13px', color: '#111827', whiteSpace: 'pre-wrap' }}>{item.message_rendered}</div> : null}
                            {item.error_detail ? <div style={{ marginTop: '10px', fontSize: '12px', color: '#b91c1c' }}>{item.error_detail}</div> : null}
                            {item.points_awarded ? <div style={{ marginTop: '10px', fontSize: '12px', color: '#166534' }}>Points awarded: {item.points_awarded}</div> : null}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </PanelSection>
            </div>
          </PanelSection>
        </div>
      ) : null}

      {mainTab === 'campaigns' ? (
        <div style={{ display: 'grid', gap: '18px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {CAMPAIGN_TABS.map(([id, label]) => (
              <button key={id} onClick={() => setCampaignTab(id)} style={mainTabButtonStyle(campaignTab === id)}>{label}</button>
            ))}
          </div>

          {campaignTab === 'send' ? (
            <div style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr)', gap: '20px', alignItems: 'start' }}>
              <PanelSection title="Template Browser" subtitle="Use Wabis or Meta as the send channel. Templates auto-refresh every 30 minutes.">
                <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
                  {[
                    { id: 'wabis', label: 'Wabis', sub: `${wabisTemplates.length} templates`, tone: 'green' },
                    { id: 'meta', label: 'Meta WA', sub: metaConfigured ? `${metaTemplates.length} templates` : 'Not configured', tone: 'blue' },
                  ].map((item) => (
                    <button key={item.id} onClick={() => handleChannelSwitch(item.id)} style={channelCardStyle(channel === item.id, item.tone)}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: channel === item.id ? toneColors(item.tone).text : '#111827' }}>{item.label}</div>
                      <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>{item.sub}</div>
                    </button>
                  ))}
                </div>

                {channel === 'meta' && !metaConfigured ? (
                  <div style={{ marginBottom: '14px', padding: '12px 14px', borderRadius: '10px', border: '1px solid #bfdbfe', background: '#eff6ff', color: '#1d4ed8', fontSize: '12px', lineHeight: 1.6 }}>
                    Meta WA is not configured on the server yet. Set the WABA ID and management token, then sync again.
                  </div>
                ) : null}

                {!templates.length ? (
                  <EmptyState title="No templates yet" body="Use Sync Now or switch channels to load approved templates from Wabis and Meta." />
                ) : (
                  <div style={{ display: 'grid', gap: '8px', maxHeight: '620px', overflowY: 'auto', paddingRight: '4px' }}>
                    {templates.map((template) => (
                      <button key={template.id} onClick={() => selectTemplate(template.id)} style={templateListItemStyle(String(template.id) === String(selectedId))}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' }}>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: '#111827', textAlign: 'left' }}>{template.name}</div>
                          <Badge label={template.category} tone="slate" />
                        </div>
                        <div style={{ marginTop: '8px', fontSize: '12px', color: '#64748b', lineHeight: 1.6, textAlign: 'left' }}>{template.body?.meta_text || template.body?.text || 'No body preview'}</div>
                        <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          {!template.send_issue ? <Badge label="ready" tone="green" /> : null}
                          {template.send_issue === 'image_header' ? <Badge label="needs image" tone="amber" /> : null}
                          {template.send_issue === 'locale_mismatch' ? <Badge label="status/locale issue" tone="red" /> : null}
                          {template.total_vars > 0 ? <Badge label={`${template.total_vars} vars`} tone="blue" /> : null}
                          <Badge label={template.locale} tone="slate" />
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </PanelSection>

              <div style={{ display: 'grid', gap: '18px' }}>
                <PanelSection title="Composer" subtitle="Preview variables, send a test, and store the latest manual send attempts locally in the panel.">
                  {!activeTpl ? (
                    <EmptyState title="Select a template" body="Choose a template from the left to preview its components and send a test message." />
                  ) : (
                    <div style={{ display: 'grid', gap: '18px' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '10px' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#64748b' }}>Template Preview</div>
                          <Badge label={`${activeTpl.locale} · ${activeTpl.category}`} tone="slate" />
                        </div>
                        <div style={{ background: '#e5ddd5', padding: '14px', borderRadius: '14px' }}>
                          <div style={{ background: '#dcf8c6', borderRadius: '10px 10px 10px 0', padding: '14px 16px', maxWidth: '420px', boxShadow: '0 1px 2px rgba(15, 23, 42, 0.08)' }}>
                            {activeTpl.header?.text ? <div style={{ fontWeight: 700, fontSize: '13px', color: '#111827', marginBottom: '6px' }}>{activeTpl.header.format === 'TEXT' ? highlightVars(activeTpl.header.text) : `[${activeTpl.header.format}]`}</div> : null}
                            <div style={{ fontSize: '13px', color: '#111827', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{highlightVars(activeTpl.body?.meta_text || activeTpl.body?.text || '')}</div>
                            {activeTpl.footer?.text ? <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>{activeTpl.footer.text}</div> : null}
                            {activeTpl.buttons?.length ? (
                              <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(15, 23, 42, 0.08)', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                {activeTpl.buttons.map((button, index) => (
                                  <div key={`${button.text}-${index}`} style={{ padding: '4px 10px', borderRadius: '999px', background: 'rgba(255, 255, 255, 0.6)', border: '1px solid rgba(5, 150, 105, 0.25)', color: '#047857', fontSize: '12px', fontWeight: 700 }}>
                                    {button.text}
                                  </div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </div>

                      <div>
                        <label style={labelStyle}>Recipient Phone</label>
                        <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="919447744583" style={inputStyle} />
                      </div>

                      {varSlots.length ? (
                        <div>
                          <label style={labelStyle}>Variables ({varSlots.length})</label>
                          <div style={{ display: 'grid', gap: '10px' }}>
                            {varSlots.map((slot) => (
                              <div key={`${slot.labelPrefix}-${slot.index}`} style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '10px', alignItems: 'center' }}>
                                <div>
                                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#111827' }}>{`${slot.labelPrefix} {{${slot.num}}}`}</div>
                                  <div style={{ marginTop: '3px', fontSize: '10px', color: '#64748b' }}>{slot.label}</div>
                                </div>
                                <input value={params[slot.index] || ''} onChange={(event) => setParams((prev) => {
                                  const next = [...prev];
                                  next[slot.index] = event.target.value;
                                  return next;
                                })} placeholder={slot.example || slot.label} style={inputStyle} />
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <Badge label="No variables required" tone="green" />
                      )}

                      {activeTpl.send_issue === 'image_header' ? (
                        <div style={{ padding: '14px', borderRadius: '12px', background: '#fffbeb', border: '1px solid #fde68a' }}>
                          <div style={{ fontSize: '12px', fontWeight: 700, color: '#92400e', marginBottom: '8px' }}>Image header template</div>
                          <input value={headerImageUrl} onChange={(event) => setHeaderImageUrl(event.target.value)} placeholder="https://pureleven.com/path/to/header-image.jpg" style={inputStyle} />
                          {!headerImageUrl.trim() ? <div style={{ marginTop: '6px', fontSize: '11px', color: '#b91c1c' }}>Provide a public image URL before sending.</div> : null}
                        </div>
                      ) : null}

                      {activeTpl.send_issue === 'locale_mismatch' ? (
                        <div style={{ padding: '14px', borderRadius: '12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', fontSize: '12px', lineHeight: 1.7 }}>
                          This template is not currently send-ready because its locale or approval state does not match a valid send path.
                        </div>
                      ) : null}

                      <button
                        onClick={handleSend}
                        disabled={sending || !phone.trim() || activeTpl.send_issue === 'locale_mismatch' || (activeTpl.send_issue === 'image_header' && !headerImageUrl.trim())}
                        style={sendButtonStyle(channel, sending || !phone.trim() || activeTpl.send_issue === 'locale_mismatch' || (activeTpl.send_issue === 'image_header' && !headerImageUrl.trim()))}
                      >
                        {sending ? 'Sending…' : channel === 'wabis' ? 'Send via Wabis' : 'Send via Meta WA'}
                      </button>

                      {result ? (
                        <div style={{ padding: '14px 16px', borderRadius: '12px', border: `1px solid ${result.ok ? '#bbf7d0' : '#fecaca'}`, background: result.ok ? '#f0fdf4' : '#fef2f2' }}>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: result.ok ? '#166534' : '#991b1b', marginBottom: '8px' }}>
                            {result.ok ? `Sent ${result.name}` : `Failed to send ${result.name}`}
                          </div>
                          <pre style={{ margin: 0, fontSize: '11px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: result.ok ? '#14532d' : '#7f1d1d' }}>{JSON.stringify(result.data, null, 2)}</pre>
                        </div>
                      ) : null}
                    </div>
                  )}
                </PanelSection>

                {activeTpl ? (
                  <PanelSection title="Editable Template Preview" subtitle="Clone any loaded template into an editable draft, preview it live, then submit it as a new Meta template.">
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: '16px', alignItems: 'start' }}>
                      <div style={{ display: 'grid', gap: '12px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px 160px', gap: '10px' }}>
                          <div>
                            <label style={labelStyle}>Template Name</label>
                            <input value={templateDraft.name} onChange={(event) => setTemplateDraft((draft) => ({ ...draft, name: event.target.value.toLowerCase().replace(/\s+/g, '_') }))} style={inputStyle} />
                          </div>
                          <div>
                            <label style={labelStyle}>Category</label>
                            <select value={templateDraft.category} onChange={(event) => setTemplateDraft((draft) => ({ ...draft, category: event.target.value }))} style={inputStyle}>
                              <option value="MARKETING">Marketing</option>
                              <option value="UTILITY">Utility</option>
                              <option value="AUTHENTICATION">Authentication</option>
                            </select>
                          </div>
                          <div>
                            <label style={labelStyle}>Language</label>
                            <select value={templateDraft.language} onChange={(event) => setTemplateDraft((draft) => ({ ...draft, language: event.target.value }))} style={inputStyle}>
                              <option value="en_US">English (US)</option>
                              <option value="en_GB">English (UK)</option>
                              <option value="en_IN">English (India)</option>
                              <option value="ml">Malayalam</option>
                              <option value="hi">Hindi</option>
                            </select>
                          </div>
                        </div>
                        <div>
                          <label style={labelStyle}>Header</label>
                          <input value={templateDraft.header} onChange={(event) => setTemplateDraft((draft) => ({ ...draft, header: event.target.value }))} maxLength={60} style={inputStyle} />
                        </div>
                        <div>
                          <label style={labelStyle}>Body</label>
                          <textarea value={templateDraft.body} onChange={(event) => setTemplateDraft((draft) => ({ ...draft, body: event.target.value }))} rows={7} style={{ ...inputStyle, minHeight: '150px', resize: 'vertical', lineHeight: 1.7 }} />
                        </div>
                        <div>
                          <label style={labelStyle}>Footer</label>
                          <input value={templateDraft.footer} onChange={(event) => setTemplateDraft((draft) => ({ ...draft, footer: event.target.value }))} maxLength={60} style={inputStyle} />
                        </div>
                        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                          <button onClick={() => { setNewTpl(templateDraft); setCampaignTab('create'); }} disabled={!templateDraft.name.trim() || !templateDraft.body.trim()} style={primaryButtonStyle(!templateDraft.name.trim() || !templateDraft.body.trim())}>Use Draft in Create Template</button>
                          <button onClick={() => setTemplateDraft({ name: `${activeTpl.name || 'template'}_edit`, category: activeTpl.category || 'MARKETING', language: activeTpl.locale || 'en_US', header: activeTpl.header?.text || '', body: activeTpl.body?.meta_text || activeTpl.body?.text || '', footer: activeTpl.footer?.text || '' })} style={secondaryButtonStyle(false)}>Reset Draft</button>
                        </div>
                      </div>
                      <div style={{ background: '#e5ddd5', borderRadius: '14px', padding: '14px', minHeight: '220px' }}>
                        <div style={{ background: '#dcf8c6', borderRadius: '10px 10px 10px 0', padding: '14px 16px', boxShadow: '0 1px 2px rgba(15, 23, 42, 0.08)' }}>
                          {templateDraft.header ? <div style={{ marginBottom: '6px', fontSize: '13px', fontWeight: 700, color: '#111827' }}>{highlightVars(templateDraft.header)}</div> : null}
                          <div style={{ fontSize: '13px', color: '#111827', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{highlightVars(templateDraft.body || 'Template body...')}</div>
                          {templateDraft.footer ? <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>{templateDraft.footer}</div> : null}
                        </div>
                      </div>
                    </div>
                  </PanelSection>
                ) : null}

                {sendHistory.length ? (
                  <PanelSection title="Local Send History" subtitle="The most recent send attempts from this browser session.">
                    <div style={{ overflowX: 'auto' }}>
                      <table style={tableStyle}>
                        <thead>
                          <tr>
                            {['Time', 'Channel', 'Phone', 'Template', 'Params', 'Status'].map((heading) => <th key={heading} style={thStyle}>{heading}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {sendHistory.map((entry) => (
                            <tr key={entry.id} style={trStyle}>
                              <td style={tdStyle}>{entry.ts}</td>
                              <td style={tdStyle}><Badge label={entry.channel} tone={entry.channel === 'wabis' ? 'green' : 'blue'} /></td>
                              <td style={tdStyle}><span style={monoStyle}>+{entry.phone}</span></td>
                              <td style={tdStyle}>{entry.template}</td>
                              <td style={tdStyle}>{entry.params.filter(Boolean).join(', ') || '—'}</td>
                              <td style={tdStyle}><StatusPill status={entry.ok ? 'sent' : 'failed'} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </PanelSection>
                ) : null}
              </div>
            </div>
          ) : (
            <CreateTemplatePane newTpl={newTpl} onChange={setNewTpl} onSubmit={handleCreateTemplate} creating={creating} createMsg={createMsg} />
          )}
        </div>
      ) : null}

      {mainTab === 'logs' ? (
        <PanelSection title="Message Logs" subtitle="Latest WhatsApp status snapshots across journey traffic and manual sends.">
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 1.2fr) repeat(2, minmax(170px, 0.7fr)) auto', gap: '10px', marginBottom: '16px' }}>
            <input value={logsFilters.search} onChange={(event) => setLogsFilters((prev) => ({ ...prev, search: event.target.value }))} placeholder="Search phone, customer, template" style={inputStyle} />
            <select value={logsFilters.status} onChange={(event) => setLogsFilters((prev) => ({ ...prev, status: event.target.value }))} style={inputStyle}>
              <option value="all">All statuses</option>
              {logStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
            <input value={logsFilters.template_name} onChange={(event) => setLogsFilters((prev) => ({ ...prev, template_name: event.target.value }))} placeholder="Filter by template" style={inputStyle} />
            <button onClick={loadLogs} disabled={logsLoading} style={primaryButtonStyle(logsLoading)}>{logsLoading ? 'Loading…' : 'Apply'}</button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            <StatCard label="Visible Logs" value={logsTotal} tone="slate" caption="Latest combined status rows" />
            {Object.entries(logSummary || {}).map(([status, count]) => (
              <StatCard key={status} label={status} value={count} tone={status === 'failed' ? 'red' : status === 'delivered' ? 'green' : status === 'read' ? 'indigo' : 'blue'} caption="Latest message state" />
            ))}
          </div>

          {logsLoading ? (
            <EmptyState title="Loading logs" body="Fetching latest status snapshots from manual sends and journey messages." />
          ) : !logRows.length ? (
            <EmptyState title="No logs available" body="Send a message or wait for WhatsApp status webhooks to populate the log view." />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    {['Time', 'Status', 'Source', 'Phone', 'Template', 'Customer', 'Stage', 'Error'].map((heading) => <th key={heading} style={thStyle}>{heading}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {logRows.map((row) => (
                    <tr key={`${row.log_id}-${row.event_at}`} style={trStyle}>
                      <td style={tdStyle}>{formatDateTime(row.event_at)}</td>
                      <td style={tdStyle}><StatusPill status={row.status} /></td>
                      <td style={tdStyle}><Badge label={row.source || 'unknown'} tone={row.source === 'manual' ? 'amber' : 'slate'} /></td>
                      <td style={tdStyle}><span style={monoStyle}>{row.recipient_phone || '—'}</span></td>
                      <td style={tdStyle}>{row.template_name || '—'}</td>
                      <td style={tdStyle}>{row.customer_name || row.customer_email || '—'}</td>
                      <td style={tdStyle}>{row.journey_stage || '—'}</td>
                      <td style={{ ...tdStyle, maxWidth: '260px', whiteSpace: 'normal', lineHeight: 1.6 }}>{row.error_detail || row.error_title || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </PanelSection>
      ) : null}
    </div>
  );
}

function CreateTemplatePane({ newTpl, onChange, onSubmit, creating, createMsg }) {
  const varCount = (newTpl.body.match(/\{\{\d+\}\}/g) || []).length;
  const templatePresets = [
    { label: 'Order Confirmed', category: 'UTILITY', name: 'order_confirmed_today_v1', body: 'Hi {{1}}, your Pureleven order {{2}} is confirmed. We will update you here when tracking is ready. Order total: {{3}}.', footer: 'Pureleven' },
    { label: 'Tracking Added', category: 'UTILITY', name: 'order_tracking_today_v1', body: 'Hi {{1}}, your Pureleven order {{2}} is on the way. Tracking ID: {{3}}. Track here: {{4}}', footer: 'Pureleven' },
    { label: 'Delivered', category: 'UTILITY', name: 'order_delivered_today_v1', body: 'Hi {{1}}, your Pureleven order {{2}} has been delivered. Please check the package and reply here if you need help.', footer: 'Pureleven' },
    { label: 'Purchased Journey', category: 'MARKETING', name: 'purchased_reorder_journey_v1', body: 'Hi {{1}}, thank you for choosing Pureleven. Based on your last order, you may like {{2}}. Shop here: {{3}}', footer: 'Pureleven' },
    { label: 'Interested Journey', category: 'MARKETING', name: 'interested_first_order_v1', body: 'Hi {{1}}, noticed your interest in Pureleven. Can we help you choose the right product today? Browse here: {{2}}', footer: 'Pureleven' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: '20px', alignItems: 'start' }}>
      <PanelSection title="Create Meta Template" subtitle="Submit directly to the selected Meta WABA. Approved templates will appear on the next sync.">
        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {templatePresets.map((preset) => (
            <button key={preset.name} onClick={() => onChange({ ...newTpl, name: preset.name, category: preset.category, language: newTpl.language || 'en_US', body: preset.body, header: preset.label, footer: preset.footer })} style={secondaryButtonStyle(false)}>
              {preset.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={labelStyle}>Template Name</label>
            <input value={newTpl.name} onChange={(event) => onChange({ ...newTpl, name: event.target.value.toLowerCase().replace(/\s+/g, '_') })} placeholder="order_confirmation" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Category</label>
            <select value={newTpl.category} onChange={(event) => onChange({ ...newTpl, category: event.target.value })} style={inputStyle}>
              <option value="MARKETING">Marketing</option>
              <option value="UTILITY">Utility</option>
              <option value="AUTHENTICATION">Authentication</option>
            </select>
          </div>
        </div>

        <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: '220px 1fr', gap: '16px' }}>
          <div>
            <label style={labelStyle}>Language</label>
            <select value={newTpl.language} onChange={(event) => onChange({ ...newTpl, language: event.target.value })} style={inputStyle}>
              <option value="en_US">English (US)</option>
              <option value="en_GB">English (UK)</option>
              <option value="hi">Hindi</option>
              <option value="ml">Malayalam</option>
            </select>
          </div>
        </div>

        <div style={{ marginTop: '16px' }}>
          <label style={labelStyle}>Header</label>
          <input value={newTpl.header} onChange={(event) => onChange({ ...newTpl, header: event.target.value })} placeholder="Optional header text" maxLength={60} style={inputStyle} />
        </div>

        <div style={{ marginTop: '16px' }}>
          <label style={labelStyle}>Body</label>
          <textarea value={newTpl.body} onChange={(event) => onChange({ ...newTpl, body: event.target.value })} placeholder={'Hello {{1}},\n\nYour order {{2}} has been placed.'} rows={8} style={{ ...inputStyle, minHeight: '170px', resize: 'vertical', lineHeight: 1.7 }} />
          {varCount ? <div style={{ marginTop: '6px', fontSize: '11px', color: '#92400e' }}>{varCount} variable slots detected.</div> : null}
        </div>

        <div style={{ marginTop: '16px' }}>
          <label style={labelStyle}>Footer</label>
          <input value={newTpl.footer} onChange={(event) => onChange({ ...newTpl, footer: event.target.value })} placeholder="Optional footer" maxLength={60} style={inputStyle} />
        </div>

        <div style={{ marginTop: '18px', padding: '14px', borderRadius: '12px', background: '#fffbeb', border: '1px solid #fde68a', fontSize: '12px', color: '#92400e', lineHeight: 1.7 }}>
          The form below submits the template directly to Meta. Approval state remains controlled by Meta review. Use Sync Now to refresh the local template list after approval or status changes.
        </div>

        {createMsg ? (
          <div style={{ marginTop: '16px', padding: '12px 14px', borderRadius: '10px', border: `1px solid ${createMsg.ok ? '#bbf7d0' : '#fecaca'}`, background: createMsg.ok ? '#f0fdf4' : '#fef2f2', color: createMsg.ok ? '#166534' : '#b91c1c', fontSize: '12px', lineHeight: 1.7 }}>
            {createMsg.text}
          </div>
        ) : null}

        <div style={{ marginTop: '16px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button onClick={onSubmit} disabled={creating || !newTpl.name.trim() || !newTpl.body.trim()} style={primaryButtonStyle(creating || !newTpl.name.trim() || !newTpl.body.trim())}>
            {creating ? 'Submitting…' : 'Submit to Meta'}
          </button>
          <a href="https://business.facebook.com/wa/manage/message-templates/" target="_blank" rel="noopener noreferrer" style={{ ...secondaryLinkStyle }}>
            Open Meta Manager
          </a>
        </div>
      </PanelSection>

      <PanelSection title="Live Preview" subtitle="Renders the same body and variables you are about to submit.">
        <div style={{ background: '#e5ddd5', borderRadius: '14px', padding: '16px', minHeight: '240px' }}>
          {newTpl.header || newTpl.body || newTpl.footer ? (
            <div style={{ background: '#dcf8c6', borderRadius: '10px 10px 10px 0', padding: '14px 16px', boxShadow: '0 1px 2px rgba(15, 23, 42, 0.08)' }}>
              {newTpl.header ? <div style={{ marginBottom: '6px', fontSize: '13px', fontWeight: 700, color: '#111827' }}>{highlightVars(newTpl.header)}</div> : null}
              <div style={{ fontSize: '13px', color: '#111827', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{newTpl.body ? highlightVars(newTpl.body) : 'Template body…'}</div>
              {newTpl.footer ? <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>{newTpl.footer}</div> : null}
            </div>
          ) : (
            <EmptyState title="Preview is empty" body="Start typing a header or body to preview the template bubble." />
          )}
        </div>
        {newTpl.name ? (
          <div style={{ marginTop: '12px', fontSize: '11px', color: '#64748b', lineHeight: 1.8, fontFamily: 'monospace' }}>
            name: {newTpl.name}<br />
            category: {newTpl.category}<br />
            language: {newTpl.language}
          </div>
        ) : null}
      </PanelSection>
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: '10px',
  border: '1px solid #d1d5db',
  fontSize: '13px',
  color: '#111827',
  background: 'white',
  boxSizing: 'border-box',
  outline: 'none',
  fontFamily: 'inherit',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '12px',
};

const thStyle = {
  padding: '10px 12px',
  textAlign: 'left',
  fontSize: '10px',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#64748b',
  background: '#f8fafc',
  borderBottom: '1px solid #e5e7eb',
};

const tdStyle = {
  padding: '12px',
  borderBottom: '1px solid #f1f5f9',
  color: '#334155',
  verticalAlign: 'top',
};

const trStyle = {
  background: 'white',
};

const monoStyle = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  color: '#111827',
};

const labelStyle = {
  display: 'block',
  marginBottom: '6px',
  fontSize: '12px',
  fontWeight: 700,
  color: '#374151',
};

function mainTabButtonStyle(active) {
  return {
    padding: '10px 16px',
    borderRadius: '999px',
    border: `1px solid ${active ? '#86efac' : '#d1d5db'}`,
    background: active ? '#f0fdf4' : 'white',
    color: active ? '#166534' : '#475569',
    fontSize: '13px',
    fontWeight: 700,
    cursor: 'pointer',
  };
}

function primaryButtonStyle(disabled) {
  return {
    padding: '10px 18px',
    borderRadius: '10px',
    border: 'none',
    background: disabled ? '#94a3b8' : '#0f766e',
    color: 'white',
    fontSize: '13px',
    fontWeight: 700,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}

function secondaryButtonStyle(disabled) {
  return {
    padding: '10px 16px',
    borderRadius: '10px',
    border: '1px solid #cbd5e1',
    background: disabled ? '#f8fafc' : 'white',
    color: '#334155',
    fontSize: '13px',
    fontWeight: 700,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}

function multiSelectChipStyle(active, tone = 'slate') {
  const colors = toneColors(tone);
  return {
    padding: '8px 12px',
    borderRadius: '999px',
    border: `1px solid ${active ? colors.border : '#d1d5db'}`,
    background: active ? colors.background : 'white',
    color: active ? colors.text : '#334155',
    fontSize: '12px',
    fontWeight: 700,
    cursor: 'pointer',
  };
}

function scoreSelectorCardStyle(active, tone = 'slate') {
  const colors = toneColors(tone);
  return {
    padding: '12px 14px',
    borderRadius: '14px',
    border: `1px solid ${active ? colors.border : '#e5e7eb'}`,
    background: active ? colors.background : 'white',
    textAlign: 'left',
    cursor: 'pointer',
    boxShadow: active ? `0 0 0 2px ${colors.border}33` : 'none',
  };
}

function softPanelStyle(tone = 'slate') {
  const colors = toneColors(tone);
  return {
    padding: '14px 16px',
    borderRadius: '14px',
    border: `1px solid ${colors.border}`,
    background: colors.background,
  };
}

function aiActionButtonStyle(disabled) {
  return {
    padding: '8px 14px',
    borderRadius: '10px',
    border: 'none',
    background: disabled ? '#a5b4fc' : '#4f46e5',
    color: 'white',
    fontSize: '12px',
    fontWeight: 800,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}

function miniMetricStyle(tone = 'slate') {
  const colors = toneColors(tone);
  return {
    background: 'white',
    borderRadius: '12px',
    padding: '12px',
    textAlign: 'center',
    border: `1px solid ${colors.border}`,
  };
}

function miniMetricValueStyle(color) {
  return {
    fontSize: '20px',
    fontWeight: 800,
    color,
    lineHeight: 1.1,
  };
}

const miniMetricLabelStyle = {
  marginTop: '4px',
  fontSize: '11px',
  color: '#64748b',
};

const secondaryLinkStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '10px 16px',
  borderRadius: '10px',
  border: '1px solid #cbd5e1',
  background: 'white',
  color: '#334155',
  fontSize: '13px',
  fontWeight: 700,
  textDecoration: 'none',
};

const inlineActionStyle = {
  padding: '8px 12px',
  borderRadius: '10px',
  border: '1px solid #cbd5e1',
  background: 'white',
  color: '#334155',
  fontSize: '12px',
  fontWeight: 700,
  cursor: 'pointer',
};

function channelCardStyle(active, tone) {
  const colors = toneColors(tone);
  return {
    flex: 1,
    padding: '12px',
    borderRadius: '12px',
    border: `1px solid ${active ? colors.border : '#e5e7eb'}`,
    background: active ? colors.background : 'white',
    textAlign: 'left',
    cursor: 'pointer',
  };
}

function templateListItemStyle(active) {
  return {
    width: '100%',
    padding: '12px 13px',
    borderRadius: '12px',
    border: `1px solid ${active ? '#86efac' : '#e5e7eb'}`,
    background: active ? '#f0fdf4' : 'white',
    textAlign: 'left',
    cursor: 'pointer',
  };
}

function sendButtonStyle(channel, disabled) {
  return {
    width: '100%',
    padding: '12px 18px',
    borderRadius: '12px',
    border: 'none',
    background: disabled ? '#94a3b8' : (channel === 'wabis' ? '#16a34a' : '#2563eb'),
    color: 'white',
    fontSize: '14px',
    fontWeight: 800,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}
