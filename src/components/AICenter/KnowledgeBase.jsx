import React, { useState, useEffect } from 'react';

/**
 * KnowledgeBase - Manage FAQ and knowledge articles
 */
export default function KnowledgeBase() {
  const [entries, setEntries] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [formData, setFormData] = useState({ question: '', answer: '', category: 'FAQ' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKB();
  }, [filterCategory]);

  const fetchKB = async () => {
    try {
      setLoading(true);
      let url = '/api/ai/knowledge-base';
      if (filterCategory !== 'all') {
        url += `?category=${filterCategory}`;
      }
      const response = await fetch(url);
      const data = await response.json();
      setEntries(data.entries || []);
    } catch (error) {
      console.error('Error fetching KB:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!formData.question || !formData.answer) {
      alert('Please fill in Question and Answer');
      return;
    }

    try {
      await fetch('/api/ai/knowledge-base', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: formData.question,
          answer: formData.answer,
          category: formData.category,
        }),
      });

      fetchKB();
      setShowForm(false);
      setEditingEntry(null);
      setFormData({ question: '', answer: '', category: 'FAQ' });
    } catch (error) {
      console.error('Error saving KB entry:', error);
      alert('Error saving entry');
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingEntry(null);
    setFormData({ question: '', answer: '', category: 'FAQ' });
  };

  const getCategoryColor = (category) => {
    const colors = {
      'FAQ': '#667eea',
      'Shipping': '#51cf66',
      'Payment': '#ff922b',
      'Policy': '#ffd93d',
      'Product': '#764ba2',
    };
    return colors[category] || '#a0a0a0';
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Loading knowledge base...</div>;
  }

  return (
    <div className="kb-container">
      <style>{`
        .kb-container {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        
        .kb-toolbar {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        
        .category-filter {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }
        
        .category-btn {
          padding: 6px 12px;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 11px;
          background: white;
          border: 1px solid #ddd;
        }
        
        .category-btn.active {
          background: #667eea;
          color: white;
          border-color: #667eea;
        }
        
        .btn-primary {
          background: #667eea;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: bold;
        }
        
        .btn-primary:hover {
          background: #764ba2;
        }
        
        .kb-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .kb-entry {
          background: white;
          padding: 12px;
          border-radius: 6px;
          border: 1px solid #eee;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .kb-entry:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .kb-entry.expanded {
          background: #f0f4ff;
          border-color: #667eea;
        }
        
        .kb-entry-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        
        .kb-question {
          font-weight: bold;
          color: #333;
          font-size: 13px;
          flex: 1;
        }
        
        .kb-category-badge {
          display: inline-block;
          padding: 3px 8px;
          border-radius: 3px;
          font-size: 10px;
          font-weight: bold;
          color: white;
          white-space: nowrap;
        }
        
        .kb-entry-body {
          margin-top: 8px;
          font-size: 12px;
          color: #666;
          line-height: 1.4;
        }
        
        .kb-form {
          background: white;
          padding: 20px;
          border-radius: 8px;
          border: 1px solid #eee;
        }
        
        .form-group {
          margin-bottom: 12px;
        }
        
        .form-group label {
          display: block;
          font-size: 12px;
          font-weight: bold;
          color: #333;
          margin-bottom: 4px;
        }
        
        .form-group input, .form-group select, .form-group textarea {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 13px;
          font-family: inherit;
        }
        
        .form-group textarea {
          min-height: 100px;
          resize: vertical;
        }
        
        .form-actions {
          display: flex;
          gap: 8px;
          margin-top: 12px;
        }
        
        .btn-save {
          background: #51cf66;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 13px;
          font-weight: bold;
        }
        
        .btn-save:hover {
          background: #40c057;
        }
        
        .btn-cancel {
          background: #a0a0a0;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 13px;
        }
        
        .btn-cancel:hover {
          background: #909090;
        }
      `}</style>

      {/* Toolbar */}
      <div className="kb-toolbar">
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? '✕ Cancel' : '+ Add New Entry'}
        </button>
      </div>

      {/* Category Filter */}
      <div className="category-filter">
        <button
          className={`category-btn ${filterCategory === 'all' ? 'active' : ''}`}
          onClick={() => setFilterCategory('all')}
        >
          All
        </button>
        <button
          className={`category-btn ${filterCategory === 'FAQ' ? 'active' : ''}`}
          onClick={() => setFilterCategory('FAQ')}
        >
          FAQ
        </button>
        <button
          className={`category-btn ${filterCategory === 'Shipping' ? 'active' : ''}`}
          onClick={() => setFilterCategory('Shipping')}
        >
          Shipping
        </button>
        <button
          className={`category-btn ${filterCategory === 'Payment' ? 'active' : ''}`}
          onClick={() => setFilterCategory('Payment')}
        >
          Payment
        </button>
        <button
          className={`category-btn ${filterCategory === 'Policy' ? 'active' : ''}`}
          onClick={() => setFilterCategory('Policy')}
        >
          Policy
        </button>
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="kb-form">
          <div style={{ fontWeight: 'bold', marginBottom: '12px', fontSize: '14px' }}>
            Add New KB Entry
          </div>

          <div className="form-group">
            <label>Question</label>
            <input
              type="text"
              value={formData.question}
              onChange={(e) => setFormData({ ...formData, question: e.target.value })}
              placeholder="e.g., Do you ship internationally?"
            />
          </div>

          <div className="form-group">
            <label>Answer</label>
            <textarea
              value={formData.answer}
              onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
              placeholder="Provide a detailed answer..."
            />
          </div>

          <div className="form-group">
            <label>Category</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            >
              <option value="FAQ">FAQ</option>
              <option value="Shipping">Shipping</option>
              <option value="Payment">Payment</option>
              <option value="Policy">Policy</option>
              <option value="Product">Product</option>
            </select>
          </div>

          <div className="form-actions">
            <button className="btn-save" onClick={handleSave}>Save Entry</button>
            <button className="btn-cancel" onClick={handleCancel}>Cancel</button>
          </div>
        </div>
      )}

      {/* KB List */}
      <div className="kb-list">
        {entries.map((entry) => (
          <div
            key={entry.kb_id}
            className={`kb-entry`}
            onClick={() => setEditingEntry(editingEntry?.kb_id === entry.kb_id ? null : entry)}
          >
            <div className="kb-entry-header">
              <div className="kb-question">{entry.question}</div>
              <span
                className="kb-category-badge"
                style={{ background: getCategoryColor(entry.category) }}
              >
                {entry.category}
              </span>
            </div>
            {editingEntry?.kb_id === entry.kb_id && (
              <div className="kb-entry-body">
                {entry.answer}
              </div>
            )}
          </div>
        ))}
      </div>

      {entries.length === 0 && (
        <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>
          No KB entries yet. Add one to help customers!
        </div>
      )}
    </div>
  );
}
