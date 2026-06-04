/**
 * CRM Dashboard V2 - Phase 3.5+ Integration
 * Views: analytics | timeline | builder | live | abtest
 */

import React, { useState, useEffect } from 'react';
import useCrmStore from './crmStore';
import JourneyAnalyticsDashboard from './JourneyAnalyticsDashboard';
import CustomerTimelineView from './CustomerTimelineView';
import JourneyBuilderUI from './JourneyBuilderUI';
import ABTestingPanel from './ABTestingPanel';
import { useSocket } from './src/utils/socketClient';

export default function CRMDashboard() {
  const { view, setView, wsConnected, setWsConnected, updateMetricsData, addStepLog, stepLogs } = useCrmStore();
  const [selectedCustomerEmail, setSelectedCustomerEmail] = useState(null);

  // Phase 3.5: Connect WebSocket and wire to Zustand store
  const { connected, metricsData, stepLogs: socketLogs } = useSocket({
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onMetricsUpdate: (data) => updateMetricsData(data),
    onStepLog: (data) => addStepLog(data),
  });

  return (
    <div style={styles.container}>
      {/* Header & Navigation */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.titleRow}>
            <h1 style={styles.title}>🎯 Pure Leven CRM Dashboard</h1>
            {/* WebSocket status indicator */}
            <div style={styles.wsStatus}>
              <span style={{
                ...styles.wsIndicator,
                background: connected ? '#10b981' : '#ef4444',
              }} />
              <span style={styles.wsLabel}>{connected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
          <p style={styles.subtitle}>Customer journey orchestration & automation</p>
        </div>

        <nav style={styles.navTabs}>
          <NavButton label="📊 Journeys" view="analytics" activeView={view} onClick={() => setView('analytics')} />
          <NavButton label="👤 Timeline" view="timeline" activeView={view} onClick={() => setView('timeline')} />
          <NavButton label="🎨 Builder" view="builder" activeView={view} onClick={() => setView('builder')} />
          <NavButton label="⚡ Live Feed" view="live" activeView={view} onClick={() => setView('live')} badge={connected ? stepLogs.length : null} />
          <NavButton label="🧪 A/B Tests" view="abtest" activeView={view} onClick={() => setView('abtest')} />
        </nav>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        {view === 'analytics' && <JourneyAnalyticsDashboard />}

        {view === 'timeline' && (
          <TimelineSection
            selectedCustomerEmail={selectedCustomerEmail}
            setSelectedCustomerEmail={setSelectedCustomerEmail}
          />
        )}

        {view === 'builder' && <JourneyBuilderUI />}

        {view === 'live' && <LiveFeedPanel connected={connected} />}

        {view === 'abtest' && <ABTestingPanel />}
      </main>
    </div>
  );
}
        
        {view === 'timeline' && (
          <TimelineSection
            selectedCustomerEmail={selectedCustomerEmail}
            setSelectedCustomerEmail={setSelectedCustomerEmail}
          />
        )}

        {view === 'builder' && <JourneyBuilderUI />}
      </main>
    </div>
  );
}

/**
 * Navigation Button Component
 */
function NavButton({ label, view, activeView, onClick, badge }) {
  const isActive = view === activeView;
  return (
    <button
      onClick={onClick}
      style={{
        ...styles.navBtn,
        background: isActive ? '#3B82F6' : 'transparent',
        color: isActive ? 'white' : '#6b7280',
        borderBottom: isActive ? '2px solid #3B82F6' : '2px solid transparent',
        position: 'relative',
      }}
    >
      {label}
      {badge !== null && badge !== undefined && badge > 0 && (
        <span style={styles.badge}>{badge > 99 ? '99+' : badge}</span>
      )}
    </button>
  );
}

/**
 * Timeline Section with Customer Search
 */
function TimelineSection({ selectedCustomerEmail, setSelectedCustomerEmail }) {
  const [searchInput, setSearchInput] = useState('');
  const [customers, setCustomers] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const searchCustomers = async (email) => {
    if (!email.trim()) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `https://track.pureleven.com/api/crm/customers?skip=0&limit=20`
      );
      const data = await response.json();
      const filtered = (data.customers || []).filter((c) =>
        c.email?.toLowerCase().includes(email.toLowerCase())
      );
      setSearchResults(filtered);
    } catch (error) {
      console.error('Search error:', error);
    }
    setLoading(false);
  };

  return (
    <div style={styles.timelineSection}>
      {/* Customer Search */}
      <div style={styles.searchBox}>
        <h2 style={styles.sectionTitle}>🔍 Find Customer</h2>
        <div style={styles.searchContainer}>
          <input
            type="email"
            placeholder="Enter customer email..."
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              searchCustomers(e.target.value);
            }}
            style={styles.searchInput}
          />
          {searchResults.length > 0 && (
            <div style={styles.searchResults}>
              {searchResults.map((customer) => (
                <div
                  key={customer.id}
                  onClick={() => {
                    setSelectedCustomerEmail(customer.email);
                    setSearchInput('');
                    setSearchResults([]);
                  }}
                  style={styles.searchResultItem}
                >
                  <div style={styles.resultName}>
                    {customer.first_name} {customer.last_name}
                  </div>
                  <div style={styles.resultEmail}>{customer.email}</div>
                  <div style={styles.resultMeta}>
                    {customer.orders_count} orders • ₹{customer.total_spent}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Customer Timeline View */}
      {selectedCustomerEmail ? (
        <div style={styles.timelineContent}>
          <button
            onClick={() => setSelectedCustomerEmail(null)}
            style={styles.backBtn}
          >
            ← Back to search
          </button>
          <CustomerTimelineView customerEmail={selectedCustomerEmail} />
        </div>
      ) : (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>👤</div>
          <p>Search for a customer to view their journey timeline</p>
        </div>
      )}
    </div>
  );
}

/**
 * Live Feed Panel — shows real-time journey step logs from WebSocket
 */
function LiveFeedPanel({ connected }) {
  const { stepLogs, metricsData, clearStepLogs } = useCrmStore();

  const stepTypeColors = {
    email: '#3b82f6',
    whatsapp: '#10b981',
    delay: '#f59e0b',
    condition: '#8b5cf6',
    meta_audience: '#ec4899',
    google_audience: '#ef4444',
    add_tag: '#6b7280',
  };

  const stepStatusColors = {
    EXECUTED: '#10b981',
    SKIPPED: '#f59e0b',
    FAILED: '#ef4444',
    PENDING: '#9ca3af',
  };

  return (
    <div style={{ padding: '24px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '700', color: '#1f2937' }}>
            ⚡ Live Journey Feed
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#6b7280' }}>
            {connected ? `Real-time step events via WebSocket` : 'Connecting to WebSocket...'}
          </p>
        </div>
        <button
          onClick={clearStepLogs}
          style={{ padding: '8px 16px', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', color: '#374151' }}
        >
          Clear Logs
        </button>
      </div>

      {/* Live Metrics Summary */}
      {metricsData && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
          {[
            { label: 'Active Instances', value: metricsData.active_instances || 0, icon: '🚀', color: '#3b82f6' },
            { label: 'Steps Today', value: metricsData.steps_today || 0, icon: '⚡', color: '#10b981' },
            { label: 'Emails Sent', value: metricsData.emails_sent || 0, icon: '📧', color: '#f59e0b' },
            { label: 'Conversions', value: metricsData.conversions || 0, icon: '💰', color: '#8b5cf6' },
          ].map((m) => (
            <div key={m.label} style={{ background: 'white', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderLeft: `4px solid ${m.color}` }}>
              <div style={{ fontSize: '28px', marginBottom: '4px' }}>{m.icon}</div>
              <div style={{ fontSize: '28px', fontWeight: '700', color: '#1f2937' }}>{m.value}</div>
              <div style={{ fontSize: '13px', color: '#6b7280' }}>{m.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Step Logs */}
      <div style={{ background: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: connected ? '#10b981' : '#d1d5db', animation: connected ? 'pulse 2s infinite' : 'none' }} />
          <span style={{ fontSize: '14px', fontWeight: '600', color: '#1f2937' }}>
            Journey Step Events ({stepLogs.length})
          </span>
        </div>

        {stepLogs.length === 0 ? (
          <div style={{ padding: '48px', textAlign: 'center', color: '#9ca3af' }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>📭</div>
            <p style={{ margin: 0 }}>No step events yet. Journey steps will appear here in real-time.</p>
          </div>
        ) : (
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {[...stepLogs].reverse().map((log, idx) => (
              <div
                key={log.id || idx}
                style={{
                  padding: '12px 20px',
                  borderBottom: '1px solid #f3f4f6',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  animation: idx === 0 ? 'fadeIn 0.3s ease' : 'none',
                }}
              >
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: stepStatusColors[log.status] || '#9ca3af',
                  marginTop: '6px',
                  flexShrink: 0,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: '600',
                      background: stepTypeColors[log.step_type] ? stepTypeColors[log.step_type] + '20' : '#f3f4f6',
                      color: stepTypeColors[log.step_type] || '#374151',
                    }}>
                      {log.step_type || 'step'}
                    </span>
                    <span style={{ fontSize: '13px', fontWeight: '500', color: '#1f2937' }}>
                      {log.step_name || log.journey_name || 'Journey Step'}
                    </span>
                    <span style={{
                      marginLeft: 'auto',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: '600',
                      background: (stepStatusColors[log.status] || '#9ca3af') + '20',
                      color: stepStatusColors[log.status] || '#9ca3af',
                    }}>
                      {log.status || 'PENDING'}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                    {log.email && <span style={{ marginRight: '12px' }}>👤 {log.email}</span>}
                    {log.customer_id && <span style={{ marginRight: '12px' }}>ID: {log.customer_id.slice(0, 8)}...</span>}
                    <span>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'just now'}</span>
                  </div>
                  {log.result && (
                    <div style={{ marginTop: '6px', padding: '6px 10px', background: '#f9fafb', borderRadius: '4px', fontSize: '11px', color: '#6b7280', fontFamily: 'monospace' }}>
                      {typeof log.result === 'string' ? log.result : JSON.stringify(log.result).slice(0, 100)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#f9fafb',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
  },
  header: {
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
    padding: '20px 32px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  headerContent: {
    marginBottom: '16px',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '4px',
  },
  title: {
    margin: 0,
    fontSize: '28px',
    fontWeight: '700',
    color: '#1f2937',
  },
  wsStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    background: '#f3f4f6',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '500',
  },
  wsIndicator: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  wsLabel: {
    color: '#374151',
  },
  subtitle: {
    margin: 0,
    fontSize: '14px',
    color: '#6b7280',
  },
  navTabs: {
    display: 'flex',
    gap: '8px',
  },
  navBtn: {
    padding: '10px 16px',
    border: 'none',
    background: 'transparent',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  badge: {
    position: 'absolute',
    top: '4px',
    right: '4px',
    background: '#ef4444',
    color: 'white',
    fontSize: '10px',
    fontWeight: '700',
    borderRadius: '10px',
    padding: '1px 5px',
    lineHeight: '1.4',
  },
  main: {
    flex: 1,
    overflow: 'auto',
  },
  timelineSection: {
    padding: '24px 32px',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '18px',
    fontWeight: '600',
    color: '#1f2937',
  },
  searchBox: {
    background: 'white',
    padding: '24px',
    borderRadius: '8px',
    marginBottom: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  searchContainer: {
    position: 'relative',
  },
  searchInput: {
    width: '100%',
    padding: '12px 16px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
  },
  searchResults: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    background: 'white',
    border: '1px solid #d1d5db',
    borderTop: 'none',
    borderRadius: '0 0 6px 6px',
    maxHeight: '300px',
    overflowY: 'auto',
    zIndex: 10,
  },
  searchResultItem: {
    padding: '12px 16px',
    borderBottom: '1px solid #e5e7eb',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  resultName: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#1f2937',
  },
  resultEmail: {
    fontSize: '13px',
    color: '#6b7280',
    margin: '2px 0',
  },
  resultMeta: {
    fontSize: '12px',
    color: '#9ca3af',
    marginTop: '4px',
  },
  timelineContent: {
    position: 'relative',
  },
  backBtn: {
    marginBottom: '16px',
    padding: '8px 16px',
    background: '#e5e7eb',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
  },
  emptyState: {
    background: 'white',
    padding: '64px 32px',
    borderRadius: '8px',
    textAlign: 'center',
    color: '#6b7280',
  },
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
};
