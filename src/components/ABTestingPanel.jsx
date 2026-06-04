/**
 * ABTestingPanel — Phase 5
 * Journey cloning, A/B variant creation & management, bulk CSV enrollment
 * Variant comparison charts with recharts
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, Cell,
} from 'recharts';

const API_BASE = 'https://track.pureleven.com/api';
const ADMIN_KEY = 'anu_admin_secret';

function getAdminSecret() {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem(ADMIN_KEY) || window.__ADMIN_SECRET__ || '';
}

function apiUrl(path) {
  const url = new URL(`${API_BASE}${path}`);
  const secret = getAdminSecret();
  if (secret) {
    url.searchParams.set('admin_secret', secret);
  }
  return url.toString();
}

export default function ABTestingPanel() {
  const [activeTab, setActiveTab] = useState('variants');  // variants | clone | bulk

  return (
    <div style={styles.container}>
      <div style={styles.pageHeader}>
        <h2 style={styles.pageTitle}>🧪 A/B Testing & Journey Management</h2>
        <p style={styles.pageSubtitle}>Test variants, clone journeys, and bulk-enroll customers</p>
      </div>

      <div style={styles.tabBar}>
        {[
          { id: 'variants', label: '🧬 A/B Variants' },
          { id: 'clone', label: '📋 Clone Journey' },
          { id: 'bulk', label: '📤 Bulk Enroll' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              ...styles.tabBtn,
              background: activeTab === t.id ? '#3b82f6' : 'white',
              color: activeTab === t.id ? 'white' : '#374151',
              borderColor: activeTab === t.id ? '#3b82f6' : '#d1d5db',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={styles.tabContent}>
        {activeTab === 'variants' && <VariantsTab />}
        {activeTab === 'clone' && <CloneTab />}
        {activeTab === 'bulk' && <BulkEnrollTab />}
      </div>
    </div>
  );
}

/* ─── A/B Variants Tab ─────────────────────────────────────────────────── */

function VariantsTab() {
  const [journeys, setJourneys] = useState([]);
  const [selectedJourney, setSelectedJourney] = useState(null);
  const [variants, setVariants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newVariant, setNewVariant] = useState({ variant_name: '', traffic_split_pct: 50 });
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetch(apiUrl('/journeys'))
      .then((r) => r.json())
      .then((d) => setJourneys(Array.isArray(d) ? d : (d.journeys || [])))
      .catch(() => {});
  }, []);

  const loadVariants = async (journey) => {
    setSelectedJourney(journey);
    setLoading(true);
    try {
      const r = await fetch(apiUrl(`/journeys/${journey.id}/variants`));
      const d = await r.json();
      setVariants(Array.isArray(d) ? d : (d.variants || []));
    } catch {
      setVariants([]);
    }
    setLoading(false);
  };

  const createVariant = async () => {
    if (!selectedJourney || !newVariant.variant_name.trim()) return;
    setCreating(true);
    try {
      const r = await fetch(apiUrl(`/journeys/${selectedJourney.id}/variants`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newVariant),
      });
      const d = await r.json();
      if (r.ok) {
        setMsg({ type: 'success', text: `Variant "${newVariant.variant_name}" created` });
        setNewVariant({ variant_name: '', traffic_split_pct: 50 });
        loadVariants(selectedJourney);
      } else {
        setMsg({ type: 'error', text: d.detail || 'Failed to create variant' });
      }
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    }
    setCreating(false);
  };

  const promoteWinner = async (variantId) => {
    if (!window.confirm('Promote this variant as the winner? This will pause all other variants.')) return;
    try {
      const r = await fetch(apiUrl(`/journeys/${selectedJourney.id}/variants/${variantId}/promote`), { method: 'POST' });
      if (r.ok) {
        setMsg({ type: 'success', text: 'Variant promoted as winner' });
        loadVariants(selectedJourney);
      }
    } catch {}
  };

  const cvr = (v) => v.enrollments ? ((v.conversions / v.enrollments) * 100).toFixed(1) : '0.0';

  return (
    <div style={styles.twoCol}>
      {/* Journey List */}
      <div style={styles.leftCol}>
        <h3 style={styles.colTitle}>Select Journey</h3>
        {journeys.length === 0 ? (
          <p style={styles.emptyText}>No journeys found.</p>
        ) : (
          journeys.map((j) => (
            <div
              key={j.id}
              onClick={() => loadVariants(j)}
              style={{
                ...styles.journeyCard,
                borderColor: selectedJourney?.id === j.id ? '#3b82f6' : '#e5e7eb',
                background: selectedJourney?.id === j.id ? '#eff6ff' : 'white',
              }}
            >
              <div style={styles.journeyName}>{j.name}</div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                <span style={{ ...styles.chip, background: j.status === 'ACTIVE' ? '#d1fae5' : '#fef3c7', color: j.status === 'ACTIVE' ? '#065f46' : '#92400e' }}>{j.status}</span>
                <span style={{ ...styles.chip, background: '#f3f4f6', color: '#6b7280' }}>{j.entry_trigger}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Variants Panel */}
      <div style={styles.rightCol}>
        {msg && (
          <div style={{ ...styles.alertBox, background: msg.type === 'success' ? '#d1fae5' : '#fee2e2', color: msg.type === 'success' ? '#065f46' : '#991b1b' }}>
            {msg.text}
            <button onClick={() => setMsg(null)} style={styles.closeBtn}>✕</button>
          </div>
        )}

        {!selectedJourney ? (
          <div style={styles.placeholder}>← Select a journey to manage variants</div>
        ) : (
          <>
            <h3 style={styles.colTitle}>Variants for "{selectedJourney.name}"</h3>

            {/* Create Variant Form */}
            <div style={styles.formCard}>
              <h4 style={styles.formTitle}>Add New Variant</h4>
              <div style={styles.formRow}>
                <input
                  value={newVariant.variant_name}
                  onChange={(e) => setNewVariant({ ...newVariant, variant_name: e.target.value })}
                  placeholder="Variant name (e.g. Variant A)"
                  style={styles.input}
                />
                <div style={styles.splitInput}>
                  <label style={styles.inputLabel}>Traffic Split %</label>
                  <input
                    type="number"
                    min="1" max="99"
                    value={newVariant.traffic_split_pct}
                    onChange={(e) => setNewVariant({ ...newVariant, traffic_split_pct: parseInt(e.target.value) || 50 })}
                    style={{ ...styles.input, width: '80px' }}
                  />
                </div>
                <button
                  onClick={createVariant}
                  disabled={creating || !newVariant.variant_name.trim()}
                  style={{ ...styles.primaryBtn, opacity: creating ? 0.6 : 1 }}
                >
                  {creating ? 'Creating...' : '+ Add Variant'}
                </button>
              </div>
            </div>

            {/* Variants List */}
            {loading ? (
              <p style={styles.emptyText}>Loading variants...</p>
            ) : variants.length === 0 ? (
              <p style={styles.emptyText}>No variants yet. Create one above.</p>
            ) : (
              variants.map((v) => (
                <div key={v.id} style={styles.variantCard}>
                  <div style={styles.variantHeader}>
                    <div>
                      <span style={styles.variantName}>{v.variant_name}</span>
                      <span style={{ ...styles.chip, marginLeft: '8px', background: v.status === 'WINNER' ? '#fef3c7' : v.status === 'ACTIVE' ? '#d1fae5' : '#f3f4f6', color: v.status === 'WINNER' ? '#92400e' : v.status === 'ACTIVE' ? '#065f46' : '#6b7280' }}>
                        {v.status === 'WINNER' ? '🏆 Winner' : v.status}
                      </span>
                    </div>
                    <div style={styles.variantActions}>
                      {v.status !== 'WINNER' && (
                        <button onClick={() => promoteWinner(v.id)} style={styles.secondaryBtn}>
                          🏆 Promote Winner
                        </button>
                      )}
                    </div>
                  </div>
                  <div style={styles.metricsRow}>
                    <div style={styles.metricBox}>
                      <div style={styles.metricVal}>{v.traffic_split_pct}%</div>
                      <div style={styles.metricLbl}>Traffic Split</div>
                    </div>
                    <div style={styles.metricBox}>
                      <div style={styles.metricVal}>{v.enrollments}</div>
                      <div style={styles.metricLbl}>Enrolled</div>
                    </div>
                    <div style={styles.metricBox}>
                      <div style={styles.metricVal}>{v.conversions}</div>
                      <div style={styles.metricLbl}>Converted</div>
                    </div>
                    <div style={styles.metricBox}>
                      <div style={{ ...styles.metricVal, color: '#10b981' }}>{cvr(v)}%</div>
                      <div style={styles.metricLbl}>CVR</div>
                    </div>
                    <div style={styles.metricBox}>
                      <div style={{ ...styles.metricVal, color: '#8b5cf6' }}>₹{v.revenue?.toFixed(0) || 0}</div>
                      <div style={styles.metricLbl}>Revenue</div>
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Comparison Chart — shown when 2+ variants have data */}
            {variants.length >= 2 && <VariantComparisonChart variants={variants} cvr={cvr} />}
          </>
        )}
      </div>
    </div>
  );
}

/* ─── Variant Comparison Chart ─────────────────────────────────────────── */

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

function VariantComparisonChart({ variants, cvr }) {
  const [metric, setMetric] = useState('cvr');

  const chartData = variants.map((v) => ({
    name: v.variant_name,
    enrollments: v.enrollments || 0,
    conversions: v.conversions || 0,
    cvr: parseFloat(cvr(v)),
    revenue: parseFloat((v.revenue || 0).toFixed(0)),
    isWinner: v.status === 'WINNER',
  }));

  const metricConfig = {
    cvr:         { label: 'Conversion Rate (%)', unit: '%',  color: '#10b981' },
    enrollments: { label: 'Enrollments',          unit: '',   color: '#3b82f6' },
    revenue:     { label: 'Revenue (₹)',           unit: '₹', color: '#8b5cf6' },
    conversions: { label: 'Conversions',           unit: '',   color: '#f59e0b' },
  };

  const cfg = metricConfig[metric];

  return (
    <div style={styles.chartCard}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h4 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: '#1f2937' }}>
          Variant Performance Comparison
        </h4>
        <div style={{ display: 'flex', gap: '6px' }}>
          {Object.entries(metricConfig).map(([key, m]) => (
            <button
              key={key}
              onClick={() => setMetric(key)}
              style={{
                padding: '4px 10px',
                fontSize: '12px',
                fontWeight: '500',
                border: '1px solid',
                borderColor: metric === key ? m.color : '#d1d5db',
                background: metric === key ? m.color : 'white',
                color: metric === key ? 'white' : '#6b7280',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              {key === 'cvr' ? 'CVR' : key.charAt(0).toUpperCase() + key.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#9ca3af' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${cfg.unit}${v}`}
          />
          <Tooltip
            formatter={(value) => [`${cfg.unit}${value}`, cfg.label]}
            contentStyle={{ fontSize: '12px', borderRadius: '6px', border: '1px solid #e5e7eb' }}
          />
          <Bar dataKey={metric} radius={[4, 4, 0, 0]} maxBarSize={60}>
            {chartData.map((entry, i) => (
              <Cell
                key={`cell-${i}`}
                fill={entry.isWinner ? '#f59e0b' : CHART_COLORS[i % CHART_COLORS.length]}
                opacity={entry.isWinner ? 1 : 0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div style={{ display: 'flex', gap: '12px', marginTop: '12px', flexWrap: 'wrap' }}>
        {chartData.map((entry, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{
              width: '10px', height: '10px', borderRadius: '2px',
              background: entry.isWinner ? '#f59e0b' : CHART_COLORS[i % CHART_COLORS.length],
            }} />
            <span style={{ fontSize: '12px', color: '#6b7280' }}>
              {entry.name}{entry.isWinner ? ' 🏆' : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CloneTab() {
  const [journeys, setJourneys] = useState([]);
  const [cloning, setCloning] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetch(apiUrl('/journeys'))
      .then((r) => r.json())
      .then((d) => setJourneys(Array.isArray(d) ? d : (d.journeys || [])))
      .catch(() => {});
  }, []);

  const cloneJourney = async (journey) => {
    setCloning(journey.id);
    setMsg(null);
    try {
      const r = await fetch(apiUrl(`/journeys/${journey.id}/clone`), { method: 'POST' });
      const d = await r.json();
      if (r.ok) {
        setMsg({ type: 'success', text: `Cloned "${journey.name}" → "${d.name}" (ID: ${d.id.slice(0, 8)}...)` });
        const updated = await fetch(apiUrl('/journeys')).then((res) => res.json());
        setJourneys(Array.isArray(updated) ? updated : (updated.journeys || []));
      } else {
        setMsg({ type: 'error', text: d.detail || 'Clone failed' });
      }
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    }
    setCloning(null);
  };

  return (
    <div>
      <h3 style={{ margin: '0 0 8px', fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>Clone a Journey</h3>
      <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#6b7280' }}>
        Cloning creates a DRAFT copy with "(Copy)" suffix. Use it to test variants or create seasonal campaigns.
      </p>

      {msg && (
        <div style={{ ...styles.alertBox, marginBottom: '16px', background: msg.type === 'success' ? '#d1fae5' : '#fee2e2', color: msg.type === 'success' ? '#065f46' : '#991b1b' }}>
          {msg.text}
          <button onClick={() => setMsg(null)} style={styles.closeBtn}>✕</button>
        </div>
      )}

      <div style={styles.cloneGrid}>
        {journeys.map((j) => (
          <div key={j.id} style={styles.cloneCard}>
            <div style={styles.cloneCardHeader}>
              <div style={styles.journeyName}>{j.name}</div>
              <span style={{ ...styles.chip, background: j.status === 'ACTIVE' ? '#d1fae5' : '#fef3c7', color: j.status === 'ACTIVE' ? '#065f46' : '#92400e' }}>
                {j.status}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '12px' }}>
              {j.entry_trigger && <span>Trigger: {j.entry_trigger}</span>}
            </div>
            <button
              onClick={() => cloneJourney(j)}
              disabled={cloning === j.id}
              style={{ ...styles.primaryBtn, width: '100%', opacity: cloning === j.id ? 0.6 : 1 }}
            >
              {cloning === j.id ? 'Cloning...' : '📋 Clone Journey'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Bulk Enroll Tab ──────────────────────────────────────────────────── */

function BulkEnrollTab() {
  const [journeys, setJourneys] = useState([]);
  const [selectedJourneyId, setSelectedJourneyId] = useState('');
  const [csvContent, setCsvContent] = useState('');
  const [enrolling, setEnrolling] = useState(false);
  const [jobResult, setJobResult] = useState(null);
  const [msg, setMsg] = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    fetch(apiUrl('/journeys'))
      .then((r) => r.json())
      .then((d) => {
        const active = (Array.isArray(d) ? d : (d.journeys || [])).filter((j) => j.status === 'ACTIVE');
        setJourneys(active);
        if (active.length > 0) setSelectedJourneyId(active[0].id);
      })
      .catch(() => {});
  }, []);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setCsvContent(ev.target.result);
    reader.readAsText(file);
  };

  const parseCsvEmails = (csv) => {
    const lines = csv.trim().split('\n').filter(Boolean);
    if (lines.length === 0) return [];
    const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
    const emailIdx = headers.indexOf('email') !== -1 ? headers.indexOf('email') :
                     headers.indexOf('customer_email') !== -1 ? headers.indexOf('customer_email') : 0;
    return lines.slice(1)
      .map((l) => l.split(',')[emailIdx]?.trim().replace(/^"|"$/g, ''))
      .filter((e) => e && e.includes('@'));
  };

  const pollJob = async (jobId) => {
    let attempts = 0;
    while (attempts < 60) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const r = await fetch(apiUrl(`/jobs/${jobId}/status`));
        const d = await r.json();
        if (d.status === 'COMPLETED' || d.status === 'FAILED') {
          setJobResult(d);
          setMsg({
            type: d.status === 'COMPLETED' ? 'success' : 'error',
            text: d.status === 'COMPLETED'
              ? `Enrolled ${d.success_count} customers (${d.error_count} errors)`
              : `Job failed`,
          });
          setEnrolling(false);
          return;
        }
        setJobResult({ ...d, _polling: true });
      } catch {}
      attempts++;
    }
    setEnrolling(false);
  };

  const handleEnroll = async () => {
    if (!selectedJourneyId || !csvContent.trim()) return;
    const emails = parseCsvEmails(csvContent);
    if (emails.length === 0) {
      setMsg({ type: 'error', text: 'No valid email addresses found. CSV must have an "email" column.' });
      return;
    }
    setEnrolling(true);
    setMsg(null);
    setJobResult(null);
    try {
      const r = await fetch(apiUrl(`/journeys/${selectedJourneyId}/enroll-bulk`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emails }),
      });
      const d = await r.json();
      if (r.ok) {
        setMsg({ type: 'success', text: `Job started for ${d.total_rows} rows. Polling for results...` });
        setCsvContent('');
        pollJob(d.job_id);
      } else {
        setMsg({ type: 'error', text: d.detail || 'Enrollment failed' });
        setEnrolling(false);
      }
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
      setEnrolling(false);
    }
  };

  const sampleCsv = `email,first_name,last_name\ncustomer@example.com,Riya,Shah\nanother@example.com,Arun,Kumar`;

  return (
    <div style={{ maxWidth: '720px' }}>
      <h3 style={{ margin: '0 0 8px', fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>Bulk Enroll Customers</h3>
      <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#6b7280' }}>
        Upload a CSV of customer emails to enroll them into a journey. Required column: <code>email</code>. Optional: <code>first_name</code>, <code>last_name</code>, <code>phone</code>.
      </p>

      {msg && (
        <div style={{ ...styles.alertBox, marginBottom: '16px', background: msg.type === 'success' ? '#d1fae5' : '#fee2e2', color: msg.type === 'success' ? '#065f46' : '#991b1b' }}>
          {msg.text}
          <button onClick={() => setMsg(null)} style={styles.closeBtn}>✕</button>
        </div>
      )}

      {/* Select Journey */}
      <div style={styles.formGroup}>
        <label style={styles.inputLabel}>Select Journey</label>
        <select
          value={selectedJourneyId}
          onChange={(e) => setSelectedJourneyId(e.target.value)}
          style={{ ...styles.input, cursor: 'pointer' }}
        >
          {journeys.length === 0 && <option value="">No active journeys</option>}
          {journeys.map((j) => (
            <option key={j.id} value={j.id}>{j.name}</option>
          ))}
        </select>
      </div>

      {/* CSV Upload */}
      <div style={styles.formGroup}>
        <label style={styles.inputLabel}>Upload CSV File</label>
        <div
          style={styles.dropZone}
          onClick={() => fileRef.current?.click()}
        >
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>📂</div>
          <div style={{ fontSize: '14px', color: '#374151', fontWeight: '500' }}>Click to upload CSV</div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>or paste CSV content below</div>
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={handleFileUpload} style={{ display: 'none' }} />
        </div>
      </div>

      {/* CSV Textarea */}
      <div style={styles.formGroup}>
        <label style={styles.inputLabel}>CSV Content (paste or upload)</label>
        <textarea
          value={csvContent}
          onChange={(e) => setCsvContent(e.target.value)}
          placeholder={sampleCsv}
          rows={8}
          style={{ ...styles.input, fontFamily: 'monospace', fontSize: '12px', resize: 'vertical' }}
        />
        <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
          {csvContent.split('\n').filter(Boolean).length - 1} customer rows detected
        </div>
      </div>

      <button
        onClick={handleEnroll}
        disabled={enrolling || !selectedJourneyId || !csvContent.trim()}
        style={{ ...styles.primaryBtn, padding: '12px 32px', fontSize: '15px', opacity: enrolling || !csvContent.trim() ? 0.6 : 1 }}
      >
        {enrolling ? '⏳ Processing...' : '🚀 Start Bulk Enrollment'}
      </button>

      {/* Result */}
      {jobResult && (
        <div style={styles.resultCard}>
          <h4 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: '600', color: '#1f2937' }}>
            {jobResult._polling ? '⏳ Processing...' : 'Enrollment Results'}
          </h4>
          {jobResult._polling && (
            <div style={{ width: '100%', height: '6px', background: '#e5e7eb', borderRadius: '3px', marginBottom: '16px' }}>
              <div style={{ width: `${jobResult.progress_pct || 0}%`, height: '100%', background: '#3b82f6', borderRadius: '3px', transition: 'width 0.5s' }} />
            </div>
          )}
          <div style={{ display: 'flex', gap: '24px' }}>
            <div style={styles.resultStat}>
              <div style={{ ...styles.metricVal, color: '#10b981' }}>{jobResult.success_count || 0}</div>
              <div style={styles.metricLbl}>Enrolled</div>
            </div>
            <div style={styles.resultStat}>
              <div style={{ ...styles.metricVal, color: '#ef4444' }}>{jobResult.error_count || 0}</div>
              <div style={styles.metricLbl}>Errors</div>
            </div>
            <div style={styles.resultStat}>
              <div style={{ ...styles.metricVal, color: '#6b7280' }}>{jobResult.total_rows || 0}</div>
              <div style={styles.metricLbl}>Total Rows</div>
            </div>
          </div>
          {jobResult.error_rows && jobResult.error_rows.length > 0 && (
            <div style={{ marginTop: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: '#1f2937', marginBottom: '8px' }}>Error Details:</div>
              {jobResult.error_rows.map((row, i) => (
                <div key={i} style={{ fontSize: '12px', color: '#ef4444', padding: '4px 0', borderBottom: '1px solid #fee2e2' }}>
                  Row {row.row}: {row.email} — {row.reason}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Styles ───────────────────────────────────────────────────────────── */

const styles = {
  container: {
    padding: '24px 32px',
  },
  pageHeader: {
    marginBottom: '24px',
  },
  pageTitle: {
    margin: '0 0 4px',
    fontSize: '24px',
    fontWeight: '700',
    color: '#1f2937',
  },
  pageSubtitle: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280',
  },
  tabBar: {
    display: 'flex',
    gap: '8px',
    marginBottom: '24px',
  },
  tabBtn: {
    padding: '10px 20px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.15s',
  },
  tabContent: {
    background: 'white',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '280px 1fr',
    gap: '24px',
  },
  leftCol: {
    borderRight: '1px solid #e5e7eb',
    paddingRight: '24px',
  },
  rightCol: {
    flex: 1,
  },
  colTitle: {
    margin: '0 0 16px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#1f2937',
  },
  journeyCard: {
    padding: '12px 16px',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    marginBottom: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  journeyName: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#1f2937',
  },
  chip: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '500',
  },
  emptyText: {
    fontSize: '13px',
    color: '#9ca3af',
    textAlign: 'center',
    padding: '24px 0',
  },
  placeholder: {
    fontSize: '14px',
    color: '#9ca3af',
    padding: '48px 0',
    textAlign: 'center',
  },
  formCard: {
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '20px',
  },
  formTitle: {
    margin: '0 0 12px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
  },
  formRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-end',
  },
  formGroup: {
    marginBottom: '16px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
    outline: 'none',
  },
  inputLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
    marginBottom: '6px',
  },
  splitInput: {
    flexShrink: 0,
  },
  primaryBtn: {
    padding: '10px 20px',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s',
  },
  secondaryBtn: {
    padding: '6px 14px',
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '500',
  },
  variantCard: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '12px',
  },
  variantHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  variantName: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#1f2937',
  },
  variantActions: {
    display: 'flex',
    gap: '8px',
  },
  metricsRow: {
    display: 'flex',
    gap: '16px',
  },
  metricBox: {
    flex: 1,
    textAlign: 'center',
    padding: '8px',
    background: '#f9fafb',
    borderRadius: '6px',
  },
  metricVal: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#1f2937',
  },
  metricLbl: {
    fontSize: '11px',
    color: '#9ca3af',
    marginTop: '2px',
  },
  alertBox: {
    padding: '12px 16px',
    borderRadius: '6px',
    fontSize: '14px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    color: 'inherit',
    padding: '0 4px',
  },
  cloneGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '16px',
  },
  cloneCard: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '16px',
    background: 'white',
  },
  cloneCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '8px',
    gap: '8px',
  },
  dropZone: {
    border: '2px dashed #d1d5db',
    borderRadius: '8px',
    padding: '32px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  resultCard: {
    marginTop: '24px',
    padding: '20px',
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
  },
  resultStat: {
    textAlign: 'center',
  },
  chartCard: {
    marginTop: '24px',
    padding: '20px',
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
  },
};
