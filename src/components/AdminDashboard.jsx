import React, { useState, useEffect } from 'react';

/**
 * AdminDashboard - Wave 0.2 Feature Control & Monitoring
 * Shows all features with toggles to enable/disable
 */
export default function AdminDashboard() {
  const [features, setFeatures] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedCategory, setExpandedCategory] = useState('Wave 0.2');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [featuresRes, summaryRes] = await Promise.all([
        fetch('/api/ai/wave02/features/all'),
        fetch('/api/ai/wave02/dashboard/summary'),
      ]);

      if (featuresRes.ok) {
        const data = await featuresRes.json();
        setFeatures(data.features || []);
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFeature = async (featureKey, currentEnabled) => {
    try {
      const response = await fetch('/api/ai/wave02/features/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feature_key: featureKey,
          enabled: !currentEnabled,
        }),
      });

      if (response.ok) {
        // Update local state
        setFeatures(
          features.map(f =>
            f.feature_key === featureKey ? { ...f, enabled: !currentEnabled } : f
          )
        );
        alert(`Feature ${!currentEnabled ? 'enabled' : 'disabled'} successfully!`);
      }
    } catch (error) {
      console.error('Error toggling feature:', error);
      alert('Failed to toggle feature');
    }
  };

  const groupedFeatures = features.reduce((acc, feature) => {
    if (!acc[feature.category]) {
      acc[feature.category] = [];
    }
    acc[feature.category].push(feature);
    return acc;
  }, {});

  const categories = Object.keys(groupedFeatures).sort();

  if (loading && !features.length) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading dashboard...</div>;
  }

  return (
    <div className="admin-dashboard">
      <style>{`
        .admin-dashboard {
          padding: 20px;
          background: #f9f9f9;
          min-height: 100vh;
        }

        .dashboard-header {
          margin-bottom: 30px;
        }

        .header-title {
          font-size: 24px;
          font-weight: bold;
          color: #333;
          margin-bottom: 8px;
        }

        .header-subtitle {
          font-size: 14px;
          color: #999;
        }

        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 30px;
        }

        .kpi-card {
          background: white;
          padding: 16px;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.05);
          border-left: 4px solid #667eea;
        }

        .kpi-label {
          font-size: 11px;
          color: #999;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 6px;
        }

        .kpi-value {
          font-size: 24px;
          font-weight: bold;
          color: #333;
        }

        .kpi-subtext {
          font-size: 12px;
          color: #666;
          margin-top: 4px;
        }

        .features-section {
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.05);
          overflow: hidden;
        }

        .category-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px;
          background: #f5f5f5;
          border-bottom: 1px solid #eee;
          cursor: pointer;
          transition: background 0.2s;
        }

        .category-header:hover {
          background: #efefef;
        }

        .category-title {
          font-weight: bold;
          font-size: 14px;
          color: #333;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .category-toggle-icon {
          font-size: 12px;
          transition: transform 0.2s;
        }

        .category-expanded .category-toggle-icon {
          transform: rotate(90deg);
        }

        .category-content {
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.3s ease;
        }

        .category-expanded .category-content {
          max-height: 1000px;
        }

        .feature-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          border-bottom: 1px solid #eee;
          transition: background 0.2s;
        }

        .feature-item:hover {
          background: #fafafa;
        }

        .feature-info {
          flex: 1;
        }

        .feature-name {
          font-weight: 600;
          font-size: 13px;
          color: #333;
          margin-bottom: 2px;
        }

        .feature-description {
          font-size: 11px;
          color: #999;
        }

        .feature-toggle-container {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .feature-status {
          font-size: 11px;
          font-weight: bold;
          padding: 4px 8px;
          border-radius: 4px;
        }

        .status-enabled {
          background: #d4edda;
          color: #155724;
        }

        .status-disabled {
          background: #f8d7da;
          color: #721c24;
        }

        .toggle-switch {
          width: 40px;
          height: 20px;
          border-radius: 10px;
          border: none;
          cursor: pointer;
          transition: all 0.2s;
          background: #ccc;
          position: relative;
        }

        .toggle-switch::before {
          content: '';
          position: absolute;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: white;
          top: 2px;
          left: 2px;
          transition: left 0.2s;
        }

        .toggle-switch.enabled {
          background: #51cf66;
        }

        .toggle-switch.enabled::before {
          left: 22px;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
          padding: 16px;
          background: #f5f5f5;
        }

        .stat-item {
          text-align: center;
          font-size: 12px;
        }

        .stat-value {
          font-size: 18px;
          font-weight: bold;
          color: #667eea;
          display: block;
          margin-bottom: 4px;
        }

        .stat-label {
          color: #999;
          font-size: 10px;
          text-transform: uppercase;
        }

        .action-buttons {
          display: flex;
          gap: 8px;
          padding: 12px 16px;
          background: #fafafa;
          border-top: 1px solid #eee;
        }

        .btn-primary {
          flex: 1;
          padding: 8px 16px;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 12px;
        }

        .btn-primary:hover {
          background: #5568d3;
        }

        .btn-secondary {
          flex: 1;
          padding: 8px 16px;
          background: white;
          color: #667eea;
          border: 1px solid #ddd;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 12px;
        }

        .btn-secondary:hover {
          background: #f5f5f5;
        }

        .summary-warning {
          background: #fff3cd;
          border: 1px solid #ffc107;
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 20px;
          font-size: 12px;
          color: #856404;
        }
      `}</style>

      {/* Header */}
      <div className="dashboard-header">
        <div className="header-title">⚙️ Wave 0.2 Admin Dashboard</div>
        <div className="header-subtitle">Control features, monitor performance, manage toggles</div>
      </div>

      {/* KPIs */}
      {summary && (
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Pending Reviews</div>
            <div className="kpi-value">{summary.review_queue?.pending || 0}</div>
            <div className="kpi-subtext">Waiting for your approval</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Learning Progress</div>
            <div className="kpi-value">{summary.learning?.estimated_current_accuracy || 65}%</div>
            <div className="kpi-subtext">Current rule engine accuracy</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">KB Performance</div>
            <div className="kpi-value">{Math.round(summary.kb?.overall_helpfulness_rate || 0)}%</div>
            <div className="kpi-subtext">Helpfulness rating</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Active KB Entries</div>
            <div className="kpi-value">{summary.kb?.total_active_entries || 0}</div>
            <div className="kpi-subtext">Knowledge base articles</div>
          </div>
        </div>
      )}

      {/* Warning */}
      <div className="summary-warning">
        💡 <strong>Tip:</strong> Toggle features off to disable functionality for testing. All features are
        enabled by default.
      </div>

      {/* Feature Toggles */}
      <div className="features-section">
        {categories.map(category => (
          <div key={category}>
            <div
              className={`category-header ${expandedCategory === category ? 'category-expanded' : ''}`}
              onClick={() => setExpandedCategory(expandedCategory === category ? null : category)}
            >
              <div className="category-title">
                <span className="category-toggle-icon">▶</span>
                {category} ({groupedFeatures[category].length} features)
              </div>
              <div style={{ fontSize: '12px', color: '#999' }}>
                {groupedFeatures[category].filter(f => f.enabled).length}/{groupedFeatures[category].length} enabled
              </div>
            </div>

            <div className="category-content">
              {groupedFeatures[category].map(feature => (
                <div key={feature.feature_key} className="feature-item">
                  <div className="feature-info">
                    <div className="feature-name">{feature.feature_name}</div>
                    <div className="feature-description">{feature.description}</div>
                  </div>
                  <div className="feature-toggle-container">
                    <div className={`feature-status ${feature.enabled ? 'status-enabled' : 'status-disabled'}`}>
                      {feature.enabled ? '✓ ON' : '✗ OFF'}
                    </div>
                    <button
                      className={`toggle-switch ${feature.enabled ? 'enabled' : ''}`}
                      onClick={() => handleToggleFeature(feature.feature_key, feature.enabled)}
                      title={`Toggle ${feature.feature_name}`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="features-section" style={{ marginTop: '20px' }}>
          <div style={{ padding: '16px', fontWeight: 'bold', borderBottom: '1px solid #eee' }}>
            📊 Performance Summary
          </div>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-value">{summary.review_queue?.approved || 0}</span>
              <span className="stat-label">Approvals</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{summary.review_queue?.reclassified || 0}</span>
              <span className="stat-label">Corrections</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{summary.learning?.total_training_examples || 0}</span>
              <span className="stat-label">Training Examples</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{summary.kb?.total_suggestions || 0}</span>
              <span className="stat-label">KB Suggestions</span>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        <button className="btn-secondary" onClick={fetchData}>
          🔄 Refresh Data
        </button>
        <button className="btn-primary" onClick={() => alert('Export functionality coming soon')}>
          📥 Export Report
        </button>
      </div>
    </div>
  );
}
