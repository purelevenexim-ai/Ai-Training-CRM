/**
 * CampaignBuilderPanel.jsx — Phase 2
 * One-off broadcast campaigns (Email, WhatsApp, Multi-channel)
 * Targets: all opted-in customers or a specific contact list
 */
import React, { useState, useEffect, useCallback } from 'react';

const API = 'https://track.pureleven.com/api';
const secret = () => localStorage.getItem('anu_admin_secret') || '';
const api = (path, p = {}) => `${API}${path}?${new URLSearchParams({ admin_secret: secret(), ...p })}`;

const STATUS_COLORS = {
  draft:     { bg: '#f3f4f6', text: '#6b7280', label: 'Draft' },
  scheduled: { bg: '#dbeafe', text: '#1d4ed8', label: 'Scheduled' },
  sending:   { bg: '#fef3c7', text: '#d97706', label: 'Sending' },
  completed: { bg: '#d1fae5', text: '#065f46', label: 'Completed' },
  failed:    { bg: '#fee2e2', text: '#991b1b', label: 'Failed' },
  paused:    { bg: '#e0e7ff', text: '#3730a3', label: 'Paused' },
};

const CHANNEL_OPTIONS = [
  { value: 'email',        label: '📧 Email',               color: '#3b82f6' },
  { value: 'whatsapp',     label: '💬 WhatsApp',            color: '#25d366' },
  { value: 'multichannel', label: '⚡ Email + WhatsApp',    color: '#8b5cf6' },
];

const AUDIENCE_OPTIONS = [
  { value: 'all',    label: '🌐 All opted-in' },
  { value: 'list',   label: '📋 Contact list' },
];

export default function CampaignBuilderPanel() {
  const [view, setView] = useState('list'); // list | create | detail
  const [campaigns, setCampaigns] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [stats, setStats] = useState(null);
  const [preview, setPreview] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Contact lists + templates for dropdowns
  const [lists, setLists] = useState([]);
  const [templates, setTemplates] = useState([]);

  // Create form
  const [form, setForm] = useState({
    name: '', description: '', type: 'email',
    audience_type: 'all', list_id: '',
    template_id: '', schedule_type: 'send_now',
    scheduled_at: '',
  });
  const [saving, setSaving] = useState(false);
  const [sendingId, setSendingId] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [previewMode, setPreviewMode] = useState('desktop');

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter ? { status: statusFilter } : {};
      const res = await fetch(api('/campaigns', params));
      const data = await res.json();
      setCampaigns(data.items || []);
      setTotal(data.total || 0);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }, [statusFilter]);

  const loadLists = useCallback(async () => {
    try {
      const res = await fetch(api('/audiences/lists'));
      const data = await res.json();
      setLists(data.lists || data.items || data || []);
    } catch {}
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await fetch(api('/audiences/templates'));
      const data = await res.json();
      setTemplates(data.templates || data.items || data || []);
    } catch {}
  }, []);

  useEffect(() => { loadCampaigns(); }, [loadCampaigns]);
  useEffect(() => { loadLists(); loadTemplates(); }, []);

  const openDetail = async (c) => {
    setSelected(c);
    setStats(null);
    setPreview([]);
    setView('detail');
    try {
      const res = await fetch(api(`/campaigns/${c.id}/stats`));
      setStats(await res.json());
    } catch {}
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = { ...form };
      if (!body.list_id) delete body.list_id;
      if (!body.template_id) delete body.template_id;
      if (!body.scheduled_at) delete body.scheduled_at;
      const res = await fetch(api('/campaigns'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      setForm({ name: '', description: '', type: 'email', audience_type: 'all', list_id: '', template_id: '', schedule_type: 'send_now', scheduled_at: '' });
      setView('list');
      loadCampaigns();
    } catch (e) { setError(e.message); }
    setSaving(false);
  };

  const handlePreview = async (cid) => {
    setPreviewLoading(true);
    try {
      const res = await fetch(api(`/campaigns/${cid}/preview`));
      setPreview(await res.json());
    } catch {}
    setPreviewLoading(false);
  };

  const handleSend = async (cid, dry_run = false) => {
    if (!dry_run && !window.confirm('Send this campaign to all recipients now?')) return;
    setSendingId(cid);
    try {
      const res = await fetch(api(`/campaigns/${cid}/send`, { dry_run: dry_run ? 'true' : 'false' }), { method: 'POST' });
      const data = await res.json();
      alert(dry_run
        ? `Dry run: ${data.recipients} recipients, template: ${data.template || 'none'}`
        : `Sent! ${data.sent} / ${data.total_recipients} delivered. Errors: ${data.errors}`
      );
      loadCampaigns();
      if (selected?.id === cid) openDetail({ ...selected });
    } catch (e) { alert('Error: ' + e.message); }
    setSendingId(null);
  };

  const handleDelete = async (cid) => {
    if (!window.confirm('Delete this draft campaign?')) return;
    await fetch(api(`/campaigns/${cid}`), { method: 'DELETE' });
    setView('list');
    loadCampaigns();
  };

  const StatusBadge = ({ s }) => {
    const sc = STATUS_COLORS[s] || STATUS_COLORS.draft;
    return (
      <span style={{ padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600, background: sc.bg, color: sc.text }}>
        {sc.label}
      </span>
    );
  };

  const selectedTemplate = templates.find(t => t.id === form.template_id);

  // ── List View ────────────────────────────────────────────────────────────
  if (view === 'list') return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>📢 Campaigns</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 14 }}>{total} campaigns total</p>
        </div>
        <button onClick={() => setView('create')} style={btnStyle('#3b82f6')}>+ New Campaign</button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['', 'draft', 'scheduled', 'sending', 'completed', 'failed'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            style={{ padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid',
              background: statusFilter === s ? '#1d4ed8' : 'white',
              color: statusFilter === s ? 'white' : '#374151',
              borderColor: statusFilter === s ? '#1d4ed8' : '#d1d5db', cursor: 'pointer' }}>
            {s || 'All'}
          </button>
        ))}
      </div>

      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>}

      {loading ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 40 }}>Loading…</div> : (
        campaigns.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📢</div>
            <p>No campaigns yet. Create your first broadcast!</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 12 }}>
            {campaigns.map(c => (
              <div key={c.id} onClick={() => openDetail(c)}
                style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, cursor: 'pointer',
                  display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'center',
                  ':hover': { boxShadow: '0 2px 8px rgba(0,0,0,0.08)' } }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span style={{ fontSize: 16, fontWeight: 700, color: '#111827' }}>{c.name}</span>
                    <StatusBadge s={c.status} />
                    <span style={{ fontSize: 12, color: '#9ca3af' }}>
                      {CHANNEL_OPTIONS.find(o => o.value === c.type)?.label || c.type}
                    </span>
                  </div>
                  {c.description && <p style={{ margin: 0, fontSize: 13, color: '#6b7280' }}>{c.description}</p>}
                  <div style={{ marginTop: 6, display: 'flex', gap: 16, fontSize: 12, color: '#9ca3af' }}>
                    <span>Audience: {AUDIENCE_OPTIONS.find(o => o.value === c.audience_type)?.label || c.audience_type}</span>
                    <span>Sent: {c.sent_count}/{c.total_recipients}</span>
                    {c.created_at && <span>{new Date(c.created_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  {c.status === 'draft' && (
                    <button onClick={e => { e.stopPropagation(); handleSend(c.id); }}
                      disabled={sendingId === c.id}
                      style={btnStyle('#10b981', { fontSize: 12, padding: '5px 12px' })}>
                      {sendingId === c.id ? 'Sending…' : '🚀 Send Now'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );

  // ── Create View ──────────────────────────────────────────────────────────
  if (view === 'create') return (
    <div style={{ padding: 24, maxWidth: 680 }}>
      <button onClick={() => setView('list')} style={backBtn}>← Back</button>
      <h2 style={{ margin: '12px 0 24px', fontSize: 22, fontWeight: 700 }}>New Campaign</h2>

      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleCreate}>
        <Field label="Campaign Name *">
          <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            required style={inputStyle} placeholder="e.g. Summer Sale 2026" />
        </Field>

        <Field label="Description">
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            style={{ ...inputStyle, height: 70, resize: 'vertical' }} placeholder="Internal notes…" />
        </Field>

        <Field label="Channel">
          <div style={{ display: 'flex', gap: 8 }}>
            {CHANNEL_OPTIONS.map(o => (
              <label key={o.value} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
                border: `2px solid ${form.type === o.value ? o.color : '#e5e7eb'}`,
                borderRadius: 8, cursor: 'pointer', background: form.type === o.value ? o.color + '15' : 'white',
                fontSize: 13, fontWeight: form.type === o.value ? 600 : 400 }}>
                <input type="radio" name="type" value={o.value} checked={form.type === o.value}
                  onChange={e => setForm(f => ({ ...f, type: e.target.value }))} style={{ display: 'none' }} />
                {o.label}
              </label>
            ))}
          </div>
        </Field>

        <Field label="Audience">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {AUDIENCE_OPTIONS.map(o => (
              <label key={o.value} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
                border: `2px solid ${form.audience_type === o.value ? '#3b82f6' : '#e5e7eb'}`,
                borderRadius: 8, cursor: 'pointer', background: form.audience_type === o.value ? '#eff6ff' : 'white',
                fontSize: 13, fontWeight: form.audience_type === o.value ? 600 : 400 }}>
                <input type="radio" name="audience_type" value={o.value} checked={form.audience_type === o.value}
                  onChange={e => setForm(f => ({ ...f, audience_type: e.target.value }))} style={{ display: 'none' }} />
                {o.label}
              </label>
            ))}
          </div>
          {form.audience_type === 'list' && (
            <select value={form.list_id} onChange={e => setForm(f => ({ ...f, list_id: e.target.value }))}
              style={{ ...inputStyle, marginTop: 8 }}>
              <option value="">— Select list —</option>
              {lists.map(l => <option key={l.id} value={l.id}>{l.name} ({l.customer_count || 0})</option>)}
            </select>
          )}
        </Field>

        <Field label="Template">
          <select value={form.template_id} onChange={e => setForm(f => ({ ...f, template_id: e.target.value }))}
            style={inputStyle}>
            <option value="">— No template (plain send) —</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name} ({t.category})</option>)}
          </select>
        </Field>

        {selectedTemplate && (
          <Field label="Live Preview">
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden', background: '#fff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', borderBottom: '1px solid #f3f4f6', background: '#f9fafb' }}>
                <strong style={{ fontSize: 13 }}>{selectedTemplate.name}</strong>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="button" onClick={() => setPreviewMode('desktop')} style={btnStyle(previewMode === 'desktop' ? '#2563eb' : '#6b7280', { fontSize: 11, padding: '4px 8px' })}>Desktop</button>
                  <button type="button" onClick={() => setPreviewMode('mobile')} style={btnStyle(previewMode === 'mobile' ? '#2563eb' : '#6b7280', { fontSize: 11, padding: '4px 8px' })}>Mobile</button>
                </div>
              </div>
              <div style={{ padding: 12 }}>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
                  Subject: <strong>{selectedTemplate.email_subject || '[No subject set]'}</strong>
                </div>
                {selectedTemplate.email_html ? (
                  <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 10, minHeight: 120, maxHeight: 280, overflow: 'auto', width: previewMode === 'mobile' ? 340 : '100%', margin: '0 auto' }}
                    dangerouslySetInnerHTML={{ __html: selectedTemplate.email_html }} />
                ) : (
                  <div style={{ border: '1px dashed #cbd5e1', borderRadius: 8, padding: 14, color: '#6b7280', fontSize: 12 }}>
                    Template body is empty. Use this starter:
                    <pre style={{ marginTop: 8, background: '#f8fafc', padding: 8, borderRadius: 6, whiteSpace: 'pre-wrap' }}>{`<h2>Hello {{first_name}}</h2>\n<p>We picked this for you.</p>\n<a href=\"https://pureleven.com\">Shop now</a>`}</pre>
                  </div>
                )}
                {selectedTemplate.whatsapp_body && (
                  <div style={{ marginTop: 10, fontSize: 12, color: '#111827' }}>
                    <strong>WhatsApp:</strong> {selectedTemplate.whatsapp_body}
                  </div>
                )}
              </div>
            </div>
          </Field>
        )}

        <Field label="Schedule">
          <div style={{ display: 'flex', gap: 8 }}>
            {[{ v: 'send_now', l: '⚡ Send Now' }, { v: 'schedule_at', l: '🕒 Schedule' }].map(o => (
              <label key={o.v} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
                border: `2px solid ${form.schedule_type === o.v ? '#3b82f6' : '#e5e7eb'}`,
                borderRadius: 8, cursor: 'pointer', background: form.schedule_type === o.v ? '#eff6ff' : 'white', fontSize: 13 }}>
                <input type="radio" name="sched" value={o.v} checked={form.schedule_type === o.v}
                  onChange={e => setForm(f => ({ ...f, schedule_type: e.target.value }))} style={{ display: 'none' }} />
                {o.l}
              </label>
            ))}
          </div>
          {form.schedule_type === 'schedule_at' && (
            <input type="datetime-local" value={form.scheduled_at}
              onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))}
              style={{ ...inputStyle, marginTop: 8 }} />
          )}
        </Field>

        <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
          <button type="submit" disabled={saving} style={btnStyle('#3b82f6', { flex: 1 })}>
            {saving ? 'Creating…' : '✓ Create Campaign'}
          </button>
          <button type="button" onClick={() => setView('list')} style={btnStyle('#6b7280')}>Cancel</button>
        </div>
      </form>
    </div>
  );

  // ── Detail View ──────────────────────────────────────────────────────────
  if (view === 'detail' && selected) return (
    <div style={{ padding: 24 }}>
      <button onClick={() => setView('list')} style={backBtn}>← Back</button>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginTop: 12, marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{selected.name}</h2>
            <StatusBadge s={selected.status} />
          </div>
          {selected.description && <p style={{ margin: 0, color: '#6b7280' }}>{selected.description}</p>}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {selected.status === 'draft' && (
            <>
              <button onClick={() => handleSend(selected.id, true)} style={btnStyle('#6b7280', { fontSize: 13 })}>🔍 Dry Run</button>
              <button onClick={() => handleSend(selected.id)}
                disabled={sendingId === selected.id}
                style={btnStyle('#10b981', { fontSize: 13 })}>
                {sendingId === selected.id ? 'Sending…' : '🚀 Send Now'}
              </button>
              <button onClick={() => handleDelete(selected.id)} style={btnStyle('#ef4444', { fontSize: 13 })}>🗑 Delete</button>
            </>
          )}
          {selected.template_id && (
            <button onClick={() => handlePreview(selected.id)} style={btnStyle('#8b5cf6', { fontSize: 13 })}>
              👁 Preview
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Recipients', value: stats.total_recipients, color: '#3b82f6' },
            { label: 'Sent', value: stats.sent, color: '#10b981' },
            { label: 'Failed', value: stats.failed, color: '#ef4444' },
            { label: 'Opened', value: `${stats.opened} (${stats.open_rate}%)`, color: '#8b5cf6' },
            { label: 'Clicked', value: `${stats.clicked} (${stats.click_rate}%)`, color: '#f59e0b' },
          ].map(s => (
            <div key={s.label} style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 8, padding: '14px 16px', textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Preview samples */}
      {previewLoading && <div style={{ color: '#6b7280', marginBottom: 16 }}>Loading preview…</div>}
      {preview.length > 0 && (
        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 20 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600 }}>Preview (first {preview.length} recipients)</h3>
          {preview.map((p, i) => (
            <div key={i} style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: 10, marginBottom: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{p.email}</div>
              {p.subject && <div style={{ fontSize: 13, color: '#374151', marginTop: 2 }}>Subject: {p.subject}</div>}
              {p.preview && <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{p.preview}…</div>}
              {p.whatsapp_body && <div style={{ fontSize: 12, color: '#25d366', marginTop: 2 }}>WA: {p.whatsapp_body.slice(0, 100)}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Campaign meta */}
      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600 }}>Details</h3>
        <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 16px', margin: 0, fontSize: 13 }}>
          <dt style={{ color: '#9ca3af' }}>Channel</dt><dd style={{ margin: 0 }}>{CHANNEL_OPTIONS.find(o => o.value === selected.type)?.label}</dd>
          <dt style={{ color: '#9ca3af' }}>Audience</dt><dd style={{ margin: 0 }}>{AUDIENCE_OPTIONS.find(o => o.value === selected.audience_type)?.label}</dd>
          <dt style={{ color: '#9ca3af' }}>Schedule</dt><dd style={{ margin: 0 }}>{selected.schedule_type === 'send_now' ? 'Send Immediately' : selected.scheduled_at}</dd>
          <dt style={{ color: '#9ca3af' }}>Created</dt><dd style={{ margin: 0 }}>{selected.created_at ? new Date(selected.created_at).toLocaleString() : '—'}</dd>
          {selected.completed_at && <><dt style={{ color: '#9ca3af' }}>Completed</dt><dd style={{ margin: 0 }}>{new Date(selected.completed_at).toLocaleString()}</dd></>}
        </dl>
      </div>
    </div>
  );

  return null;
}

// ── Helpers ────────────────────────────────────────────────────────────────
function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  );
}
const inputStyle = { width: '100%', padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, outline: 'none', boxSizing: 'border-box' };
const backBtn = { background: 'none', border: 'none', color: '#3b82f6', cursor: 'pointer', fontSize: 14, padding: 0 };
function btnStyle(bg, extra = {}) {
  return { background: bg, color: 'white', border: 'none', borderRadius: 8, padding: '9px 18px', fontWeight: 600, fontSize: 14, cursor: 'pointer', ...extra };
}
