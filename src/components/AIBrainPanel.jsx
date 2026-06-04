import React, { useEffect, useState } from 'react';

const API = 'https://track.pureleven.com/api';
const secret = () => localStorage.getItem('anu_admin_secret') || '';
const api = (path, p = {}) => `${API}${path}?${new URLSearchParams({ admin_secret: secret(), ...p })}`;

export default function AIBrainPanel() {
  const [days, setDays] = useState(30);
  const [customerEmail, setCustomerEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [dashboard, setDashboard] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [error, setError] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [dashRes, decRes] = await Promise.all([
        fetch(api('/ai/performance-dashboard', { days })),
        fetch(api('/ai/decisions', { limit: 100, customer_email: customerEmail || undefined })),
      ]);
      const dash = await dashRes.json();
      const dec = await decRes.json();
      setDashboard(dash);
      setDecisions(dec.items || []);
    } catch (e) {
      setError(e.message || 'Failed to load AI metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [days]);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22 }}>🧠 AI Brain</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 13 }}>
            Explainable AI decisions, model outputs, and decision trail
          </p>
        </div>
        <button onClick={loadData} style={btn('#2563eb')} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={input(130)}>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
        <input
          type="email"
          placeholder="Filter by customer email"
          value={customerEmail}
          onChange={(e) => setCustomerEmail(e.target.value)}
          style={input(260)}
        />
        <button onClick={loadData} style={btn('#374151')}>Apply Filter</button>
      </div>

      {error && <div style={{ background: '#fee2e2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: 8, padding: 10, marginBottom: 12 }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 12, marginBottom: 16 }}>
        <Card title="AI Decisions (period)" value={Object.values(dashboard?.ai_decisions || {}).reduce((acc, bySource) => acc + Object.values(bySource).reduce((a, b) => a + b, 0), 0)} />
        <Card title="Cache Entries" value={dashboard?.cache_stats?.total ?? 0} />
        <Card title="Active Cache" value={dashboard?.cache_stats?.active ?? 0} />
        <Card title="Expired Cache" value={dashboard?.cache_stats?.expired ?? 0} />
      </div>

      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 14, marginBottom: 16 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>AI Decision Types</h3>
        {dashboard?.ai_decisions && Object.keys(dashboard.ai_decisions).length > 0 ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {Object.entries(dashboard.ai_decisions).map(([type, sources]) => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f3f4f6', paddingBottom: 6 }}>
                <strong style={{ fontSize: 13 }}>{type}</strong>
                <span style={{ fontSize: 12, color: '#6b7280' }}>
                  {Object.entries(sources).map(([src, count]) => `${src}: ${count}`).join(' | ')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: '#9ca3af', fontSize: 13 }}>No decisions in selected range</div>
        )}
      </div>

      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', fontWeight: 600, fontSize: 14 }}>Per-Customer AI Decision Log</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#f9fafb' }}>
              <th style={th}>Time</th>
              <th style={th}>Decision</th>
              <th style={th}>Customer</th>
              <th style={th}>Source</th>
              <th style={th}>Output</th>
            </tr>
          </thead>
          <tbody>
            {decisions.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: 22, textAlign: 'center', color: '#9ca3af' }}>No decision logs found</td></tr>
            ) : decisions.map(d => (
              <tr key={d.id} style={{ borderTop: '1px solid #f3f4f6' }}>
                <td style={td}>{d.created_at ? new Date(d.created_at).toLocaleString('en-IN') : '-'}</td>
                <td style={td}><strong>{d.decision_type}</strong></td>
                <td style={td}>{d.customer_id}</td>
                <td style={td}>{d.source}</td>
                <td style={td}><pre style={{ margin: 0, whiteSpace: 'pre-wrap', maxWidth: 460 }}>{JSON.stringify(d.ai_output || {}, null, 0)}</pre></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Card({ title, value }) {
  return (
    <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 12 }}>
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#111827' }}>{value ?? 0}</div>
    </div>
  );
}

const th = { textAlign: 'left', padding: '8px 10px', fontSize: 11, color: '#6b7280', fontWeight: 700 };
const td = { textAlign: 'left', padding: '8px 10px', color: '#111827', verticalAlign: 'top' };
const btn = (bg) => ({ background: bg, color: 'white', border: 'none', borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 });
const input = (w) => ({ width: w, border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 10px', fontSize: 12 });
