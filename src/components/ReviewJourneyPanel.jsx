/**
 * ReviewJourneyPanel.jsx
 *
 * Post-Purchase Review Journey Dashboard
 * Psychology: Appreciation → Review → Return Visit → Repeat Purchase
 *
 * Tabs:
 *   Overview  — KPI cards + funnel chart
 *   Customers — Searchable / filterable customer table
 *   Messages  — Message send logs with open/click/review tracking
 *   Analytics — Funnel + daily message chart + status distribution
 */

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'https://track.pureleven.com/api';

// ── Brand tokens ──────────────────────────────────────────────────────────────
const G  = '#2E7D32';   // green
const GL = '#f0fdf4';   // light green
const GB = '#bbf7d0';
const GD = '#1b5e20';   // dark green
const S  = {
  card:   { background:'#fff', borderRadius:10, boxShadow:'0 1px 6px rgba(0,0,0,.08)', padding:'20px 24px' },
  label:  { fontSize:12, fontWeight:600, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'.5px', marginBottom:6 },
  big:    { fontSize:32, fontWeight:800, color:'#111827', lineHeight:1 },
  sub:    { fontSize:12, color:'#6b7280', marginTop:4 },
  badge:  (col) => ({ display:'inline-block', padding:'2px 9px', borderRadius:20, fontSize:11, fontWeight:600,
            background: col+'22', color: col, border: `1px solid ${col}44` }),
  btn:    (primary) => ({
    padding: primary ? '10px 20px' : '8px 16px',
    background: primary ? G : '#fff',
    color: primary ? '#fff' : '#374151',
    border: primary ? 'none' : '1px solid #d1d5db',
    borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: 'pointer',
  }),
  input:  { padding:'8px 12px', border:'1px solid #d1d5db', borderRadius:6, fontSize:14, width:'100%', boxSizing:'border-box' },
  th:     { padding:'10px 14px', fontSize:12, fontWeight:700, color:'#6b7280', textAlign:'left',
            borderBottom:'2px solid #e5e7eb', background:'#f9fafb' },
  td:     { padding:'11px 14px', fontSize:13, color:'#374151', borderBottom:'1px solid #f3f4f6', verticalAlign:'top' },
};

// ── Status colours ────────────────────────────────────────────────────────────
const STATUS_COLOR = { cold:'#6b7280', warm:'#f59e0b', hot:'#ef4444', purchased:'#8b5cf6', vip:'#2E7D32' };
const STATUS_ICON  = { cold:'🥶', warm:'🌤️', hot:'🔥', purchased:'💜', vip:'⭐' };

function StatusBadge({ status }) {
  const col = STATUS_COLOR[status] || '#6b7280';
  return <span style={S.badge(col)}>{STATUS_ICON[status] || ''} {status || 'cold'}</span>;
}

function StageLabel({ stage }) {
  const map = {
    review_pure_day15:   { label:'Day 15 Review', color:'#2563eb' },
    review_thanks_day18: { label:'Day 18 Thank You', color:'#059669' },
    crosssell_day18:     { label:'Day 18 Cross-sell', color:'#d97706' },
    replenishment_day45: { label:'Day 45 Replenish', color:'#7c3aed' },
    vip_day75:           { label:'Day 75 VIP', color:'#b45309' },
  };
  const meta = map[stage] || { label: stage, color:'#374151' };
  return <span style={S.badge(meta.color)}>{meta.label}</span>;
}

// ── Small KPI card ────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color }) {
  return (
    <div style={{ ...S.card, borderTop:`3px solid ${color || G}`, minWidth:150 }}>
      <div style={S.label}>{label}</div>
      <div style={{ ...S.big, color: color || '#111827' }}>{value ?? '—'}</div>
      {sub && <div style={S.sub}>{sub}</div>}
    </div>
  );
}

// ── Simple horizontal bar chart ───────────────────────────────────────────────
function FunnelBar({ steps }) {
  const max = Math.max(...steps.map(s => s.count), 1);
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
      {steps.map((step, i) => (
        <div key={i} style={{ display:'flex', alignItems:'center', gap:12 }}>
          <div style={{ width:170, fontSize:12, color:'#374151', textAlign:'right', flexShrink:0 }}>{step.label}</div>
          <div style={{ flex:1, background:'#f3f4f6', borderRadius:4, height:28, position:'relative' }}>
            <div style={{
              width: `${(step.count / max) * 100}%`,
              background: `hsl(${140 - i * 18},60%,44%)`,
              borderRadius:4, height:'100%',
              transition:'width .4s ease',
            }} />
          </div>
          <div style={{ width:50, fontSize:13, fontWeight:700, color:'#111827', flexShrink:0 }}>{step.count}</div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────
export default function ReviewJourneyPanel() {
  const [tab, setTab] = useState('overview');

  return (
    <div style={{ padding:'24px', background:'#f8fafc', minHeight:'100vh' }}>
      {/* Header */}
      <div style={{ marginBottom:24 }}>
        <h2 style={{ margin:0, fontSize:22, fontWeight:800, color:'#111827' }}>
          🌿 Review Journey Dashboard
        </h2>
        <p style={{ margin:'6px 0 0', fontSize:14, color:'#6b7280' }}>
          Post-purchase psychology: Appreciation → Review → Return Visit → Repeat Purchase
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display:'flex', gap:4, marginBottom:24, borderBottom:'2px solid #e5e7eb' }}>
        {[
          { id:'overview',   label:'📊 Overview'  },
          { id:'customers',  label:'👥 Customers' },
          { id:'messages',   label:'💬 Messages'  },
          { id:'analytics',  label:'📈 Analytics' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding:'10px 18px', background:'transparent', border:'none',
            borderBottom: tab === t.id ? `3px solid ${G}` : '3px solid transparent',
            color: tab === t.id ? G : '#6b7280',
            fontWeight: tab === t.id ? 700 : 500,
            fontSize:14, cursor:'pointer', marginBottom:-2,
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview'   && <OverviewTab />}
      {tab === 'customers'  && <CustomersTab />}
      {tab === 'messages'   && <MessagesTab />}
      {tab === 'analytics'  && <AnalyticsTab />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Overview Tab
// ─────────────────────────────────────────────────────────────────────────────
function OverviewTab() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [orchestrating, setOrchestrating] = useState(false);
  const [orchResult, setOrchResult] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await fetch(`${API_BASE}/review-journey/overview`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runOrchestrate = async (dryRun) => {
    setOrchestrating(true); setOrchResult(null);
    try {
      const r = await fetch(`${API_BASE}/review-journey/orchestrate?dry_run=${dryRun}`, { method:'POST' });
      const d = await r.json();
      setOrchResult(d);
      if (!dryRun) load();  // refresh metrics
    } catch (e) { setOrchResult({ error: e.message }); }
    finally { setOrchestrating(false); }
  };

  if (loading) return <div style={{ color:'#6b7280', padding:24 }}>Loading overview…</div>;
  if (error)   return <div style={{ color:'#ef4444', padding:24 }}>Error: {error}</div>;
  const d = data || {};

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:24 }}>
      {/* Action buttons */}
      <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
        <button style={S.btn(true)} onClick={() => runOrchestrate(false)} disabled={orchestrating}>
          {orchestrating ? '⏳ Sending…' : '▶️ Run Journey Now'}
        </button>
        <button style={S.btn(false)} onClick={() => runOrchestrate(true)} disabled={orchestrating}>
          🧪 Dry Run
        </button>
        <button style={S.btn(false)} onClick={load}>🔄 Refresh</button>
      </div>

      {/* Orchestration result */}
      {orchResult && (
        <div style={{ ...S.card, borderLeft:`4px solid ${orchResult.error ? '#ef4444' : G}`, padding:'14px 18px' }}>
          {orchResult.error
            ? <span style={{ color:'#ef4444' }}>❌ {orchResult.error}</span>
            : <span style={{ color:G }}>✅ {orchResult.dry_run ? '[DRY RUN] ' : ''}Sent {orchResult.total_sent} messages</span>
          }
          {orchResult.stage_summary && (
            <div style={{ marginTop:8, display:'flex', gap:8, flexWrap:'wrap' }}>
              {Object.entries(orchResult.stage_summary).map(([stage, s]) => (
                <span key={stage} style={S.badge('#374151')}>
                  {stage}: {s.sent} sent / {s.suppressed} skipped
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* KPI cards */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))', gap:16 }}>
        <KpiCard label="Total Customers"    value={d.total_customers}       color="#374151" />
        <KpiCard label="Review Requests"    value={d.review_requests_sent}  color="#2563eb"
          sub={`${d.click_rate_pct}% click rate`} />
        <KpiCard label="Reviews Submitted"  value={d.reviews_submitted}     color={G}
          sub={`${d.review_rate_pct}% conversion`} />
        <KpiCard label="Cross-sell Sent"    value={d.crosssell_sent}        color="#d97706" />
        <KpiCard label="Replenishment Sent" value={d.replenishment_sent}    color="#7c3aed" />
        <KpiCard label="VIP Messages"       value={d.vip_sent}              color="#b45309" />
        <KpiCard label="Repeat Purchases"   value={d.repeat_purchases}      color="#059669"
          sub={`${d.repeat_purchase_rate_pct}% of customers`} />
      </div>

      {/* Status breakdown */}
      {d.status_breakdown && (
        <div style={S.card}>
          <div style={{ ...S.label, marginBottom:14 }}>Customer Status Breakdown</div>
          <div style={{ display:'flex', gap:12, flexWrap:'wrap' }}>
            {Object.entries(d.status_breakdown).map(([status, cnt]) => (
              <div key={status} style={{ textAlign:'center', minWidth:80 }}>
                <div style={{ fontSize:24 }}>{STATUS_ICON[status] || '❓'}</div>
                <div style={{ fontSize:20, fontWeight:700, color: STATUS_COLOR[status] || '#374151' }}>{cnt}</div>
                <div style={{ fontSize:11, color:'#9ca3af', textTransform:'capitalize' }}>{status}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Customers Tab
// ─────────────────────────────────────────────────────────────────────────────
function CustomersTab() {
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [page, setPage]         = useState(1);
  const [search, setSearch]     = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [reviewedFilter, setReviewedFilter] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [confirmReview, setConfirmReview] = useState({ open:false, customerId:'', rating:5 });
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    const params = new URLSearchParams({ page, per_page: 25 });
    if (search) params.set('search', search);
    if (statusFilter) params.set('status', statusFilter);
    if (reviewedFilter !== '') params.set('reviewed', reviewedFilter);
    try {
      const r = await fetch(`${API_BASE}/review-journey/customers?${params}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [page, search, statusFilter, reviewedFilter]);

  useEffect(() => { load(); }, [load]);

  const handleConfirmReview = async () => {
    setSubmitting(true);
    try {
      const r = await fetch(`${API_BASE}/review-journey/confirm-review`, {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ customer_id: confirmReview.customerId, rating: confirmReview.rating, channel:'google' }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setConfirmReview({ open:false, customerId:'', rating:5 });
      load();
    } catch (e) { alert('Error: ' + e.message); }
    finally { setSubmitting(false); }
  };

  const customers = data?.customers || [];
  const total     = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      {/* Filters */}
      <div style={{ display:'flex', gap:10, flexWrap:'wrap', alignItems:'center' }}>
        <input placeholder="Search name, phone, email…" value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          style={{ ...S.input, width:240 }} />
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          style={{ ...S.input, width:140 }}>
          <option value="">All statuses</option>
          <option value="cold">🥶 Cold</option>
          <option value="warm">🌤️ Warm</option>
          <option value="hot">🔥 Hot</option>
          <option value="purchased">💜 Purchased</option>
          <option value="vip">⭐ VIP</option>
        </select>
        <select value={reviewedFilter} onChange={e => { setReviewedFilter(e.target.value); setPage(1); }}
          style={{ ...S.input, width:160 }}>
          <option value="">All review status</option>
          <option value="true">✅ Reviewed</option>
          <option value="false">⏳ Not yet reviewed</option>
        </select>
        <button style={S.btn(false)} onClick={load}>🔄 Refresh</button>
        <span style={{ fontSize:12, color:'#9ca3af', marginLeft:'auto' }}>{total} customers</span>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ color:'#6b7280', padding:24 }}>Loading…</div>
      ) : error ? (
        <div style={{ color:'#ef4444' }}>Error: {error}</div>
      ) : (
        <div style={{ ...S.card, padding:0, overflow:'hidden' }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>
                {['Customer', 'Phone', 'Product', 'Status', 'Days Since Delivery',
                  'Review', 'Messages Sent', 'Order Value', 'Actions'].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {customers.length === 0 && (
                <tr><td colSpan={9} style={{ ...S.td, textAlign:'center', color:'#9ca3af' }}>No customers found</td></tr>
              )}
              {customers.map(c => (
                <tr key={c.id} style={{ cursor:'pointer' }} onClick={() => setSelectedCustomer(c)}>
                  <td style={S.td}>
                    <div style={{ fontWeight:600 }}>{c.name}</div>
                    <div style={{ fontSize:11, color:'#9ca3af' }}>{c.shopify_order_id}</div>
                  </td>
                  <td style={S.td}>{c.phone}</td>
                  <td style={S.td} title={c.purchased_product_name}>
                    <div style={{ maxWidth:140, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                      {c.purchased_product_name || '—'}
                    </div>
                  </td>
                  <td style={S.td}><StatusBadge status={c.customer_status} /></td>
                  <td style={{ ...S.td, textAlign:'center' }}>
                    {c.days_since_delivery != null ? (
                      <span style={{ fontWeight:700, color: c.days_since_delivery > 45 ? '#ef4444' : '#374151' }}>
                        Day {c.days_since_delivery}
                      </span>
                    ) : '—'}
                  </td>
                  <td style={S.td}>
                    {c.review_submitted_at
                      ? <span style={S.badge(G)}>✅ {c.review_rating ? `${c.review_rating}★` : 'Reviewed'}</span>
                      : c.day15_sent
                        ? <span style={S.badge('#f59e0b')}>⏳ Requested</span>
                        : <span style={S.badge('#9ca3af')}>—</span>
                    }
                  </td>
                  <td style={{ ...S.td, textAlign:'center' }}>
                    <div style={{ display:'flex', gap:3, flexWrap:'wrap' }}>
                      {c.day15_sent             && <span title="Day 15 sent" style={S.badge('#2563eb')}>15</span>}
                      {c.crosssell_day18_sent   && <span title="Day 18 sent" style={S.badge('#d97706')}>18</span>}
                      {c.replenishment_day45_sent && <span title="Day 45 sent" style={S.badge('#7c3aed')}>45</span>}
                      {c.vip_day75_sent         && <span title="Day 75 VIP" style={S.badge('#b45309')}>75</span>}
                    </div>
                  </td>
                  <td style={S.td}>₹{c.order_value_inr?.toLocaleString('en-IN') || '—'}</td>
                  <td style={S.td} onClick={e => e.stopPropagation()}>
                    {!c.review_submitted_at && (
                      <button style={{ ...S.btn(false), padding:'5px 10px', fontSize:11 }}
                        onClick={() => setConfirmReview({ open:true, customerId:c.id, rating:5 })}>
                        ✅ Mark Reviewed
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div style={{ display:'flex', gap:8, alignItems:'center', justifyContent:'center' }}>
        <button style={S.btn(false)} disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
        <span style={{ fontSize:13, color:'#374151' }}>Page {page} of {totalPages}</span>
        <button style={S.btn(false)} disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
      </div>

      {/* Confirm review modal */}
      {confirmReview.open && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,.4)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 }}>
          <div style={{ ...S.card, width:340, padding:28 }}>
            <h3 style={{ margin:'0 0 16px', fontSize:18 }}>Mark Review Submitted</h3>
            <label style={{ ...S.label, display:'block', marginBottom:6 }}>Star Rating</label>
            <select value={confirmReview.rating}
              onChange={e => setConfirmReview(r => ({ ...r, rating: parseInt(e.target.value) }))}
              style={{ ...S.input, marginBottom:20 }}>
              {[5,4,3,2,1].map(n => <option key={n} value={n}>{n} ⭐</option>)}
            </select>
            <div style={{ display:'flex', gap:10 }}>
              <button style={S.btn(true)} onClick={handleConfirmReview} disabled={submitting}>
                {submitting ? 'Saving…' : '✅ Confirm'}
              </button>
              <button style={S.btn(false)} onClick={() => setConfirmReview({ open:false, customerId:'', rating:5 })}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Customer detail side panel */}
      {selectedCustomer && (
        <CustomerDetailPanel
          customerId={selectedCustomer.id}
          onClose={() => setSelectedCustomer(null)}
          onRefresh={load}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Customer Detail Panel (side drawer)
// ─────────────────────────────────────────────────────────────────────────────
function CustomerDetailPanel({ customerId, onClose, onRefresh }) {
  const [data, setData]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/review-journey/customer/${customerId}`)
      .then(r => r.json())
      .then(d => setData(d))
      .finally(() => setLoading(false));
  }, [customerId]);

  const sendStage = async (stage) => {
    setSending(true); setSendResult(null);
    try {
      const r = await fetch(`${API_BASE}/review-journey/send-stage`, {
        method:'POST', headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ customer_id: customerId, stage }),
      });
      setSendResult(await r.json());
      if (r.ok) onRefresh();
    } catch (e) { setSendResult({ error: e.message }); }
    finally { setSending(false); }
  };

  const c = data?.customer;

  return (
    <div style={{ position:'fixed', top:0, right:0, bottom:0, width:420, background:'#fff',
      boxShadow:'-4px 0 20px rgba(0,0,0,.12)', zIndex:900, display:'flex', flexDirection:'column' }}>
      <div style={{ padding:'16px 20px', borderBottom:'1px solid #e5e7eb', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <h3 style={{ margin:0, fontSize:16, fontWeight:700 }}>Customer Detail</h3>
        <button onClick={onClose} style={{ background:'none', border:'none', cursor:'pointer', fontSize:20 }}>✕</button>
      </div>
      <div style={{ flex:1, overflowY:'auto', padding:'20px' }}>
        {loading ? <div style={{ color:'#9ca3af' }}>Loading…</div> : !c ? <div>Not found</div> : (
          <>
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:18, fontWeight:700 }}>{c.name}</div>
              <div style={{ fontSize:13, color:'#6b7280' }}>{c.phone} · {c.email || 'no email'}</div>
              <div style={{ marginTop:8, display:'flex', gap:8, flexWrap:'wrap' }}>
                <StatusBadge status={c.customer_status} />
                <span style={S.badge('#374151')}>Day {c.days_since_delivery ?? '?'}</span>
                <span style={S.badge('#374151')}>₹{Math.round((c.order_value_paise||0)/100)}</span>
              </div>
            </div>

            <div style={{ ...S.card, marginBottom:16, background:'#f8fafc' }}>
              <div style={{ ...S.label }}>Product</div>
              <div style={{ fontSize:14, fontWeight:600 }}>{c.purchased_product_name || '—'}</div>
              <div style={{ fontSize:12, color:'#9ca3af' }}>
                Delivered: {c.delivered_at ? new Date(c.delivered_at).toLocaleDateString('en-IN') : '—'}
              </div>
            </div>

            {/* Journey progress */}
            <div style={{ ...S.card, marginBottom:16, background:'#f8fafc' }}>
              <div style={{ ...S.label, marginBottom:10 }}>Journey Progress</div>
              {[
                { stage:'review_pure_day15',   flag:'day15_sent',             ts:'day15_sent_at',             label:'Day 15 Review Request' },
                { stage:'crosssell_day18',     flag:'crosssell_day18_sent',   ts:'crosssell_day18_sent_at',   label:'Day 18 Cross-sell/Thanks' },
                { stage:'replenishment_day45', flag:'replenishment_day45_sent',ts:'replenishment_day45_sent_at',label:'Day 45 Replenishment' },
                { stage:'vip_day75',           flag:'vip_day75_sent',          ts:'vip_day75_sent_at',          label:'Day 75 VIP' },
              ].map(row => (
                <div key={row.stage} style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
                  <span style={{ fontSize:16 }}>{c[row.flag] ? '✅' : '⬜'}</span>
                  <div style={{ flex:1 }}>
                    <div style={{ fontSize:13, fontWeight:c[row.flag] ? 600 : 400 }}>{row.label}</div>
                    {c[row.ts] && <div style={{ fontSize:11, color:'#9ca3af' }}>
                      {new Date(c[row.ts]).toLocaleDateString('en-IN')}
                    </div>}
                  </div>
                  {!c[row.flag] && (
                    <button style={{ ...S.btn(false), padding:'4px 10px', fontSize:11 }}
                      onClick={() => sendStage(row.stage)} disabled={sending}>
                      Send
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Review status */}
            <div style={{ ...S.card, marginBottom:16, background:'#f8fafc' }}>
              <div style={S.label}>Review Status</div>
              {c.review_submitted_at ? (
                <div>
                  <span style={S.badge(G)}>✅ Reviewed</span>
                  <div style={{ fontSize:12, color:'#6b7280', marginTop:4 }}>
                    {c.review_rating}★ · {c.review_submitted_channel} ·{' '}
                    {new Date(c.review_submitted_at).toLocaleDateString('en-IN')}
                  </div>
                  {c.review_text && <p style={{ fontSize:13, fontStyle:'italic', color:'#374151', marginTop:8 }}>
                    "{c.review_text.slice(0,200)}"
                  </p>}
                </div>
              ) : <span style={S.badge('#9ca3af')}>Not yet submitted</span>}
            </div>

            {sendResult && (
              <div style={{ padding:10, background: sendResult.error ? '#fef2f2' : '#f0fdf4',
                borderRadius:6, fontSize:13, marginBottom:12 }}>
                {sendResult.error ? `❌ ${sendResult.error}` : `✅ Sent: ${sendResult.template} (${sendResult.status})`}
              </div>
            )}

            {/* Message history */}
            {data.messages?.length > 0 && (
              <div>
                <div style={{ ...S.label, marginBottom:8 }}>Message History</div>
                {data.messages.map(m => (
                  <div key={m.id} style={{ padding:'10px 12px', background:'#f9fafb', borderRadius:6,
                    marginBottom:6, borderLeft:`3px solid ${m.delivery_status === 'sent' ? G : '#ef4444'}` }}>
                    <div style={{ display:'flex', justifyContent:'space-between' }}>
                      <StageLabel stage={m.journey_stage} />
                      <span style={{ fontSize:11, color:'#9ca3af' }}>
                        {m.sent_at ? new Date(m.sent_at).toLocaleDateString('en-IN') : ''}
                      </span>
                    </div>
                    <div style={{ fontSize:12, color:'#6b7280', marginTop:4 }}>
                      {m.template_name} · {m.channel}
                      {m.opened_at && ' · 👁️ Opened'}
                      {m.clicked_at && ' · 🖱️ Clicked'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Messages Tab
// ─────────────────────────────────────────────────────────────────────────────
function MessagesTab() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [page, setPage]       = useState(1);
  const [stageFilter, setStageFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    const params = new URLSearchParams({ page, per_page: 50 });
    if (stageFilter) params.set('stage', stageFilter);
    try {
      const r = await fetch(`${API_BASE}/review-journey/messages?${params}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [page, stageFilter]);

  useEffect(() => { load(); }, [load]);

  const messages  = data?.messages || [];
  const total     = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div style={{ display:'flex', gap:10, flexWrap:'wrap', alignItems:'center' }}>
        <select value={stageFilter} onChange={e => { setStageFilter(e.target.value); setPage(1); }}
          style={{ ...S.input, width:220 }}>
          <option value="">All stages</option>
          <option value="review_pure_day15">Day 15 Review Request</option>
          <option value="review_thanks_day18">Day 18 Thank You</option>
          <option value="crosssell_day18">Day 18 Cross-sell</option>
          <option value="replenishment_day45">Day 45 Replenishment</option>
          <option value="vip_day75">Day 75 VIP</option>
        </select>
        <button style={S.btn(false)} onClick={load}>🔄 Refresh</button>
        <span style={{ fontSize:12, color:'#9ca3af', marginLeft:'auto' }}>{total} messages</span>
      </div>

      {loading ? <div style={{ color:'#6b7280' }}>Loading…</div>
        : error ? <div style={{ color:'#ef4444' }}>Error: {error}</div>
        : (
        <div style={{ ...S.card, padding:0, overflow:'hidden' }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>
                {['Time', 'Customer', 'Stage', 'Template', 'Channel',
                  'Status', 'Opened', 'Clicked', 'Reviewed'].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {messages.length === 0 && (
                <tr><td colSpan={9} style={{ ...S.td, textAlign:'center', color:'#9ca3af' }}>No messages</td></tr>
              )}
              {messages.map(m => (
                <tr key={m.id}>
                  <td style={S.td}>
                    <div style={{ fontSize:12 }}>
                      {m.sent_at ? new Date(m.sent_at).toLocaleDateString('en-IN') : '—'}
                    </div>
                    <div style={{ fontSize:11, color:'#9ca3af' }}>
                      {m.sent_at ? new Date(m.sent_at).toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' }) : ''}
                    </div>
                  </td>
                  <td style={S.td}>
                    <div style={{ fontWeight:600 }}>{m.customer_name}</div>
                    <div style={{ fontSize:11, color:'#9ca3af' }}>{m.phone}</div>
                  </td>
                  <td style={S.td}><StageLabel stage={m.journey_stage} /></td>
                  <td style={{ ...S.td, fontSize:11 }}>{m.template_name}</td>
                  <td style={{ ...S.td, textAlign:'center' }}>
                    {m.channel === 'whatsapp'
                      ? <span title="WhatsApp">💬</span>
                      : <span title="Email">📧</span>}
                  </td>
                  <td style={S.td}>
                    <span style={S.badge(m.delivery_status === 'sent' ? G : '#ef4444')}>
                      {m.delivery_status}
                    </span>
                  </td>
                  <td style={{ ...S.td, textAlign:'center' }}>
                    {m.opened_at ? <span title={m.opened_at}>✅</span> : <span style={{ color:'#d1d5db' }}>—</span>}
                  </td>
                  <td style={{ ...S.td, textAlign:'center' }}>
                    {m.clicked_at ? <span title={m.clicked_at}>🖱️</span> : <span style={{ color:'#d1d5db' }}>—</span>}
                  </td>
                  <td style={{ ...S.td, textAlign:'center' }}>
                    {m.review_submitted_at ? <span>⭐</span> : <span style={{ color:'#d1d5db' }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display:'flex', gap:8, alignItems:'center', justifyContent:'center' }}>
        <button style={S.btn(false)} disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
        <span style={{ fontSize:13, color:'#374151' }}>Page {page} of {totalPages}</span>
        <button style={S.btn(false)} disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Analytics Tab
// ─────────────────────────────────────────────────────────────────────────────
function AnalyticsTab() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [days, setDays]       = useState(90);

  useEffect(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/review-journey/analytics?days=${days}`)
      .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
      .then(setData)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <div style={{ color:'#6b7280', padding:24 }}>Loading analytics…</div>;
  if (error)   return <div style={{ color:'#ef4444', padding:24 }}>Error: {error}</div>;
  const d = data || {};

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:24 }}>
      {/* Period selector */}
      <div style={{ display:'flex', gap:8 }}>
        {[30,60,90,180].map(n => (
          <button key={n} style={{ ...S.btn(days === n), padding:'6px 14px' }}
            onClick={() => setDays(n)}>{n}d</button>
        ))}
      </div>

      {/* Funnel */}
      {d.funnel?.length > 0 && (
        <div style={S.card}>
          <div style={{ ...S.label, marginBottom:16 }}>Conversion Funnel (Last {days} days)</div>
          <FunnelBar steps={d.funnel} />
        </div>
      )}

      {/* Status distribution + Rating distribution */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        {d.status_distribution?.length > 0 && (
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom:12 }}>Customer Status</div>
            {d.status_distribution.map(s => (
              <div key={s.status} style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
                <span style={{ width:20 }}>{STATUS_ICON[s.status] || '❓'}</span>
                <div style={{ flex:1, background:'#f3f4f6', borderRadius:3, height:20, position:'relative' }}>
                  <div style={{
                    width:`${(s.count / Math.max(...d.status_distribution.map(x => x.count), 1)) * 100}%`,
                    background: STATUS_COLOR[s.status] || '#374151',
                    borderRadius:3, height:'100%',
                  }} />
                </div>
                <span style={{ width:40, fontSize:13, fontWeight:700, textAlign:'right' }}>{s.count}</span>
              </div>
            ))}
          </div>
        )}

        {d.rating_distribution?.length > 0 && (
          <div style={S.card}>
            <div style={{ ...S.label, marginBottom:12 }}>Review Ratings</div>
            {[5,4,3,2,1].map(star => {
              const row = d.rating_distribution.find(r => r.rating === star) || { count: 0 };
              const maxCount = Math.max(...d.rating_distribution.map(r => r.count), 1);
              return (
                <div key={star} style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8 }}>
                  <span style={{ width:24, fontSize:13 }}>{star}⭐</span>
                  <div style={{ flex:1, background:'#f3f4f6', borderRadius:3, height:18 }}>
                    <div style={{
                      width:`${(row.count / maxCount) * 100}%`,
                      background:'#f59e0b', borderRadius:3, height:'100%',
                    }} />
                  </div>
                  <span style={{ width:30, fontSize:13, textAlign:'right' }}>{row.count}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Top products */}
      {d.top_products?.length > 0 && (
        <div style={S.card}>
          <div style={{ ...S.label, marginBottom:12 }}>Top Products Purchased</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
            {d.top_products.map(p => (
              <div key={p.product} style={S.badge(G)}>
                {p.product} <strong>({p.count})</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily messages chart (simple text table) */}
      {d.daily_messages?.length > 0 && (
        <div style={S.card}>
          <div style={{ ...S.label, marginBottom:12 }}>Daily Messages (Last 30 days)</div>
          <div style={{ overflowX:'auto' }}>
            <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
              <thead>
                <tr>
                  <th style={S.th}>Date</th>
                  <th style={S.th}>Day 15</th>
                  <th style={S.th}>Day 18</th>
                  <th style={S.th}>Day 45</th>
                  <th style={S.th}>Day 75</th>
                  <th style={S.th}>Total</th>
                </tr>
              </thead>
              <tbody>
                {d.daily_messages.slice(-14).map(row => {
                  const total = (row.review_pure_day15 || 0) +
                    (row.review_thanks_day18 || 0) + (row.crosssell_day18 || 0) +
                    (row.replenishment_day45 || 0) + (row.vip_day75 || 0);
                  return (
                    <tr key={row.date}>
                      <td style={S.td}>{row.date}</td>
                      <td style={{ ...S.td, textAlign:'center' }}>{row.review_pure_day15 || '—'}</td>
                      <td style={{ ...S.td, textAlign:'center' }}>
                        {(row.review_thanks_day18 || 0) + (row.crosssell_day18 || 0) || '—'}
                      </td>
                      <td style={{ ...S.td, textAlign:'center' }}>{row.replenishment_day45 || '—'}</td>
                      <td style={{ ...S.td, textAlign:'center' }}>{row.vip_day75 || '—'}</td>
                      <td style={{ ...S.td, textAlign:'center', fontWeight:700 }}>{total}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
