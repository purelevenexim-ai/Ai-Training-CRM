/**
 * CRM Dashboard V2 - Phase 3.5+ Integration
 * Views: analytics | timeline | builder | live | abtest
 */

import React, { useEffect, useState } from 'react';
import useCrmStore from '../utils/crmStore';
import JourneyAnalyticsDashboard from './JourneyAnalyticsDashboard';
import CustomerTimelineView from './CustomerTimelineView';
import JourneyBuilderUI from './JourneyBuilderUI';
import ABTestingPanel from './ABTestingPanel';
import WhatsAppPanel from './WhatsAppPanel';
import EmailCampaignsPanel from './EmailCampaignsPanel';
import ReviewJourneyPanel from './ReviewJourneyPanel';
import SystemHealthDashboard from './SystemHealthDashboard';
import LeadManagerPanel from './LeadManagerPanel';
import ContactsPanel from './ContactsPanel';
import CampaignBuilderPanel from './CampaignBuilderPanel';
import UnifiedAnalyticsPanel from './UnifiedAnalyticsPanel';
import ShopifyIntegrationPanel from './ShopifyIntegrationPanel';
import AIBrainPanel from './AIBrainPanel';
import TrackingAttributionPanel from './TrackingAttributionPanel';
import { useSocket } from '../utils/socketClient';

const ADMIN_KEY = 'anu_admin_secret';
const OWNER_ADMIN_KEY = 'anu_owner_secret';

const DEFAULT_AI_CONTROL = {
  ai_running: true,
  selected_model: 'gemini_flash',
  temperature: 0.25,
  languages: ['english', 'manglish', 'malayalam'],
  followup_send_enabled: false,
  available_models: [],
};

function resolveInitialAdminSecret() {
  if (typeof window === 'undefined') {
    return '';
  }
  return localStorage.getItem(ADMIN_KEY) || localStorage.getItem(OWNER_ADMIN_KEY) || window.__ADMIN_SECRET__ || '';
}

const EXTERNAL_TOOLS = [
  { label: 'n8n', href: 'https://automations.pureleven.com', tone: '#3b82f6' },
  { label: 'Plunk', href: 'https://plunk.pureleven.com', tone: '#10b981' },
  { label: 'API Docs', href: 'https://track.pureleven.com/api/docs', tone: '#8b5cf6' },
  { label: 'Health API', href: 'https://track.pureleven.com/api/health', tone: '#f59e0b' },
];

const WORKSPACES = [
  {
    id: 'journeys',
    label: 'Journeys',
    icon: '📊',
    summary: 'Build, monitor, and test automations',
    views: [
      { label: 'Journey Analytics', icon: '📈', view: 'analytics' },
      { label: 'Builder', icon: '🔁', view: 'builder' },
      { label: 'Live Feed', icon: '⚡', view: 'live', liveBadge: true },
      { label: 'A/B Tests', icon: '🧪', view: 'abtest' },
      { label: 'Reviews', icon: '🌿', view: 'review_journey' },
    ],
  },
  {
    id: 'customers',
    label: 'People',
    icon: '👥',
    summary: 'Contacts, leads, and customer timelines',
    views: [
      { label: 'Contacts', icon: '👥', view: 'contacts' },
      { label: 'Timeline', icon: '👤', view: 'timeline' },
      { label: 'Leads', icon: '📋', view: 'leads' },
    ],
  },
  {
    id: 'messaging',
    label: 'Messaging',
    icon: '💬',
    summary: 'WhatsApp, email, and campaigns',
    views: [
      { label: 'WhatsApp', icon: '💬', view: 'whatsapp' },
      { label: 'Email', icon: '📧', view: 'email' },
      { label: 'Campaigns', icon: '📢', view: 'campaigns' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    icon: '🧠',
    summary: 'Performance analytics and AI decisions',
    views: [
      { label: 'Analytics', icon: '📈', view: 'comm_analytics' },
      { label: 'AI Brain', icon: '🧠', view: 'ai_brain' },
    ],
  },
  {
    id: 'operations',
    label: 'Ops',
    icon: '🩺',
    summary: 'Shopify sync and system health',
    views: [
      { label: 'Shopify', icon: '🛍️', view: 'shopify' },
      { label: 'Tracking', icon: '🎯', view: 'tracking' },
      { label: 'Health', icon: '🩺', view: 'health' },
    ],
  },
];

const QUICK_LINKS = [
  { label: 'Timeline', icon: '👤', view: 'timeline' },
  { label: 'WhatsApp', icon: '💬', view: 'whatsapp' },
  { label: 'Email', icon: '📧', view: 'email' },
  { label: 'Health', icon: '🩺', view: 'health' },
];

function workspaceForView(view) {
  return WORKSPACES.find((workspace) => workspace.views.some((item) => item.view === view)) || WORKSPACES[0];
}

export default function CRMDashboard() {
  const { view, setView, setWsConnected, updateMetricsData, addStepLog, stepLogs } = useCrmStore();
  const [selectedCustomerEmail, setSelectedCustomerEmail] = useState(null);
  const [aiControl, setAiControl] = useState(DEFAULT_AI_CONTROL);
  const [aiControlSaving, setAiControlSaving] = useState(false);
  const [adminSecret, setAdminSecret] = useState(() => {
    const nextSecret = resolveInitialAdminSecret();
    if (nextSecret) {
      localStorage.setItem(ADMIN_KEY, nextSecret);
      window.__ADMIN_SECRET__ = nextSecret;
    }
    return nextSecret;
  });

  // Phase 3.5: Connect WebSocket and wire to Zustand store
  const { connected } = useSocket({
    token: adminSecret,
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onMetricsUpdate: (data) => updateMetricsData(data),
    onStepLog: (data) => addStepLog(data),
  });

  const activeWorkspace = workspaceForView(view);
  const activeWorkspaceViews = activeWorkspace.views;
  const visibleQuickLinks = QUICK_LINKS.filter(
    (item) => !activeWorkspaceViews.some((workspaceItem) => workspaceItem.view === item.view)
  );

  useEffect(() => {
    if (!adminSecret) {
      setAiControl(DEFAULT_AI_CONTROL);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const response = await fetch('/api/owner/dashboard/ai-control', {
          headers: {
            'x-anu-admin-secret': adminSecret,
          },
        });

        if (!response.ok) {
          throw new Error(`AI control load failed: ${response.status}`);
        }

        const payload = await response.json();
        if (!cancelled) {
          setAiControl({ ...DEFAULT_AI_CONTROL, ...payload });
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('Failed to load AI control settings:', error);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [adminSecret]);

  async function saveAiControl(nextControl) {
    if (!adminSecret) return;
    setAiControlSaving(true);
    try {
      const response = await fetch('/api/owner/dashboard/ai-control', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'x-anu-admin-secret': adminSecret,
        },
        body: JSON.stringify(nextControl),
      });

      if (!response.ok) {
        throw new Error(`AI control update failed: ${response.status}`);
      }

      const payload = await response.json();
      setAiControl({ ...DEFAULT_AI_CONTROL, ...payload });
    } catch (error) {
      console.error('Failed to update AI control:', error);
    } finally {
      setAiControlSaving(false);
    }
  }

  function toggleAiRunning() {
    saveAiControl({ ...aiControl, ai_running: !aiControl.ai_running });
  }

  function toggleFollowupSending() {
    saveAiControl({ ...aiControl, followup_send_enabled: !aiControl.followup_send_enabled });
  }

  return (
    <div style={styles.container}>
      <div style={styles.externalBar}>
        <span style={styles.externalLabel}>External Tools</span>
        <div style={styles.externalLinks}>
          {EXTERNAL_TOOLS.map((tool) => (
            <a
              key={tool.label}
              href={tool.href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ ...styles.externalLink, color: tool.tone, borderColor: `${tool.tone}33`, background: `${tool.tone}10` }}
            >
              {tool.label}
            </a>
          ))}
        </div>
      </div>

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

        <AdminAccessControl
          adminSecret={adminSecret}
          aiControl={aiControl}
          aiControlSaving={aiControlSaving}
          onToggleAiRunning={toggleAiRunning}
          onToggleFollowupSending={toggleFollowupSending}
          onSave={(value) => {
            localStorage.setItem(ADMIN_KEY, value);
            window.__ADMIN_SECRET__ = value;
            setAdminSecret(value);
            window.dispatchEvent(new Event('anu-admin-secret-updated'));
          }}
          onClear={() => {
            localStorage.removeItem(ADMIN_KEY);
            delete window.__ADMIN_SECRET__;
            setAdminSecret('');
            setAiControl(DEFAULT_AI_CONTROL);
            setAiControlSaving(false);
            window.dispatchEvent(new Event('anu-admin-secret-updated'));
          }}
        />

        <nav style={styles.navShell} aria-label="CRM workspace navigation">
          <div style={styles.workspaceRow}>
            {WORKSPACES.map((workspace) => (
              <WorkspaceButton
                key={workspace.id}
                workspace={workspace}
                isActive={workspace.id === activeWorkspace.id}
                onClick={() => setView(workspace.views[0].view)}
              />
            ))}
          </div>

          <div style={styles.subNavRow}>
            <div style={styles.subNavMeta}>
              <span style={styles.subNavLabel}>{activeWorkspace.label}</span>
              <span style={styles.subNavSummary}>{activeWorkspace.summary}</span>
            </div>
            <div style={styles.subNavButtons}>
              {activeWorkspaceViews.map((item) => (
                <NavButton
                  key={item.view}
                  label={`${item.icon} ${item.label}`}
                  view={item.view}
                  activeView={view}
                  onClick={() => setView(item.view)}
                  badge={item.liveBadge && connected ? stepLogs.length : null}
                />
              ))}
            </div>
            {visibleQuickLinks.length > 0 && (
              <div style={styles.quickNav}>
                <span style={styles.quickDivider}>Quick</span>
                {visibleQuickLinks.map((item) => (
                  <NavButton
                    key={item.view}
                    label={`${item.icon} ${item.label}`}
                    view={item.view}
                    activeView={view}
                    onClick={() => setView(item.view)}
                  />
                ))}
              </div>
            )}
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        {view === 'analytics' && <JourneyAnalyticsDashboard />}

        {view === 'contacts' && <ContactsPanel />}

        {view === 'timeline' && (
          <TimelineSection
            selectedCustomerEmail={selectedCustomerEmail}
            setSelectedCustomerEmail={setSelectedCustomerEmail}
          />
        )}

        {view === 'leads' && <LeadManagerPanel />}

        {view === 'builder' && <JourneyBuilderUI />}

        {view === 'live' && <LiveFeedPanel connected={connected} />}

        {view === 'abtest' && <ABTestingPanel />}

        {view === 'whatsapp' && <WhatsAppPanel />}

        {view === 'email' && <EmailCampaignsPanel />}

        {view === 'review_journey' && <ReviewJourneyPanel />}

        {view === 'campaigns' && <CampaignBuilderPanel />}

        {view === 'comm_analytics' && <UnifiedAnalyticsPanel />}

        {view === 'ai_brain' && <AIBrainPanel />}

        {view === 'shopify' && <ShopifyIntegrationPanel />}

        {view === 'tracking' && <TrackingAttributionPanel />}

        {view === 'health' && <SystemHealthDashboard />}
      </main>
    </div>
  );
}

function AdminAccessControl({
  adminSecret,
  aiControl,
  aiControlSaving,
  onToggleAiRunning,
  onToggleFollowupSending,
  onSave,
  onClear,
}) {
  const [draft, setDraft] = useState('');

  if (adminSecret) {
    return (
      <div style={styles.adminAccessBar}>
        <span style={styles.adminAccessPill}>Admin access active</span>
        <span style={styles.adminAccessHint}>Protected dashboards and live feeds can load in this browser.</span>
        <span style={styles.adminAccessPill}>{aiControl?.ai_running ? 'AI Running' : 'AI Paused'}</span>
        <span style={styles.adminAccessHint}>Model: {aiControl?.selected_model || 'gemini_flash'}</span>
        <button
          type="button"
          onClick={onToggleAiRunning}
          disabled={aiControlSaving}
          style={{ ...styles.adminAccessButton, opacity: aiControlSaving ? 0.65 : 1 }}
        >
          {aiControl?.ai_running ? 'Turn AI Off' : 'Turn AI On'}
        </button>
        <button
          type="button"
          onClick={onToggleFollowupSending}
          disabled={aiControlSaving}
          style={{ ...styles.adminAccessButtonSecondary, opacity: aiControlSaving ? 0.65 : 1 }}
        >
          {aiControl?.followup_send_enabled ? 'Pause Follow-ups' : 'Enable Follow-ups'}
        </button>
        <button type="button" onClick={onClear} style={styles.adminAccessButtonSecondary}>
          Clear
        </button>
      </div>
    );
  }

  return (
    <div style={styles.adminAccessBar}>
      <span style={styles.adminAccessWarning}>Admin access required</span>
      <input
        type="password"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Enter admin secret"
        aria-label="Admin secret"
        style={styles.adminAccessInput}
      />
      <button
        type="button"
        onClick={() => {
          const value = draft.trim();
          if (!value) return;
          onSave(value);
          setDraft('');
        }}
        disabled={!draft.trim()}
        style={{ ...styles.adminAccessButton, opacity: draft.trim() ? 1 : 0.55 }}
      >
        Save Access
      </button>
    </div>
  );
}

/**
 * Navigation Button Component
 */
function WorkspaceButton({ workspace, isActive, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={workspace.summary}
      aria-pressed={isActive}
      style={{
        ...styles.workspaceBtn,
        ...(isActive ? styles.workspaceBtnActive : {}),
      }}
    >
      <span style={styles.workspaceIcon}>{workspace.icon}</span>
      <span style={styles.workspaceText}>
        <span style={styles.workspaceLabel}>{workspace.label}</span>
        <span style={styles.workspaceSummary}>{workspace.summary}</span>
      </span>
    </button>
  );
}

function NavButton({ label, view, activeView, onClick, badge }) {
  const isActive = view === activeView;
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        ...styles.navBtn,
        background: isActive ? '#111827' : 'white',
        color: isActive ? 'white' : '#4b5563',
        borderColor: isActive ? '#111827' : '#e5e7eb',
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
      const url = new URL('https://track.pureleven.com/api/customers');
      url.searchParams.set('skip', '0');
      url.searchParams.set('limit', '20');
      const adminSecret = window.localStorage.getItem(ADMIN_KEY) || window.__ADMIN_SECRET__ || '';
      if (adminSecret) {
        url.searchParams.set('admin_secret', adminSecret);
      }
      const response = await fetch(url.toString());
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
    flex: 1,
    background: '#f9fafb',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
  },
  externalBar: {
    background: 'white',
    borderTop: '1px solid #e5e7eb',
    borderBottom: '1px solid #e5e7eb',
    padding: '8px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    flexWrap: 'wrap',
    flexShrink: 0,
  },
  externalLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#9ca3af',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  externalLinks: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  externalLink: {
    padding: '5px 10px',
    fontSize: '12px',
    borderRadius: '999px',
    border: '1px solid',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    textDecoration: 'none',
    lineHeight: 1.2,
  },
  header: {
    background: 'white',
    borderBottom: '1px solid #e5e7eb',
    padding: '18px 32px 16px',
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
  adminAccessBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
    padding: '10px 12px',
    marginBottom: '12px',
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
  },
  adminAccessPill: {
    padding: '4px 9px',
    borderRadius: '999px',
    background: '#dcfce7',
    color: '#166534',
    fontSize: '12px',
    fontWeight: '800',
  },
  adminAccessWarning: {
    padding: '4px 9px',
    borderRadius: '999px',
    background: '#fffbeb',
    color: '#92400e',
    fontSize: '12px',
    fontWeight: '800',
  },
  adminAccessHint: {
    color: '#6b7280',
    fontSize: '12px',
    marginRight: 'auto',
  },
  adminAccessInput: {
    width: '220px',
    maxWidth: '100%',
    padding: '7px 10px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '12px',
    outline: 'none',
  },
  adminAccessButton: {
    padding: '7px 11px',
    border: '1px solid #111827',
    borderRadius: '6px',
    background: '#111827',
    color: 'white',
    fontSize: '12px',
    fontWeight: '800',
    cursor: 'pointer',
  },
  adminAccessButtonSecondary: {
    marginLeft: 'auto',
    padding: '7px 11px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    background: 'white',
    color: '#374151',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  navShell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  workspaceRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(156px, 1fr))',
    gap: '8px',
  },
  workspaceBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    minHeight: '58px',
    padding: '10px 12px',
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.15s ease',
  },
  workspaceBtnActive: {
    background: '#111827',
    borderColor: '#111827',
    color: 'white',
    boxShadow: '0 6px 14px rgba(17, 24, 39, 0.16)',
  },
  workspaceIcon: {
    width: '28px',
    height: '28px',
    borderRadius: '8px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(255,255,255,0.18)',
    flexShrink: 0,
  },
  workspaceText: {
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  workspaceLabel: {
    fontSize: '13px',
    fontWeight: '800',
    lineHeight: 1.1,
  },
  workspaceSummary: {
    fontSize: '11px',
    fontWeight: '500',
    color: 'inherit',
    opacity: 0.72,
    lineHeight: 1.25,
  },
  subNavRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
    padding: '10px',
    background: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
  },
  subNavMeta: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: '140px',
    marginRight: '4px',
  },
  subNavLabel: {
    fontSize: '12px',
    fontWeight: '800',
    color: '#111827',
  },
  subNavSummary: {
    fontSize: '11px',
    color: '#6b7280',
  },
  subNavButtons: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
  },
  quickNav: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
    marginLeft: 'auto',
  },
  quickDivider: {
    fontSize: '10px',
    fontWeight: '800',
    color: '#9ca3af',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  navBtn: {
    minHeight: '34px',
    padding: '7px 11px',
    border: '1px solid #e5e7eb',
    borderRadius: '999px',
    background: 'white',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '700',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
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
