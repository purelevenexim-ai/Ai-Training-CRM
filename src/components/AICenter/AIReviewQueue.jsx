import React, { useState, useEffect } from 'react';

/**
 * AIReviewQueue - Daily question review interface (Wave 0.2)
 * Shows low-confidence messages that need your approval
 */
export default function AIReviewQueue() {
  const [reviews, setReviews] = useState([]);
  const [selectedReview, setSelectedReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [correctedIntent, setCorrectedIntent] = useState(null);
  const [notes, setNotes] = useState('');
  const [showAddKB, setShowAddKB] = useState(false);
  const [kbCategory, setKbCategory] = useState('FAQ');

  useEffect(() => {
    fetchPendingReviews();
    const interval = setInterval(fetchPendingReviews, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchPendingReviews = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/ai/review/pending?limit=50');
      const data = await response.json();
      setReviews(data.reviews || []);
    } catch (error) {
      console.error('Error fetching reviews:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedReview) return;

    try {
      const response = await fetch('/api/ai/review/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          queue_id: selectedReview.queue_id,
          approved_intent: correctedIntent,
          add_to_kb: showAddKB,
          kb_category: kbCategory,
          notes: notes,
        }),
      });

      if (response.ok) {
        // Remove from list and show next
        const remaining = reviews.filter(r => r.queue_id !== selectedReview.queue_id);
        setReviews(remaining);
        setSelectedReview(remaining[0] || null);
        resetForm();

        // Show success message
        alert('Approved! Learning system updated.');
      }
    } catch (error) {
      console.error('Error approving review:', error);
      alert('Error approving review');
    }
  };

  const handleEscalate = async () => {
    if (!selectedReview) return;

    try {
      const response = await fetch('/api/ai/review/escalate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          queue_id: selectedReview.queue_id,
          reason: notes,
        }),
      });

      if (response.ok) {
        // Remove from list
        const remaining = reviews.filter(r => r.queue_id !== selectedReview.queue_id);
        setReviews(remaining);
        setSelectedReview(remaining[0] || null);
        resetForm();

        alert('Escalated to manual team.');
      }
    } catch (error) {
      console.error('Error escalating review:', error);
      alert('Error escalating review');
    }
  };

  const resetForm = () => {
    setCorrectedIntent(null);
    setNotes('');
    setShowAddKB(false);
    setKbCategory('FAQ');
  };

  const getLanguageIcon = (lang) => {
    const icons = {
      'english': '🇬🇧',
      'malayalam': '🇮🇳 ML',
      'manglish': '🇮🇳 Mix',
      'mixed': '🌐',
    };
    return icons[lang] || '?';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return '#51cf66';
    if (confidence >= 0.5) return '#ffd93d';
    return '#ff6b6b';
  };

  if (loading && reviews.length === 0) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading reviews...</div>;
  }

  if (reviews.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>
        ✅ All caught up! No pending reviews. Great job with the learning!
      </div>
    );
  }

  return (
    <div className="review-queue-container">
      <style>{`
        .review-queue-container {
          display: flex;
          gap: 20px;
          height: 100%;
        }
        
        .review-list {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 70vh;
          overflow-y: auto;
        }
        
        .review-item {
          background: white;
          padding: 12px;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
          border-left: 4px solid #ddd;
        }
        
        .review-item:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          transform: translateX(4px);
        }
        
        .review-item.selected {
          background: #f0f4ff;
          border-left-color: #667eea;
        }
        
        .review-item.low-confidence {
          border-left-color: #ff6b6b;
        }
        
        .review-meta {
          font-size: 11px;
          color: #999;
          display: flex;
          gap: 8px;
          align-items: center;
          margin-bottom: 4px;
        }
        
        .confidence-badge {
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 10px;
          font-weight: bold;
          color: white;
        }
        
        .review-message {
          font-size: 13px;
          color: #333;
          line-height: 1.3;
        }
        
        .review-panel {
          flex: 0 0 400px;
          background: white;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          overflow-y: auto;
        }
        
        .panel-header {
          font-weight: bold;
          font-size: 14px;
          margin-bottom: 12px;
          color: #333;
        }
        
        .section {
          margin-bottom: 12px;
          padding-bottom: 10px;
          border-bottom: 1px solid #eee;
        }
        
        .section:last-child {
          border-bottom: none;
        }
        
        .label {
          font-size: 10px;
          color: #999;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }
        
        .value {
          font-size: 13px;
          color: #333;
          word-break: break-word;
          line-height: 1.4;
        }
        
        .intent-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: bold;
          color: white;
          background: #667eea;
        }
        
        .option-group {
          margin-bottom: 12px;
        }
        
        .option-label {
          font-size: 11px;
          font-weight: bold;
          color: #333;
          margin-bottom: 4px;
        }
        
        .option-button {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s;
          margin-bottom: 4px;
        }
        
        .option-button:hover {
          border-color: #667eea;
          background: #f0f4ff;
        }
        
        .option-button.selected {
          background: #667eea;
          color: white;
          border-color: #667eea;
        }
        
        .textarea {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 12px;
          font-family: inherit;
          resize: vertical;
          min-height: 60px;
        }
        
        .checkbox-group {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 6px;
        }
        
        .action-buttons {
          display: flex;
          gap: 8px;
          margin-top: 12px;
        }
        
        .btn-approve {
          flex: 1;
          background: #51cf66;
          color: white;
          border: none;
          padding: 10px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: bold;
          font-size: 12px;
        }
        
        .btn-approve:hover {
          background: #40c057;
        }
        
        .btn-escalate {
          flex: 1;
          background: #ff922b;
          color: white;
          border: none;
          padding: 10px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: bold;
          font-size: 12px;
        }
        
        .btn-escalate:hover {
          background: #fd7e14;
        }
        
        .progress-bar {
          width: 100%;
          height: 4px;
          background: #eee;
          border-radius: 2px;
          overflow: hidden;
          margin-top: 4px;
        }
        
        .progress-fill {
          height: 100%;
          background: #667eea;
        }
      `}</style>

      {/* Review List */}
      <div className="review-list">
        <div style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
          📋 {reviews.length} pending ({reviews.length > 0 ? 'Estimated 30 min to review all' : 'Done!'})
        </div>
        {reviews.map((review, idx) => (
          <div
            key={review.queue_id}
            className={`review-item ${selectedReview?.queue_id === review.queue_id ? 'selected' : ''} ${review.intent_confidence < 0.6 ? 'low-confidence' : ''}`}
            onClick={() => setSelectedReview(review)}
          >
            <div className="review-meta">
              <span>{getLanguageIcon(review.detected_language)}</span>
              <span className="intent-badge">{review.detected_intent?.replace('_', ' ')}</span>
              <span
                className="confidence-badge"
                style={{ background: getConfidenceColor(review.intent_confidence) }}
              >
                {Math.round(review.intent_confidence * 100)}%
              </span>
              <span>#{idx + 1}</span>
            </div>
            <div className="review-message">
              {review.customer_message.substring(0, 100)}
              {review.customer_message.length > 100 ? '...' : ''}
            </div>
          </div>
        ))}
      </div>

      {/* Review Panel */}
      {selectedReview && (
        <div className="review-panel">
          <div className="panel-header">Review Details</div>

          {/* Original Message */}
          <div className="section">
            <div className="label">Customer Message</div>
            <div className="value">{selectedReview.customer_message}</div>
          </div>

          {/* AI Detection */}
          <div className="section">
            <div className="label">AI Detected Intent</div>
            <div className="value">
              <span className="intent-badge">{selectedReview.detected_intent?.replace('_', ' ')}</span>
              <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                Confidence: {Math.round(selectedReview.intent_confidence * 100)}%
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${selectedReview.intent_confidence * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* AI Response */}
          <div className="section">
            <div className="label">AI Generated Response</div>
            <div className="value">"{selectedReview.ai_response}"</div>
          </div>

          {/* Your Corrections */}
          <div className="section">
            <div className="label">Is the intent correct?</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className={`option-button ${!correctedIntent ? 'selected' : ''}`}
                onClick={() => setCorrectedIntent(null)}
              >
                ✅ Yes, correct
              </button>
              <button
                className={`option-button ${correctedIntent ? 'selected' : ''}`}
                onClick={() => setCorrectedIntent('DIFFERENT')}
              >
                ❌ No, wrong
              </button>
            </div>
          </div>

          {/* If Wrong, Select Correct Intent */}
          {correctedIntent === 'DIFFERENT' && (
            <div className="section">
              <div className="label">What was the correct intent?</div>
              {[
                'PRICE_INQUIRY',
                'SHIPPING_INQUIRY',
                'COD_INQUIRY',
                'TRACKING_INQUIRY',
                'PURCHASE',
                'COMPLAINT',
                'GENERAL',
              ].map((intent) => (
                <button
                  key={intent}
                  className={`option-button ${correctedIntent === intent ? 'selected' : ''}`}
                  onClick={() => setCorrectedIntent(intent)}
                  style={{ marginBottom: '4px' }}
                >
                  {intent.replace('_', ' ')}
                </button>
              ))}
            </div>
          )}

          {/* Add to KB */}
          <div className="section">
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="add-kb"
                checked={showAddKB}
                onChange={(e) => setShowAddKB(e.target.checked)}
              />
              <label htmlFor="add-kb" style={{ fontSize: '12px', margin: 0 }}>
                Add to Knowledge Base
              </label>
            </div>
            {showAddKB && (
              <div style={{ marginTop: '8px' }}>
                <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#333' }}>Category</label>
                <select
                  value={kbCategory}
                  onChange={(e) => setKbCategory(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    marginTop: '4px',
                  }}
                >
                  <option value="FAQ">FAQ</option>
                  <option value="Shipping">Shipping</option>
                  <option value="Payment">Payment</option>
                  <option value="Policy">Policy</option>
                </select>
              </div>
            )}
          </div>

          {/* Notes */}
          <div className="section">
            <div className="label">Notes (optional)</div>
            <textarea
              className="textarea"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Why did you correct it? Any context for future learning?"
            />
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button className="btn-approve" onClick={handleApprove}>
              ✅ Approve
            </button>
            <button className="btn-escalate" onClick={handleEscalate}>
              ⚠️ Escalate
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
