import React, { useState, useEffect } from 'react';

/**
 * Conversations - Chat history and conversation logs
 */
export default function Conversations() {
  const [logs, setLogs] = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterIntent, setFilterIntent] = useState('all');

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000); // Refresh every 15s
    return () => clearInterval(interval);
  }, [filterIntent]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/ai/logs?limit=50');
      const data = await response.json();
      let filtered = data.logs || [];
      
      if (filterIntent !== 'all') {
        filtered = filtered.filter(l => l.intent_detected === filterIntent);
      }
      
      setLogs(filtered);
    } catch (error) {
      console.error('Error fetching logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getIntentColor = (intent) => {
    const colors = {
      'PRICE_INQUIRY': '#667eea',
      'SHIPPING_INQUIRY': '#51cf66',
      'COD_INQUIRY': '#ff922b',
      'TRACKING_INQUIRY': '#764ba2',
      'PURCHASE': '#ffd93d',
      'COMPLAINT': '#ff6b6b',
      'GENERAL': '#a0a0a0',
    };
    return colors[intent] || '#999';
  };

  const getLanguageIcon = (lang) => {
    const icons = {
      'english': '🇬🇧',
      'malayalam': '🇮🇳',
      'manglish': '🇮🇳',
      'mixed': '🌐',
    };
    return icons[lang] || '?';
  };

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading conversations...</div>;
  }

  return (
    <div className="conversations-container">
      <style>{`
        .conversations-container {
          display: flex;
          gap: 20px;
          height: 100%;
        }
        
        .conversations-list {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .intent-filter {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
          flex-wrap: wrap;
        }
        
        .intent-btn {
          padding: 6px 12px;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 11px;
          background: white;
          border: 1px solid #ddd;
        }
        
        .intent-btn.active {
          background: #667eea;
          color: white;
          border-color: #667eea;
        }
        
        .conversation-item {
          background: white;
          padding: 12px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .conversation-item:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .conversation-item.selected {
          background: #f0f4ff;
          border-left: 4px solid #667eea;
        }
        
        .conversation-icon {
          font-size: 24px;
        }
        
        .conversation-info {
          flex: 1;
        }
        
        .conversation-meta {
          font-size: 11px;
          color: #999;
          display: flex;
          gap: 8px;
        }
        
        .conversation-intent {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 3px;
          font-size: 10px;
          font-weight: bold;
          color: white;
        }
        
        .conversation-time {
          font-size: 11px;
          color: #999;
        }
        
        .conversation-modal {
          flex: 0 0 350px;
          background: white;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          overflow-y: auto;
        }
        
        .modal-header {
          font-weight: bold;
          font-size: 14px;
          margin-bottom: 12px;
          color: #333;
        }
        
        .modal-section {
          margin-bottom: 12px;
          padding-bottom: 10px;
          border-bottom: 1px solid #eee;
        }
        
        .modal-section:last-child {
          border-bottom: none;
        }
        
        .modal-label {
          font-size: 10px;
          color: #999;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }
        
        .modal-value {
          font-size: 12px;
          color: #333;
          word-break: break-word;
        }
      `}</style>

      <div className="conversations-list">
        {/* Intent Filter */}
        <div className="intent-filter">
          <button
            className={`intent-btn ${filterIntent === 'all' ? 'active' : ''}`}
            onClick={() => setFilterIntent('all')}
          >
            All
          </button>
          <button
            className={`intent-btn ${filterIntent === 'PRICE_INQUIRY' ? 'active' : ''}`}
            onClick={() => setFilterIntent('PRICE_INQUIRY')}
          >
            Price
          </button>
          <button
            className={`intent-btn ${filterIntent === 'SHIPPING_INQUIRY' ? 'active' : ''}`}
            onClick={() => setFilterIntent('SHIPPING_INQUIRY')}
          >
            Shipping
          </button>
          <button
            className={`intent-btn ${filterIntent === 'COD_INQUIRY' ? 'active' : ''}`}
            onClick={() => setFilterIntent('COD_INQUIRY')}
          >
            COD
          </button>
          <button
            className={`intent-btn ${filterIntent === 'PURCHASE' ? 'active' : ''}`}
            onClick={() => setFilterIntent('PURCHASE')}
          >
            Purchase
          </button>
        </div>

        {/* Conversation List */}
        {logs.map((log) => (
          <div
            key={log.log_id}
            className={`conversation-item ${selectedLog?.log_id === log.log_id ? 'selected' : ''}`}
            onClick={() => setSelectedLog(log)}
          >
            <div className="conversation-icon">
              {getLanguageIcon(log.language_detected)}
            </div>
            <div className="conversation-info">
              <div className="conversation-meta">
                <span
                  className="conversation-intent"
                  style={{ background: getIntentColor(log.intent_detected) }}
                >
                  {log.intent_detected?.replace('_', ' ')}
                </span>
                <span className="conversation-time">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Conversation Detail Modal */}
      {selectedLog && (
        <div className="conversation-modal">
          <div className="modal-header">Conversation Details</div>

          {/* Intent & Language */}
          <div className="modal-section">
            <div className="modal-label">Detected Intent</div>
            <div
              className="conversation-intent"
              style={{ background: getIntentColor(selectedLog.intent_detected), display: 'inline-block' }}
            >
              {selectedLog.intent_detected?.replace('_', ' ')}
            </div>
            <div className="modal-label" style={{ marginTop: '8px' }}>Language</div>
            <div className="modal-value">
              {getLanguageIcon(selectedLog.language_detected)} {selectedLog.language_detected}
            </div>
          </div>

          {/* Response Details */}
          <div className="modal-section">
            <div className="modal-label">AI Response</div>
            <div className="modal-value">
              {selectedLog.response_text ? selectedLog.response_text.substring(0, 200) : 'N/A'}
              {selectedLog.response_text && selectedLog.response_text.length > 200 ? '...' : ''}
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="modal-section">
            <div className="modal-label">Tokens Used</div>
            <div className="modal-value">{selectedLog.tokens_used || 0}</div>
            <div className="modal-label" style={{ marginTop: '6px' }}>Latency</div>
            <div className="modal-value">{selectedLog.latency_ms || 0}ms</div>
          </div>

          {/* Timestamp */}
          <div className="modal-section">
            <div className="modal-label">Timestamp</div>
            <div className="modal-value">
              {new Date(selectedLog.created_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
