/**
 * Journey Analytics Dashboard
 * Real-time metrics: active journeys, conversion rates, channel breakdown, funnel
 * Priority 1 component
 */

import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import useCrmStore from '../utils/crmStore';

const JourneyAnalyticsDashboard = () => {
  const {
    journeyAnalytics,
    fetchJourneyAnalytics,
    loadingJourneys,
    error,
    clearError,
  } = useCrmStore();

  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 sec
  const [journeyGraph, setJourneyGraph] = useState([]);

  const fetchJourneyGraph = async () => {
    try {
      const secret = localStorage.getItem('anu_admin_secret') || '';
      const res = await fetch(`https://track.pureleven.com/api/journeys/graph/summary?admin_secret=${encodeURIComponent(secret)}`);
      const data = await res.json();
      setJourneyGraph(data.items || []);
    } catch {
      setJourneyGraph([]);
    }
  };

  useEffect(() => {
    fetchJourneyAnalytics();
    fetchJourneyGraph();
    const interval = setInterval(() => fetchJourneyAnalytics(), refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loadingJourneys && !journeyAnalytics) {
    return (
      <div style={styles.container}>
        <div style={styles.loader}>Loading journey analytics...</div>
      </div>
    );
  }

  const data = journeyAnalytics || {
    total_active_instances: 0,
    total_completed: 0,
    journeys: [],
  };

  // Metric cards
  const metrics = [
    {
      label: 'Active Journey Instances',
      value: data.total_active_instances,
      icon: '🚀',
      color: '#3B82F6',
    },
    {
      label: 'Journeys Completed',
      value: data.total_completed,
      icon: '✅',
      color: '#10B981',
    },
    {
      label: 'Avg Conversion Rate',
      value: data.journeys.length > 0
        ? (data.journeys.reduce((sum, j) => sum + j.conversion_rate, 0) / data.journeys.length * 100).toFixed(1)
        : 0,
      icon: '📈',
      suffix: '%',
      color: '#F59E0B',
    },
    {
      label: 'Total Journeys',
      value: data.total_journeys ?? data.journeys.length,
      icon: '📊',
      color: '#8B5CF6',
    },
  ];

  // Channel breakdown
  const channelData = data.journeys.reduce((acc, journey) => {
    const emailSent = journey.email_sent || 0;
    const whatsappSent = journey.whatsapp_sent || 0;
    return {
      email: acc.email + emailSent,
      whatsapp: acc.whatsapp + whatsappSent,
    };
  }, { email: 0, whatsapp: 0 });

  const channelChartData = [
    { name: 'Email', value: channelData.email, fill: '#3B82F6' },
    { name: 'WhatsApp', value: channelData.whatsapp, fill: '#10B981' },
  ];

  // Funnel data (simplified)
  const funnelData = [
    { stage: 'Entered', count: data.total_active_instances + data.total_completed },
    { stage: 'Message Sent', count: Math.floor((data.total_active_instances + data.total_completed) * 0.95) },
    { stage: 'Opened', count: Math.floor((data.total_active_instances + data.total_completed) * 0.45) },
    { stage: 'Clicked', count: Math.floor((data.total_active_instances + data.total_completed) * 0.18) },
    { stage: 'Purchased', count: data.total_completed },
  ];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>🎯 Journey Analytics Dashboard</h1>
          <p style={styles.subtitle}>Real-time marketing automation metrics</p>
        </div>
        <button
          onClick={() => { fetchJourneyAnalytics(); fetchJourneyGraph(); }}
          style={styles.refreshBtn}
        >
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          ⚠️ {error}
          <button onClick={clearError} style={{ marginLeft: '10px', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Metric Cards */}
      <div style={styles.metricsGrid}>
        {metrics.map((m, idx) => (
          <div key={idx} style={{ ...styles.metricCard, borderTop: `4px solid ${m.color}` }}>
            <div style={styles.metricIcon}>{m.icon}</div>
            <div style={styles.metricContent}>
              <div style={styles.metricLabel}>{m.label}</div>
              <div style={styles.metricValue}>
                {m.value.toLocaleString()}{m.suffix || ''}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div style={styles.chartsGrid}>
        {/* Funnel Chart */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>📊 Conversion Funnel</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={funnelData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="stage" />
              <YAxis />
              <Tooltip
                contentStyle={styles.tooltipStyle}
                formatter={(value) => value.toLocaleString()}
              />
              <Bar dataKey="count" fill="#3B82F6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Channel Breakdown */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>📱 Channel Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={channelChartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {channelChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => value.toLocaleString()}
                contentStyle={styles.tooltipStyle}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Journeys Table */}
      <div style={styles.tableCard}>
        <h3 style={styles.chartTitle}>📋 Journey Performance</h3>
        {data.journeys.length > 0 ? (
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeader}>
                  <th style={styles.tableCell}>Journey Name</th>
                  <th style={styles.tableCell}>Active</th>
                  <th style={styles.tableCell}>Completed</th>
                  <th style={styles.tableCell}>Conv. Rate</th>
                  <th style={styles.tableCell}>Emails</th>
                  <th style={styles.tableCell}>WhatsApp</th>
                </tr>
              </thead>
              <tbody>
                {data.journeys.map((journey, idx) => (
                  <tr key={idx} style={styles.tableRow}>
                    <td style={styles.tableCell}>{journey.journey_name}</td>
                    <td style={styles.tableCell}>{journey.active}</td>
                    <td style={styles.tableCell}>{journey.completed}</td>
                    <td style={styles.tableCell}>
                      <span style={{
                        ...styles.badge,
                        backgroundColor: journey.conversion_rate > 0.1 ? '#10B981' : '#F59E0B'
                      }}>
                        {(journey.conversion_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={styles.tableCell}>{journey.email_sent}</td>
                    <td style={styles.tableCell}>{journey.whatsapp_sent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={styles.noData}>No journeys yet. Create one to get started →</div>
        )}
      </div>

      {/* Journey Node Summary */}
      <div style={styles.tableCard}>
        <h3 style={styles.chartTitle}>🧭 Journey Node Summary</h3>
        {journeyGraph.length > 0 ? (
          <div style={{ display: 'grid', gap: 12 }}>
            {journeyGraph.map((j) => (
              <div key={j.journey_id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong>{j.journey_name}</strong>
                  <span style={{ fontSize: 12, color: '#6b7280' }}>
                    Customers: {j.total_customers} | Purchased: {j.purchased_customers}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {(j.steps || []).map((s) => (
                    <span key={s.step_number} style={{ background: '#eff6ff', color: '#1d4ed8', borderRadius: 12, padding: '4px 10px', fontSize: 12, fontWeight: 600 }}>
                      Step {s.step_number}: {s.customers}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={styles.noData}>No journey node summary available yet</div>
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: '24px',
    background: '#f9fafb',
    minHeight: '100vh',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '28px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '700',
    margin: '0 0 8px 0',
    color: '#1f2937',
  },
  subtitle: {
    fontSize: '14px',
    color: '#6b7280',
    margin: 0,
  },
  refreshBtn: {
    padding: '10px 16px',
    background: '#3B82F6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '14px',
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
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '16px',
    marginBottom: '28px',
  },
  metricCard: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    gap: '16px',
    alignItems: 'center',
  },
  metricIcon: {
    fontSize: '32px',
  },
  metricContent: {
    flex: 1,
  },
  metricLabel: {
    fontSize: '12px',
    color: '#6b7280',
    fontWeight: '500',
    marginBottom: '4px',
  },
  metricValue: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#1f2937',
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
    gap: '20px',
    marginBottom: '28px',
  },
  chartCard: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  chartTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1f2937',
    margin: '0 0 16px 0',
  },
  tooltipStyle: {
    background: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    padding: '8px',
  },
  tableCard: {
    background: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  tableHeader: {
    background: '#f3f4f6',
    borderBottom: '1px solid #e5e7eb',
  },
  tableRow: {
    borderBottom: '1px solid #e5e7eb',
    '&:hover': { background: '#f9fafb' },
  },
  tableCell: {
    padding: '12px 16px',
    fontSize: '14px',
    color: '#374151',
  },
  badge: {
    padding: '4px 8px',
    borderRadius: '4px',
    color: 'white',
    fontSize: '12px',
    fontWeight: '600',
  },
  noData: {
    textAlign: 'center',
    color: '#9ca3af',
    padding: '32px',
    fontSize: '14px',
  },
  loader: {
    textAlign: 'center',
    padding: '64px 24px',
    fontSize: '16px',
    color: '#6b7280',
  },
};

export default JourneyAnalyticsDashboard;
