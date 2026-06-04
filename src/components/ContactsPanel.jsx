/**
 * ContactsPanel — Unified Customer Management
 * Features: Customer list, search/filter, CSV import, Shopify sync, customer detail
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = 'https://track.pureleven.com/api';
const ADMIN_KEY = 'anu_admin_secret';

function apiUrl(path, params = {}) {
  const secret = localStorage.getItem(ADMIN_KEY) || '';
  const qs = new URLSearchParams({ admin_secret: secret, ...params }).toString();
  return `${API_BASE}${path}?${qs}`;
}

const STATUS_COLORS = {
  vip: { bg: '#fef3c7', text: '#92400e', label: '👑 VIP' },
  active: { bg: '#d1fae5', text: '#065f46', label: '✅ Active' },
  new: { bg: '#dbeafe', text: '#1e40af', label: '🌱 New' },
  inactive: { bg: '#f3f4f6', text: '#4b5563', label: '😴 Inactive' },
  churned: { bg: '#fee2e2', text: '#991b1b', label: '🚫 Churned' },
};

const ENGAGEMENT_COLORS = {
  cold: { bg: '#e5e7eb', text: '#374151' },
  warm: { bg: '#fef3c7', text: '#92400e' },
  hot: { bg: '#fee2e2', text: '#991b1b' },
};

// Score badge config
const SCORE_BADGE = {
  95: { bg: '#dcfce7', text: '#15803d', label: 'Customer' },
  90: { bg: '#dbeafe', text: '#1d4ed8', label: 'Lead' },
  75: { bg: '#fef9c3', text: '#a16207', label: 'Form' },
  60: { bg: '#ede9fe', text: '#6d28d9', label: 'Meta Ad' },
  50: { bg: '#f3e8ff', text: '#7e22ce', label: 'Wabis' },
  0:  { bg: '#f3f4f6', text: '#6b7280', label: 'Unknown' },
};

const SOURCE_ICONS = {
  shopify: '🛍️',
  wabis: '💬',
  lead: '📋',
  google_form: '📝',
  meta_ad: '📣',
  unknown: '❓',
};

function ScoreBadge({ score }) {
  const s = score ?? 0;
  // find closest bucket
  const keys = [95, 90, 75, 60, 50, 0];
  const key = keys.find(k => s >= k) ?? 0;
  const cfg = SCORE_BADGE[key];
  return (
    <span style={{ background: cfg.bg, color: cfg.text, padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 700 }}>
      {s} · {cfg.label}
    </span>
  );
}

function SourceBadges({ tags, source }) {
  const list = Array.isArray(tags) ? tags : [];
  if (list.length === 0 && source) list.push(source);
  if (list.length === 0) list.push('unknown');
  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
      {[...new Set(list)].slice(0, 3).map(t => (
        <span key={t} title={t} style={{ background: '#f1f5f9', color: '#475569', padding: '1px 6px', borderRadius: 10, fontSize: 11 }}>
          {SOURCE_ICONS[t] || '🔗'} {t}
        </span>
      ))}
    </div>
  );
}

const SOURCE_TABS = [
  { key: '', label: 'All', icon: '👥' },
  { key: 'shopify', label: 'Customers', icon: '🛍️', minScore: 95 },
  { key: 'lead', label: 'Leads', icon: '📋' },
  { key: 'wabis', label: 'Wabis', icon: '💬', wabisOnly: true },
];

export default function ContactsPanel() {
  const [customers, setCustomers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [emailOptedIn, setEmailOptedIn] = useState('');
  const [sourceTab, setSourceTab] = useState('');
  const [page, setPage] = useState(0);
  const [orderBy, setOrderBy] = useState('created_at');
  const PAGE_SIZE = 50;

  // CSV import
  const [importMode, setImportMode] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [defaultTags, setDefaultTags] = useState('');
  const [importFormat, setImportFormat] = useState('csv');
  const fileRef = useRef(null);

  // Shopify sync
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  // Customer detail
  const [selected, setSelected] = useState(null);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tab = SOURCE_TABS.find(t => t.key === sourceTab) || SOURCE_TABS[0];
      const params = {
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
      };
      if (tab.minScore) params.min_score = tab.minScore;
      if (tab.wabisOnly) params.wabis_only = 'true';
      if (tab.key && !tab.wabisOnly && !tab.minScore) params.source = tab.key;

      const res = await fetch(apiUrl('/crm/customers/unified', params));
      const data = await res.json();
      setCustomers(data.customers || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [page, sourceTab, search, emailOptedIn]);

  useEffect(() => { fetchCustomers(); }, [fetchCustomers]);

  // Breakdown stats
  const [breakdown, setBreakdown] = useState(null);
  useEffect(() => {
    const secret = localStorage.getItem(ADMIN_KEY) || '';
    fetch(`${API_BASE}/crm/customers/breakdown?admin_secret=${encodeURIComponent(secret)}`)
      .then(r => r.json())
      .then(d => setBreakdown(d))
      .catch(() => {});
  }, []);

  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const secret = localStorage.getItem(ADMIN_KEY) || '';
      const qs = new URLSearchParams({
        admin_secret: secret,
        default_tags: defaultTags,
        email_opted_in: true,
      }).toString();
      const endpoint = importFormat === 'xml' ? '/customers/import/xml' : '/customers/import/csv';
      const res = await fetch(`${API_BASE}${endpoint}?${qs}`, { method: 'POST', body: form });
      const data = await res.json();
      setImportResult(data);
      if (data.status === 'complete') fetchCustomers();
    } catch (err) {
      setImportResult({ status: 'error', message: err.message });
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleShopifySync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch(apiUrl('/customers/sync/shopify'), { method: 'POST' });
      const data = await res.json();
      setSyncResult(data);
      if (data.status === 'ok') fetchCustomers();
    } catch (err) {
      setSyncResult({ status: 'error', message: err.message });
    } finally {
      setSyncing(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, color: '#111827', fontSize: 22 }}>👥 Contacts</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 14 }}>
            {total.toLocaleString()} unified profiles
            {breakdown && (
              <span style={{ marginLeft: 10, fontSize: 12 }}>
                · 🛍️ {(breakdown.by_score?.['95'] || 0).toLocaleString()} customers
                · 💬 {(breakdown.wabis_subscribed || 0).toLocaleString()} wabis
              </span>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => setImportMode(!importMode)}
            style={btnStyle('#3b82f6')}
          >
            📥 Import CSV
          </button>
          <button
            onClick={handleShopifySync}
            disabled={syncing}
            style={btnStyle('#10b981')}
          >
            {syncing ? '⏳ Syncing…' : '🛍️ Sync Shopify'}
          </button>
        </div>
      </div>

      {/* CSV Import Panel */}
      {importMode && (
        <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 10, padding: 20, marginBottom: 20 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>📥 Import Customers from CSV</h3>
          <p style={{ margin: '0 0 12px', fontSize: 13, color: '#475569' }}>
            Required column: <code>email</code>. Optional: <code>name</code>, <code>first_name</code>, <code>last_name</code>, <code>phone</code>, <code>tags</code>
          </p>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Default tags (e.g. newsletter,vip)"
              value={defaultTags}
              onChange={e => setDefaultTags(e.target.value)}
              style={inputStyle(220)}
            />
            <select value={importFormat} onChange={(e) => setImportFormat(e.target.value)} style={inputStyle(140)}>
              <option value="csv">CSV</option>
              <option value="xml">XML</option>
            </select>
            <label style={{
              ...btnStyle('#6366f1'),
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
            }}>
              {importing ? '⏳ Importing…' : `📂 Choose ${importFormat.toUpperCase()} File`}
              <input ref={fileRef} type="file" accept={importFormat === 'xml' ? '.xml' : '.csv'} onChange={handleImport} style={{ display: 'none' }} disabled={importing} />
            </label>
          </div>
          {importResult && (
            <div style={{
              marginTop: 12,
              padding: '10px 14px',
              borderRadius: 6,
              background: importResult.status === 'complete' ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${importResult.status === 'complete' ? '#bbf7d0' : '#fecaca'}`,
              fontSize: 13,
            }}>
              {importResult.status === 'complete' ? (
                <span>
                  ✅ Import complete: <strong>{importResult.created}</strong> created,{' '}
                  <strong>{importResult.updated}</strong> updated,{' '}
                  <strong>{importResult.skipped}</strong> skipped
                  {importResult.errors?.length > 0 && (
                    <span style={{ color: '#dc2626', marginLeft: 8 }}>
                      ({importResult.errors.length} errors)
                    </span>
                  )}
                </span>
              ) : (
                <span>❌ {importResult.message}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Sync result */}
      {syncResult && (
        <div style={{ background: syncResult.status === 'ok' ? '#f0fdf4' : '#fef2f2', border: `1px solid ${syncResult.status === 'ok' ? '#bbf7d0' : '#fecaca'}`, borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>
          {syncResult.status === 'ok'
            ? `✅ Shopify sync complete`
            : `❌ Sync failed: ${syncResult.message}`}
        </div>
      )}

      {/* Source Tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {SOURCE_TABS.map(tab => {
          const count = tab.key === '' ? breakdown?.total
            : tab.key === 'shopify' ? breakdown?.by_score?.['95']
            : tab.wabisOnly ? breakdown?.wabis_subscribed
            : breakdown?.by_source?.[tab.key];
          return (
            <button
              key={tab.key}
              onClick={() => { setSourceTab(tab.key); setPage(0); }}
              style={{
                padding: '6px 16px',
                borderRadius: 20,
                border: sourceTab === tab.key ? 'none' : '1px solid #d1d5db',
                background: sourceTab === tab.key ? '#111827' : 'white',
                color: sourceTab === tab.key ? 'white' : '#374151',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              {tab.icon} {tab.label}
              {count != null && (
                <span style={{
                  background: sourceTab === tab.key ? 'rgba(255,255,255,0.25)' : '#f3f4f6',
                  color: sourceTab === tab.key ? 'white' : '#6b7280',
                  borderRadius: 10,
                  padding: '1px 7px',
                  fontSize: 11,
                }}>{Number(count).toLocaleString()}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Table */}
      {error && <div style={{ color: '#dc2626', marginBottom: 12 }}>Error: {error}</div>}
      <div style={{ background: 'white', borderRadius: 10, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
              {['Customer', 'Phone', 'Score', 'Source', 'Orders', 'Spent (₹)', 'Last Order', ''].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: '#374151', fontWeight: 600, fontSize: 12 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>Loading…</td></tr>
            ) : customers.length === 0 ? (
              <tr><td colSpan={8} style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No customers found</td></tr>
            ) : customers.map(c => {
              return (
                <tr key={c.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontWeight: 500, color: '#111827' }}>{`${c.first_name || ''} ${c.last_name || ''}`.trim() || '—'}</div>
                    <div style={{ color: '#6b7280', fontSize: 12 }}>{c.email || c.wabis_phone || '—'}</div>
                  </td>
                  <td style={{ padding: '10px 14px', color: '#374151' }}>{c.phone || c.wabis_phone || '—'}</td>
                  <td style={{ padding: '10px 14px' }}><ScoreBadge score={c.customer_score} /></td>
                  <td style={{ padding: '10px 14px' }}><SourceBadges tags={c.unified_source_tags} source={c.primary_customer_source} /></td>
                  <td style={{ padding: '10px 14px', color: '#374151' }}>{c.orders_count ?? 0}</td>
                  <td style={{ padding: '10px 14px', color: '#374151' }}>₹{Number(c.total_spent || 0).toLocaleString('en-IN')}</td>
                  <td style={{ padding: '10px 14px', color: '#374151', fontSize: 12 }}>
                    {c.last_order_date ? new Date(c.last_order_date).toLocaleDateString('en-IN') : '—'}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <button
                      onClick={() => setSelected(c)}
                      style={{ background: 'none', border: '1px solid #d1d5db', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 12, color: '#374151' }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            style={paginBtn(page === 0)}
          >← Prev</button>
          <span style={{ padding: '6px 14px', fontSize: 13, color: '#374151' }}>
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            style={paginBtn(page >= totalPages - 1)}
          >Next →</button>
        </div>
      )}

      {/* Customer Detail Modal */}
      {selected && (
        <CustomerDetailModal customer={selected} onClose={() => setSelected(null)} onRefresh={fetchCustomers} />
      )}
    </div>
  );
}

// ── Customer 360 Tab (Sprint 1 CIAMP) ─────────────────────────────────────────

const TIMELINE_ICONS = {
  order: '🛍️',
  event: '📡',
  message: '✉️',
};

const HEALTH_BADGE = {
  active: { bg: '#d1fae5', text: '#065f46', label: '✅ Active' },
  lapsed: { bg: '#fef3c7', text: '#92400e', label: '⚠️ Lapsed' },
  inactive: { bg: '#f3f4f6', text: '#4b5563', label: '😴 Inactive' },
};

function Customer360Tab({ customerId }) {
  const [profile, setProfile] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!customerId) { setError('No customer ID'); setLoading(false); return; }
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [pRes, tRes] = await Promise.all([
          fetch(apiUrl(`/customers/${customerId}/360`)),
          fetch(apiUrl(`/customers/${customerId}/timeline`, { limit: 30 })),
        ]);
        if (!pRes.ok) throw new Error(`360 API: ${pRes.status}`);
        setProfile(await pRes.json());
        setTimeline(await tRes.json());
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [customerId]);

  if (loading) return <div style={{ padding: 20, color: '#64748b', fontSize: 13 }}>Loading 360 profile…</div>;
  if (error) return <div style={{ padding: 20, color: '#ef4444', fontSize: 13 }}>Error: {error}</div>;
  if (!profile) return null;

  const health = HEALTH_BADGE[profile.customer_health?.status] || HEALTH_BADGE.inactive;

  return (
    <div>
      {/* Health + Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        {[
          { label: 'Health', value: <span style={{ background: health.bg, color: health.text, padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 700 }}>{health.label}</span> },
          { label: 'Revenue', value: `₹${(profile.stats?.total_revenue || 0).toLocaleString('en-IN')}` },
          { label: 'Orders', value: profile.stats?.order_count ?? 0 },
          { label: 'Messages Sent', value: profile.messages_count ?? 0 },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 14px', textAlign: 'center' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>{label.toUpperCase()}</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#111827' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Segments */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 8 }}>SEGMENTS</div>
        {(profile.segments || []).length === 0
          ? <span style={{ fontSize: 13, color: '#9ca3af' }}>No segments yet</span>
          : (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {(profile.segments || []).map(seg => (
                <span key={seg.id} title={seg.description} style={{ background: '#ede9fe', color: '#6d28d9', padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
                  🏷️ {seg.name}
                </span>
              ))}
            </div>
          )
        }
      </div>

      {/* Timeline */}
      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#374151', marginBottom: 8 }}>
          TIMELINE <span style={{ fontWeight: 400, color: '#94a3b8' }}>({timeline?.total ?? 0} items)</span>
        </div>
        {(timeline?.items || []).length === 0
          ? <div style={{ fontSize: 13, color: '#9ca3af' }}>No timeline activity yet</div>
          : (
            <div style={{ display: 'grid', gap: 8 }}>
              {(timeline?.items || []).slice(0, 20).map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                  <span style={{ fontSize: 18, flexShrink: 0 }}>{TIMELINE_ICONS[item.type] || '📌'}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{item.description}</div>
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                      {item.type.toUpperCase()}
                      {item.status && ` · ${item.status}`}
                      {item.date && ` · ${new Date(item.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`}
                    </div>
                  </div>
                  {item.amount && (
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#059669', flexShrink: 0 }}>₹{item.amount.toLocaleString('en-IN')}</div>
                  )}
                </div>
              ))}
            </div>
          )
        }
      </div>
    </div>
  );
}

// ── CustomerDetailModal ────────────────────────────────────────────────────────

function CustomerDetailModal({ customer, onClose, onRefresh }) {
  const c = customer;
  const s = STATUS_COLORS[c.customer_status] || STATUS_COLORS.new;
  const tags = (() => { try { return JSON.parse(c.tags || '[]'); } catch { return []; } })();
  const [activeTab, setActiveTab] = useState('overview');
  const [intelligence, setIntelligence] = useState(null);
  const [loadingIntelligence, setLoadingIntelligence] = useState(false);
  const [aiReplyInput, setAiReplyInput] = useState('');
  const [aiReply, setAiReply] = useState(null);

  useEffect(() => {
    const loadIntelligence = async () => {
      setLoadingIntelligence(true);
      try {
        const res = await fetch(apiUrl(`/customers/${encodeURIComponent(c.email)}/intelligence`));
        const data = await res.json();
        setIntelligence(data);
      } finally {
        setLoadingIntelligence(false);
      }
    };
    loadIntelligence();
  }, [c.email]);

  const togglePause = async () => {
    const paused = !(intelligence?.customer?.pause_campaigns || c.pause_campaigns);
    await fetch(apiUrl(`/customers/${encodeURIComponent(c.email)}/pause-campaigns`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paused }),
    });
    const res = await fetch(apiUrl(`/customers/${encodeURIComponent(c.email)}/intelligence`));
    setIntelligence(await res.json());
    onRefresh();
  };

  const generateAiReply = async () => {
    if (!aiReplyInput.trim()) return;
    const res = await fetch(apiUrl(`/customers/${encodeURIComponent(c.email)}/ai-reply-draft`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ inbound_message: aiReplyInput }),
    });
    setAiReply(await res.json());
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete customer ${c.email}?`)) return;
    await fetch(apiUrl(`/customers/${encodeURIComponent(c.email)}`), { method: 'DELETE' });
    onRefresh();
    onClose();
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: 'white', borderRadius: 14, padding: 28, width: 860, maxWidth: '92vw', maxHeight: '88vh', overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 18 }}>{c.name || c.email}</h3>
            <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>{c.email || c.phone || c.id}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#9ca3af' }}>×</button>
        </div>

        {/* Tab Bar */}
        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid #e5e7eb', marginBottom: 20 }}>
          {[
            { key: 'overview', label: '📋 Overview' },
            { key: '360', label: '🎯 360 View' },
          ].map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
              padding: '8px 16px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: activeTab === tab.key ? 700 : 400,
              color: activeTab === tab.key ? '#4f46e5' : '#6b7280',
              borderBottom: activeTab === tab.key ? '2px solid #4f46e5' : '2px solid transparent',
              marginBottom: -1,
            }}>{tab.label}</button>
          ))}
        </div>

        {/* 360 Tab */}
        {activeTab === '360' && <Customer360Tab customerId={c.id} />}

        {/* Overview Tab */}
        {activeTab === 'overview' && (<>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
          <InfoRow label="Customer UID">{c.customer_uid || '—'}</InfoRow>
          <InfoRow label="Status">
            <span style={{ background: s.bg, color: s.text, padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 }}>{s.label}</span>
          </InfoRow>
          <InfoRow label="Phone">{c.phone || '—'}</InfoRow>
          <InfoRow label="Orders">{c.total_orders}</InfoRow>
          <InfoRow label="Total Spent">₹{Number(c.total_spent || 0).toLocaleString('en-IN')}</InfoRow>
          <InfoRow label="First Order">{c.first_order_date ? new Date(c.first_order_date).toLocaleDateString('en-IN') : '—'}</InfoRow>
          <InfoRow label="Last Order">{c.last_order_date ? new Date(c.last_order_date).toLocaleDateString('en-IN') : '—'}</InfoRow>
          <InfoRow label="Email Opt-in">{c.email_opted_in ? '✅ Yes' : '❌ No'}</InfoRow>
          <InfoRow label="WhatsApp">{c.whatsapp_opted_in ? '✅ Yes' : '❌ No'}</InfoRow>
          <InfoRow label="Source">{c.source || '—'}</InfoRow>
          <InfoRow label="Shopify ID">{c.shopify_customer_id || '—'}</InfoRow>
          <InfoRow label="Meta Lead">{c.meta_lead_id || '—'}</InfoRow>
          <InfoRow label="Google GCLID">{c.google_gclid || '—'}</InfoRow>
          <InfoRow label="Preferred Channel">{c.preferred_channel || 'auto'}</InfoRow>
          <InfoRow label="Purchase">{c.purchase_status || 'not_purchased'}</InfoRow>
          <InfoRow label="Label">{(c.engagement_label || 'cold').toUpperCase()}</InfoRow>
          <InfoRow label="Customer Score"><ScoreBadge score={c.customer_score} /></InfoRow>
          <InfoRow label="Source"><SourceBadges tags={c.unified_source_tags} source={c.primary_customer_source} /></InfoRow>
          <InfoRow label="Lead Score">{c.lead_score ?? 0}/100</InfoRow>
          <InfoRow label="Lead Status">{c.lead_status || '—'}</InfoRow>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <button onClick={togglePause} style={btnStyle((intelligence?.customer?.pause_campaigns || c.pause_campaigns) ? '#16a34a' : '#f59e0b')}>
            {(intelligence?.customer?.pause_campaigns || c.pause_campaigns) ? '▶ Resume Campaigns' : '⏸ Pause Campaigns'}
          </button>
          <button onClick={handleDelete} style={btnStyle('#ef4444')}>🗑 Delete Customer</button>
        </div>

        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10, marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Journey + Communication Intelligence</div>
          {loadingIntelligence ? <div style={{ color: '#64748b', fontSize: 12 }}>Loading intelligence…</div> : (
            <>
              <div style={{ fontSize: 12, color: '#334155', marginBottom: 4 }}>
                Active Journeys: {(intelligence?.journeys?.active || []).length} | Planned Messages: {intelligence?.communication?.planned_messages || 0} | Emails Sent: {intelligence?.communication?.emails_sent || 0}
              </div>
              <div style={{ fontSize: 12, color: '#334155' }}>
                AI Plan: {intelligence?.ai?.next_action || '—'} ({intelligence?.ai?.reason || 'no reason yet'})
              </div>
            </>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Identity Map</div>
            {(intelligence?.identity_map || []).length > 0 ? (
              <div style={{ display: 'grid', gap: 6 }}>
                {(intelligence.identity_map || []).slice(0, 8).map((idn, idx) => (
                  <div key={idx} style={{ fontSize: 12, color: '#334155', display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <span style={{ fontWeight: 600 }}>{idn.identity_type}</span>
                    <span style={{ textAlign: 'right', overflowWrap: 'anywhere' }}>{idn.identity_value}</span>
                  </div>
                ))}
              </div>
            ) : <div style={{ color: '#94a3b8', fontSize: 12 }}>No identities mapped yet</div>}
          </div>

          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Score History</div>
            {(intelligence?.score_history || []).length > 0 ? (
              <div style={{ display: 'grid', gap: 6 }}>
                {(intelligence.score_history || []).slice(0, 5).map((h, idx) => (
                  <div key={idx} style={{ fontSize: 12, color: '#334155' }}>
                    <strong>{h.lead_score}/100</strong> {String(h.engagement_label || '').toUpperCase()} - {h.reason || 'updated'}
                  </div>
                ))}
              </div>
            ) : <div style={{ color: '#94a3b8', fontSize: 12 }}>No score history yet</div>}
          </div>
        </div>

        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>AI Reply Draft (Email)</div>
          <textarea
            value={aiReplyInput}
            onChange={(e) => setAiReplyInput(e.target.value)}
            placeholder="Paste customer email response here..."
            style={{ width: '100%', minHeight: 68, border: '1px solid #cbd5e1', borderRadius: 6, padding: 8, fontSize: 12, marginBottom: 8 }}
          />
          <button onClick={generateAiReply} style={btnStyle('#4f46e5')}>Generate AI Reply</button>
          {aiReply?.draft && (
            <div style={{ marginTop: 10, fontSize: 12, color: '#1f2937' }}>
              <div><strong>Subject:</strong> {aiReply.draft.subject}</div>
              <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}><strong>Body:</strong> {aiReply.draft.body}</div>
              <div style={{ marginTop: 4, color: '#6b7280' }}>
                Intent: {aiReply.draft.intent} | Confidence: {aiReply.draft.confidence}
              </div>
            </div>
          )}
        </div>

        {tags.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', marginBottom: 6 }}>TAGS</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {tags.map(t => (
                <span key={t} style={{ background: '#eff6ff', color: '#3b82f6', padding: '2px 8px', borderRadius: 10, fontSize: 11 }}>{t}</span>
              ))}
            </div>
          </div>
        )}

        {c.notes && (
          <div style={{ background: '#f9fafb', borderRadius: 6, padding: '8px 12px', fontSize: 13, color: '#374151', marginBottom: 12 }}>
            <strong>Notes:</strong> {c.notes}
          </div>
        )}

        <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 8 }}>
          Created: {c.created_at ? new Date(c.created_at).toLocaleDateString('en-IN') : '—'}
        </div>
        </>)}
      </div>
    </div>
  );
}

function InfoRow({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', marginBottom: 2 }}>{label.toUpperCase()}</div>
      <div style={{ fontSize: 13, color: '#111827' }}>{children}</div>
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

function btnStyle(color) {
  return {
    background: color,
    color: 'white',
    border: 'none',
    borderRadius: 8,
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
  };
}

function inputStyle(width) {
  return {
    border: '1px solid #d1d5db',
    borderRadius: 8,
    padding: '7px 12px',
    fontSize: 13,
    width,
    outline: 'none',
  };
}

function selectStyle() {
  return {
    border: '1px solid #d1d5db',
    borderRadius: 8,
    padding: '7px 12px',
    fontSize: 13,
    background: 'white',
    cursor: 'pointer',
  };
}

function paginBtn(disabled) {
  return {
    background: disabled ? '#f3f4f6' : 'white',
    border: '1px solid #d1d5db',
    borderRadius: 6,
    padding: '6px 14px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 13,
    color: disabled ? '#9ca3af' : '#374151',
  };
}
