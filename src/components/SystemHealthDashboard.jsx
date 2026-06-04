import React, { useState, useEffect } from 'react';

/**
 * SystemHealthDashboard.jsx
 * 
 * Real-time system health monitoring dashboard.
 * Displays status of critical components: database, Redis, WebSocket, API latency, background jobs.
 * 
 * Features:
 * - Health status cards with real-time updates
 * - Metrics charts (last 24h)
 * - Recent issues list
 * - Active alerts
 * 
 * Updates every 10 seconds via polling.
 */
const SystemHealthDashboard = () => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(null);

  // Fetch comprehensive health check
  const fetchHealth = async () => {
    try {
      const response = await fetch('https://track.pureleven.com/api/monitoring/health');
      if (!response.ok) throw new Error('Failed to fetch health data');

      const raw = await response.json();
      // Normalize backend response to component's expected shape
      const components = raw.components || {};
      const data = {
        status: raw.overall_status || raw.status || 'unknown',
        timestamp: raw.collected_at || raw.timestamp || new Date().toISOString(),
        checks: {
          database:  components.database  || { status: 'unknown' },
          whatsapp:  components.whatsapp  || { status: 'unknown' },
          email:     components.email     || { status: 'unknown' },
          journeys:  components.journeys  || { status: 'unknown' },
          queue:     components.queue     || { status: 'unknown' },
          campaigns: components.campaigns || { status: 'unknown' },
          // Legacy keys for backwards compat with existing UI code
          redis:      { status: 'unknown', note: 'Not applicable (SQLite)' },
          websocket:  { status: 'unknown', note: 'Not monitored' },
          background_jobs: {
            status: components.queue?.status || 'unknown',
            pending: components.queue?.pending_campaigns || 0,
          },
        },
      };
      setHealthData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Health check error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch metrics from Prometheus
  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/metrics');
      if (response.ok) {
        // Prometheus returns plain text, we could parse it if needed
        return await response.text();
      }
    } catch (err) {
      console.error('Metrics fetch error:', err);
    }
  };

  // Initial load and setup polling
  useEffect(() => {
    fetchHealth();
    
    const interval = setInterval(() => {
      fetchHealth();
    }, 10000); // Poll every 10 seconds

    setRefreshInterval(interval);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const styles = {
    container: {
      padding: '24px',
      backgroundColor: '#f9fafb',
      minHeight: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    },
    header: {
      marginBottom: '32px',
    },
    title: {
      fontSize: '28px',
      fontWeight: '700',
      color: '#111827',
      margin: '0 0 8px 0',
    },
    subtitle: {
      fontSize: '14px',
      color: '#6b7280',
      margin: 0,
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: '16px',
      marginBottom: '32px',
    },
    card: {
      backgroundColor: 'white',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    },
    cardTitle: {
      fontSize: '14px',
      fontWeight: '600',
      color: '#6b7280',
      margin: '0 0 12px 0',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    statusBadge: {
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '20px',
      fontSize: '12px',
      fontWeight: '600',
      marginBottom: '12px',
    },
    statusHealthy: {
      backgroundColor: '#dcfce7',
      color: '#166534',
      border: '1px solid #bbf7d0',
    },
    statusDegraded: {
      backgroundColor: '#fef3c7',
      color: '#92400e',
      border: '1px solid #fcd34d',
    },
    statusUnhealthy: {
      backgroundColor: '#fee2e2',
      color: '#991b1b',
      border: '1px solid #fecaca',
    },
    metric: {
      marginBottom: '16px',
    },
    metricLabel: {
      fontSize: '12px',
      color: '#6b7280',
      marginBottom: '4px',
      fontWeight: '500',
    },
    metricValue: {
      fontSize: '20px',
      fontWeight: '600',
      color: '#1f2937',
    },
    metricUnit: {
      fontSize: '12px',
      color: '#9ca3af',
      marginLeft: '4px',
    },
    latencyBars: {
      display: 'flex',
      gap: '8px',
      alignItems: 'flex-end',
      height: '60px',
      marginTop: '8px',
    },
    latencyBar: {
      flex: 1,
      backgroundColor: '#3b82f6',
      borderRadius: '4px',
      position: 'relative',
      minHeight: '20px',
    },
    latencyLabel: {
      position: 'absolute',
      bottom: '-20px',
      left: 0,
      right: 0,
      textAlign: 'center',
      fontSize: '10px',
      color: '#6b7280',
    },
    section: {
      marginBottom: '32px',
    },
    sectionTitle: {
      fontSize: '18px',
      fontWeight: '700',
      color: '#111827',
      margin: '0 0 16px 0',
      paddingBottom: '8px',
      borderBottom: '2px solid #e5e7eb',
    },
    issueBox: {
      backgroundColor: 'white',
      border: '1px solid #fecaca',
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '12px',
    },
    issueTitle: {
      fontSize: '14px',
      fontWeight: '600',
      color: '#991b1b',
      margin: '0 0 4px 0',
    },
    issueDetail: {
      fontSize: '12px',
      color: '#6b7280',
      margin: 0,
    },
    emptyState: {
      textAlign: 'center',
      padding: '32px',
      color: '#6b7280',
    },
    refreshButton: {
      padding: '8px 16px',
      backgroundColor: '#3b82f6',
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      fontSize: '12px',
      fontWeight: '600',
      cursor: 'pointer',
      marginLeft: '12px',
    },
    timestamp: {
      fontSize: '12px',
      color: '#9ca3af',
      marginTop: '16px',
      paddingTop: '16px',
      borderTop: '1px solid #e5e7eb',
    },
  };

  if (loading && !healthData) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>⚙️ System Health</h1>
        </div>
        <div style={styles.emptyState}>
          <p>Loading system status...</p>
        </div>
      </div>
    );
  }

  if (error && !healthData) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>⚙️ System Health</h1>
        </div>
        <div style={{ ...styles.card, backgroundColor: '#fee2e2', borderColor: '#fecaca' }}>
          <p style={{ color: '#991b1b', margin: 0 }}>
            ❌ Failed to load health data: {error}
          </p>
        </div>
      </div>
    );
  }

  const checks = healthData?.checks || {};
  const overallStatus = healthData?.status || 'unknown';

  // Determine status styles
  const getStatusStyle = (status) => {
    if (status === 'healthy') return styles.statusHealthy;
    if (status === 'degraded') return styles.statusDegraded;
    return styles.statusUnhealthy;
  };

  const getStatusIcon = (status) => {
    if (status === 'healthy') return '✅';
    if (status === 'degraded') return '⚠️';
    return '❌';
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={styles.title}>⚙️ System Health</h1>
            <p style={styles.subtitle}>Real-time monitoring of critical infrastructure</p>
          </div>
          <button
            onClick={fetchHealth}
            style={styles.refreshButton}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Overall Status Badge */}
      <div style={styles.grid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Overall Status</h3>
          <div style={{
            ...styles.statusBadge,
            ...getStatusStyle(overallStatus),
          }}>
            {getStatusIcon(overallStatus)} {overallStatus.toUpperCase()}
          </div>
          <p style={{ fontSize: '12px', color: '#6b7280', margin: 0 }}>
            Last updated: {new Date(healthData?.timestamp).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Health Status Cards */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>🔍 Component Status</h2>
        <div style={styles.grid}>
          {/* Database */}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Database</h3>
            <div style={{
              ...styles.statusBadge,
              ...getStatusStyle(checks.database?.status),
            }}>
              {getStatusIcon(checks.database?.status)} {checks.database?.status?.toUpperCase() || 'UNKNOWN'}
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>Response Time</div>
              <div style={styles.metricValue}>
                {checks.database?.response_time_ms?.toFixed(2) || 'N/A'}
                <span style={styles.metricUnit}>ms</span>
              </div>
            </div>
            {checks.database?.error && (
              <p style={{ fontSize: '12px', color: '#991b1b', margin: '8px 0 0 0' }}>
                Error: {checks.database.error}
              </p>
            )}
          </div>

          {/* Redis */}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Cache (Redis)</h3>
            <div style={{
              ...styles.statusBadge,
              ...getStatusStyle(checks.redis?.status),
            }}>
              {getStatusIcon(checks.redis?.status)} {checks.redis?.status?.toUpperCase() || 'UNKNOWN'}
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>Response Time</div>
              <div style={styles.metricValue}>
                {checks.redis?.response_time_ms?.toFixed(2) || 'N/A'}
                <span style={styles.metricUnit}>ms</span>
              </div>
            </div>
            {checks.redis?.error && (
              <p style={{ fontSize: '12px', color: '#991b1b', margin: '8px 0 0 0' }}>
                Error: {checks.redis.error}
              </p>
            )}
          </div>

          {/* WebSocket */}
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Real-time (WebSocket)</h3>
            <div style={{
              ...styles.statusBadge,
              ...getStatusStyle(checks.websocket?.status),
            }}>
              {getStatusIcon(checks.websocket?.status)} {checks.websocket?.status?.toUpperCase() || 'UNKNOWN'}
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>Active Connections</div>
              <div style={styles.metricValue}>
                {checks.websocket?.active_connections || 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* API Latency */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>📊 API Performance</h2>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Response Time Distribution</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>P50 (Median)</div>
              <div style={styles.metricValue}>
                {checks.api_latency?.p50 || 0}
                <span style={styles.metricUnit}>ms</span>
              </div>
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>P95 (95th %ile)</div>
              <div style={styles.metricValue}>
                {checks.api_latency?.p95 || 0}
                <span style={styles.metricUnit}>ms</span>
              </div>
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>P99 (99th %ile)</div>
              <div style={styles.metricValue}>
                {checks.api_latency?.p99 || 0}
                <span style={styles.metricUnit}>ms</span>
              </div>
            </div>
          </div>

          <div style={styles.latencyBars}>
            <div style={{
              ...styles.latencyBar,
              height: `${(checks.api_latency?.p50 || 0) / 15}px`,
            }}>
              <div style={styles.latencyLabel}>P50</div>
            </div>
            <div style={{
              ...styles.latencyBar,
              height: `${(checks.api_latency?.p95 || 0) / 15}px`,
            }}>
              <div style={styles.latencyLabel}>P95</div>
            </div>
            <div style={{
              ...styles.latencyBar,
              height: `${(checks.api_latency?.p99 || 0) / 15}px`,
            }}>
              <div style={styles.latencyLabel}>P99</div>
            </div>
          </div>
        </div>
      </div>

      {/* Background Jobs */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>📋 Background Jobs</h2>
        <div style={styles.card}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>Pending</div>
              <div style={styles.metricValue}>
                {checks.background_jobs?.pending || 0}
              </div>
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>Running</div>
              <div style={styles.metricValue}>
                {checks.background_jobs?.running || 0}
              </div>
            </div>
            <div style={styles.metric}>
              <div style={styles.metricLabel}>Failed</div>
              <div style={{ ...styles.metricValue, color: checks.background_jobs?.failed > 0 ? '#ef4444' : '#10b981' }}>
                {checks.background_jobs?.failed || 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Issues */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>⚠️ Recent Issues</h2>
        {Object.entries(checks).some(([_, check]) => check?.error || check?.status === 'unhealthy') ? (
          <div>
            {Object.entries(checks).map(([name, check]) => {
              if (check?.error) {
                return (
                  <div key={name} style={styles.issueBox}>
                    <h4 style={styles.issueTitle}>❌ {name}</h4>
                    <p style={styles.issueDetail}>{check.error}</p>
                  </div>
                );
              }
              return null;
            })}
          </div>
        ) : (
          <div style={{ ...styles.card, backgroundColor: '#dcfce7', borderColor: '#bbf7d0' }}>
            <p style={{ color: '#166534', margin: 0 }}>✅ All systems operational</p>
          </div>
        )}
      </div>

      {/* Timestamp */}
      <div style={styles.timestamp}>
        Last updated: {new Date(healthData?.timestamp).toLocaleString()} | Auto-refresh: every 10s
      </div>
    </div>
  );
};

export default SystemHealthDashboard;
