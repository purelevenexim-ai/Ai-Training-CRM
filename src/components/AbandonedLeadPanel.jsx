import React, { useMemo, useState } from 'react';

const API_BASE = 'https://adsapi.pureleven.com/api';

export default function AbandonedLeadPanel() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [product, setProduct] = useState('');
  const [category, setCategory] = useState('general');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [statusLeadId, setStatusLeadId] = useState('');
  const [statusData, setStatusData] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);

  const canCreate = useMemo(() => {
    return name.trim() && email.trim() && phone.trim() && product.trim();
  }, [name, email, phone, product]);

  const createLead = async () => {
    if (!canCreate) return;
    setLoading(true);
    setResult(null);

    try {
      const params = new URLSearchParams({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        product: product.trim(),
        category,
      });

      const response = await fetch(`${API_BASE}/abandoned/create-lead?${params.toString()}`, {
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create lead');
      }

      setResult({ type: 'success', text: `Lead created: ${data.lead_id || data.id || 'unknown'}`, data });
      if (data.lead_id) {
        setStatusLeadId(data.lead_id);
      }
    } catch (error) {
      setResult({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  const sendCampaign = async () => {
    if (!statusLeadId.trim()) return;
    setSending(true);
    setResult(null);

    try {
      const params = new URLSearchParams({ lead_id: statusLeadId.trim() });
      const response = await fetch(`${API_BASE}/abandoned/send-campaign?${params.toString()}`, {
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to send campaign');
      }

      setResult({ type: 'success', text: 'Campaign send triggered.', data });
    } catch (error) {
      setResult({ type: 'error', text: error.message });
    } finally {
      setSending(false);
    }
  };

  const fetchStatus = async () => {
    if (!statusLeadId.trim()) return;
    setStatusLoading(true);
    setStatusData(null);

    try {
      const params = new URLSearchParams({ lead_id: statusLeadId.trim() });
      const response = await fetch(`${API_BASE}/abandoned/status?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch status');
      }
      setStatusData(data);
    } catch (error) {
      setResult({ type: 'error', text: error.message });
    } finally {
      setStatusLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Abandoned Lead Recovery</h2>
        <p style={styles.subtitle}>Reconnects the existing abandoned-lead API with a usable control panel.</p>
      </div>

      {result && (
        <div style={{ ...styles.alert, ...(result.type === 'success' ? styles.success : styles.error) }}>
          {result.text}
        </div>
      )}

      <div style={styles.grid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Create Test Lead</h3>
          <div style={styles.formGrid}>
            <input style={styles.input} placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <input style={styles.input} placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <input style={styles.input} placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <input style={styles.input} placeholder="Interested product" value={product} onChange={(e) => setProduct(e.target.value)} />
            <select style={styles.input} value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="general">general</option>
              <option value="turmeric">turmeric</option>
              <option value="spices">spices</option>
              <option value="oils">oils</option>
              <option value="ghee">ghee</option>
            </select>
          </div>
          <button style={styles.primaryBtn} disabled={!canCreate || loading} onClick={createLead}>
            {loading ? 'Creating...' : 'Create Lead'}
          </button>
        </div>

        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Campaign Controls</h3>
          <input
            style={styles.input}
            placeholder="Lead ID"
            value={statusLeadId}
            onChange={(e) => setStatusLeadId(e.target.value)}
          />

          <div style={styles.buttonRow}>
            <button style={styles.secondaryBtn} disabled={!statusLeadId || statusLoading} onClick={fetchStatus}>
              {statusLoading ? 'Checking...' : 'Check Status'}
            </button>
            <button style={styles.primaryBtn} disabled={!statusLeadId || sending} onClick={sendCampaign}>
              {sending ? 'Sending...' : 'Send Next Campaign'}
            </button>
          </div>

          {statusData && (
            <pre style={styles.code}>{JSON.stringify(statusData, null, 2)}</pre>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: '24px 32px',
  },
  header: {
    marginBottom: '16px',
  },
  title: {
    margin: '0 0 6px',
    fontSize: '24px',
    color: '#111827',
  },
  subtitle: {
    margin: 0,
    color: '#6b7280',
    fontSize: '14px',
  },
  alert: {
    borderRadius: '8px',
    padding: '10px 12px',
    marginBottom: '16px',
    fontSize: '13px',
    fontWeight: '500',
  },
  success: {
    background: '#dcfce7',
    color: '#166534',
    border: '1px solid #86efac',
  },
  error: {
    background: '#fee2e2',
    color: '#991b1b',
    border: '1px solid #fca5a5',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '16px',
  },
  card: {
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    padding: '16px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  cardTitle: {
    margin: '0 0 12px',
    fontSize: '16px',
    color: '#1f2937',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: '10px',
    marginBottom: '12px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  buttonRow: {
    display: 'flex',
    gap: '8px',
    marginTop: '10px',
  },
  primaryBtn: {
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid #2563eb',
    background: '#2563eb',
    color: '#fff',
    fontWeight: '600',
    cursor: 'pointer',
  },
  secondaryBtn: {
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    background: '#fff',
    color: '#111827',
    fontWeight: '600',
    cursor: 'pointer',
  },
  code: {
    marginTop: '12px',
    background: '#111827',
    color: '#d1fae5',
    borderRadius: '8px',
    padding: '12px',
    fontSize: '12px',
    maxHeight: '260px',
    overflow: 'auto',
  },
};
