import React, { useEffect, useMemo, useState } from 'react';
import crmApi from '../utils/crmApi';

const DESTINATIONS = ['meta', 'google', 'ga4'];

export default function TrackingAttributionPanel() {
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const summary = health?.summary || { total: 0, sent: 0, failed: 0, skipped: 0 };

  const sentRate = useMemo(() => {
    if (!summary.total) return 0;
    return Math.round((summary.sent / summary.total) * 100);
  }, [summary]);

  async function loadData() {
    setLoading(true);
    setError('');
    try {
      const [h, a, e] = await Promise.all([
        crmApi.getTrackingHealth(24),
        crmApi.getTrackingAlerts(6),
        crmApi.getTrackingEvents({ limit: 100, status: statusFilter || undefined }),
      ]);
      setHealth(h);
      setAlerts(a);
      setEvents(e.items || []);
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  async function retryRecent() {
    setLoading(true);
    setError('');
    try {
      await crmApi.retryTracking(['failed', 'skipped'], DESTINATIONS, 72, 50);
      await loadData();
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setLoading(false);
    }
  }

  async function replayOrder(orderId) {
    setLoading(true);
    setError('');
    try {
      await crmApi.replayTrackingOrder(orderId, DESTINATIONS, true);
      await loadData();
    } catch (err) {
      setError(String(err?.message || err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: '24px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, color: '#1f2937' }}>Tracking and Attribution Center</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280' }}>Server-side conversion reliability, skips, retries, and alerts.</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={retryRecent} disabled={loading} style={btnPrimary}>Retry Failed and Skipped</button>
          <button onClick={loadData} disabled={loading} style={btnSecondary}>Refresh</button>
        </div>
      </div>

      {alerts?.severity && alerts.severity !== 'ok' && (
        <div style={{ marginBottom: 14, padding: 12, borderRadius: 8, background: '#fff7ed', border: '1px solid #fdba74' }}>
          <strong style={{ color: '#9a3412' }}>Alert: {alerts.severity.toUpperCase()}</strong>
          <ul style={{ margin: '6px 0 0 18px', color: '#7c2d12' }}>
            {(alerts.alerts || []).map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}

      {error && (
        <div style={{ marginBottom: 14, padding: 10, borderRadius: 8, background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(120px, 1fr))', gap: 12, marginBottom: 16 }}>
        <Card label='Total Events' value={summary.total} tone='#0f172a' />
        <Card label='Sent' value={summary.sent} tone='#166534' />
        <Card label='Failed' value={summary.failed} tone='#991b1b' />
        <Card label='Skipped' value={summary.skipped} tone='#92400e' />
        <Card label='Sent Rate' value={`${sentRate}%`} tone='#1d4ed8' />
      </div>

      <div style={{ marginBottom: 10, display: 'flex', gap: 10, alignItems: 'center' }}>
        <label style={{ color: '#374151', fontWeight: 600 }}>Status filter</label>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={selectStyle}>
          <option value=''>All</option>
          <option value='sent'>Sent</option>
          <option value='failed'>Failed</option>
          <option value='skipped'>Skipped</option>
        </select>
      </div>

      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f9fafb', color: '#374151', textAlign: 'left' }}>
              <th style={th}>Time</th>
              <th style={th}>Order</th>
              <th style={th}>Destination</th>
              <th style={th}>Status</th>
              <th style={th}>Error</th>
              <th style={th}>Action</th>
            </tr>
          </thead>
          <tbody>
            {events.slice(0, 100).map((row) => (
              <tr key={`${row.order_id}-${row.destination}-${row.created_at}`} style={{ borderTop: '1px solid #f3f4f6' }}>
                <td style={td}>{row.created_at ? new Date(row.created_at).toLocaleString() : '-'}</td>
                <td style={td}>{row.order_id}</td>
                <td style={td}>{row.destination}</td>
                <td style={td}>{row.status}</td>
                <td style={td}>{row.error || '-'}</td>
                <td style={td}>
                  {(row.status === 'failed' || row.status === 'skipped') ? (
                    <button style={btnTiny} disabled={loading} onClick={() => replayOrder(row.order_id)}>Replay</button>
                  ) : '—'}
                </td>
              </tr>
            ))}
            {!events.length && !loading && (
              <tr>
                <td style={{ ...td, textAlign: 'center', color: '#6b7280' }} colSpan={6}>No tracking events found for current filter.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Card({ label, value, tone }) {
  return (
    <div style={{ background: 'white', border: '1px solid #e5e7eb', borderLeft: `4px solid ${tone}`, borderRadius: 8, padding: 12 }}>
      <div style={{ color: '#6b7280', fontSize: 12, fontWeight: 600 }}>{label}</div>
      <div style={{ color: '#111827', fontSize: 22, fontWeight: 800 }}>{value}</div>
    </div>
  );
}

const th = { padding: '10px 12px', fontSize: 12, fontWeight: 700 };
const td = { padding: '10px 12px', fontSize: 12, color: '#1f2937', verticalAlign: 'top' };
const selectStyle = { border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 8px', background: 'white' };
const btnPrimary = { background: '#111827', color: 'white', border: '1px solid #111827', borderRadius: 6, padding: '8px 11px', cursor: 'pointer', fontWeight: 700 };
const btnSecondary = { background: 'white', color: '#374151', border: '1px solid #d1d5db', borderRadius: 6, padding: '8px 11px', cursor: 'pointer', fontWeight: 700 };
const btnTiny = { background: '#111827', color: 'white', border: '1px solid #111827', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 11, fontWeight: 700 };