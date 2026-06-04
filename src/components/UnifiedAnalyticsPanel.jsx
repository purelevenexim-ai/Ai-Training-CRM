/**
 * UnifiedAnalyticsPanel.jsx — Phase 3
 * Unified Email + WhatsApp performance analytics
 */
import React, { useState, useEffect, useCallback } from 'react';

const API = 'https://track.pureleven.com/api';
const secret = () => localStorage.getItem('anu_admin_secret') || '';
const api = (path, p = {}) => `${API}${path}?${new URLSearchParams({ admin_secret: secret(), ...p })}`;

export default function UnifiedAnalyticsPanel() {
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [journeys, setJourneys] = useState([]);
  const [campStats, setCampStats] = useState({});
  const [jourStats, setJourStats] = useState({});
  const [activeTab, setActiveTab] = useState('overview');

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(api('/comm/stats/overview', { days }));
      if (!res.ok) throw new Error('Stats unavailable');
      setOverview(await res.json());
    } catch (e) { setError(e.message); }
    setLoading(false);
  }, [days]);

  const loadCampaigns = useCallback(async () => {
    try {
      const res = await fetch(api('/campaigns', { limit: 20 }));
      const data = await res.json();
      const list = data.items || [];
      setCampaigns(list);
      // Fetch stats for each
      const statsMap = {};
      await Promise.all(list.slice(0, 10).map(async c => {
        try {
          const r = await fetch(api(`/campaigns/${c.id}/stats`));
          statsMap[c.id] = await r.json();
        } catch {}
      }));
      setCampStats(statsMap);
    } catch {}
  }, []);

  const loadJourneys = useCallback(async () => {
    try {
      const res = await fetch(api('/journeys', { limit: 20 }));
      const data = await res.json();
      const list = data.items || data || [];
      setJourneys(list);
      const statsMap = {};
      await Promise.all(list.slice(0, 10).map(async j => {
        try {
          const r = await fetch(api(`/journeys/${j.id}/stats`));
          statsMap[j.id] = await r.json();
        } catch {}
      }));
      setJourStats(statsMap);
    } catch {}
  }, []);

  useEffect(() => { loadOverview(); }, [loadOverview]);
  useEffect(() => { if (activeTab === 'campaigns') loadCampaigns(); }, [activeTab, loadCampaigns]);
  useEffect(() => { if (activeTab === 'journeys') loadJourneys(); }, [activeTab, loadJourneys]);

  const tabs = [
    { id: 'overview', label: '📊 Overview' },
    { id: 'campaigns', label: '📢 Campaigns' },
    { id: 'journeys', label: '🗺️ Journeys' },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>📈 Communications Analytics</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 14 }}>Unified Email + WhatsApp performance</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, color: '#6b7280' }}>Last</span>
          {[7, 14, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              style={{ padding: '6px 14px', borderRadius: 20, fontSize: 13, fontWeight: 600, border: '1px solid',
                background: days === d ? '#1d4ed8' : 'white', color: days === d ? 'white' : '#374151',
                borderColor: days === d ? '#1d4ed8' : '#d1d5db', cursor: 'pointer' }}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #e5e7eb', paddingBottom: 0 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{ padding: '8px 18px', fontSize: 14, fontWeight: activeTab === t.id ? 700 : 500,
              background: 'none', border: 'none', borderBottom: activeTab === t.id ? '3px solid #3b82f6' : '3px solid transparent',
              color: activeTab === t.id ? '#1d4ed8' : '#6b7280', cursor: 'pointer', marginBottom: -1 }}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>}

      {/* ── Overview ── */}
      {activeTab === 'overview' && (
        loading ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>Loading analytics…</div> :
        overview ? (
          <div>
            {/* Email KPIs */}
            <SectionTitle>📧 Email ({days}d)</SectionTitle>
            <div style={kpiGrid}>
              <KpiCard label="Sent" value={overview.email.sent} color="#3b82f6" />
              <KpiCard label="Opened" value={overview.email.opened} color="#10b981" sub={`${overview.email.open_rate}% rate`} />
              <KpiCard label="Clicked" value={overview.email.clicked} color="#8b5cf6" sub={`${overview.email.click_rate}% rate`} />
              <KpiCard label="Bounced" value={overview.email.bounced} color="#ef4444" />
              <KpiCard label="Unsubs" value={overview.email.unsubscribed} color="#f59e0b" />
            </div>

            {/* WhatsApp KPIs */}
            <SectionTitle style={{ marginTop: 28 }}>💬 WhatsApp ({days}d)</SectionTitle>
            <div style={kpiGrid}>
              <KpiCard label="Sent" value={overview.whatsapp.sent} color="#25d366" />
              <KpiCard label="Delivered" value={overview.whatsapp.delivered} color="#10b981" sub={`${overview.whatsapp.delivery_rate}% rate`} />
              <KpiCard label="Read" value={overview.whatsapp.read} color="#0ea5e9" sub={`${overview.whatsapp.read_rate}% rate`} />
              <KpiCard label="Replied" value={overview.whatsapp.replied} color="#8b5cf6" />
              <KpiCard label="Failed" value={overview.whatsapp.failed} color="#ef4444" />
            </div>

            {/* Engagement Funnel */}
            <SectionTitle style={{ marginTop: 28 }}>🔻 Email Engagement Funnel</SectionTitle>
            <FunnelChart data={[
              { label: 'Sent', value: overview.email.sent, color: '#3b82f6' },
              { label: 'Opened', value: overview.email.opened, color: '#10b981' },
              { label: 'Clicked', value: overview.email.clicked, color: '#8b5cf6' },
            ]} />
          </div>
        ) : (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: 40 }}>No data available for this period</div>
        )
      )}

      {/* ── Campaigns ── */}
      {activeTab === 'campaigns' && (
        <div>
          <SectionTitle>Campaigns Performance</SectionTitle>
          {campaigns.length === 0 ? (
            <div style={{ color: '#9ca3af', padding: 40, textAlign: 'center' }}>No campaigns yet</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  {['Campaign', 'Channel', 'Status', 'Recipients', 'Sent', 'Opened', 'Clicked', 'Open Rate', 'Click Rate'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {campaigns.map(c => {
                  const s = campStats[c.id] || {};
                  return (
                    <tr key={c.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>{c.name}</td>
                      <td style={{ padding: '10px 12px' }}>{c.type}</td>
                      <td style={{ padding: '10px 12px' }}><StatusDot s={c.status} /></td>
                      <td style={{ padding: '10px 12px' }}>{s.total_recipients ?? c.total_recipients ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>{s.sent ?? c.sent_count ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>{s.opened ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>{s.clicked ?? '—'}</td>
                      <td style={{ padding: '10px 12px', color: '#10b981', fontWeight: 600 }}>{s.open_rate != null ? `${s.open_rate}%` : '—'}</td>
                      <td style={{ padding: '10px 12px', color: '#8b5cf6', fontWeight: 600 }}>{s.click_rate != null ? `${s.click_rate}%` : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Journeys ── */}
      {activeTab === 'journeys' && (
        <div>
          <SectionTitle>Journey Performance</SectionTitle>
          {journeys.length === 0 ? (
            <div style={{ color: '#9ca3af', padding: 40, textAlign: 'center' }}>No journeys yet</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  {['Journey', 'Trigger', 'Status', 'Enrolled', 'Completed', 'Email Sent', 'WA Sent', 'Open Rate', 'Read Rate'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {journeys.map(j => {
                  const s = jourStats[j.id] || {};
                  return (
                    <tr key={j.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>{j.name}</td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: '#6b7280' }}>{j.trigger_event}</td>
                      <td style={{ padding: '10px 12px' }}><StatusDot s={j.status} /></td>
                      <td style={{ padding: '10px 12px' }}>{s.enrolled ?? j.enrolled_count ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>{s.completed ?? j.completed_count ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>{s.email_sent ?? s.total_sent ?? '—'}</td>
                      <td style={{ padding: '10px 12px' }}>{s.wa_sent ?? '—'}</td>
                      <td style={{ padding: '10px 12px', color: '#10b981', fontWeight: 600 }}>{s.email_open_rate != null ? `${s.email_open_rate}%` : '—'}</td>
                      <td style={{ padding: '10px 12px', color: '#0ea5e9', fontWeight: 600 }}>{s.wa_read_rate != null ? `${s.wa_read_rate}%` : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function SectionTitle({ children, style }) {
  return <h3 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 700, color: '#111827', ...style }}>{children}</h3>;
}

function KpiCard({ label, value, color, sub }) {
  return (
    <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 20px' }}>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{(value || 0).toLocaleString()}</div>
      <div style={{ fontSize: 13, color: '#374151', fontWeight: 600, marginTop: 4 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function FunnelChart({ data }) {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 20 }}>
      {data.map((d, i) => (
        <div key={d.label} style={{ marginBottom: i < data.length - 1 ? 12 : 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13, color: '#374151' }}>
            <span>{d.label}</span>
            <span style={{ fontWeight: 700 }}>{(d.value || 0).toLocaleString()}</span>
          </div>
          <div style={{ background: '#f3f4f6', borderRadius: 4, height: 20, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(d.value / max) * 100}%`, background: d.color, borderRadius: 4, transition: 'width 0.5s ease' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

const STATUS_COLORS = { active: '#10b981', draft: '#9ca3af', paused: '#f59e0b', completed: '#3b82f6', failed: '#ef4444' };
function StatusDot({ s }) {
  return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, fontWeight: 600, color: STATUS_COLORS[s] || '#9ca3af' }}>
    <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS[s] || '#9ca3af', display: 'inline-block' }} />
    {s}
  </span>;
}

const kpiGrid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
  gap: 12,
};
