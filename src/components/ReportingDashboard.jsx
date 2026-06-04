import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'https://track.pureleven.com/api';

const TABS = ['Summary', 'Campaigns', 'Cohorts', 'CLV'];

const fmt = (n) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n || 0);
const fmtCur = (n) => `₹${fmt(n)}`;
const fmtPct = (n) => `${(n || 0).toFixed(1)}%`;

const KPICard = ({ label, value, sub, color = '#3b82f6' }) => (
  <div style={{
    background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
    padding: '20px 24px', boxShadow: '0 1px 3px rgba(0,0,0,.07)',
  }}>
    <div style={{ fontSize: 12, color: '#6b7280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: .5 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color, margin: '6px 0 2px' }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: '#9ca3af' }}>{sub}</div>}
  </div>
);

const Badge = ({ label, color = '#6366f1' }) => (
  <span style={{
    display: 'inline-block', padding: '2px 10px', borderRadius: 20,
    fontSize: 11, fontWeight: 600, background: color + '22', color,
  }}>{label}</span>
);

export default function ReportingDashboard() {
  const [activeTab, setActiveTab] = useState('Summary');
  const [days, setDays] = useState(30);
  const [model, setModel] = useState('last_touch');

  const [summary, setSummary] = useState(null);
  const [roi, setRoi] = useState(null);
  const [cohorts, setCohorts] = useState(null);
  const [clv, setClv] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const shopDomain = 'rwxtic-gz.myshopify.com';

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'Summary') {
        const [sumRes, roiRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/summary?shop_domain=${shopDomain}&days=${days}`),
          fetch(`${API_BASE}/analytics/roi?shop_domain=${shopDomain}&days=${days}&model=${model}`),
        ]);
        setSummary(await sumRes.json());
        setRoi(await roiRes.json());
      } else if (activeTab === 'Campaigns') {
        const res = await fetch(`${API_BASE}/analytics/roi?shop_domain=${shopDomain}&days=${days}&model=${model}`);
        setRoi(await res.json());
      } else if (activeTab === 'Cohorts') {
        const res = await fetch(`${API_BASE}/analytics/cohorts?shop_domain=${shopDomain}&cohort_weeks=8`);
        setCohorts(await res.json());
      } else if (activeTab === 'CLV') {
        const res = await fetch(`${API_BASE}/analytics/clv?shop_domain=${shopDomain}&top_n=100`);
        setClv(await res.json());
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [activeTab, days, model]);

  useEffect(() => { load(); }, [load]);

  const s = {
    wrap: { padding: 28, background: '#f8fafc', minHeight: '100vh', fontFamily: 'system-ui,sans-serif' },
    hdr: { marginBottom: 24 },
    h1: { fontSize: 26, fontWeight: 700, color: '#111827', margin: '0 0 4px' },
    sub: { fontSize: 13, color: '#6b7280', margin: 0 },
    tabs: { display: 'flex', gap: 4, marginBottom: 24, borderBottom: '2px solid #e5e7eb', paddingBottom: 0 },
    tab: (active) => ({
      padding: '8px 18px', border: 'none', background: 'none', cursor: 'pointer',
      fontSize: 14, fontWeight: 600, color: active ? '#6366f1' : '#6b7280',
      borderBottom: active ? '2px solid #6366f1' : '2px solid transparent',
      marginBottom: -2,
    }),
    controls: { display: 'flex', gap: 12, alignItems: 'center', marginBottom: 24, flexWrap: 'wrap' },
    select: {
      padding: '6px 12px', border: '1px solid #d1d5db', borderRadius: 6,
      fontSize: 13, background: '#fff', color: '#374151',
    },
    grid4: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 16, marginBottom: 28 },
    table: { width: '100%', borderCollapse: 'collapse' },
    th: { textAlign: 'left', padding: '10px 14px', background: '#f3f4f6', fontSize: 12, fontWeight: 700, color: '#374151', borderBottom: '2px solid #e5e7eb' },
    td: { padding: '10px 14px', borderBottom: '1px solid #f3f4f6', fontSize: 13, color: '#374151', verticalAlign: 'middle' },
    card: { background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,.07)', marginBottom: 20 },
    empty: { textAlign: 'center', padding: 48, color: '#9ca3af', fontSize: 14 },
    err: { background: '#fee2e2', border: '1px solid #fecaca', borderRadius: 8, padding: 16, color: '#991b1b', fontSize: 13 },
  };

  const modelLabels = { last_touch: 'Last Touch', first_touch: 'First Touch', linear: 'Linear', time_decay: 'Time Decay' };

  return (
    <div style={s.wrap}>
      <div style={s.hdr}>
        <h1 style={s.h1}>📊 Reporting & ROI</h1>
        <p style={s.sub}>Campaign attribution, cohort retention, and customer lifetime value</p>
      </div>

      {/* Tabs */}
      <div style={s.tabs}>
        {TABS.map(t => (
          <button key={t} style={s.tab(activeTab === t)} onClick={() => setActiveTab(t)}>{t}</button>
        ))}
      </div>

      {/* Controls */}
      <div style={s.controls}>
        {(activeTab === 'Summary' || activeTab === 'Campaigns') && (
          <>
            <select style={s.select} value={days} onChange={e => setDays(+e.target.value)}>
              {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>Last {d} days</option>)}
            </select>
            <select style={s.select} value={model} onChange={e => setModel(e.target.value)}>
              {Object.entries(modelLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <button onClick={load} style={{ padding: '6px 14px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              {loading ? '...' : '↻ Refresh'}
            </button>
          </>
        )}
      </div>

      {error && <div style={s.err}>⚠️ {error}</div>}
      {loading && !error && <div style={s.empty}>Loading...</div>}

      {/* ── Summary Tab ── */}
      {!loading && activeTab === 'Summary' && (
        <>
          <div style={s.grid4}>
            <KPICard label="Total Revenue" value={fmtCur(summary?.purchase_revenue)} sub={`${summary?.purchase_count || 0} orders`} color="#059669" />
            <KPICard label="Attributed Revenue" value={fmtCur(roi?.total_attributed_revenue)} sub={`${modelLabels[model]} model`} color="#6366f1" />
            <KPICard label="Add to Cart" value={fmt(summary?.add_to_cart)} sub={`Checkout rate: ${fmtPct(summary?.checkout_rate)}`} />
            <KPICard label="Purchase Rate" value={fmtPct(summary?.purchase_rate)} sub={`${summary?.unique_sessions || 0} sessions`} />
          </div>

          {/* Attribution banner */}
          {roi?.campaigns?.length > 0 && (
            <div style={s.card}>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16, color: '#374151' }}>Top Campaigns by Attributed Revenue</div>
              <table style={s.table}>
                <thead>
                  <tr>
                    {['Campaign', 'Orders', 'Attributed Revenue', 'ROI%'].map(h => <th key={h} style={s.th}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {roi.campaigns.slice(0, 5).map((c, i) => (
                    <tr key={i}>
                      <td style={s.td}>{c.campaign_name || c.campaign_id?.slice(0, 8)}</td>
                      <td style={s.td}>{c.orders || 0}</td>
                      <td style={s.td}>{fmtCur(c.total_attributed)}</td>
                      <td style={s.td}><Badge label={`${c.roi_pct || 0}%`} color={c.roi_pct >= 100 ? '#059669' : '#f59e0b'} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── Campaigns Tab ── */}
      {!loading && activeTab === 'Campaigns' && (
        <div style={s.card}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16, color: '#374151' }}>
            Campaign ROI — {modelLabels[model]} Attribution
          </div>
          {(!roi?.campaigns || roi.campaigns.length === 0) ? (
            <div style={s.empty}>No attribution data for this period. Run a campaign and track purchases to see ROI.</div>
          ) : (
            <table style={s.table}>
              <thead>
                <tr>
                  {['Campaign', 'Sent', 'Open Rate', 'Click Rate', 'Orders', 'Customers', 'Attributed Rev', 'Avg Days', 'ROI'].map(h => (
                    <th key={h} style={s.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {roi.campaigns.map((c, i) => (
                  <tr key={i} style={{ background: i % 2 === 0 ? '#fafafa' : '#fff' }}>
                    <td style={s.td}><strong>{c.campaign_name || '—'}</strong><br /><span style={{ fontSize: 11, color: '#9ca3af' }}>{c.campaign_id?.slice(0, 8)}</span></td>
                    <td style={s.td}>{fmt(c.total_sent)}</td>
                    <td style={s.td}>{fmtPct(c.open_rate)}</td>
                    <td style={s.td}>{fmtPct(c.click_rate)}</td>
                    <td style={s.td}>{c.orders || 0}</td>
                    <td style={s.td}>{c.customers || 0}</td>
                    <td style={s.td}><strong>{fmtCur(c.total_attributed)}</strong></td>
                    <td style={s.td}>{c.avg_days_to_convert ? `${Math.round(c.avg_days_to_convert)}d` : '—'}</td>
                    <td style={s.td}><Badge label={`${c.roi_pct || 0}%`} color={c.roi_pct >= 100 ? '#059669' : c.roi_pct >= 50 ? '#f59e0b' : '#ef4444'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Cohorts Tab ── */}
      {!loading && activeTab === 'Cohorts' && (
        <div style={s.card}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4, color: '#374151' }}>Weekly Cohort Retention</div>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 16 }}>% of cohort that purchased again in subsequent weeks</div>
          {(!cohorts?.cohorts || cohorts.cohorts.length === 0) ? (
            <div style={s.empty}>No cohort data yet. Purchase events needed to build retention curves.</div>
          ) : (
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}>Cohort</th>
                  <th style={s.th}>Size</th>
                  {[0, 1, 2, 3, 4].map(w => <th key={w} style={s.th}>Week {w}</th>)}
                </tr>
              </thead>
              <tbody>
                {cohorts.cohorts.map((c, i) => (
                  <tr key={i}>
                    <td style={s.td}>{c.cohort_week}</td>
                    <td style={s.td}>{c.size}</td>
                    {[0, 1, 2, 3, 4].map(w => {
                      const pct = c[`week_${w}`] || 0;
                      const bg = pct >= 50 ? '#dcfce7' : pct >= 20 ? '#fef3c7' : pct > 0 ? '#fee2e2' : '#f9fafb';
                      return (
                        <td key={w} style={{ ...s.td, background: bg, textAlign: 'center' }}>
                          {pct > 0 ? `${pct}%` : '—'}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── CLV Tab ── */}
      {!loading && activeTab === 'CLV' && (
        <>
          <div style={s.grid4}>
            <KPICard label="Total Revenue (Top 100)" value={fmtCur(clv?.total_revenue)} sub={`${clv?.customer_count || 0} customers`} color="#059669" />
            <KPICard label="Average LTV" value={fmtCur(clv?.avg_ltv)} sub="Per top customer" color="#6366f1" />
          </div>
          <div style={s.card}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16 }}>Top Customers by Lifetime Revenue</div>
            {(!clv?.customers || clv.customers.length === 0) ? (
              <div style={s.empty}>No purchase data available.</div>
            ) : (
              <table style={s.table}>
                <thead>
                  <tr>
                    {['#', 'Customer', 'Orders', 'Total Revenue', 'First Purchase', 'Last Purchase'].map(h => (
                      <th key={h} style={s.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {clv.customers.map((c, i) => (
                    <tr key={i} style={{ background: i % 2 === 0 ? '#fafafa' : '#fff' }}>
                      <td style={{ ...s.td, color: '#9ca3af' }}>{i + 1}</td>
                      <td style={s.td}>{c.email || c.cid}</td>
                      <td style={s.td}>{c.purchase_count}</td>
                      <td style={s.td}><strong>{fmtCur(c.total_revenue)}</strong></td>
                      <td style={s.td}>{c.first_purchase ? new Date(c.first_purchase).toLocaleDateString('en-IN') : '—'}</td>
                      <td style={s.td}>{c.last_purchase ? new Date(c.last_purchase).toLocaleDateString('en-IN') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
