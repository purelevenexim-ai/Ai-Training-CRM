/**
 * Customer Timeline View
 * Single-screen customer intelligence panel with journeys and message history
 * Priority 2 component
 */

import React, { useState, useEffect } from 'react';
import useCrmStore from '../utils/crmStore';

const API_BASE = 'https://track.pureleven.com/api';
const secret = () => localStorage.getItem('anu_admin_secret') || '';
const apiUrl = (path, p = {}) =>
  `${API_BASE}${path}?${new URLSearchParams({ admin_secret: secret(), ...p })}`;

const CustomerTimelineView = ({ customerEmail }) => {
  const {
    customerTimeline,
    fetchCustomerTimeline,
    enrollInJourney,
    pauseJourney,
    resumeJourney,
    loadingTimeline,
    error,
    clearError,
  } = useCrmStore();

  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [selectedJourneyForEnroll, setSelectedJourneyForEnroll] = useState(null);

  // Phase 4: Unified communication timeline
  const [unifiedTimeline, setUnifiedTimeline] = useState([]);
  const [unifiedSummary, setUnifiedSummary] = useState(null);
  const [unifiedLoading, setUnifiedLoading] = useState(false);
  const [unifiedError, setUnifiedError] = useState('');
  const [activeTimelineTab, setActiveTimelineTab] = useState('unified');

  useEffect(() => {
    if (customerEmail) {
      fetchCustomerTimeline(customerEmail);
    }
  }, [customerEmail]);

  useEffect(() => {
    if (!customerEmail) return;
    setUnifiedLoading(true);
    setUnifiedError('');
    fetch(apiUrl('/comm/timeline', { email: customerEmail }))
      .then(async (r) => {
        if (!r.ok) {
          let detail = `Timeline request failed (${r.status})`;
          try {
            const payload = await r.json();
            if (payload?.detail) {
              detail = payload.detail;
            }
          } catch {
            // Keep fallback detail.
          }
          throw new Error(detail);
        }
        return r.json();
      })
      .then(data => {
        setUnifiedTimeline(data.events || []);
        setUnifiedSummary(data.summary || null);
      })
      .catch((err) => {
        setUnifiedError(err?.message || 'Unable to load unified timeline');
      })
      .finally(() => setUnifiedLoading(false));
  }, [customerEmail]);

  if (loadingTimeline && !customerTimeline) {
    return <div style={styles.loader}>Loading customer timeline...</div>;
  }

  if (!customerTimeline) {
    return <div style={styles.error}>Customer not found</div>;
  }

  const customer = customerTimeline.customer || {};
  const activeJourneys = customerTimeline.active_journeys || [];
  const messages = customerTimeline.messages || [];
  const nextAction = customerTimeline.next_action;

  return (
    <div style={styles.container}>
      {/* Error Banner */}
      {error && (
        <div style={styles.errorBanner}>
          ⚠️ {error}
          <button onClick={clearError} style={{ marginLeft: '10px', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Customer Header */}
      <div style={styles.customerHeader}>
        <div style={styles.profileSection}>
          <div style={styles.avatar}>{customer.first_name?.[0] || 'C'}</div>
          <div>
            <h1 style={styles.customerName}>
              {customer.first_name} {customer.last_name}
            </h1>
            <p style={styles.customerEmail}>{customer.email}</p>
          </div>
        </div>

        <div style={styles.statsSection}>
          <div style={styles.stat}>
            <div style={styles.statLabel}>Orders</div>
            <div style={styles.statValue}>{customer.orders_count || 0}</div>
          </div>
          <div style={styles.stat}>
            <div style={styles.statLabel}>Total Spent</div>
            <div style={styles.statValue}>₹{(customer.total_spent || 0).toLocaleString()}</div>
          </div>
          <div style={styles.stat}>
            <div style={styles.statLabel}>Last Order</div>
            <div style={styles.statValue}>
              {customer.last_order_date
                ? new Date(customer.last_order_date).toLocaleDateString()
                : 'Never'}
            </div>
          </div>
        </div>
      </div>

      {/* Active Journeys */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>🚀 Active Journeys</h2>
        {activeJourneys.length > 0 ? (
          <div style={styles.journeyList}>
            {activeJourneys.map((journey, idx) => (
              <div key={idx} style={styles.journeyCard}>
                <div style={styles.journeyHeader}>
                  <div>
                    <h3 style={styles.journeyName}>{journey.journey_name}</h3>
                    <p style={styles.journeyStatus}>{journey.status}</p>
                  </div>
                  <div style={{...styles.progressBar, background: '#e5e7eb'}}>
                    <div
                      style={{
                        ...styles.progressFill,
                        width: `${journey.progress_pct}%`,
                        background: '#10B981',
                      }}
                    />
                  </div>
                </div>
                <div style={styles.journeyMeta}>
                  <span>Step {journey.current_step} / {journey.total_steps}</span>
                  <span>{journey.progress_pct}% complete</span>
                </div>
                <div style={styles.journeyActions}>
                  {journey.status === 'ACTIVE' ? (
                    <button
                      onClick={() => pauseJourney(journey.instance_id)}
                      style={styles.actionBtn}
                    >
                      ⏸ Pause
                    </button>
                  ) : (
                    <button
                      onClick={() => resumeJourney(journey.instance_id)}
                      style={styles.actionBtn}
                    >
                      ▶ Resume
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={styles.noData}>
            No active journeys. 
            <button
              onClick={() => setShowEnrollModal(true)}
              style={{ ...styles.link, marginLeft: '8px' }}
            >
              Enroll now →
            </button>
          </div>
        )}
      </div>

      {/* Next Scheduled Action */}
      {nextAction && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>⏰ Next Scheduled Action</h2>
          <div style={styles.actionCard}>
            <div style={styles.actionContent}>
              <div style={styles.actionType}>
                {nextAction.step_type === 'email' && '📧'}
                {nextAction.step_type === 'whatsapp' && '💬'}
                {nextAction.step_type === 'meta_audience' && '📱'}
                {nextAction.step_type === 'delay' && '⏳'}
                {' '}
                {nextAction.step_name}
              </div>
              {nextAction.scheduled_at && (
                <div style={styles.actionTime}>
                  Scheduled: {new Date(nextAction.scheduled_at).toLocaleString()}
                </div>
              )}
            </div>
            <button style={styles.overrideBtn}>Override</button>
          </div>
        </div>
      )}

      {/* Phase 4: Unified Activity Timeline */}
      <div style={styles.section}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h2 style={styles.sectionTitle}>📡 Activity Timeline</h2>
          <div style={{ display: 'flex', gap: 4 }}>
            {['unified', 'legacy'].map(t => (
              <button key={t} onClick={() => setActiveTimelineTab(t)}
                style={{ padding: '5px 14px', fontSize: 12, fontWeight: 600, border: '1px solid',
                  background: activeTimelineTab === t ? '#1d4ed8' : 'white',
                  color: activeTimelineTab === t ? 'white' : '#374151',
                  borderColor: activeTimelineTab === t ? '#1d4ed8' : '#d1d5db',
                  borderRadius: 20, cursor: 'pointer' }}>
                {t === 'unified' ? '📡 All Events' : '📬 Journey Msgs'}
              </button>
            ))}
          </div>
        </div>

        {/* Unified stats summary */}
        {unifiedSummary && (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            {[
              { label: 'Emails Sent', value: unifiedSummary.emails_sent, color: '#3b82f6' },
              { label: 'WA Sent', value: unifiedSummary.wa_messages_sent, color: '#25d366' },
              { label: 'Orders', value: unifiedSummary.shopify_orders, color: '#f59e0b' },
              { label: 'Spent', value: `₹${(unifiedSummary.shopify_total_spent || 0).toLocaleString()}`, color: '#10b981' },
            ].map(s => (
              <div key={s.label} style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 14px', textAlign: 'center', minWidth: 80 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {unifiedError && (
          <div style={styles.inlineWarning}>
            {unifiedError}
          </div>
        )}

        {activeTimelineTab === 'unified' && (
          unifiedLoading ? (
            <div style={{ textAlign: 'center', color: '#9ca3af', padding: 24 }}>Loading events…</div>
          ) : unifiedTimeline.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#9ca3af', padding: 24 }}>No activity yet</div>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              {unifiedTimeline.map((ev, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, padding: '10px 14px', background: '#f9fafb',
                  borderRadius: 8, borderLeft: `3px solid ${ev.color || '#9ca3af'}` }}>
                  <span style={{ fontSize: 18, flexShrink: 0 }}>{ev.icon || '•'}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{ev.title}</div>
                    {ev.subtitle && <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ev.subtitle}</div>}
                  </div>
                  <div style={{ fontSize: 11, color: '#9ca3af', whiteSpace: 'nowrap', flexShrink: 0 }}>
                    {ev.ts ? new Date(ev.ts).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {activeTimelineTab === 'legacy' && (
          messages.length > 0 ? (
            <div style={styles.timeline}>
              {messages.map((msg, idx) => (
                <div key={idx} style={styles.timelineItem}>
                  <div style={styles.timelineIcon}>
                    {msg.channel === 'email' && '📧'}
                    {msg.channel === 'whatsapp' && '💬'}
                  </div>
                  <div style={styles.timelineContent}>
                    <div style={styles.timelineTitle}>
                      {msg.channel === 'email' ? 'Email' : 'WhatsApp'}
                      {' • '}
                      <span style={styles.templateBadge}>{msg.template_id}</span>
                    </div>
                    <div style={styles.timelineTime}>{new Date(msg.sent_at).toLocaleString()}</div>
                    <div style={{ ...styles.statusBadge, backgroundColor: getStatusColor(msg.status) }}>{msg.status}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.noData}>No journey messages sent yet</div>
          )
        )}
      </div>

      {/* Enroll Modal */}
      {showEnrollModal && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h2>Enroll in Journey</h2>
            <p style={styles.noData}>Journey selection UI would go here (from journeys list)</p>
            <button onClick={() => setShowEnrollModal(false)} style={styles.closeBtn}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const getStatusColor = (status) => {
  const colors = {
    SENT: '#DBEAFE',
    OPENED: '#DCFCE7',
    CLICKED: '#FEF3C7',
    BOUNCED: '#FEE2E2',
    FAILED: '#FEE2E2',
  };
  return colors[status] || '#F3F4F6';
};

const styles = {
  container: {
    padding: '24px',
    background: '#f9fafb',
    minHeight: '100vh',
  },
  errorBanner: {
    background: '#FEE2E2',
    color: '#991B1B',
    padding: '12px 16px',
    borderRadius: '6px',
    marginBottom: '20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    border: '1px solid #FECACA',
  },
  inlineWarning: {
    background: '#FEF3C7',
    color: '#92400E',
    border: '1px solid #FCD34D',
    borderRadius: '6px',
    padding: '10px 12px',
    marginBottom: '12px',
    fontSize: '13px',
    fontWeight: '500',
  },
  loader: {
    textAlign: 'center',
    padding: '64px 24px',
    fontSize: '16px',
    color: '#6b7280',
  },
  error: {
    textAlign: 'center',
    padding: '64px 24px',
    color: '#dc2626',
    fontSize: '16px',
  },
  customerHeader: {
    background: 'white',
    padding: '24px',
    borderRadius: '8px',
    marginBottom: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '32px',
  },
  profileSection: {
    display: 'flex',
    gap: '16px',
    alignItems: 'center',
  },
  avatar: {
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    background: '#3B82F6',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    fontWeight: '700',
  },
  customerName: {
    margin: '0 0 4px 0',
    fontSize: '20px',
    fontWeight: '700',
    color: '#1f2937',
  },
  customerEmail: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280',
  },
  statsSection: {
    display: 'flex',
    gap: '32px',
  },
  stat: {
    textAlign: 'center',
  },
  statLabel: {
    fontSize: '12px',
    color: '#6b7280',
    fontWeight: '500',
    marginBottom: '4px',
  },
  statValue: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#1f2937',
  },
  section: {
    background: 'white',
    padding: '24px',
    borderRadius: '8px',
    marginBottom: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '18px',
    fontWeight: '600',
    color: '#1f2937',
  },
  journeyList: {
    display: 'grid',
    gap: '12px',
  },
  journeyCard: {
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '16px',
    background: '#f9fafb',
  },
  journeyHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '8px',
  },
  journeyName: {
    margin: 0,
    fontSize: '16px',
    fontWeight: '600',
    color: '#1f2937',
  },
  journeyStatus: {
    margin: '4px 0 0 0',
    fontSize: '12px',
    color: '#6b7280',
  },
  progressBar: {
    width: '100px',
    height: '6px',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    transition: 'width 0.3s',
  },
  journeyMeta: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#6b7280',
    marginBottom: '12px',
  },
  journeyActions: {
    display: 'flex',
    gap: '8px',
  },
  actionBtn: {
    padding: '6px 12px',
    background: '#3B82F6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '500',
  },
  actionCard: {
    background: '#EFF6FF',
    border: '1px solid #BFDBFE',
    borderRadius: '6px',
    padding: '16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  actionContent: {
    flex: 1,
  },
  actionType: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: '4px',
  },
  actionTime: {
    fontSize: '12px',
    color: '#6b7280',
  },
  overrideBtn: {
    padding: '8px 16px',
    background: '#F59E0B',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  timeline: {
    display: 'grid',
    gap: '12px',
  },
  timelineItem: {
    display: 'flex',
    gap: '12px',
    padding: '12px',
    background: '#f9fafb',
    borderRadius: '6px',
    borderLeft: '2px solid #3B82F6',
  },
  timelineIcon: {
    fontSize: '20px',
  },
  timelineContent: {
    flex: 1,
  },
  timelineTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#1f2937',
  },
  templateBadge: {
    background: '#F3F4F6',
    padding: '2px 6px',
    borderRadius: '3px',
    fontSize: '12px',
    color: '#6b7280',
  },
  timelineTime: {
    fontSize: '12px',
    color: '#6b7280',
    margin: '4px 0',
  },
  statusBadge: {
    display: 'inline-block',
    padding: '4px 8px',
    borderRadius: '3px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#374151',
  },
  noData: {
    textAlign: 'center',
    color: '#9ca3af',
    padding: '32px',
    fontSize: '14px',
  },
  link: {
    background: 'none',
    border: 'none',
    color: '#3B82F6',
    cursor: 'pointer',
    textDecoration: 'underline',
    padding: 0,
    fontSize: '14px',
  },
  modal: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    background: 'white',
    padding: '32px',
    borderRadius: '8px',
    maxWidth: '500px',
    width: '90%',
  },
  closeBtn: {
    padding: '8px 16px',
    background: '#E5E7EB',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginTop: '16px',
  },
};

export default CustomerTimelineView;
