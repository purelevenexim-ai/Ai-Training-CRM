import React, { useState, useEffect } from 'react';
import crmApi from '../utils/crmApi';
import './LeadManagerPanel.css';

/**
 * LeadManagerPanel - Lead Intake Interface
 *
 * Displays live lead captures with search, creation, and email-capture actions.
 */
export function LeadManagerPanel() {
  // State
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalLeads, setTotalLeads] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [captureLead, setCaptureLead] = useState(null);
  const [captureEmail, setCaptureEmail] = useState('');
  const [captureLoading, setCaptureLoading] = useState(false);
  const [captureError, setCaptureError] = useState(null);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [scoreMinFilter, setScoreMinFilter] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  
  // Pagination
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  
  // UI state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [selectedLeads, setSelectedLeads] = useState(new Set());
  const [statusUpdateLead, setStatusUpdateLead] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    phone: '',
    company: '',
    job_title: '',
    industry: '',
    lead_source: 'manual'
  });

  // Load leads on component mount or filter change
  useEffect(() => {
    loadLeads();
  }, [searchQuery, skip, limit]);

  // Load leads from API
  const loadLeads = async () => {
    setLoading(true);
    try {
      const response = await crmApi.get('/leads', {
        limit,
        search: searchQuery || undefined,
      });
      
      setLeads(response.items || []);
      setTotalLeads(response.total || 0);
    } catch (error) {
      console.error('Failed to load leads:', error);
      alert('Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  // Create new lead
  const handleCreateLead = async () => {
    if (!formData.phone) {
      alert('Phone is required');
      return;
    }

    try {
      await crmApi.post('/leads', {
        source: formData.lead_source || 'manual',
        provider: 'manual',
        name: formData.name || undefined,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        consent: true,
      });
      alert('Lead created successfully');
      setFormData({
        email: '',
        name: '',
        phone: '',
        company: '',
        job_title: '',
        industry: '',
        lead_source: 'manual'
      });
      setShowCreateForm(false);
      loadLeads();
    } catch (error) {
      console.error('Failed to create lead:', error);
      alert('Failed to create lead');
    }
  };

  const handleCaptureEmail = async (lead) => {
    const nextEmail = captureEmail.trim();
    if (!lead?.id || !lead?.phone || !nextEmail) {
      alert('Select a lead, enter a phone number, and provide an email.');
      return;
    }

    setCaptureLoading(true);
    setCaptureError(null);
    try {
      await crmApi.put(`/leads/${lead.id}/email`, {
        phone: lead.phone,
        email: nextEmail,
      });
      setCaptureLead(null);
      setCaptureEmail('');
      loadLeads();
      alert('Email captured successfully');
    } catch (error) {
      console.error('Failed to capture lead email:', error);
      setCaptureError(error.message);
    } finally {
      setCaptureLoading(false);
    }
  };

  // Update lead
  const handleUpdateLead = async () => {
    alert('Lead editing is not available in the live backend.');
  };

  // Update lead status
  const handleStatusChange = async (leadId, newStatus) => {
    alert('Lead status updates are not available in the live backend.');
  };

  // Convert lead to customer
  const handleConvertLead = async (leadId) => {
    alert('Lead conversion is not available in the live backend.');
  };

  // Delete lead
  const handleDeleteLead = async (leadId) => {
    alert('Lead delete is not available in the live backend.');
  };

  // Calculate propensity score color
  const getScoreColor = (score) => {
    if (score >= 0.8) return '#22c55e'; // green
    if (score >= 0.6) return '#3b82f6'; // blue
    if (score >= 0.4) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  // Status badge
  const getStatusBadge = (status) => {
    const colors = {
      new: '#6b7280',
      contacted: '#3b82f6',
      qualified: '#8b5cf6',
      customer: '#22c55e',
      lost: '#ef4444'
    };
    return (
      <span style={{
        backgroundColor: colors[status] || '#6b7280',
        color: 'white',
        padding: '4px 12px',
        borderRadius: '20px',
        fontSize: '12px',
        fontWeight: 'bold'
      }}>
        {status}
      </span>
    );
  };

  // Lead source badge
  const getSourceBadge = (source) => {
    const sourceColors = {
      manual: '#9ca3af',
      google_forms: '#4285f4',
      meta_ads: '#1877f2',
      contact_form: '#3b82f6',
      csv_import: '#8b5cf6',
      email: '#ec4899'
    };
    return (
      <span style={{
        backgroundColor: sourceColors[source] || '#9ca3af',
        color: 'white',
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '11px'
      }}>
        {source}
      </span>
    );
  };

  // Render
  return (
    <div className="lead-manager-panel">
      <div className="lead-header">
        <h2>Lead Management</h2>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : '+ New Lead'}
        </button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="lead-form">
          <h3>Create New Lead</h3>
          <div className="form-grid">
            <input
              type="email"
              placeholder="Email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
            <input
              type="text"
              placeholder="Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
            <input
              type="tel"
              placeholder="Phone"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            />
            <input
              type="text"
              placeholder="Company"
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
            />
            <input
              type="text"
              placeholder="Job Title"
              value={formData.job_title}
              onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
            />
            <input
              type="text"
              placeholder="Industry"
              value={formData.industry}
              onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
            />
            <select
              value={formData.lead_source}
              onChange={(e) => setFormData({ ...formData, lead_source: e.target.value })}
            >
              <option value="manual">Manual</option>
              <option value="google_forms">Google Forms</option>
              <option value="meta_ads">Meta Ads</option>
              <option value="contact_form">Contact Form</option>
              <option value="csv_import">CSV Import</option>
              <option value="email">Email</option>
            </select>
          </div>
          <button className="btn btn-success" onClick={handleCreateLead}>
            Create Lead
          </button>
        </div>
      )}

      {/* Live search and status */}
      <div className="lead-filters">
        <input
          type="search"
          placeholder="Search by name, email, source, or phone"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button className="btn btn-secondary" onClick={loadLeads}>
          Refresh
        </button>
        <div style={{ gridColumn: '1 / -1', color: '#6b7280', fontSize: '13px' }}>
          Live backend supports lead listing, lead creation, and email capture.
        </div>
      </div>

      {/* Metrics Summary */}
      <div className="lead-metrics">
        <div className="metric">
          <span className="metric-label">Total Leads</span>
          <span className="metric-value">{totalLeads}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Loaded</span>
          <span className="metric-value">{leads.length}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Window</span>
          <span className="metric-value">{limit}</span>
        </div>
      </div>

      {captureLead && (
        <div className="lead-form">
          <h3>Capture Email for Lead #{captureLead.id}</h3>
          <div className="form-grid">
            <input
              type="tel"
              placeholder="Phone"
              value={captureLead.phone || ''}
              readOnly
            />
            <input
              type="email"
              placeholder="Email"
              value={captureEmail}
              onChange={(e) => setCaptureEmail(e.target.value)}
            />
          </div>
          {captureError && (
            <div style={{ color: '#b91c1c', marginBottom: '12px' }}>
              {captureError}
            </div>
          )}
          <button
            className="btn btn-success"
            onClick={() => handleCaptureEmail(captureLead)}
            disabled={captureLoading}
          >
            {captureLoading ? 'Saving...' : 'Save Email'}
          </button>
          <button
            className="btn btn-secondary"
            style={{ marginLeft: '8px' }}
            onClick={() => {
              setCaptureLead(null);
              setCaptureEmail('');
              setCaptureError(null);
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Leads List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>
      ) : leads.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
          No leads found
        </div>
      ) : (
        <table className="lead-table">
          <thead>
            <tr>
              <th>Lead</th>
              <th>Phone</th>
              <th>Source</th>
              <th>Provider</th>
              <th>Consent</th>
              <th>Captured</th>
              <th>Coupon</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} className="lead-row">
                <td>
                  <div className="lead-info">
                    <div className="lead-name">{lead.name || lead.email || 'Unnamed lead'}</div>
                    <div className="lead-email">ID #{lead.id}</div>
                  </div>
                </td>
                <td>{lead.phone || '-'}</td>
                <td>{lead.source || '-'}</td>
                <td>{lead.provider || '-'}</td>
                <td>{lead.consent ? 'Yes' : 'No'}</td>
                <td>
                  {lead.captured_at ? new Date(lead.captured_at).toLocaleString() : '-'}
                </td>
                <td>{lead.coupon_code || '-'}</td>
                <td className="lead-actions">
                  {lead.phone ? (
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => {
                        setCaptureLead(lead);
                        setCaptureEmail(lead.email || '');
                        setCaptureError(null);
                      }}
                    >
                      Capture email
                    </button>
                  ) : (
                    <span style={{ color: '#6b7280', fontSize: '12px' }}>No phone</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="lead-pagination">
        <span>
          Showing the latest {limit} records. Refine search to narrow results.
        </span>
      </div>

      {/* Edit Modal */}
      {editingLead && (
        <div className="modal-overlay" onClick={() => setEditingLead(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Edit Lead</h3>
            <div className="form-grid">
              <input
                type="text"
                placeholder="Name"
                value={editingLead.name || ''}
                onChange={(e) =>
                  setEditingLead({ ...editingLead, name: e.target.value })
                }
              />
              <input
                type="tel"
                placeholder="Phone"
                value={editingLead.phone || ''}
                onChange={(e) =>
                  setEditingLead({ ...editingLead, phone: e.target.value })
                }
              />
              <input
                type="text"
                placeholder="Company"
                value={editingLead.company || ''}
                onChange={(e) =>
                  setEditingLead({ ...editingLead, company: e.target.value })
                }
              />
              <input
                type="text"
                placeholder="Job Title"
                value={editingLead.job_title || ''}
                onChange={(e) =>
                  setEditingLead({ ...editingLead, job_title: e.target.value })
                }
              />
              <input
                type="text"
                placeholder="Industry"
                value={editingLead.industry || ''}
                onChange={(e) =>
                  setEditingLead({ ...editingLead, industry: e.target.value })
                }
              />
            </div>
            <div className="modal-actions">
              <button className="btn btn-success" onClick={handleUpdateLead}>
                Save
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setEditingLead(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default LeadManagerPanel;
