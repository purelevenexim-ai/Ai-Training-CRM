import React, { useState, useEffect } from 'react';

/**
 * Customers - Customer list with AI scores
 */
export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('score');

  useEffect(() => {
    fetchCustomers();
  }, [filter]);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      const response = await fetch(`/api/ai/customers?${params}`);
      const data = await response.json();
      
      let sorted = data.customers || [];
      if (sortBy === 'score') {
        sorted.sort((a, b) => b.overall_score - a.overall_score);
      } else if (sortBy === 'spent') {
        sorted.sort((a, b) => b.total_spent - a.total_spent);
      }
      
      setCustomers(sorted);
    } catch (error) {
      console.error('Error fetching customers:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 76) return '#51cf66';
    if (score >= 51) return '#ffd93d';
    if (score >= 26) return '#ff922b';
    return '#ff6b6b';
  };

  const getStatusBadge = (status) => {
    const colors = {
      'Ready': '#51cf66',
      'Hot': '#ffd93d',
      'Warm': '#ff922b',
      'Cold': '#a0a0a0',
    };
    return (
      <span style={{
        background: colors[status] || '#999',
        color: status === 'Hot' ? '#333' : 'white',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 'bold',
      }}>
        {status}
      </span>
    );
  };

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading customers...</div>;
  }

  return (
    <div className="customers-container">
      <style>{`
        .customers-container {
          display: flex;
          gap: 20px;
          height: 100%;
        }
        
        .customers-list {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .customers-header {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }
        
        .filter-btn, .sort-btn {
          padding: 8px 16px;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
          background: white;
          border: 1px solid #ddd;
        }
        
        .filter-btn.active, .sort-btn.active {
          background: #667eea;
          color: white;
          border-color: #667eea;
        }
        
        .customer-row {
          background: white;
          padding: 12px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        
        .customer-row:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          transform: translateY(-2px);
        }
        
        .customer-row.selected {
          background: #f0f4ff;
          border-left: 4px solid #667eea;
        }
        
        .customer-info {
          flex: 1;
        }
        
        .customer-name {
          font-weight: bold;
          color: #333;
          font-size: 14px;
        }
        
        .customer-email {
          font-size: 12px;
          color: #999;
        }
        
        .customer-detail {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 6px;
        }
        
        .score-display {
          font-weight: bold;
          font-size: 18px;
          padding: 4px 12px;
          border-radius: 6px;
          background: #f5f5f5;
        }
        
        .customer-modal {
          flex: 0 0 350px;
          background: white;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .modal-header {
          font-weight: bold;
          font-size: 16px;
          margin-bottom: 12px;
          color: #333;
        }
        
        .modal-section {
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #eee;
        }
        
        .modal-section:last-child {
          border-bottom: none;
        }
        
        .modal-label {
          font-size: 11px;
          color: #999;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }
        
        .modal-value {
          font-size: 14px;
          color: #333;
          font-weight: bold;
        }
        
        .score-bar {
          height: 6px;
          background: #eee;
          border-radius: 3px;
          overflow: hidden;
          margin-top: 4px;
        }
        
        .score-bar-fill {
          height: 100%;
          transition: width 0.3s;
        }
      `}</style>

      <div className="customers-list">
        {/* Filters */}
        <div className="customers-header">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filter === 'Ready' ? 'active' : ''}`}
            onClick={() => setFilter('Ready')}
          >
            Ready
          </button>
          <button
            className={`filter-btn ${filter === 'Hot' ? 'active' : ''}`}
            onClick={() => setFilter('Hot')}
          >
            Hot
          </button>
          <button
            className={`filter-btn ${filter === 'Warm' ? 'active' : ''}`}
            onClick={() => setFilter('Warm')}
          >
            Warm
          </button>
          <button
            className={`sort-btn ${sortBy === 'score' ? 'active' : ''}`}
            onClick={() => setSortBy('score')}
          >
            Sort by Score
          </button>
          <button
            className={`sort-btn ${sortBy === 'spent' ? 'active' : ''}`}
            onClick={() => setSortBy('spent')}
          >
            Sort by Spend
          </button>
        </div>

        {/* Customer List */}
        {customers.map((customer) => (
          <div
            key={customer.customer_id}
            className={`customer-row ${selectedCustomer?.customer_id === customer.customer_id ? 'selected' : ''}`}
            onClick={() => setSelectedCustomer(customer)}
          >
            <div className="customer-info">
              <div className="customer-name">{customer.name || 'Unknown'}</div>
              <div className="customer-email">{customer.email || customer.phone}</div>
            </div>
            <div className="customer-detail">
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <div
                  className="score-display"
                  style={{ color: getScoreColor(customer.overall_score) }}
                >
                  {customer.overall_score}
                </div>
                {getStatusBadge(customer.lead_status)}
              </div>
              <div style={{ fontSize: '11px', color: '#999' }}>
                ₹{(customer.total_spent || 0).toLocaleString('en-IN')}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Customer Detail Modal */}
      {selectedCustomer && (
        <div className="customer-modal">
          <div className="modal-header">
            {selectedCustomer.name || 'Customer Details'}
          </div>

          {/* Scores */}
          <div className="modal-section">
            <div className="modal-label">Overall Score</div>
            <div className="modal-value">{selectedCustomer.overall_score}</div>
            <div className="score-bar">
              <div
                className="score-bar-fill"
                style={{
                  width: `${selectedCustomer.overall_score}%`,
                  background: getScoreColor(selectedCustomer.overall_score),
                }}
              />
            </div>
          </div>

          {/* Status */}
          <div className="modal-section">
            <div className="modal-label">Lead Status</div>
            {getStatusBadge(selectedCustomer.lead_status)}
          </div>

          {/* Contact */}
          <div className="modal-section">
            <div className="modal-label">Email</div>
            <div className="modal-value" style={{ fontSize: '12px' }}>{selectedCustomer.email || 'N/A'}</div>
            <div className="modal-label" style={{ marginTop: '8px' }}>Phone</div>
            <div className="modal-value" style={{ fontSize: '12px' }}>{selectedCustomer.phone || 'N/A'}</div>
          </div>

          {/* Order History */}
          <div className="modal-section">
            <div className="modal-label">Total Orders</div>
            <div className="modal-value">{selectedCustomer.orders_count || 0}</div>
            <div className="modal-label" style={{ marginTop: '8px' }}>Total Spent</div>
            <div className="modal-value">₹{(selectedCustomer.total_spent || 0).toLocaleString('en-IN')}</div>
          </div>

          {/* Last Activity */}
          <div className="modal-section">
            <div className="modal-label">Last Activity</div>
            <div className="modal-value" style={{ fontSize: '12px' }}>
              {selectedCustomer.last_activity ? new Date(selectedCustomer.last_activity).toLocaleDateString() : 'Never'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
