import React, { useState } from 'react';

/**
 * AISandbox - Debug tool for testing message detection
 */
export default function AISandbox() {
  const [message, setMessage] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTest = async () => {
    if (!message.trim()) {
      alert('Please enter a message');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/ai/sandbox/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error testing message:', error);
      alert('Error testing message');
    } finally {
      setLoading(false);
    }
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

  const getMethodColor = (method) => {
    return method === 'Rule Engine' ? '#51cf66' : '#667eea';
  };

  return (
    <div className="sandbox-container">
      <style>{`
        .sandbox-container {
          display: flex;
          flex-direction: column;
          gap: 20px;
          max-width: 900px;
        }
        
        .sandbox-input-section {
          background: white;
          padding: 20px;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .input-label {
          font-weight: bold;
          color: #333;
          margin-bottom: 8px;
          font-size: 14px;
        }
        
        .input-area {
          display: flex;
          gap: 8px;
        }
        
        .message-input {
          flex: 1;
          padding: 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 13px;
          font-family: inherit;
          resize: none;
          min-height: 80px;
        }
        
        .message-input:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn-test {
          background: #667eea;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: bold;
          height: fit-content;
        }
        
        .btn-test:hover {
          background: #764ba2;
        }
        
        .btn-test:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .sandbox-result {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 12px;
        }
        
        .result-card {
          background: white;
          padding: 16px;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .result-label {
          font-size: 11px;
          color: #999;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 6px;
        }
        
        .result-value {
          font-size: 18px;
          font-weight: bold;
          color: #333;
        }
        
        .result-subtext {
          font-size: 12px;
          color: #666;
          margin-top: 4px;
        }
        
        .result-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
          color: white;
          margin-top: 4px;
        }
        
        .confidence-bar {
          height: 6px;
          background: #eee;
          border-radius: 3px;
          overflow: hidden;
          margin-top: 8px;
        }
        
        .confidence-bar-fill {
          height: 100%;
          background: #667eea;
          border-radius: 3px;
        }
        
        .response-section {
          background: white;
          padding: 16px;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .response-label {
          font-weight: bold;
          color: #333;
          margin-bottom: 8px;
          font-size: 14px;
        }
        
        .response-text {
          background: #f5f5f5;
          padding: 12px;
          border-radius: 4px;
          font-size: 13px;
          color: #666;
          line-height: 1.4;
          border-left: 3px solid #667eea;
        }
        
        .quick-test {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 12px;
        }
        
        .quick-test-btn {
          background: #f0f4ff;
          border: 1px solid #667eea;
          color: #667eea;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
          font-weight: bold;
        }
        
        .quick-test-btn:hover {
          background: #667eea;
          color: white;
        }
      `}</style>

      {/* Input Section */}
      <div className="sandbox-input-section">
        <div className="input-label">Test Message Detection</div>
        <div className="input-area">
          <textarea
            className="message-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter a customer message here... (e.g., 'What is the price of pepper?', 'വില എത്ര?')"
          />
          <button
            className="btn-test"
            onClick={handleTest}
            disabled={loading}
          >
            {loading ? 'Testing...' : 'Test'}
          </button>
        </div>

        {/* Quick Test Buttons */}
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '11px', color: '#999', marginBottom: '8px' }}>Quick Test Examples:</div>
          <div className="quick-test">
            <button className="quick-test-btn" onClick={() => setMessage('What is the price of black pepper?')}>
              Price (EN)
            </button>
            <button className="quick-test-btn" onClick={() => setMessage('വില എത്ര?')}>
              Price (ML)
            </button>
            <button className="quick-test-btn" onClick={() => setMessage('ship aavumo?')}>
              Price (Manglish)
            </button>
            <button className="quick-test-btn" onClick={() => setMessage('When will my order arrive?')}>
              Shipping
            </button>
            <button className="quick-test-btn" onClick={() => setMessage('Can I pay by COD?')}>
              COD
            </button>
            <button className="quick-test-btn" onClick={() => setMessage('I want to order now')}>
              Purchase
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {result && (
        <>
          <div className="sandbox-result">
            {/* Language Detection */}
            <div className="result-card">
              <div className="result-label">Detected Language</div>
              <div className="result-value">
                {getLanguageIcon(result.detected_language)} {result.detected_language}
              </div>
              <div className="result-subtext">
                Confidence: {Math.round(result.language_confidence * 100)}%
              </div>
              <div className="confidence-bar">
                <div
                  className="confidence-bar-fill"
                  style={{ width: `${result.language_confidence * 100}%` }}
                />
              </div>
            </div>

            {/* Intent Detection */}
            <div className="result-card">
              <div className="result-label">Detected Intent</div>
              <div className="result-value">
                {result.detected_intent?.replace('_', ' ')}
              </div>
              <div className="result-subtext">
                Confidence: {Math.round(result.intent_confidence * 100)}%
              </div>
              <div className="confidence-bar">
                <div
                  className="confidence-bar-fill"
                  style={{
                    width: `${result.intent_confidence * 100}%`,
                    background: getIntentColor(result.detected_intent),
                  }}
                />
              </div>
            </div>

            {/* Detection Method */}
            <div className="result-card">
              <div className="result-label">Detection Method</div>
              <span
                className="result-badge"
                style={{ background: getMethodColor(result.detection_method) }}
              >
                {result.detection_method}
              </span>
              <div className="result-subtext" style={{ marginTop: '8px' }}>
                {result.detection_method === 'Rule Engine'
                  ? 'Detected by keyword matching (No API cost)'
                  : 'Will use Gemini API (Small token cost)'}
              </div>
            </div>

            {/* Context Info */}
            <div className="result-card">
              <div className="result-label">Context Available</div>
              <div className="result-value" style={{ fontSize: '16px' }}>
                📦 {result.products_available} | 📚 {result.kb_matches}
              </div>
              <div className="result-subtext">
                Products | KB Matches
              </div>
            </div>
          </div>

          {/* Sample Response */}
          {result.sample_response && (
            <div className="response-section">
              <div className="response-label">
                💬 Sample Response (Rule Engine)
              </div>
              <div className="response-text">
                {result.sample_response}
              </div>
            </div>
          )}
        </>
      )}

      {/* Info Box */}
      <div style={{
        background: '#f0f4ff',
        border: '1px solid #667eea',
        padding: '16px',
        borderRadius: '8px',
        fontSize: '13px',
        color: '#666',
        lineHeight: '1.5',
      }}>
        <strong>How it works:</strong><br />
        1. Your message is analyzed for language (English, Malayalam, Manglish)<br />
        2. Intent is detected using keyword matching (65% accuracy, zero cost)<br />
        3. If confidence &lt; 70%, Gemini API is called for uncertain intents<br />
        4. Response is generated with product/KB context<br />
        5. All interactions are logged and scored for customer intelligence
      </div>
    </div>
  );
}
