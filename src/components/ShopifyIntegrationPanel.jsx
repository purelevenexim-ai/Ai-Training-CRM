/**
 * ShopifyIntegrationPanel.jsx — Phase 5
 * Shopify customer + order sync dashboard
 * - View sync log
 * - Trigger historical backfill
 * - Configure Shopify webhook endpoints
 */
import React, { useState, useEffect, useCallback } from 'react';

const API = 'https://track.pureleven.com/api';
const secret = () => localStorage.getItem('anu_admin_secret') || '';
const api = (path, p = {}) => `${API}${path}?${new URLSearchParams({ admin_secret: secret(), ...p })}`;

const WEBHOOK_ENDPOINTS = [
  { event: 'customers/create', url: `${API}/shopify/webhooks/customers/create`, desc: 'New customer → unified profile' },
  { event: 'customers/update', url: `${API}/shopify/webhooks/customers/update`, desc: 'Customer update → sync profile' },
  { event: 'orders/create',    url: `${API}/shopify/webhooks/orders/create`,    desc: 'New order → sync + enroll journey' },
  { event: 'orders/fulfilled', url: `${API}/shopify/webhooks/orders/fulfilled`, desc: 'Fulfilled → trigger delivery journey' },
];

export default function ShopifyIntegrationPanel() {
  const [syncLog, setSyncLog] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const [logError, setLogError] = useState(null);

  // Backfill form
  const [shopUrl, setShopUrl] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [backfillDays, setBackfillDays] = useState(90);
  const [backfilling, setBackfilling] = useState({ customers: false, orders: false });
  const [backfillResult, setBackfillResult] = useState({ customers: null, orders: null });

  const [activeTab, setActiveTab] = useState('webhooks');

  const loadLog = useCallback(async () => {
    setLogLoading(true);
    setLogError(null);
    try {
      const res = await fetch(api('/shopify/sync/log', { limit: 100 }));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSyncLog(Array.isArray(data) ? data : []);
    } catch (e) { setLogError(e.message); }
    setLogLoading(false);
  }, []);

  useEffect(() => { if (activeTab === 'log') loadLog(); }, [activeTab, loadLog]);

  const runBackfill = async (type) => {
    if (!shopUrl || !accessToken) {
      alert('Enter Shopify store URL and access token first.');
      return;
    }
    setBackfilling(b => ({ ...b, [type]: true }));
    setBackfillResult(r => ({ ...r, [type]: null }));
    try {
      const res = await fetch(`${API}/shopify/backfill/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          admin_secret: secret(),
          shop_url: shopUrl,
          access_token: accessToken,
          ...(type === 'orders' ? { days: backfillDays } : {}),
        }),
      });
      const data = await res.json();
      setBackfillResult(r => ({ ...r, [type]: data }));
    } catch (e) {
      setBackfillResult(r => ({ ...r, [type]: { error: e.message } }));
    }
    setBackfilling(b => ({ ...b, [type]: false }));
  };

  const tabs = [
    { id: 'webhooks', label: '🔗 Webhooks' },
    { id: 'backfill', label: '🔄 Backfill' },
    { id: 'log', label: '📋 Sync Log' },
  ];

  const statusColor = { ok: '#10b981', error: '#ef4444', skipped: '#f59e0b' };

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>🛍️ Shopify Integration</h2>
        <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 14 }}>Real-time customer & order sync, historical backfill</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid #e5e7eb', marginBottom: 24 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{ padding: '8px 18px', fontSize: 14, fontWeight: activeTab === t.id ? 700 : 500,
              background: 'none', border: 'none', borderBottom: activeTab === t.id ? '3px solid #3b82f6' : '3px solid transparent',
              color: activeTab === t.id ? '#1d4ed8' : '#6b7280', cursor: 'pointer', marginBottom: -1 }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Webhooks Tab ── */}
      {activeTab === 'webhooks' && (
        <div>
          <p style={{ color: '#374151', marginBottom: 16, fontSize: 14 }}>
            Register these URLs in your Shopify Admin → Settings → Notifications → Webhooks.
            Use <strong>API version 2024-01</strong> and format <strong>JSON</strong>.
          </p>
          <div style={{ display: 'grid', gap: 10 }}>
            {WEBHOOK_ENDPOINTS.map(wh => (
              <div key={wh.event} style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
                      <code style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 4, fontSize: 13, color: '#7c3aed' }}>
                        {wh.event}
                      </code>
                    </div>
                    <p style={{ margin: 0, fontSize: 13, color: '#6b7280' }}>{wh.desc}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <code style={{ fontSize: 12, background: '#f9fafb', border: '1px solid #e5e7eb', padding: '6px 10px', borderRadius: 6, color: '#374151', wordBreak: 'break-all', maxWidth: 400 }}>
                      {wh.url}
                    </code>
                    <button onClick={() => navigator.clipboard.writeText(wh.url)}
                      style={{ padding: '6px 12px', fontSize: 12, background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, color: '#1d4ed8', cursor: 'pointer', fontWeight: 600, whiteSpace: 'nowrap' }}>
                      Copy
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, padding: 16, marginTop: 20 }}>
            <h4 style={{ margin: '0 0 8px', fontSize: 14 }}>⚠️ HMAC Validation</h4>
            <p style={{ margin: 0, fontSize: 13, color: '#78350f' }}>
              Set <code>SHOPIFY_WEBHOOK_SECRET</code> in your server environment to validate webhook signatures.
              Without it, webhooks are accepted in dev mode (insecure for production).
            </p>
          </div>
        </div>
      )}

      {/* ── Backfill Tab ── */}
      {activeTab === 'backfill' && (
        <div style={{ maxWidth: 560 }}>
          <p style={{ color: '#374151', marginBottom: 20, fontSize: 14 }}>
            Import existing Shopify customers and orders into the unified customer database.
          </p>

          <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 20, marginBottom: 20 }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 700 }}>Shopify Credentials</h3>
            <Field label="Store URL (e.g. your-store.myshopify.com)">
              <input value={shopUrl} onChange={e => setShopUrl(e.target.value)} style={inputStyle} placeholder="your-store.myshopify.com" />
            </Field>
            <Field label="Admin API Access Token">
              <input value={accessToken} onChange={e => setAccessToken(e.target.value)} type="password"
                style={inputStyle} placeholder="<SHOPIFY_ADMIN_TOKEN>" />
            </Field>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {/* Customer Backfill */}
            <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
              <h4 style={{ margin: '0 0 8px', fontSize: 15, fontWeight: 700 }}>👥 Customers</h4>
              <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 12px' }}>Sync all Shopify customers → unified customer table</p>
              <button onClick={() => runBackfill('customers')} disabled={backfilling.customers}
                style={{ ...btnStyle('#3b82f6'), width: '100%', marginBottom: 10 }}>
                {backfilling.customers ? 'Syncing…' : '🔄 Sync Customers'}
              </button>
              {backfillResult.customers && (
                <div style={{ fontSize: 12, background: backfillResult.customers.error ? '#fee2e2' : '#d1fae5',
                  color: backfillResult.customers.error ? '#991b1b' : '#065f46',
                  padding: '8px 10px', borderRadius: 6 }}>
                  {backfillResult.customers.error ? `Error: ${backfillResult.customers.error}` :
                    `✅ Created: ${backfillResult.customers.created} | Updated: ${backfillResult.customers.updated} | Skipped: ${backfillResult.customers.skipped} | Errors: ${backfillResult.customers.errors}`
                  }
                </div>
              )}
            </div>

            {/* Order Backfill */}
            <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
              <h4 style={{ margin: '0 0 8px', fontSize: 15, fontWeight: 700 }}>🛒 Orders</h4>
              <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 12px' }}>Sync recent orders → update customer stats</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                <span style={{ fontSize: 13, color: '#374151' }}>Last</span>
                <select value={backfillDays} onChange={e => setBackfillDays(Number(e.target.value))}
                  style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13 }}>
                  {[30, 60, 90, 180, 365].map(d => <option key={d} value={d}>{d} days</option>)}
                </select>
              </div>
              <button onClick={() => runBackfill('orders')} disabled={backfilling.orders}
                style={{ ...btnStyle('#10b981'), width: '100%', marginBottom: 10 }}>
                {backfilling.orders ? 'Syncing…' : '🔄 Sync Orders'}
              </button>
              {backfillResult.orders && (
                <div style={{ fontSize: 12, background: backfillResult.orders.error ? '#fee2e2' : '#d1fae5',
                  color: backfillResult.orders.error ? '#991b1b' : '#065f46',
                  padding: '8px 10px', borderRadius: 6 }}>
                  {backfillResult.orders.error ? `Error: ${backfillResult.orders.error}` :
                    `✅ Synced: ${backfillResult.orders.synced} | Errors: ${backfillResult.orders.errors}`
                  }
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Sync Log Tab ── */}
      {activeTab === 'log' && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Recent Sync Events</h3>
            <button onClick={loadLog} style={btnStyle('#6b7280', { fontSize: 13 })}>↻ Refresh</button>
          </div>

          {logError && <div style={{ background: '#fee2e2', color: '#991b1b', padding: 12, borderRadius: 8, marginBottom: 16 }}>{logError}</div>}

          {logLoading ? (
            <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>Loading…</div>
          ) : syncLog.length === 0 ? (
            <div style={{ color: '#9ca3af', textAlign: 'center', padding: 40 }}>No sync events yet. Webhook events will appear here.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    {['Time', 'Type', 'Event', 'Shopify ID', 'Email', 'Status', 'Error'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {syncLog.map(r => (
                    <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '8px 12px', color: '#6b7280', whiteSpace: 'nowrap' }}>
                        {r.created_at ? new Date(r.created_at).toLocaleTimeString() : '—'}
                      </td>
                      <td style={{ padding: '8px 12px' }}><code style={{ fontSize: 12, background: '#f3f4f6', padding: '2px 6px', borderRadius: 4 }}>{r.sync_type}</code></td>
                      <td style={{ padding: '8px 12px', color: '#374151' }}>{r.event_type || '—'}</td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 12 }}>{r.shopify_id || '—'}</td>
                      <td style={{ padding: '8px 12px' }}>{r.customer_email || '—'}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: statusColor[r.status] || '#6b7280' }}>
                          {r.status}
                        </span>
                      </td>
                      <td style={{ padding: '8px 12px', color: '#ef4444', fontSize: 12 }}>{r.error_reason || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5 }}>{label}</label>
      {children}
    </div>
  );
}
const inputStyle = { width: '100%', padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, outline: 'none', boxSizing: 'border-box' };
function btnStyle(bg, extra = {}) {
  return { background: bg, color: 'white', border: 'none', borderRadius: 8, padding: '9px 18px', fontWeight: 600, fontSize: 14, cursor: 'pointer', ...extra };
}
