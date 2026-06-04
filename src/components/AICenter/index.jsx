import React, { useState } from 'react';
import Dashboard from './Dashboard';
import Customers from './Customers';
import Conversations from './Conversations';
import ProductCatalog from './ProductCatalog';
import KnowledgeBase from './KnowledgeBase';
import AISandbox from './AISandbox';

/**
 * AICenter - Main container for AI CRM interface (Wave 0.1)
 * Manages navigation between 6 screens
 */
export default function AICenter() {
  const [activeScreen, setActiveScreen] = useState('dashboard');

  const screens = [
    { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
    { id: 'customers', label: '👥 Customers', icon: '👥' },
    { id: 'conversations', label: '💬 Conversations', icon: '💬' },
    { id: 'products', label: '🛍️ Products', icon: '🛍️' },
    { id: 'knowledge', label: '📚 Knowledge Base', icon: '📚' },
    { id: 'sandbox', label: '🧪 Sandbox', icon: '🧪' },
  ];

  const renderScreen = () => {
    switch (activeScreen) {
      case 'dashboard':
        return <Dashboard />;
      case 'customers':
        return <Customers />;
      case 'conversations':
        return <Conversations />;
      case 'products':
        return <ProductCatalog />;
      case 'knowledge':
        return <KnowledgeBase />;
      case 'sandbox':
        return <AISandbox />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="ai-center-container">
      <style>{`
        .ai-center-container {
          display: flex;
          height: 100vh;
          background: #f5f5f5;
        }
        
        .ai-sidebar {
          width: 250px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          overflow-y: auto;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .ai-sidebar-header {
          font-size: 20px;
          font-weight: bold;
          margin-bottom: 30px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .ai-sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .ai-nav-item {
          padding: 12px 16px;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s ease;
          font-size: 14px;
        }
        
        .ai-nav-item:hover {
          background: rgba(255,255,255,0.2);
          transform: translateX(4px);
        }
        
        .ai-nav-item.active {
          background: rgba(255,255,255,0.3);
          font-weight: bold;
          border-left: 3px solid white;
          padding-left: 13px;
        }
        
        .ai-main-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        
        .ai-header {
          background: white;
          padding: 20px;
          border-bottom: 1px solid #e0e0e0;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .ai-screen-content {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
        }
        
        .ai-screen-content::-webkit-scrollbar {
          width: 8px;
        }
        
        .ai-screen-content::-webkit-scrollbar-track {
          background: #f1f1f1;
        }
        
        .ai-screen-content::-webkit-scrollbar-thumb {
          background: #667eea;
          border-radius: 4px;
        }
        
        .ai-screen-content::-webkit-scrollbar-thumb:hover {
          background: #764ba2;
        }
      `}</style>

      {/* Sidebar Navigation */}
      <div className="ai-sidebar">
        <div className="ai-sidebar-header">
          🤖 AI Center
        </div>
        <nav className="ai-sidebar-nav">
          {screens.map((screen) => (
            <button
              key={screen.id}
              className={`ai-nav-item ${activeScreen === screen.id ? 'active' : ''}`}
              onClick={() => setActiveScreen(screen.id)}
              style={{ border: 'none', textAlign: 'left', color: 'white' }}
            >
              {screen.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="ai-main-content">
        <div className="ai-header">
          <h1 style={{ margin: 0, color: '#333', fontSize: '24px' }}>
            {screens.find(s => s.id === activeScreen)?.label || 'AI Center'}
          </h1>
        </div>
        <div className="ai-screen-content">
          {renderScreen()}
        </div>
      </div>
    </div>
  );
}
