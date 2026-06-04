import React, { useState, useEffect } from 'react';

/**
 * LearningProgress - Track rule engine improvement from manual reviews (Wave 0.2)
 */
export default function LearningProgress() {
  const [progress, setProgress] = useState(null);
  const [stats, setStats] = useState(null);
  const [intentDist, setIntentDist] = useState(null);
  const [langDist, setLangDist] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProgressData();
    const interval = setInterval(fetchProgressData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchProgressData = async () => {
    try {
      setLoading(true);
      
      const [progressRes, statsRes, intentRes, langRes] = await Promise.all([
        fetch('/api/ai/review/learning/progress'),
        fetch('/api/ai/review/stats'),
        fetch('/api/ai/review/learning/intent-distribution'),
        fetch('/api/ai/review/learning/language-distribution'),
      ]);

      if (progressRes.ok) setProgress(await progressRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      if (intentRes.ok) setIntentDist((await intentRes.json()).distribution || {});
      if (langRes.ok) setLangDist((await langRes.json()).distribution || {});
    } catch (error) {
      console.error('Error fetching progress data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading learning progress...</div>;
  }

  return (
    <div className="learning-progress-container">
      <style>{`
        .learning-progress-container {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        
        .progress-card {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .card-title {
          font-weight: bold;
          font-size: 14px;
          color: #333;
          margin-bottom: 12px;
        }
        
        .progress-bar-container {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .progress-bar {
          flex: 1;
          height: 12px;
          background: #eee;
          border-radius: 6px;
          overflow: hidden;
        }
        
        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea, #764ba2);
          transition: width 0.3s ease;
        }
        
        .progress-label {
          font-size: 13px;
          font-weight: bold;
          color: #667eea;
          min-width: 50px;
          text-align: right;
        }
        
        .stat-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
          margin-top: 12px;
        }
        
        .stat-box {
          background: #f5f5f5;
          padding: 12px;
          border-radius: 6px;
          border-left: 3px solid #667eea;
        }
        
        .stat-label {
          font-size: 10px;
          color: #999;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }
        
        .stat-value {
          font-size: 18px;
          font-weight: bold;
          color: #333;
        }
        
        .accuracy-box {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 16px;
          border-radius: 8px;
          text-align: center;
          margin-top: 12px;
        }
        
        .accuracy-big {
          font-size: 32px;
          font-weight: bold;
        }
        
        .accuracy-label {
          font-size: 12px;
          opacity: 0.9;
          margin-top: 4px;
        }
        
        .milestone {
          font-size: 12px;
          color: white;
          margin-top: 8px;
          opacity: 0.8;
        }
        
        .distribution-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .distribution-item {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .dist-label {
          min-width: 120px;
          font-size: 12px;
          font-weight: bold;
          color: #333;
        }
        
        .dist-bar {
          flex: 1;
          height: 24px;
          background: #eee;
          border-radius: 4px;
          overflow: hidden;
          display: flex;
          align-items: center;
        }
        
        .dist-fill {
          height: 100%;
          background: #667eea;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 11px;
          font-weight: bold;
        }
        
        .milestone-box {
          background: #f0f4ff;
          border-left: 4px solid #667eea;
          padding: 12px;
          border-radius: 4px;
          margin-top: 12px;
        }
        
        .milestone-title {
          font-weight: bold;
          font-size: 12px;
          color: #667eea;
          margin-bottom: 4px;
        }
        
        .milestone-text {
          font-size: 11px;
          color: #666;
          line-height: 1.4;
        }
      `}</style>

      {/* Overall Accuracy Progress */}
      {progress && (
        <div className="progress-card">
          <div className="card-title">📈 Rule Engine Accuracy Improvement</div>
          
          <div className="accuracy-box">
            <div className="accuracy-big">{progress.estimated_current_accuracy}%</div>
            <div className="accuracy-label">Current Estimated Accuracy</div>
            <div className="milestone">Target: {progress.next_milestone}</div>
          </div>

          <div className="progress-bar-container" style={{ marginTop: '12px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '10px', color: '#999', marginBottom: '4px' }}>
                Learning Progress
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress.learning_progress_pct}%` }}
                />
              </div>
            </div>
            <div className="progress-label">{progress.learning_progress_pct}%</div>
          </div>

          <div className="stat-grid">
            <div className="stat-box">
              <div className="stat-label">Training Examples</div>
              <div className="stat-value">{progress.total_training_examples}</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Reclassifications</div>
              <div className="stat-value">{progress.reclassified_from_reviews}</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Accuracy Boost</div>
              <div className="stat-value" style={{ color: '#51cf66' }}>
                +{progress.estimated_current_accuracy - progress.base_accuracy}%
              </div>
            </div>
          </div>

          <div className="milestone-box">
            <div className="milestone-title">💡 How Learning Works</div>
            <div className="milestone-text">
              Each time you correct the AI's intent, it becomes a training example. The rule engine learns new keywords for better accuracy. No retraining needed!
            </div>
          </div>
        </div>
      )}

      {/* Review Queue Stats */}
      {stats && (
        <div className="progress-card">
          <div className="card-title">📋 Review Queue Status</div>
          
          <div className="stat-grid">
            <div className="stat-box">
              <div className="stat-label">Pending Reviews</div>
              <div className="stat-value" style={{ color: stats.pending > 0 ? '#ff6b6b' : '#51cf66' }}>
                {stats.pending}
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Approved</div>
              <div className="stat-value">{stats.approved}</div>
            </div>
            <div className="stat-box">
              <div className="stat-label">Corrected</div>
              <div className="stat-value" style={{ color: '#667eea' }}>{stats.reclassified}</div>
            </div>
          </div>

          {stats.pending > 0 && (
            <div style={{
              marginTop: '12px',
              padding: '12px',
              background: '#ffe3e3',
              border: '1px solid #ff8787',
              borderRadius: '4px',
              fontSize: '12px',
              color: '#c92a2a',
            }}>
              📌 You have <strong>{stats.pending} pending reviews</strong>. Spend 30 min reviewing to improve accuracy!
            </div>
          )}
        </div>
      )}

      {/* Intent Distribution */}
      {Object.keys(intentDist).length > 0 && (
        <div className="progress-card">
          <div className="card-title">🎯 Training Examples by Intent</div>
          
          <div className="distribution-list">
            {Object.entries(intentDist)
              .sort((a, b) => b[1] - a[1])
              .map(([intent, count]) => {
                const max = Math.max(...Object.values(intentDist));
                const pct = (count / max) * 100;
                return (
                  <div key={intent} className="distribution-item">
                    <div className="dist-label">{intent.replace('_', ' ')}</div>
                    <div className="dist-bar">
                      <div className="dist-fill" style={{ width: `${pct}%` }}>
                        {count}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>

          <div style={{ fontSize: '11px', color: '#999', marginTop: '8px' }}>
            Total: {Object.values(intentDist).reduce((a, b) => a + b, 0)} training examples
          </div>
        </div>
      )}

      {/* Language Distribution */}
      {Object.keys(langDist).length > 0 && (
        <div className="progress-card">
          <div className="card-title">🌐 Language Distribution</div>
          
          <div className="distribution-list">
            {Object.entries(langDist)
              .sort((a, b) => b[1] - a[1])
              .map(([lang, count]) => {
                const max = Math.max(...Object.values(langDist));
                const pct = (count / max) * 100;
                const langName = {
                  'english': '🇬🇧 English',
                  'malayalam': '🇮🇳 Malayalam',
                  'manglish': '🇮🇳 Manglish',
                  'mixed': '🌐 Mixed',
                };
                return (
                  <div key={lang} className="distribution-item">
                    <div className="dist-label">{langName[lang] || lang}</div>
                    <div className="dist-bar">
                      <div className="dist-fill" style={{ width: `${pct}%` }}>
                        {count}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Next Steps */}
      <div className="progress-card">
        <div className="card-title">✨ Next Steps</div>
        
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          fontSize: '12px',
          color: '#666',
          lineHeight: '1.5',
        }}>
          <div>
            <strong>Weekly Goal:</strong> Review 50 pending questions
            {progress && progress.total_training_examples < 50 && (
              <div style={{ color: '#667eea', marginTop: '4px' }}>
                → {50 - progress.total_training_examples} more examples needed to hit 72% accuracy
              </div>
            )}
          </div>
          <div>
            <strong>Time Commitment:</strong> ~2 hours/day during first 2 weeks
          </div>
          <div>
            <strong>Result:</strong> Rule engine accuracy improves from 65% → 72%+, no Gemini cost increase
          </div>
          <div style={{ marginTop: '12px', padding: '12px', background: '#f0f4ff', borderRadius: '4px', color: '#667eea' }}>
            <strong>Wave 1 Unlocks When:</strong> Rule engine > 70% accuracy (usually week 3)
          </div>
        </div>
      </div>
    </div>
  );
}
