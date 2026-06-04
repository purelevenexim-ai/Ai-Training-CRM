/**
 * JourneyBuilderUI — Full multi-channel journey builder
 *
 * Allows marketing team to:
 * - Create journeys with a trigger event
 * - Add steps with delay, channel (Email/WhatsApp/Both), and template selection
 * - Activate/pause journeys
 * - View per-journey stats
 */
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'https://track.pureleven.com/api';
const ADMIN_KEY = 'anu_admin_secret';

function apiUrl(path, params = {}) {
  const secret = localStorage.getItem(ADMIN_KEY) || '';
  const qs = new URLSearchParams({ admin_secret: secret, ...params }).toString();
  return `${API_BASE}${path}?${qs}`;
}

async function api(method, path, body) {
  const secret = localStorage.getItem(ADMIN_KEY) || '';
  const url = `${API_BASE}${path}?admin_secret=${encodeURIComponent(secret)}`;
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const TRIGGER_OPTIONS = [
  { value: 'order_delivered', label: '📦 Order Delivered' },
  { value: 'order_created', label: '🛒 Order Created' },
  { value: 'customer_created', label: '👤 New Customer' },
  { value: 'no_purchase_90d', label: '⏰ No Purchase in 90 Days' },
  { value: 'review_pending', label: '⭐ Review Pending' },
  { value: 'custom', label: '⚙️ Custom Trigger' },
];

const CHANNEL_OPTIONS = [
  { value: 'email', label: '📧 Email', color: '#3b82f6' },
  { value: 'whatsapp', label: '💬 WhatsApp', color: '#10b981' },
  { value: 'both', label: '📡 Email + WhatsApp', color: '#8b5cf6' },
];

const STATUS_STYLES = {
  draft: { bg: '#f3f4f6', text: '#374151', label: '📝 Draft' },
  active: { bg: '#d1fae5', text: '#065f46', label: '✅ Active' },
  paused: { bg: '#fef3c7', text: '#92400e', label: '⏸️ Paused' },
  archived: { bg: '#fee2e2', text: '#991b1b', label: '🗄️ Archived' },
};

export default function JourneyBuilderUI() {
  const [journeys, setJourneys] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // View state
  const [view, setView] = useState('list'); // list | create | edit | stats
  const [selectedJourney, setSelectedJourney] = useState(null);
  const [stats, setStats] = useState(null);

  // Create form
  const [form, setForm] = useState({
    name: '',
    description: '',
    trigger_event: 'order_delivered',
    trigger_delay_hours: 0,
    steps: [],
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const fetchJourneys = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api('GET', '/crm/journeys');
      const list = Array.isArray(data) ? data : (data.journeys || []);
      const normalized = list.map(j => ({
        ...j,
        status: (j.status || 'DRAFT').toLowerCase(),
        trigger_event: j.entry_trigger || j.trigger_event || 'custom',
        enrolled_count: j.enrolled_count || 0,
        completed_count: j.completed_count || 0,
      }));
      setJourneys(normalized);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const data = await api('GET', '/audiences/templates');
      setTemplates(data.templates || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchJourneys();
    fetchTemplates();
  }, [fetchJourneys, fetchTemplates]);

  const handleCreate = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await api('POST', '/crm/journeys', {
        name: form.name,
        description: form.description,
        entry_trigger: form.trigger_event,
        template_json: form.steps,
      });
      await fetchJourneys();
      setView('list');
      setForm({ name: '', description: '', trigger_event: 'order_delivered', trigger_delay_hours: 0, steps: [] });
    } catch (e) {
      setSaveError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (journeyId) => {
    try {
      await api('PATCH', `/crm/journeys/${journeyId}`, { status: 'ACTIVE' });
      await fetchJourneys();
    } catch (e) {
      setError(e.message);
    }
  };

  const handlePause = async (journeyId) => {
    try {
      await api('PATCH', `/crm/journeys/${journeyId}`, { status: 'PAUSED' });
      await fetchJourneys();
    } catch (e) {
      setError(e.message);
    }
  };

  const loadStats = async (journey) => {
    setSelectedJourney(journey);
    setView('stats');
    setStats(null);
    try {
      const data = await api('GET', `/crm/journeys/${journey.id}`);
      setStats(data);
    } catch (e) {
      setStats({ error: e.message });
    }
  };

  const openEdit = (journey) => {
    setSelectedJourney(journey);
    setForm({
      name: journey.name,
      description: journey.description || '',
      trigger_event: journey.trigger_event,
      trigger_delay_hours: journey.trigger_delay_hours || 0,
      steps: journey.steps || [],
    });
    setView('edit');
  };

  const handleSaveEdit = async () => {
    if (!selectedJourney) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api('PATCH', `/crm/journeys/${selectedJourney.id}`, {
        description: form.description,
        entry_trigger: form.trigger_event,
      });
      await fetchJourneys();
      setView('list');
    } catch (e) {
      setSaveError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (view === 'stats' && selectedJourney) {
    return <JourneyStats journey={selectedJourney} stats={stats} onBack={() => setView('list')} />;
  }

  if (view === 'create' || view === 'edit') {
    return (
      <JourneyForm
        title={view === 'create' ? '🆕 New Journey' : `✏️ Edit: ${selectedJourney?.name}`}
        form={form}
        setForm={setForm}
        templates={templates}
        saving={saving}
        error={saveError}
        onSave={view === 'create' ? handleCreate : handleSaveEdit}
        onCancel={() => setView('list')}
      />
    );
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, color: '#111827', fontSize: 22 }}>🔁 Journey Builder</h2>
          <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: 14 }}>
            Automated multi-channel customer journeys
          </p>
        </div>
        <button
          onClick={() => {
            setForm({ name: '', description: '', trigger_event: 'order_delivered', trigger_delay_hours: 0, steps: [] });
            setView('create');
          }}
          style={{ background: '#6366f1', color: 'white', border: 'none', borderRadius: 8, padding: '9px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          + New Journey
        </button>
      </div>

      {error && <div style={{ color: '#dc2626', marginBottom: 12, fontSize: 13 }}>⚠️ {error}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af' }}>Loading journeys…</div>
      ) : journeys.length === 0 ? (
        <EmptyState onCreateClick={() => setView('create')} />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
          {journeys.map(j => (
            <JourneyCard
              key={j.id}
              journey={j}
              onEdit={() => openEdit(j)}
              onStats={() => loadStats(j)}
              onActivate={() => handleActivate(j.id)}
              onPause={() => handlePause(j.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function JourneyCard({ journey, onEdit, onStats, onActivate, onPause }) {
  const s = STATUS_STYLES[journey.status] || STATUS_STYLES.draft;
  const trigger = TRIGGER_OPTIONS.find(t => t.value === journey.trigger_event) || { label: journey.trigger_event };

  return (
    <div style={{ background: 'white', borderRadius: 12, border: '1px solid #e5e7eb', padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: '#111827' }}>{journey.name}</div>
          {journey.description && (
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 3 }}>{journey.description}</div>
          )}
        </div>
        <span style={{ background: s.bg, color: s.text, padding: '3px 9px', borderRadius: 12, fontSize: 11, fontWeight: 600 }}>
          {s.label}
        </span>
      </div>

      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
        <div>🎯 Trigger: <strong>{trigger.label}</strong></div>
        <div style={{ marginTop: 4 }}>
          👥 Enrolled: <strong>{journey.enrolled_count}</strong> ·
          ✅ Completed: <strong>{journey.completed_count}</strong>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={onEdit} style={miniBtn('#f3f4f6', '#374151')}>✏️ Edit</button>
        <button onClick={onStats} style={miniBtn('#eff6ff', '#3b82f6')}>📊 Stats</button>
        {journey.status === 'draft' || journey.status === 'paused' ? (
          <button onClick={onActivate} style={miniBtn('#d1fae5', '#065f46')}>▶️ Activate</button>
        ) : (
          <button onClick={onPause} style={miniBtn('#fef3c7', '#92400e')}>⏸️ Pause</button>
        )}
      </div>
    </div>
  );
}

function JourneyForm({ title, form, setForm, templates, saving, error, onSave, onCancel }) {
  const addStep = () => {
    setForm(f => ({
      ...f,
      steps: [...f.steps, {
        name: `Step ${f.steps.length + 1}`,
        delay_days: f.steps.length === 0 ? 0 : 3,
        delay_hours: 0,
        channel: 'email',
        template_id: null,
        conditions: {},
        max_retries: 1,
      }],
    }));
  };

  const removeStep = (idx) => {
    setForm(f => ({ ...f, steps: f.steps.filter((_, i) => i !== idx) }));
  };

  const updateStep = (idx, field, value) => {
    setForm(f => ({
      ...f,
      steps: f.steps.map((s, i) => i === idx ? { ...s, [field]: value } : s),
    }));
  };

  const moveStep = (idx, dir) => {
    const steps = [...form.steps];
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= steps.length) return;
    [steps[idx], steps[newIdx]] = [steps[newIdx], steps[idx]];
    setForm(f => ({ ...f, steps }));
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button onClick={onCancel} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#9ca3af' }}>←</button>
        <h2 style={{ margin: 0, color: '#111827', fontSize: 20 }}>{title}</h2>
      </div>

      {/* Journey config */}
      <div style={{ background: 'white', borderRadius: 12, border: '1px solid #e5e7eb', padding: 24, marginBottom: 20 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, color: '#374151' }}>Journey Settings</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={labelStyle}>Journey Name *</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Post-Purchase Review Journey"
              style={{ ...fldStyle(), width: '100%', boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={labelStyle}>Description</label>
            <input
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="What does this journey do?"
              style={{ ...fldStyle(), width: '100%', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={labelStyle}>Trigger Event</label>
            <select
              value={form.trigger_event}
              onChange={e => setForm(f => ({ ...f, trigger_event: e.target.value }))}
              style={selStyle()}
            >
              {TRIGGER_OPTIONS.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Delay After Trigger (hours)</label>
            <input
              type="number"
              min={0}
              value={form.trigger_delay_hours}
              onChange={e => setForm(f => ({ ...f, trigger_delay_hours: parseInt(e.target.value) || 0 }))}
              style={{ ...fldStyle(), width: '100%', boxSizing: 'border-box' }}
            />
          </div>
        </div>
      </div>

      {/* Steps */}
      <div style={{ background: 'white', borderRadius: 12, border: '1px solid #e5e7eb', padding: 24, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 15, color: '#374151' }}>Journey Steps ({form.steps.length})</h3>
          <button onClick={addStep} style={{ background: '#eff6ff', color: '#3b82f6', border: '1px solid #bfdbfe', borderRadius: 7, padding: '6px 14px', fontSize: 13, cursor: 'pointer', fontWeight: 600 }}>
            + Add Step
          </button>
        </div>

        {form.steps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#9ca3af', fontSize: 14 }}>
            No steps yet. Click "Add Step" to build your journey.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {form.steps.map((step, idx) => (
              <StepEditor
                key={idx}
                step={step}
                index={idx}
                total={form.steps.length}
                templates={templates}
                onChange={(field, val) => updateStep(idx, field, val)}
                onRemove={() => removeStep(idx)}
                onMoveUp={() => moveStep(idx, -1)}
                onMoveDown={() => moveStep(idx, 1)}
              />
            ))}
          </div>
        )}
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', color: '#dc2626', fontSize: 13, marginBottom: 16 }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{ background: '#f3f4f6', color: '#374151', border: 'none', borderRadius: 8, padding: '9px 20px', cursor: 'pointer', fontSize: 13 }}>
          Cancel
        </button>
        <button
          onClick={onSave}
          disabled={saving || !form.name}
          style={{ background: saving || !form.name ? '#9ca3af' : '#6366f1', color: 'white', border: 'none', borderRadius: 8, padding: '9px 22px', fontSize: 13, fontWeight: 600, cursor: saving || !form.name ? 'not-allowed' : 'pointer' }}
        >
          {saving ? '⏳ Saving…' : '💾 Save Journey'}
        </button>
      </div>
    </div>
  );
}

function StepEditor({ step, index, total, templates, onChange, onRemove, onMoveUp, onMoveDown }) {
  const ch = CHANNEL_OPTIONS.find(c => c.value === step.channel) || CHANNEL_OPTIONS[0];

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, background: '#fafafa' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ background: '#eff6ff', color: '#3b82f6', fontWeight: 700, borderRadius: '50%', width: 26, height: 26, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>
            {index + 1}
          </span>
          <span style={{ background: ch.color + '20', color: ch.color, fontSize: 12, fontWeight: 600, padding: '2px 8px', borderRadius: 10 }}>
            {ch.label}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {index > 0 && <button onClick={onMoveUp} style={iconBtn}>↑</button>}
          {index < total - 1 && <button onClick={onMoveDown} style={iconBtn}>↓</button>}
          <button onClick={onRemove} style={{ ...iconBtn, color: '#dc2626' }}>×</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
        <div>
          <label style={labelStyle}>Step Name</label>
          <input
            value={step.name || ''}
            onChange={e => onChange('name', e.target.value)}
            placeholder="e.g. Welcome Email"
            style={{ ...fldStyle(), width: '100%', boxSizing: 'border-box' }}
          />
        </div>
        <div>
          <label style={labelStyle}>Delay After Trigger</label>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              type="number" min={0}
              value={step.delay_days}
              onChange={e => onChange('delay_days', parseInt(e.target.value) || 0)}
              style={{ ...fldStyle(), width: 60 }}
              placeholder="Days"
            />
            <span style={{ lineHeight: '34px', fontSize: 12, color: '#6b7280' }}>d</span>
            <input
              type="number" min={0} max={23}
              value={step.delay_hours}
              onChange={e => onChange('delay_hours', parseInt(e.target.value) || 0)}
              style={{ ...fldStyle(), width: 50 }}
              placeholder="h"
            />
            <span style={{ lineHeight: '34px', fontSize: 12, color: '#6b7280' }}>h</span>
          </div>
        </div>
        <div>
          <label style={labelStyle}>Channel</label>
          <select value={step.channel} onChange={e => onChange('channel', e.target.value)} style={selStyle()}>
            {CHANNEL_OPTIONS.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={labelStyle}>Template</label>
          <select
            value={step.template_id || ''}
            onChange={e => onChange('template_id', e.target.value || null)}
            style={{ ...selStyle(), width: '100%', boxSizing: 'border-box' }}
          >
            <option value="">— No template selected —</option>
            {templates.map(t => (
              <option key={t.id} value={t.id}>{t.name} ({t.category})</option>
            ))}
          </select>
          {templates.length === 0 && (
            <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 4 }}>
              ⚠️ No templates found. Create templates in Audiences → Templates first.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function JourneyStats({ journey, stats, onBack }) {
  const openRate = stats?.sent > 0 ? ((stats.opened || 0) / stats.sent * 100).toFixed(1) : '—';
  const clickRate = stats?.sent > 0 ? ((stats.clicked || 0) / stats.sent * 100).toFixed(1) : '—';

  return (
    <div style={{ padding: '24px 32px', maxWidth: 700, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#9ca3af' }}>←</button>
        <div>
          <h2 style={{ margin: 0, fontSize: 20 }}>📊 {journey.name}</h2>
          <p style={{ margin: '3px 0 0', color: '#6b7280', fontSize: 13 }}>Journey Performance</p>
        </div>
      </div>

      {!stats ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af' }}>Loading…</div>
      ) : stats.error ? (
        <div style={{ color: '#dc2626', padding: 16 }}>{stats.error}</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          {[
            { label: 'Enrolled', value: stats.total_enrolled ?? journey.enrolled_count, icon: '👥' },
            { label: 'Completed', value: stats.completed ?? journey.completed_count, icon: '✅' },
            { label: 'Active', value: stats.active ?? 0, icon: '⚡' },
            { label: 'Total Sends', value: stats.total_sends ?? 0, icon: '📨' },
            { label: 'Open Rate', value: openRate === '—' ? '—' : `${openRate}%`, icon: '📬' },
            { label: 'Click Rate', value: clickRate === '—' ? '—' : `${clickRate}%`, icon: '🖱️' },
          ].map(m => (
            <div key={m.label} style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, padding: 18, textAlign: 'center' }}>
              <div style={{ fontSize: 24, marginBottom: 6 }}>{m.icon}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#111827' }}>{m.value ?? '—'}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{m.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState({ onCreateClick }) {
  return (
    <div style={{ textAlign: 'center', padding: '60px 20px', color: '#9ca3af' }}>
      <div style={{ fontSize: 64, marginBottom: 16 }}>🔁</div>
      <h3 style={{ margin: '0 0 8px', color: '#374151' }}>No journeys yet</h3>
      <p style={{ margin: '0 0 20px', fontSize: 14 }}>
        Journeys automatically send the right message to customers at the right time.
      </p>
      <button
        onClick={onCreateClick}
        style={{ background: '#6366f1', color: 'white', border: 'none', borderRadius: 8, padding: '10px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
      >
        Create Your First Journey
      </button>
    </div>
  );
}

// ── Shared styles ──────────────────────────────────────────────────────────────

const labelStyle = {
  display: 'block',
  fontSize: 11,
  fontWeight: 600,
  color: '#6b7280',
  marginBottom: 5,
  textTransform: 'uppercase',
};

function fldStyle() {
  return { border: '1px solid #d1d5db', borderRadius: 7, padding: '7px 10px', fontSize: 13, outline: 'none' };
}

function selStyle() {
  return { border: '1px solid #d1d5db', borderRadius: 7, padding: '7px 10px', fontSize: 13, background: 'white', cursor: 'pointer', width: '100%' };
}

function miniBtn(bg, color) {
  return { background: bg, color, border: 'none', borderRadius: 6, padding: '5px 12px', fontSize: 12, cursor: 'pointer', fontWeight: 500 };
}

const iconBtn = {
  background: '#f3f4f6',
  border: 'none',
  borderRadius: 5,
  padding: '2px 8px',
  cursor: 'pointer',
  fontSize: 14,
  color: '#6b7280',
};

