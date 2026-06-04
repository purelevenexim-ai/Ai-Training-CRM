import React, { useState, useEffect } from 'react';

/**
 * ProductCatalog - Manage products (instant update, no retraining)
 */
export default function ProductCatalog() {
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({ name: '', price_inr: '', stock: '', category: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/ai/products');
      const data = await response.json();
      setProducts(data.products || []);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.price_inr) {
      alert('Please fill in Name and Price');
      return;
    }

    try {
      if (editingProduct) {
        // Update product
        await fetch(`/api/ai/products/${editingProduct.product_id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            price_inr: parseFloat(formData.price_inr),
            stock: parseInt(formData.stock) || 0,
          }),
        });
      } else {
        // Create product
        await fetch('/api/ai/products', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: formData.name,
            price_inr: parseFloat(formData.price_inr),
            stock: parseInt(formData.stock) || 0,
            category: formData.category,
          }),
        });
      }

      fetchProducts();
      setShowForm(false);
      setEditingProduct(null);
      setFormData({ name: '', price_inr: '', stock: '', category: '' });
    } catch (error) {
      console.error('Error saving product:', error);
      alert('Error saving product');
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      price_inr: product.price_inr.toString(),
      stock: product.stock.toString(),
      category: product.category || '',
    });
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingProduct(null);
    setFormData({ name: '', price_inr: '', stock: '', category: '' });
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Loading products...</div>;
  }

  return (
    <div className="product-catalog-container">
      <style>{`
        .product-catalog-container {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        
        .product-toolbar {
          display: flex;
          gap: 8px;
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
        
        .product-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .product-row {
          background: white;
          padding: 12px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          border: 1px solid #eee;
        }
        
        .product-info {
          flex: 1;
        }
        
        .product-name {
          font-weight: bold;
          color: #333;
          font-size: 13px;
        }
        
        .product-meta {
          font-size: 11px;
          color: #999;
          margin-top: 4px;
        }
        
        .product-price {
          font-size: 14px;
          font-weight: bold;
          color: #667eea;
        }
        
        .product-stock {
          font-size: 11px;
          color: ${(props) => props.low ? '#ff6b6b' : '#51cf66'};
          font-weight: bold;
        }
        
        .btn-edit {
          background: #667eea;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
        }
        
        .btn-edit:hover {
          background: #764ba2;
        }
        
        .product-form {
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
        
        .form-group input, .form-group select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 13px;
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
      <div className="product-toolbar">
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? '✕ Cancel' : '+ Add New Product'}
        </button>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <div className="product-form">
          <div style={{ fontWeight: 'bold', marginBottom: '12px', fontSize: '14px' }}>
            {editingProduct ? 'Edit Product' : 'Add New Product'}
          </div>
          
          <div className="form-group">
            <label>Product Name {editingProduct && '(Read-only)'}</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              disabled={!!editingProduct}
              placeholder="e.g., Black Pepper"
            />
          </div>

          <div className="form-group">
            <label>Price (₹)</label>
            <input
              type="number"
              value={formData.price_inr}
              onChange={(e) => setFormData({ ...formData, price_inr: e.target.value })}
              placeholder="e.g., 450"
            />
          </div>

          <div className="form-group">
            <label>Stock Units</label>
            <input
              type="number"
              value={formData.stock}
              onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
              placeholder="e.g., 100"
            />
          </div>

          <div className="form-group">
            <label>Category {!editingProduct && '(Optional)'}</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              disabled={!!editingProduct}
            >
              <option value="">Select Category</option>
              <option value="Pepper">Black Pepper</option>
              <option value="Cardamom">Cardamom</option>
              <option value="Cinnamon">Cinnamon</option>
              <option value="Clove">Clove</option>
              <option value="Turmeric">Turmeric</option>
              <option value="Other">Other Spices</option>
            </select>
          </div>

          <div className="form-actions">
            <button className="btn-save" onClick={handleSave}>Save</button>
            <button className="btn-cancel" onClick={handleCancel}>Cancel</button>
          </div>
        </div>
      )}

      {/* Product List */}
      <div className="product-list">
        {products.map((product) => (
          <div key={product.product_id} className="product-row">
            <div className="product-info">
              <div className="product-name">{product.name}</div>
              <div className="product-meta">
                {product.category && <span>{product.category}</span>}
                {product.category && product.status && <span> • </span>}
                {product.status && <span>{product.status}</span>}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="product-price">₹{product.price_inr.toLocaleString('en-IN')}</div>
              <div className="product-stock">
                Stock: {product.stock}
              </div>
            </div>
            <button className="btn-edit" onClick={() => handleEdit(product)}>
              Edit
            </button>
          </div>
        ))}
      </div>

      {products.length === 0 && (
        <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>
          No products yet. Add one to get started!
        </div>
      )}
    </div>
  );
}
