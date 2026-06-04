import React, { startTransition, useEffect, useRef, useState } from 'react';

const DEFAULT_AI_CONTROL = {
  ai_running: true,
  server_orchestration_enabled: true,
  flow_break_detection_enabled: true,
  structured_button_passthrough_enabled: true,
  wabis_fallback_when_disabled: true,
  wabis_priority_minutes: 5,
  selected_model: 'gemini_flash',
  temperature: 0.25,
  languages: ['english', 'manglish', 'malayalam'],
  followup_send_enabled: false,
  available_models: [],
};

const DEFAULT_KB_FORM = {
  category: 'fallback',
  product: 'general',
  product_name: '',
  trigger_examples: '',
  answer_primary: '',
  language: 'english',
  needs_review: false,
  review_reason: '',
  answer_variants: '',
  follow_up: '',
  tone: 'english_warm',
  intent: 'fallback',
  tags: '',
};

const KNOWLEDGE_INTENTS = [
  'availability',
  'price',
  'details',
  'quality',
  'origin',
  'processing',
  'usage',
  'benefits',
  'best_pack',
  'budget',
  'combo',
  'comparison',
  'price_objection',
  'delivery_charge',
  'delivery_time',
  'free_delivery',
  'order_request',
  'order_confirm',
  'wholesale',
  'gift',
  'stock_check',
  'complaint',
  'return_refund',
  'followup',
  'negation',
  'human_handoff',
  'business_info',
  'payment',
  'fallback',
];

const JOURNEY_TRIGGER_OPTIONS = [
  { value: 'product_interest', label: 'Product Interest' },
  { value: 'price_shared', label: 'Price Shared' },
  { value: 'cart_inactive', label: 'Cart / Chat Inactive' },
  { value: 'payment_pending', label: 'Payment Pending' },
  { value: 'order_confirmed', label: 'Order Confirmed' },
];

const JOURNEY_MESSAGE_TYPE_OPTIONS = [
  { value: 'text', label: 'Text Message' },
  { value: 'text_with_image', label: 'Product Image + Text' },
  { value: 'image_only', label: 'Image Only' },
  { value: 'combo', label: 'Combo List' },
  { value: 'payment_reminder', label: 'Payment Reminder' },
  { value: 'order_confirmation', label: 'Order Confirmation' },
];

function createEmptyProductForm() {
  return {
    product_key: '',
    display_name: '',
    aliases: '',
    origin: '',
    description: '',
    recommended_pack: '',
    recommendations_english: '',
    recommendations_manglish: '',
    recommendations_malayalam: '',
    reply_cta: '',
    images: [],
    variants: [
      {
        size: '',
        price: '',
        delivery: '',
      },
    ],
  };
}

function createDefaultJourneyForm() {
  return {
    id: '',
    name: 'Default Product Follow-up',
    description: 'Clean follow-up journey after a product reply.',
    status: 'active',
    applies_to: 'all_products',
    selected_products: '',
    trigger_type: 'product_interest',
    stop_on_reply: true,
    stop_on_order: true,
    stop_on_not_interested: true,
    stop_on_stop: true,
    steps: [
      { step_order: 1, delay_value: 4, delay_unit: 'minutes', message_type: 'text', message_text: 'Order venenkil peru, address, phone number, pincode ayacholu 😊', active: true },
      { step_order: 2, delay_value: 4, delay_unit: 'hours', message_type: 'text_with_image', message_text: 'Ithu venenkil innu dispatch cheyyan try cheyyam. Fresh stock aanu 😊', active: true },
      { step_order: 3, delay_value: 10, delay_unit: 'hours', message_type: 'combo', message_text: 'Combo vangumbol value nallath aanu. Kerala-il ₹600+ orderinu free delivery undu.', active: true },
      { step_order: 4, delay_value: 23, delay_unit: 'hours', message_type: 'text', message_text: 'Ithu close cheyyatte? Venamengil quantity paranjal order ready cheyyam 😊', active: true },
    ],
  };
}

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'customers', label: 'Customers' },
  { key: 'knowledge', label: 'Knowledge Base' },
  { key: 'ai', label: 'AI Control' },
  { key: 'gaps', label: 'Needs Fixing' },
  { key: 'products', label: 'Products' },
  { key: 'journeys', label: 'Customer Journey' },
];

const METRIC_LABELS = {
  today_chats: "Today's Chats",
  hot_leads: 'Hot Leads',
  orders_generated: 'Orders Generated',
  ai_success_rate: 'AI Success Rate',
  warm_leads: 'Warm Leads',
  cold_leads: 'Cold Leads',
  purchased: 'Purchased',
  trained_questions: 'Intent Patterns',
  needs_fixing: 'Needs Fixing',
};

const CRM_DASHBOARD_URL = '/journey/';

function formatDateTime(value) {
  if (!value) {
    return '—';
  }
  try {
    return new Intl.DateTimeFormat('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatPercent(value) {
  if (value === undefined || value === null) {
    return '0%';
  }
  return `${value}%`;
}

function toneBadge(label) {
  switch ((label || '').toLowerCase()) {
    case 'hot':
      return 'Hot';
    case 'warm':
      return 'Warm';
    case 'purchased':
      return 'Purchased';
    default:
      return 'Cold';
  }
}

function buildHeaders(secret) {
  return {
    'Content-Type': 'application/json',
    'x-anu-admin-secret': secret,
  };
}

export default function OwnerDashboard() {
  const params = new URLSearchParams(window.location.search);
  const secretFromQuery = params.get('admin_secret') || params.get('secret') || '';
  const [adminSecret, setAdminSecret] = useState(() => secretFromQuery || localStorage.getItem('anu_owner_secret') || '');
  const [secretDraft, setSecretDraft] = useState(() => secretFromQuery || localStorage.getItem('anu_owner_secret') || '');
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const [infrastructure, setInfrastructure] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [customerQuery, setCustomerQuery] = useState('');
  const [customerLabel, setCustomerLabel] = useState('all');
  const [selectedTimeline, setSelectedTimeline] = useState(null);
  const [kbItems, setKbItems] = useState([]);
  const [kbMeta, setKbMeta] = useState({ count: 0, search: '' });
  const [kbQuery, setKbQuery] = useState('');
  const [kbForm, setKbForm] = useState(DEFAULT_KB_FORM);
  const [editingKbId, setEditingKbId] = useState('');
  const [aiControl, setAiControl] = useState(DEFAULT_AI_CONTROL);
  const [gaps, setGaps] = useState({ knowledge_gaps: [], missing_products: [] });
  const [products, setProducts] = useState({ products: [], combos: [] });
  const [customerJourneys, setCustomerJourneys] = useState({ items: [], count: 0 });
  const [journeyForm, setJourneyForm] = useState(() => createDefaultJourneyForm());
  const [editingJourneyId, setEditingJourneyId] = useState('');
  const [productForm, setProductForm] = useState(() => createEmptyProductForm());
  const [editingProductKey, setEditingProductKey] = useState('');
  const [flashMessage, setFlashMessage] = useState('');
  const [productImageUrlDraft, setProductImageUrlDraft] = useState('');
  const [productImageCaptionDraft, setProductImageCaptionDraft] = useState('');
  const [productImagePrimaryDraft, setProductImagePrimaryDraft] = useState(true);
  const [productImageUploadActive, setProductImageUploadActive] = useState(false);
  const [productImageError, setProductImageError] = useState('');
  const [driveFolderUrlDraft, setDriveFolderUrlDraft] = useState('');
  const [driveSyncActive, setDriveSyncActive] = useState(false);
  const [driveSyncReport, setDriveSyncReport] = useState(null);
  const productImageInputRef = useRef(null);

  async function apiFetch(path, options = {}, secretOverride = adminSecret) {
    const isFormData =
      typeof FormData !== 'undefined' && options.body instanceof FormData;
    const response = await fetch(path, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(isFormData ? { 'x-anu-admin-secret': secretOverride } : buildHeaders(secretOverride)),
      },
    });

    if (response.status === 401) {
      throw new Error('Admin secret is required to open this dashboard.');
    }
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  async function loadCustomers(secretOverride = adminSecret, search = customerQuery, label = customerLabel) {
    const query = new URLSearchParams({
      search,
      label,
      limit: '80',
    });
    const payload = await apiFetch(`/api/owner/dashboard/customers?${query.toString()}`, {}, secretOverride);
    setCustomers(payload.items || []);
  }

  async function loadKnowledgeBase(secretOverride = adminSecret, search = kbQuery) {
    const query = new URLSearchParams({
      search,
      limit: '1000',
    });
    const payload = await apiFetch(`/api/owner/dashboard/knowledge-base?${query.toString()}`, {}, secretOverride);
    setKbItems(payload.items || []);
    setKbMeta({
      count: payload.count || 0,
      search: payload.search || search,
      storage_mode: payload.storage_mode || '',
      source_kind: payload.source_kind || '',
    });
  }

  async function loadAll(secretOverride = adminSecret) {
    if (!secretOverride) {
      return;
    }

    setLoading(true);
    setError('');
    try {
      const [
        summaryPayload,
        infrastructurePayload,
        customersPayload,
        knowledgePayload,
        aiPayload,
        gapsPayload,
        productsPayload,
        journeyPayload,
      ] = await Promise.all([
        apiFetch('/api/owner/dashboard/summary', {}, secretOverride),
        apiFetch('/api/owner/dashboard/infrastructure', {}, secretOverride),
        apiFetch('/api/owner/dashboard/customers?search=&label=all&limit=80', {}, secretOverride),
        apiFetch('/api/owner/dashboard/knowledge-base?search=&limit=1000', {}, secretOverride),
        apiFetch('/api/owner/dashboard/ai-control', {}, secretOverride),
        apiFetch('/api/owner/dashboard/training-gaps?limit=40', {}, secretOverride),
        apiFetch('/api/owner/dashboard/products', {}, secretOverride),
        apiFetch('/api/owner/dashboard/customer-journeys', {}, secretOverride),
      ]);

      startTransition(() => {
        setSummary(summaryPayload);
        setInfrastructure(infrastructurePayload);
        setCustomers(customersPayload.items || []);
        setKbItems(knowledgePayload.items || []);
        setKbMeta({
          count: knowledgePayload.count || 0,
          search: knowledgePayload.search || '',
          storage_mode: knowledgePayload.storage_mode || '',
          source_kind: knowledgePayload.source_kind || '',
        });
        setAiControl({ ...DEFAULT_AI_CONTROL, ...aiPayload });
        setGaps(gapsPayload);
        setProducts(productsPayload);
        setCustomerJourneys(journeyPayload);
      });
    } catch (loadError) {
      setError(loadError.message || 'Dashboard load failed.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (adminSecret) {
      loadAll(adminSecret);
    }
  }, [adminSecret]);

  useEffect(() => {
    const defaultDriveUrl = products?.media_sync?.default_drive_folder_url || '';
    if (defaultDriveUrl && !driveFolderUrlDraft) {
      setDriveFolderUrlDraft(defaultDriveUrl);
    }
  }, [products, driveFolderUrlDraft]);

  async function handleUnlock(event) {
    event.preventDefault();
    const trimmed = secretDraft.trim();
    if (!trimmed) {
      setError('Enter the admin secret to continue.');
      return;
    }
    localStorage.setItem('anu_owner_secret', trimmed);
    setError('');
    setAdminSecret(trimmed);
  }

  function handleLogout() {
    localStorage.removeItem('anu_owner_secret');
    setAdminSecret('');
    setSecretDraft('');
    setSummary(null);
    setInfrastructure(null);
    setCustomers([]);
    setSelectedTimeline(null);
    setKbItems([]);
    setKbMeta({ count: 0, search: '' });
    setGaps({ knowledge_gaps: [], missing_products: [] });
    setProducts({ products: [], combos: [] });
    setCustomerJourneys({ items: [], count: 0 });
    setJourneyForm(createDefaultJourneyForm());
    setEditingJourneyId('');
    setProductForm(createEmptyProductForm());
    setEditingProductKey('');
    setProductImageUrlDraft('');
    setProductImageCaptionDraft('');
    setProductImagePrimaryDraft(true);
    setProductImageUploadActive(false);
    setProductImageError('');
    setDriveFolderUrlDraft('');
    setDriveSyncActive(false);
    setDriveSyncReport(null);
    setActiveTab('overview');
    setError('');
    setFlashMessage('Logged out.');
    setTimeout(() => setFlashMessage(''), 1800);
  }

  async function handleTimeline(customer) {
    setError('');
    try {
      const payload = await apiFetch(`/api/owner/dashboard/customers/${encodeURIComponent(customer.phone || customer.id)}/timeline`);
      setSelectedTimeline(payload);
    } catch (timelineError) {
      setError(timelineError.message || 'Could not load customer timeline.');
    }
  }

  async function handleSaveAIControl(event) {
    event.preventDefault();
    setError('');
    try {
      const payload = await apiFetch('/api/owner/dashboard/ai-control', {
        method: 'PUT',
        body: JSON.stringify({
          ai_running: aiControl.ai_running,
          server_orchestration_enabled: aiControl.server_orchestration_enabled,
          flow_break_detection_enabled: aiControl.flow_break_detection_enabled,
          structured_button_passthrough_enabled: aiControl.structured_button_passthrough_enabled,
          wabis_fallback_when_disabled: aiControl.wabis_fallback_when_disabled,
          wabis_priority_minutes: Number(aiControl.wabis_priority_minutes || 5),
          selected_model: aiControl.selected_model,
          temperature: Number(aiControl.temperature),
          languages: aiControl.languages,
          followup_send_enabled: aiControl.followup_send_enabled,
        }),
      });
      setAiControl({ ...DEFAULT_AI_CONTROL, ...payload });
      setFlashMessage('AI control updated.');
      setTimeout(() => setFlashMessage(''), 2400);
      loadAll();
    } catch (saveError) {
      setError(saveError.message || 'Could not save AI control settings.');
    }
  }

  function beginKbEdit(item) {
    setEditingKbId(item.id);
    setKbForm({
      category: item.category || item.intent || 'fallback',
      product: item.product || 'general',
      product_name: item.product_name || '',
      trigger_examples: (item.trigger_examples || item.examples || [item.customer_input, ...(item.input_variations || [])])
        .filter(Boolean)
        .join('\n'),
      answer_primary: item.answer_primary || item.ideal_response || '',
      language: item.language || 'english',
      needs_review: Boolean(item.needs_review),
      review_reason: item.review_reason || '',
      answer_variants: (item.answer_variants || []).join('\n'),
      follow_up: item.follow_up || '',
      tone: item.tone || `${item.language || 'english'}_warm`,
      intent: item.intent || item.category || 'fallback',
      tags: (item.tags || []).join(', '),
    });
    setActiveTab('knowledge');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function resetKbForm() {
    setEditingKbId('');
    setKbForm(DEFAULT_KB_FORM);
  }

  async function handleKbSave(event) {
    event.preventDefault();
    setError('');
    try {
      const path = editingKbId
        ? `/api/owner/dashboard/knowledge-base/${encodeURIComponent(editingKbId)}`
        : '/api/owner/dashboard/knowledge-base';
      const method = editingKbId ? 'PUT' : 'POST';
      await apiFetch(path, {
        method,
        body: JSON.stringify({
          ...kbForm,
          category: kbForm.intent || kbForm.category,
          trigger_examples: kbForm.trigger_examples
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
          answer_primary: kbForm.answer_primary,
          answer_variants: kbForm.answer_variants
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
          tags: kbForm.tags
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
      setFlashMessage(editingKbId ? 'Intent pattern updated.' : 'Intent pattern added.');
      setTimeout(() => setFlashMessage(''), 2400);
      resetKbForm();
      loadKnowledgeBase();
      loadAll();
    } catch (saveError) {
      setError(saveError.message || 'Could not save the knowledge base entry.');
    }
  }

  async function handleKbDelete(entryId) {
    const confirmed = window.confirm('Delete this knowledge base entry?');
    if (!confirmed) {
      return;
    }
    setError('');
    try {
      await apiFetch(`/api/owner/dashboard/knowledge-base/${encodeURIComponent(entryId)}`, {
        method: 'DELETE',
      });
      if (editingKbId === entryId) {
        resetKbForm();
      }
      setFlashMessage('Intent pattern deleted.');
      setTimeout(() => setFlashMessage(''), 2400);
      loadKnowledgeBase();
      loadAll();
    } catch (deleteError) {
      setError(deleteError.message || 'Could not delete the knowledge base entry.');
    }
  }

  function beginProductEdit(product) {
    setEditingProductKey(product.product_key || '');
    setProductForm({
      product_key: product.product_key || '',
      display_name: product.display_name || '',
      aliases: (product.aliases || []).join(', '),
      origin: product.origin || '',
      description: product.description || '',
      recommended_pack: product.recommended_pack || '',
      recommendations_english: product.recommendations?.english || '',
      recommendations_manglish: product.recommendations?.manglish || '',
      recommendations_malayalam: product.recommendations?.malayalam || '',
      reply_cta: product.reply_cta || '',
      images: (product.images || []).map((image, index) => ({
        ...image,
        url: image.url || image.public_url || '',
        caption: image.caption || '',
        is_primary: Boolean(image.is_primary),
        sort_order: Number(image.sort_order ?? index) || index,
      })),
      variants: (product.variants || []).length
        ? product.variants.map((variant) => ({
            size: variant.size || '',
            price: String(variant.price ?? ''),
            delivery: variant.delivery || '',
          }))
        : createEmptyProductForm().variants,
    });
    setProductImageUrlDraft('');
    setProductImageCaptionDraft('');
    setProductImagePrimaryDraft(true);
    setProductImageError('');
    setActiveTab('products');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function resetProductForm() {
    setEditingProductKey('');
    setProductForm(createEmptyProductForm());
    setProductImageUrlDraft('');
    setProductImageCaptionDraft('');
    setProductImagePrimaryDraft(true);
    setProductImageUploadActive(false);
    setProductImageError('');
  }

  function updateProductVariant(index, field, value) {
    setProductForm((current) => ({
      ...current,
      variants: current.variants.map((variant, variantIndex) =>
        variantIndex === index ? { ...variant, [field]: value } : variant,
      ),
    }));
  }

  function addProductVariant() {
    setProductForm((current) => ({
      ...current,
      variants: [
        ...current.variants,
        {
          size: '',
          price: '',
          delivery: '',
        },
      ],
    }));
  }

  function removeProductVariant(index) {
    setProductForm((current) => {
      if (current.variants.length <= 1) {
        return current;
      }
      return {
        ...current,
        variants: current.variants.filter((_, variantIndex) => variantIndex !== index),
      };
    });
  }

  function applyUpdatedProduct(updatedProduct) {
    if (!updatedProduct?.product_key) {
      return;
    }

    const normalizedImages = (updatedProduct.images || []).map((image, index) => ({
      ...image,
      url: image.url || image.public_url || '',
      caption: image.caption || '',
      is_primary: Boolean(image.is_primary),
      sort_order: Number(image.sort_order ?? index) || index,
    }));

    setProducts((current) => ({
      ...current,
      products: (current.products || []).map((item) =>
        item.product_key === updatedProduct.product_key
          ? { ...item, ...updatedProduct, images: normalizedImages }
          : item,
      ),
    }));

    if (editingProductKey === updatedProduct.product_key || productForm.product_key === updatedProduct.product_key) {
      setProductForm((current) => ({
        ...current,
        ...updatedProduct,
        images: normalizedImages,
      }));
    }
  }

  async function uploadProductImageEntry(productKey, formData) {
    return apiFetch(`/api/owner/dashboard/products/${encodeURIComponent(productKey)}/images`, {
      method: 'POST',
      body: formData,
    });
  }

  async function handleProductImageFiles(fileList) {
    const files = Array.from(fileList || []).filter(Boolean);
    const productKey = (editingProductKey || productForm.product_key || '').trim();

    if (!productKey) {
      setProductImageError('Save the product first, then upload images for it.');
      return;
    }
    if (!files.length) {
      return;
    }

    setProductImageError('');
    setProductImageUploadActive(true);
    try {
      for (let index = 0; index < files.length; index += 1) {
        const file = files[index];
        const formData = new FormData();
        formData.append('image', file);
        formData.append('caption', productImageCaptionDraft);
        formData.append('is_primary', String(productImagePrimaryDraft && index === 0));
        formData.append('sort_order', String((productForm.images || []).length + index));
        const payload = await uploadProductImageEntry(productKey, formData);
        applyUpdatedProduct(payload.item);
      }
      setFlashMessage(`Uploaded ${files.length} image${files.length === 1 ? '' : 's'} for ${productKey}.`);
      setTimeout(() => setFlashMessage(''), 2400);
    } catch (uploadError) {
      setProductImageError(uploadError.message || 'Could not upload product image.');
    } finally {
      setProductImageUploadActive(false);
    }
  }

  async function handleProductImageUrlSubmit() {
    const productKey = (editingProductKey || productForm.product_key || '').trim();
    const imageUrl = productImageUrlDraft.trim();
    if (!productKey) {
      setProductImageError('Save the product first, then upload images for it.');
      return;
    }
    if (!imageUrl) {
      return;
    }

    setProductImageError('');
    setProductImageUploadActive(true);
    try {
      const formData = new FormData();
      formData.append('image_url', imageUrl);
      formData.append('caption', productImageCaptionDraft);
      formData.append('is_primary', String(productImagePrimaryDraft));
      formData.append('sort_order', String((productForm.images || []).length));
      const payload = await uploadProductImageEntry(productKey, formData);
      applyUpdatedProduct(payload.item);
      setProductImageUrlDraft('');
      setFlashMessage(`Added image URL for ${productKey}.`);
      setTimeout(() => setFlashMessage(''), 2400);
    } catch (uploadError) {
      setProductImageError(uploadError.message || 'Could not import image URL.');
    } finally {
      setProductImageUploadActive(false);
    }
  }

  function clearProductImageDrafts() {
    setProductImageUrlDraft('');
    setProductImageCaptionDraft('');
    setProductImagePrimaryDraft(true);
    setProductImageError('');
    if (productImageInputRef.current) {
      productImageInputRef.current.value = '';
    }
  }

  async function handleProductImageDelete(imageId) {
    const productKey = (editingProductKey || productForm.product_key || '').trim();
    if (!productKey) {
      return;
    }
    setProductImageError('');
    try {
      const payload = await apiFetch(
        `/api/owner/dashboard/products/${encodeURIComponent(productKey)}/images/${encodeURIComponent(imageId)}`,
        {
          method: 'DELETE',
        },
      );
      applyUpdatedProduct(payload.item);
      setFlashMessage('Product image removed.');
      setTimeout(() => setFlashMessage(''), 2200);
    } catch (deleteError) {
      setProductImageError(deleteError.message || 'Could not delete product image.');
    }
  }

  async function handleProductImagePrimary(imageId) {
    const productKey = (editingProductKey || productForm.product_key || '').trim();
    if (!productKey) {
      return;
    }
    setProductImageError('');
    try {
      const payload = await apiFetch(
        `/api/owner/dashboard/products/${encodeURIComponent(productKey)}/images/${encodeURIComponent(imageId)}/primary`,
        {
          method: 'PUT',
        },
      );
      applyUpdatedProduct(payload.item);
      setFlashMessage('Primary product image updated.');
      setTimeout(() => setFlashMessage(''), 2200);
    } catch (primaryError) {
      setProductImageError(primaryError.message || 'Could not set primary image.');
    }
  }

  async function handleDriveSync() {
    const folderUrl = driveFolderUrlDraft.trim();
    if (!folderUrl) {
      setError('Paste the Google Drive folder URL before syncing product images.');
      return;
    }

    setError('');
    setDriveSyncActive(true);
    try {
      const payload = await apiFetch('/api/owner/dashboard/products/import-drive-folder', {
        method: 'POST',
        body: JSON.stringify({
          folder_url: folderUrl,
        }),
      });
      setDriveSyncReport(payload);
      setFlashMessage(
        payload.imported_count
          ? `Imported ${payload.imported_count} product image${payload.imported_count === 1 ? '' : 's'} from Drive.`
          : 'Drive sync finished. No new images were added.',
      );
      setTimeout(() => setFlashMessage(''), 2600);
      await loadAll();
    } catch (syncError) {
      setError(syncError.message || 'Could not sync product images from Google Drive.');
    } finally {
      setDriveSyncActive(false);
    }
  }

  async function handleProductSave(event) {
    event.preventDefault();
    setError('');
    try {
      const path = editingProductKey
        ? `/api/owner/dashboard/products/${encodeURIComponent(editingProductKey)}`
        : '/api/owner/dashboard/products';
      const method = editingProductKey ? 'PUT' : 'POST';
      await apiFetch(path, {
        method,
        body: JSON.stringify({
          product_key: productForm.product_key,
          display_name: productForm.display_name,
          aliases: productForm.aliases,
          origin: productForm.origin,
          description: productForm.description,
          recommended_pack: productForm.recommended_pack,
          recommendations: {
            english: productForm.recommendations_english,
            manglish: productForm.recommendations_manglish,
            malayalam: productForm.recommendations_malayalam,
          },
          reply_cta: productForm.reply_cta,
          images: productForm.images,
          variants: productForm.variants
            .filter((variant) => variant.size.trim())
            .map((variant) => ({
              size: variant.size.trim(),
              price: Number(variant.price || 0),
              delivery: variant.delivery.trim(),
            })),
        }),
      });
      setFlashMessage(editingProductKey ? 'Product updated.' : 'Product added.');
      setTimeout(() => setFlashMessage(''), 2400);
      resetProductForm();
      loadAll();
    } catch (saveError) {
      setError(saveError.message || 'Could not save the product.');
    }
  }

  async function handleProductDelete(productKey) {
    const confirmed = window.confirm('Delete this product from the catalog?');
    if (!confirmed) {
      return;
    }
    setError('');
    try {
      await apiFetch(`/api/owner/dashboard/products/${encodeURIComponent(productKey)}`, {
        method: 'DELETE',
      });
      if (editingProductKey === productKey) {
        resetProductForm();
      }
      setFlashMessage('Product deleted.');
      setTimeout(() => setFlashMessage(''), 2400);
      loadAll();
    } catch (deleteError) {
      setError(deleteError.message || 'Could not delete the product.');
    }
  }

  function beginJourneyEdit(journey) {
    setEditingJourneyId(journey.id);
    setJourneyForm({
      ...createDefaultJourneyForm(),
      ...journey,
      selected_products: (journey.selected_products || []).join(', '),
      steps: (journey.steps || []).map((step, index) => ({
        id: step.id || '',
        step_order: step.step_order || index + 1,
        delay_value: step.delay_value || 1,
        delay_unit: step.delay_unit || 'minutes',
        message_type: step.message_type || 'text',
        message_text: step.message_text || '',
        active: Boolean(step.active ?? true),
      })),
    });
    setActiveTab('journeys');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function resetJourneyForm() {
    setEditingJourneyId('');
    setJourneyForm(createDefaultJourneyForm());
  }

  function updateJourneyStep(index, field, value) {
    const steps = [...journeyForm.steps];
    steps[index] = { ...steps[index], [field]: value };
    setJourneyForm({ ...journeyForm, steps });
  }

  function addJourneyStep() {
    setJourneyForm({
      ...journeyForm,
      steps: [
        ...journeyForm.steps,
        {
          step_order: journeyForm.steps.length + 1,
          delay_value: 1,
          delay_unit: 'hours',
          message_type: 'text',
          message_text: '',
          active: true,
        },
      ],
    });
  }

  function removeJourneyStep(index) {
    setJourneyForm({
      ...journeyForm,
      steps: journeyForm.steps.filter((_, itemIndex) => itemIndex !== index),
    });
  }

  async function handleJourneySave(event) {
    event.preventDefault();
    setError('');
    try {
      const path = editingJourneyId
        ? `/api/owner/dashboard/customer-journeys/${encodeURIComponent(editingJourneyId)}`
        : '/api/owner/dashboard/customer-journeys';
      const method = editingJourneyId ? 'PUT' : 'POST';
      await apiFetch(path, {
        method,
        body: JSON.stringify({
          ...journeyForm,
          selected_products: String(journeyForm.selected_products || '')
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
          steps: journeyForm.steps.map((step, index) => ({
            ...step,
            step_order: Number(step.step_order || index + 1),
            delay_value: Number(step.delay_value || 1),
          })),
        }),
      });
      setFlashMessage(editingJourneyId ? 'Customer journey updated.' : 'Customer journey created.');
      setTimeout(() => setFlashMessage(''), 2400);
      resetJourneyForm();
      loadAll();
    } catch (saveError) {
      setError(saveError.message || 'Could not save customer journey.');
    }
  }

  async function handleJourneyDelete(journeyId) {
    const confirmed = window.confirm('Delete this customer journey?');
    if (!confirmed) {
      return;
    }
    setError('');
    try {
      await apiFetch(`/api/owner/dashboard/customer-journeys/${encodeURIComponent(journeyId)}`, {
        method: 'DELETE',
      });
      setFlashMessage('Customer journey deleted.');
      setTimeout(() => setFlashMessage(''), 2400);
      resetJourneyForm();
      loadAll();
    } catch (deleteError) {
      setError(deleteError.message || 'Could not delete customer journey.');
    }
  }

  function toggleLanguage(language) {
    const current = new Set(aiControl.languages || []);
    if (current.has(language)) {
      current.delete(language);
    } else {
      current.add(language);
    }
    setAiControl({
      ...aiControl,
      languages: Array.from(current),
    });
  }

  if (!adminSecret) {
    const hasSavedSecret = Boolean(localStorage.getItem('anu_owner_secret'));
    return (
      <div className="owner-shell owner-shell--centered">
        <div className="owner-login-card">
          <p className="eyebrow">Pure Leven AI Owner Dashboard</p>
          <h1>Unlock Dashboard</h1>
          <p className="muted-copy">
            This dashboard is secured with your admin secret. Once you save it here, all sections load from the live
            `/api/owner/dashboard` endpoints on the current domain.
          </p>
          <div className="toolbar">
            <a className="ghost-button" href={CRM_DASHBOARD_URL} target="_blank" rel="noreferrer">
              Open Customer Journey CRM
            </a>
          </div>
          <form onSubmit={handleUnlock} className="owner-login-form">
            <label>
              Admin Secret
              <input
                type="password"
                value={secretDraft}
                onChange={(event) => setSecretDraft(event.target.value)}
                placeholder="Enter x-anu-admin-secret"
              />
            </label>
            <div className="toolbar">
              <button type="submit">Open Dashboard</button>
              {hasSavedSecret ? (
                <button type="button" className="ghost-button" onClick={handleLogout}>
                  Clear Saved Secret
                </button>
              ) : null}
            </div>
          </form>
          {flashMessage ? <p className="flash-banner">{flashMessage}</p> : null}
          {error ? <p className="error-text">{error}</p> : null}
        </div>
      </div>
    );
  }

  const metrics = summary?.metrics || {};
  const aiStatus = summary?.ai_status || {};
  const recentConversations = summary?.recent_conversations || [];
  const serverControlEnabled = Boolean(
    aiStatus.server_orchestration_enabled ?? aiControl.server_orchestration_enabled
  );

  return (
    <div className="owner-shell">
      <header className="owner-hero">
        <div>
          <p className="eyebrow">Pure Leven AI Sales Agent</p>
          <h1>Owner Dashboard</h1>
          <p className="hero-copy">
            Quick visibility into AI health, lead quality, trained questions, and what needs your attention today.
          </p>
        </div>
        <div className="hero-meta">
          <div className={`status-pill ${serverControlEnabled ? 'status-pill--live' : 'status-pill--paused'}`}>
            {serverControlEnabled ? 'Server Control ON' : 'Wabis Fallback Mode'}
          </div>
          <div className={`status-pill ${aiStatus.running ? 'status-pill--live' : 'status-pill--paused'}`}>
            {aiStatus.running ? 'AI Running' : 'AI Paused'}
          </div>
          <div className={`status-pill ${infrastructure?.https_enabled ? 'status-pill--secure' : 'status-pill--muted'}`}>
            {infrastructure?.https_enabled ? 'HTTPS Active' : 'HTTPS Missing'}
          </div>
          <a className="ghost-button" href={CRM_DASHBOARD_URL} target="_blank" rel="noreferrer">
            Customer Journey CRM
          </a>
          <button
            type="button"
            className="ghost-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </header>

      <section className="owner-infra-grid">
        <article className="infra-card">
          <span className="infra-label">Domain</span>
          <strong>{infrastructure?.domain || window.location.hostname || 'ai.pureleven.com'}</strong>
          <p>{infrastructure?.dashboard_url || `${window.location.protocol}//${window.location.host}`}</p>
        </article>
        <article className="infra-card">
          <span className="infra-label">Certificate</span>
          <strong>{infrastructure?.certificate_found ? 'Installed' : 'Missing'}</strong>
          <p>
            {infrastructure?.certificate_found
              ? `Expires in ${infrastructure?.days_remaining ?? '—'} days`
              : 'No certificate detected from the backend runtime.'}
          </p>
        </article>
        <article className="infra-card">
          <span className="infra-label">Model</span>
          <strong>{aiStatus.selected_model || aiControl.selected_model}</strong>
          <p>Temperature {Number(aiStatus.temperature ?? aiControl.temperature ?? 0).toFixed(2)}</p>
        </article>
        <article className="infra-card">
          <span className="infra-label">Languages</span>
          <strong>{(aiStatus.languages || aiControl.languages || []).join(', ')}</strong>
          <p>Reply tone follows English, Manglish, and Malayalam support.</p>
        </article>
      </section>

      <nav className="owner-tabs" aria-label="Dashboard sections">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={tab.key === activeTab ? 'owner-tab owner-tab--active' : 'owner-tab'}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {flashMessage ? <p className="flash-banner">{flashMessage}</p> : null}
      {loading ? <p className="muted-copy">Loading dashboard…</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      {activeTab === 'overview' ? (
        <section className="dashboard-panel">
          <div className="metric-grid">
            {Object.entries(METRIC_LABELS).map(([key, label]) => (
              <article key={key} className="metric-card">
                <span>{label}</span>
                <strong>{key === 'ai_success_rate' ? formatPercent(metrics[key]) : metrics[key] ?? 0}</strong>
              </article>
            ))}
          </div>

          <div className="panel-grid">
            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Recent Conversations</p>
                  <h2>Who is active right now</h2>
                </div>
              </div>
              <div className="conversation-stack">
                {recentConversations.length ? (
                  recentConversations.map((item) => (
                    <button key={`${item.phone}-${item.asked_at}`} type="button" className="conversation-row" onClick={() => handleTimeline(item)}>
                      <div>
                        <strong>{item.customer_name || item.phone}</strong>
                        <p>{item.asked}</p>
                      </div>
                      <div className="conversation-meta">
                        <span className={`label-chip label-chip--${item.badge || item.label}`}>{toneBadge(item.label)}</span>
                        <small>{formatDateTime(item.asked_at)}</small>
                      </div>
                    </button>
                  ))
                ) : (
                  <p className="muted-copy">No conversations captured for today yet.</p>
                )}
              </div>
            </article>

            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">AI Status</p>
                  <h2>Control snapshot</h2>
                </div>
              </div>
              <ul className="detail-list">
                <li>AI replies: {aiStatus.running ? 'Running' : 'Paused'}</li>
                <li>Follow-up sending: {aiStatus.followup_send_enabled ? 'Enabled' : 'Queued only'}</li>
                <li>Active sessions: {metrics.active_sessions ?? 0}</li>
                <li>AI replies in 7 days: {metrics.ai_generated_last_7d ?? 0}</li>
              </ul>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'customers' ? (
        <section className="dashboard-panel">
          <div className="panel-card">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Customers</p>
                <h2>Simple journey table</h2>
              </div>
              <form
                className="toolbar"
                onSubmit={(event) => {
                  event.preventDefault();
                  loadCustomers();
                }}
              >
                <input value={customerQuery} onChange={(event) => setCustomerQuery(event.target.value)} placeholder="Search name or phone" />
                <select value={customerLabel} onChange={(event) => setCustomerLabel(event.target.value)}>
                  <option value="all">All labels</option>
                  <option value="hot">Hot</option>
                  <option value="warm">Warm</option>
                  <option value="cold">Cold</option>
                  <option value="purchased">Purchased</option>
                </select>
                <button type="submit">Filter</button>
              </form>
            </div>
            <div className="table-wrap">
              <table className="owner-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Label</th>
                    <th>Score</th>
                    <th>Stage</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((customer) => (
                    <tr key={customer.id || customer.phone} onClick={() => handleTimeline(customer)}>
                      <td>{customer.name}</td>
                      <td>{customer.phone}</td>
                      <td>
                        <span className={`label-chip label-chip--${customer.label}`}>{toneBadge(customer.label)}</span>
                      </td>
                      <td>{customer.score}</td>
                      <td>{customer.stage}</td>
                      <td>{formatDateTime(customer.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === 'knowledge' ? (
        <section className="dashboard-panel">
          <div className="panel-grid">
            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Knowledge Base</p>
                  <h2>Intent knowledge patterns ({kbMeta.count || kbItems.length})</h2>
                  <p className="muted-copy">
                    We train reusable intent patterns now: product + intent + language + examples.
                  </p>
                </div>
                <form
                  className="toolbar"
                  onSubmit={(event) => {
                    event.preventDefault();
                    loadKnowledgeBase();
                  }}
                >
                  <input value={kbQuery} onChange={(event) => setKbQuery(event.target.value)} placeholder="Search intent, product, example, or answer" />
                  <button type="submit">Search</button>
                </form>
              </div>
              <div className="knowledge-list">
                {kbItems.map((item) => (
                  <article key={item.id} className="knowledge-row">
                    <div>
                      <strong>{item.display_title || `${item.product_name || item.product} • ${item.intent}`}</strong>
                      <p>{item.answer_primary || item.ideal_response}</p>
                      {(item.trigger_examples || []).length ? (
                        <small>
                          Examples: {(item.trigger_examples || []).slice(0, 3).join(' • ')}
                        </small>
                      ) : null}
                      <small>
                        {item.product} • {item.intent || item.category} • {item.language} • {(item.example_count || (item.trigger_examples || []).length || 1)} examples
                      </small>
                    </div>
                    <div className="toolbar">
                      <button type="button" className="ghost-button" onClick={() => beginKbEdit(item)}>
                        Edit
                      </button>
                      <button type="button" className="ghost-button" onClick={() => handleKbDelete(item.id)}>
                        Delete
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{editingKbId ? 'Update intent pattern' : 'Add intent pattern'}</p>
                  <h2>{editingKbId ? 'Edit reusable response logic' : 'Create reusable response logic'}</h2>
                </div>
              </div>
              <form className="stack-form" onSubmit={handleKbSave}>
                <label>
                  Product
                  <select
                    value={kbForm.product}
                    onChange={(event) => {
                      const nextProduct = event.target.value;
                      const matchedProduct = (products.products || []).find((item) => item.product_key === nextProduct);
                      setKbForm({
                        ...kbForm,
                        product: nextProduct,
                        product_name: matchedProduct?.display_name || (nextProduct === 'general' ? 'General' : kbForm.product_name),
                      });
                    }}
                  >
                    <option value="general">General</option>
                    {(products.products || []).map((product) => (
                      <option key={product.product_key} value={product.product_key}>
                        {product.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Product Name
                  <input value={kbForm.product_name} onChange={(event) => setKbForm({ ...kbForm, product_name: event.target.value })} />
                </label>
                <label>
                  Intent
                  <select
                    value={kbForm.intent}
                    onChange={(event) => setKbForm({ ...kbForm, intent: event.target.value, category: event.target.value })}
                  >
                    {KNOWLEDGE_INTENTS.map((intent) => (
                      <option key={intent} value={intent}>
                        {intent}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Tone
                  <input value={kbForm.tone} onChange={(event) => setKbForm({ ...kbForm, tone: event.target.value })} placeholder="english_warm / manglish_price" />
                </label>
                <label>
                  Trigger Examples
                  <textarea
                    rows="6"
                    value={kbForm.trigger_examples}
                    onChange={(event) => setKbForm({ ...kbForm, trigger_examples: event.target.value })}
                    placeholder={'One example per line\nkurumulak undo?\nblack pepper price\npepper delivery undo?'}
                  />
                </label>
                <label>
                  Primary Answer
                  <textarea
                    rows="8"
                    value={kbForm.answer_primary}
                    onChange={(event) => setKbForm({ ...kbForm, answer_primary: event.target.value })}
                  />
                </label>
                <label>
                  Answer Variants
                  <textarea
                    rows="5"
                    value={kbForm.answer_variants}
                    onChange={(event) => setKbForm({ ...kbForm, answer_variants: event.target.value })}
                    placeholder="Optional alternate phrasings, one per line"
                  />
                </label>
                <label>
                  Follow-up Guidance
                  <textarea
                    rows="3"
                    value={kbForm.follow_up}
                    onChange={(event) => setKbForm({ ...kbForm, follow_up: event.target.value })}
                    placeholder="How this intent should continue after the main reply"
                  />
                </label>
                <label>
                  Language
                  <select value={kbForm.language} onChange={(event) => setKbForm({ ...kbForm, language: event.target.value })}>
                    <option value="english">English</option>
                    <option value="manglish">Manglish</option>
                    <option value="malayalam">Malayalam</option>
                  </select>
                </label>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={kbForm.needs_review}
                    onChange={(event) => setKbForm({ ...kbForm, needs_review: event.target.checked })}
                  />
                  Mark for review
                </label>
                <label>
                  Review reason
                  <input value={kbForm.review_reason} onChange={(event) => setKbForm({ ...kbForm, review_reason: event.target.value })} />
                </label>
                <label>
                  Tags
                  <input value={kbForm.tags} onChange={(event) => setKbForm({ ...kbForm, tags: event.target.value })} placeholder="cardamom, availability, english_warm" />
                </label>
                <div className="toolbar">
                  <button type="submit">{editingKbId ? 'Update entry' : 'Save entry'}</button>
                  <button type="button" className="ghost-button" onClick={resetKbForm}>
                    Clear
                  </button>
                </div>
              </form>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'ai' ? (
        <section className="dashboard-panel">
          <article className="panel-card">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">AI Control Center</p>
                <h2>Simple runtime controls</h2>
              </div>
            </div>
            <form className="stack-form" onSubmit={handleSaveAIControl}>
              <div className={`control-callout ${aiControl.server_orchestration_enabled ? 'control-callout--live' : 'control-callout--fallback'}`}>
                <div>
                  <strong>
                    {aiControl.server_orchestration_enabled
                      ? 'Server-first routing is active'
                      : 'Emergency Wabis fallback is active'}
                  </strong>
                  <p>
                    {aiControl.server_orchestration_enabled
                      ? 'Every incoming WhatsApp message is routed by PureLeven first. Button clicks stay with Wabis, but product/support text can break out to AI.'
                      : 'PureLeven will receive/audit webhooks but will not route, mutate flow state, or send AI replies. Wabis native automation can continue.'}
                  </p>
                </div>
              </div>

              <label>
                Instant WhatsApp Control
                <div className="split-toggle">
                  <button
                    type="button"
                    className={aiControl.server_orchestration_enabled ? 'toggle-button toggle-button--active' : 'toggle-button'}
                    onClick={() => setAiControl({ ...aiControl, server_orchestration_enabled: true })}
                  >
                    Server Controls
                  </button>
                  <button
                    type="button"
                    className={!aiControl.server_orchestration_enabled ? 'toggle-button toggle-button--active toggle-button--danger' : 'toggle-button'}
                    onClick={() => setAiControl({ ...aiControl, server_orchestration_enabled: false })}
                  >
                    Wabis Fallback
                  </button>
                </div>
                <span className="helper-copy">
                  Use Wabis Fallback as the instant kill switch if replies break during live testing.
                </span>
              </label>

              <label>
                AI Reply Generation
              <div className="split-toggle">
                <button
                  type="button"
                  className={aiControl.ai_running ? 'toggle-button toggle-button--active' : 'toggle-button'}
                  onClick={() => setAiControl({ ...aiControl, ai_running: true })}
                >
                  Start AI
                </button>
                <button
                  type="button"
                  className={!aiControl.ai_running ? 'toggle-button toggle-button--active' : 'toggle-button'}
                  onClick={() => setAiControl({ ...aiControl, ai_running: false })}
                >
                  Stop AI
                </button>
              </div>
                <span className="helper-copy">
                  This pauses generated AI/product replies. Server control can still audit and protect Wabis button flows.
                </span>
              </label>

              <label>
                Model Selection
                <select
                  value={aiControl.selected_model}
                  onChange={(event) => setAiControl({ ...aiControl, selected_model: event.target.value })}
                >
                  {(aiControl.available_models || []).map((model) => (
                    <option key={model.key} value={model.key}>
                      {model.label} {model.available ? '' : '(Unavailable)'}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Temperature
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={aiControl.temperature}
                  onChange={(event) => setAiControl({ ...aiControl, temperature: Number(event.target.value) })}
                />
                <span className="slider-value">{Number(aiControl.temperature).toFixed(2)} — Precise to Creative</span>
              </label>

              <div className="language-box">
                <span>Languages</span>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={(aiControl.languages || []).includes('english')}
                    onChange={() => toggleLanguage('english')}
                  />
                  English
                </label>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={(aiControl.languages || []).includes('manglish')}
                    onChange={() => toggleLanguage('manglish')}
                  />
                  Manglish
                </label>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={(aiControl.languages || []).includes('malayalam')}
                    onChange={() => toggleLanguage('malayalam')}
                  />
                  Malayalam
                </label>
              </div>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={Boolean(aiControl.followup_send_enabled)}
                  onChange={(event) => setAiControl({ ...aiControl, followup_send_enabled: event.target.checked })}
                />
                Enable live follow-up sending
              </label>

              <div className="language-box">
                <span>Routing Guardrails</span>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={Boolean(aiControl.flow_break_detection_enabled)}
                    onChange={(event) => setAiControl({ ...aiControl, flow_break_detection_enabled: event.target.checked })}
                  />
                  Detect flow breaks from product/support text
                </label>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={Boolean(aiControl.structured_button_passthrough_enabled)}
                    onChange={(event) => setAiControl({ ...aiControl, structured_button_passthrough_enabled: event.target.checked })}
                  />
                  Let Wabis structured button clicks continue the flow
                </label>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={Boolean(aiControl.wabis_fallback_when_disabled)}
                    onChange={(event) => setAiControl({ ...aiControl, wabis_fallback_when_disabled: event.target.checked })}
                  />
                  Treat Wabis as fallback owner when server control is off
                </label>
                <label>
                  Wabis Priority Window (minutes)
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={aiControl.wabis_priority_minutes}
                    onChange={(event) => setAiControl({ ...aiControl, wabis_priority_minutes: Number(event.target.value || 5) })}
                  />
                  <span className="helper-copy">
                    During this window, Wabis automation stays in charge and AI only waits in the background.
                  </span>
                </label>
              </div>

              <button type="submit">Save AI settings</button>
            </form>
          </article>
        </section>
      ) : null}

      {activeTab === 'gaps' ? (
        <section className="dashboard-panel">
          <div className="panel-grid">
            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Lead Inbox</p>
                  <h2>Unresolved knowledge gaps</h2>
                </div>
              </div>
              <div className="gap-stack">
                {(gaps.knowledge_gaps || []).map((gap) => (
                  <article key={gap.id} className="gap-row">
                    <strong>{gap.original_query}</strong>
                    <p>
                      {gap.detected_intent || 'unknown intent'} • {gap.phone || 'no phone'}
                    </p>
                    <small>{formatDateTime(gap.created_at)}</small>
                  </article>
                ))}
                {!gaps.knowledge_gaps?.length ? <p className="muted-copy">No unresolved knowledge gaps right now.</p> : null}
              </div>
            </article>

            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Missing Products</p>
                  <h2>Catalog requests to add</h2>
                </div>
              </div>
              <div className="gap-stack">
                {(gaps.missing_products || []).map((product) => (
                  <article key={`${product.product_name}-${product.last_searched}`} className="gap-row">
                    <strong>{product.product_name}</strong>
                    <p>Searched {product.search_count || 0} times</p>
                    <small>{formatDateTime(product.last_searched)}</small>
                  </article>
                ))}
                {!gaps.missing_products?.length ? <p className="muted-copy">No missing product requests detected.</p> : null}
              </div>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'products' ? (
        <section className="dashboard-panel">
          <div className="panel-grid">
            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Products</p>
                  <h2>Current live catalog ({(products.products || []).length})</h2>
                </div>
              </div>
              <div className="product-stack">
                {(products.products || []).map((product) => (
                  <article key={product.product_key} className="product-card">
                    <div className="product-card__head">
                      <div>
                        <strong>{product.display_name}</strong>
                        <p>
                          {product.origin} • {product.description}
                        </p>
                      </div>
                      <div className="product-card__meta">
                        <span className="label-chip label-chip--neutral">Recommended: {product.recommended_pack}</span>
                        <span className="label-chip label-chip--neutral">
                          Reply images: {(product.images || []).length}
                        </span>
                      </div>
                    </div>
                    <div className="table-wrap">
                      <table className="owner-table owner-table--compact">
                        <thead>
                          <tr>
                            <th>Size</th>
                            <th>Price</th>
                            <th>Delivery</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(product.variants || []).map((variant) => (
                            <tr key={`${product.product_key}-${variant.size}`}>
                              <td>{variant.size}</td>
                              <td>₹{variant.price}</td>
                              <td>{variant.delivery}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {(product.images || []).length ? (
                      <div className="product-media-grid">
                        {(product.images || []).map((image) => (
                          <figure
                            key={image.id || image.url}
                            className={`product-media-thumb${image.is_primary ? ' product-media-thumb--primary' : ''}`}
                          >
                            <img src={image.url || image.public_url || ''} alt={image.caption || product.display_name} />
                            <figcaption>
                              <span>{image.is_primary ? 'Primary' : 'Image'}</span>
                              {image.caption ? <small>{image.caption}</small> : null}
                            </figcaption>
                          </figure>
                        ))}
                      </div>
                    ) : null}
                    <small className="muted-copy">Aliases: {(product.aliases || []).join(', ')}</small>
                    <div className="toolbar">
                      <button type="button" className="ghost-button" onClick={() => beginProductEdit(product)}>
                        Manage Images
                      </button>
                      <button type="button" className="ghost-button" onClick={() => beginProductEdit(product)}>
                        Edit Product
                      </button>
                      <button type="button" className="ghost-button" onClick={() => handleProductDelete(product.product_key)}>
                        Delete Product
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{editingProductKey ? 'Update product' : 'Add product'}</p>
                  <h2>{editingProductKey ? 'Edit product details' : 'Create a new product'}</h2>
                </div>
              </div>
              <section className="product-upload-card">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Google Drive Sync</p>
                    <h2>Import product images from Drive</h2>
                  </div>
                  <span className="label-chip label-chip--neutral">
                    {driveSyncActive ? 'Syncing…' : 'One-click import'}
                  </span>
                </div>
                <label>
                  Shared Drive Folder URL
                  <input
                    value={driveFolderUrlDraft}
                    onChange={(event) => setDriveFolderUrlDraft(event.target.value)}
                    placeholder="Paste the public Google Drive folder URL"
                  />
                </label>
                <p className="helper-copy">
                  Keep one subfolder per product, like <strong>Black Pepper</strong> or <strong>Clove</strong>. We’ll
                  match those folder names to the live product aliases and attach the images automatically.
                </p>
                <div className="toolbar">
                  <button type="button" onClick={handleDriveSync} disabled={driveSyncActive || !driveFolderUrlDraft.trim()}>
                    {driveSyncActive ? 'Syncing Drive Images…' : 'Sync Drive Images'}
                  </button>
                </div>
                {driveSyncReport ? (
                  <div className="drive-sync-report">
                    <p className="muted-copy">
                      Imported <strong>{driveSyncReport.imported_count || 0}</strong> image{driveSyncReport.imported_count === 1 ? '' : 's'}.
                    </p>
                    {(driveSyncReport.products_updated || []).length ? (
                      <ul className="detail-list">
                        {(driveSyncReport.products_updated || []).map((item) => (
                          <li key={item.product_key}>
                            {item.display_name}: {item.image_count} live image{item.image_count === 1 ? '' : 's'}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {(driveSyncReport.unmatched_folders || []).length ? (
                      <p className="muted-copy">
                        Unmatched folders: {(driveSyncReport.unmatched_folders || []).join(', ')}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </section>
              <form className="stack-form" onSubmit={handleProductSave}>
                <label>
                  Product Name
                  <input value={productForm.display_name} onChange={(event) => setProductForm({ ...productForm, display_name: event.target.value })} />
                </label>
                <label>
                  Product Key
                  <input
                    value={productForm.product_key}
                    onChange={(event) => setProductForm({ ...productForm, product_key: event.target.value })}
                    placeholder="cardamom / black_pepper"
                    readOnly={Boolean(editingProductKey)}
                  />
                  {editingProductKey ? <small className="helper-copy">Product key is locked after the first save so images stay attached.</small> : null}
                </label>
                <label>
                  Aliases
                  <textarea rows="3" value={productForm.aliases} onChange={(event) => setProductForm({ ...productForm, aliases: event.target.value })} placeholder="cardamom, elakka, yelakka" />
                </label>
                <label>
                  Origin
                  <input value={productForm.origin} onChange={(event) => setProductForm({ ...productForm, origin: event.target.value })} />
                </label>
                <label>
                  Description
                  <input value={productForm.description} onChange={(event) => setProductForm({ ...productForm, description: event.target.value })} />
                </label>
                <label>
                  Recommended Pack
                  <input value={productForm.recommended_pack} onChange={(event) => setProductForm({ ...productForm, recommended_pack: event.target.value })} />
                </label>
                <label>
                  English Recommendation
                  <textarea rows="3" value={productForm.recommendations_english} onChange={(event) => setProductForm({ ...productForm, recommendations_english: event.target.value })} />
                </label>
                <label>
                  Manglish Recommendation
                  <textarea rows="3" value={productForm.recommendations_manglish} onChange={(event) => setProductForm({ ...productForm, recommendations_manglish: event.target.value })} />
                </label>
                <label>
                  Malayalam Recommendation
                  <textarea rows="3" value={productForm.recommendations_malayalam} onChange={(event) => setProductForm({ ...productForm, recommendations_malayalam: event.target.value })} />
                </label>
                <label>
                  Reply CTA
                  <textarea rows="3" value={productForm.reply_cta} onChange={(event) => setProductForm({ ...productForm, reply_cta: event.target.value })} />
                </label>
                <section className="product-upload-card">
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">Product Media</p>
                      <h2>Upload images for replies</h2>
                    </div>
                    <span className="label-chip label-chip--neutral">
                      {(productForm.images || []).length ? `${productForm.images.length} image${productForm.images.length === 1 ? '' : 's'}` : 'No images'}
                    </span>
                  </div>
                  <div
                    className={`product-upload-dropzone ${productImageUploadActive ? 'product-upload-dropzone--busy' : ''}`}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => {
                      event.preventDefault();
                      handleProductImageFiles(event.dataTransfer.files);
                    }}
                    onClick={() => productImageInputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                  >
                    <strong>Drag and drop product photos here</strong>
                    <p>Use clean, clear images for black pepper, clove, cinnamon, turmeric, or any future product.</p>
                    <div className="toolbar">
                      <button type="button" className="ghost-button" onClick={(event) => {
                        event.stopPropagation();
                        productImageInputRef.current?.click();
                      }}>
                        Browse images
                      </button>
                      <button type="button" className="ghost-button" onClick={(event) => {
                        event.stopPropagation();
                        clearProductImageDrafts();
                      }}>
                        Clear uploader
                      </button>
                    </div>
                  </div>
                  {!editingProductKey && !productForm.product_key ? (
                    <p className="helper-copy">
                      Save the product first or click <strong>Manage Images</strong> on an existing product, then drag
                      and drop the reply photos here.
                    </p>
                  ) : null}
                  <input
                    ref={productImageInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    hidden
                    onChange={(event) => {
                      handleProductImageFiles(event.target.files);
                      event.target.value = '';
                    }}
                  />
                  <div className="product-upload-actions">
                    <label>
                      Image URL
                      <input
                        value={productImageUrlDraft}
                        onChange={(event) => setProductImageUrlDraft(event.target.value)}
                        placeholder="Paste a direct image URL or hosted file URL"
                      />
                    </label>
                    <label>
                      Caption
                      <input
                        value={productImageCaptionDraft}
                        onChange={(event) => setProductImageCaptionDraft(event.target.value)}
                        placeholder="Short caption for the image"
                      />
                    </label>
                    <label className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={productImagePrimaryDraft}
                        onChange={(event) => setProductImagePrimaryDraft(event.target.checked)}
                      />
                      Set as primary image
                    </label>
                    <div className="toolbar">
                      <button type="button" className="ghost-button" onClick={handleProductImageUrlSubmit} disabled={!productImageUrlDraft.trim() || productImageUploadActive}>
                        Add Image URL
                      </button>
                    </div>
                  </div>
                  {(productForm.images || []).length ? (
                    <div className="product-media-grid product-media-grid--editor">
                      {(productForm.images || []).map((image) => (
                        <figure
                          key={image.id || image.url}
                          className={`product-media-thumb${image.is_primary ? ' product-media-thumb--primary' : ''}`}
                        >
                          <img src={image.url || image.public_url || ''} alt={image.caption || productForm.display_name || 'Product image'} />
                          <figcaption>
                            <span>{image.is_primary ? 'Primary' : 'Image'}</span>
                            <small>{image.caption || image.filename || 'Uploaded image'}</small>
                          </figcaption>
                          <div className="toolbar product-media-thumb__actions">
                            <button type="button" className="ghost-button" onClick={() => handleProductImagePrimary(image.id)}>
                              Make Primary
                            </button>
                            <button type="button" className="ghost-button" onClick={() => handleProductImageDelete(image.id)}>
                              Delete
                            </button>
                          </div>
                        </figure>
                      ))}
                    </div>
                  ) : (
                    <p className="muted-copy">No product images uploaded yet. Add at least one image so replies can include visuals.</p>
                  )}
                  {productImageError ? <p className="error-text">{productImageError}</p> : null}
                </section>
                <div className="variant-editor">
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">Variants</p>
                      <h2>Sizes and pricing</h2>
                    </div>
                    <button type="button" className="ghost-button" onClick={addProductVariant}>
                      Add Variant
                    </button>
                  </div>
                  {productForm.variants.map((variant, index) => (
                    <div key={`variant-${index}`} className="variant-row">
                      <input
                        value={variant.size}
                        onChange={(event) => updateProductVariant(index, 'size', event.target.value)}
                        placeholder="Size"
                      />
                      <input
                        type="number"
                        value={variant.price}
                        onChange={(event) => updateProductVariant(index, 'price', event.target.value)}
                        placeholder="Price"
                      />
                      <input
                        value={variant.delivery}
                        onChange={(event) => updateProductVariant(index, 'delivery', event.target.value)}
                        placeholder="Delivery"
                      />
                      <button type="button" className="ghost-button" onClick={() => removeProductVariant(index)}>
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <div className="toolbar">
                  <button type="submit">{editingProductKey ? 'Update Product' : 'Save Product'}</button>
                  <button type="button" className="ghost-button" onClick={resetProductForm}>
                    Clear
                  </button>
                </div>
              </form>
              <div className="gap-stack product-combos">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Combos</p>
                    <h2>Current offer packs</h2>
                  </div>
                </div>
                {(products.combos || []).map((combo) => (
                  <article key={`${combo.title}-${combo.includes}`} className="gap-row">
                    <strong>{combo.title}</strong>
                    <p>{combo.includes}</p>
                    <small>
                      ₹{combo.price} • {combo.delivery}
                    </small>
                  </article>
                ))}
                {!products.combos?.length ? <p className="muted-copy">No combo packs configured yet.</p> : null}
              </div>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'journeys' ? (
        <section className="dashboard-panel">
          <div className="panel-grid">
            <article className="panel-card">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Customer Journey</p>
                  <h2>Customer Journey automation</h2>
                  <p className="muted-copy">
                    Create, edit, pause, and delete the timed customer journeys used after product replies.
                  </p>
                </div>
                <button type="button" className="ghost-button" onClick={resetJourneyForm}>
                  + Create Journey
                </button>
              </div>
              <div className="table-wrap">
                <table className="owner-table owner-table--compact">
                  <thead>
                    <tr>
                      <th>Journey</th>
                      <th>Status</th>
                      <th>Applies To</th>
                      <th>Trigger</th>
                      <th>Steps</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(customerJourneys.items || []).map((journey) => (
                      <tr key={journey.id}>
                        <td>
                          <strong>{journey.name}</strong>
                          <p className="muted-copy">{journey.description || 'No description'}</p>
                        </td>
                        <td>{journey.status}</td>
                        <td>
                          {journey.applies_to === 'selected_products'
                            ? (journey.selected_products || []).join(', ') || 'Selected products'
                            : 'All products'}
                        </td>
                        <td>{journey.trigger_type}</td>
                        <td>{journey.steps?.length || 0}</td>
                        <td>
                          <div className="toolbar toolbar--compact">
                            <button type="button" className="ghost-button" onClick={() => beginJourneyEdit(journey)}>
                              Edit
                            </button>
                            <button type="button" className="ghost-button" onClick={() => handleJourneyDelete(journey.id)}>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!customerJourneys.items?.length ? (
                      <tr>
                        <td colSpan="6">No journeys configured yet. Save the default journey to activate one.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel-card">
              <form onSubmit={handleJourneySave} className="knowledge-form">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">{editingJourneyId ? 'Edit Journey' : 'New Journey'}</p>
                    <h2>{editingJourneyId ? 'Update follow-up steps' : 'Create follow-up journey'}</h2>
                  </div>
                </div>
                <label>
                  Journey Name
                  <input
                    value={journeyForm.name}
                    onChange={(event) => setJourneyForm({ ...journeyForm, name: event.target.value })}
                    placeholder="Default Product Interest Follow-up"
                  />
                </label>
                <label>
                  Description
                  <textarea
                    rows="2"
                    value={journeyForm.description}
                    onChange={(event) => setJourneyForm({ ...journeyForm, description: event.target.value })}
                  />
                </label>
                <div className="form-grid">
                  <label>
                    Status
                    <select
                      value={journeyForm.status}
                      onChange={(event) => setJourneyForm({ ...journeyForm, status: event.target.value })}
                    >
                      <option value="active">Active</option>
                      <option value="draft">Draft</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </label>
                  <label>
                    Applies To
                    <select
                      value={journeyForm.applies_to}
                      onChange={(event) => setJourneyForm({ ...journeyForm, applies_to: event.target.value })}
                    >
                      <option value="all_products">All products</option>
                      <option value="selected_products">Selected products</option>
                    </select>
                  </label>
                  <label>
                    Selected Products
                    <input
                      value={journeyForm.selected_products}
                      onChange={(event) => setJourneyForm({ ...journeyForm, selected_products: event.target.value })}
                      placeholder="black_pepper, cardamom"
                    />
                  </label>
                  <label>
                    Trigger
                    <select
                      value={journeyForm.trigger_type}
                      onChange={(event) => setJourneyForm({ ...journeyForm, trigger_type: event.target.value })}
                    >
                      {JOURNEY_TRIGGER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="toggle-row">
                  {[
                    ['stop_on_reply', 'Stop when customer replies'],
                    ['stop_on_order', 'Stop after order'],
                    ['stop_on_not_interested', 'Stop on not interested'],
                    ['stop_on_stop', 'Stop on stop/cancel'],
                  ].map(([key, label]) => (
                    <label key={key} className="toggle-pill">
                      <input
                        type="checkbox"
                        checked={Boolean(journeyForm[key])}
                        onChange={(event) => setJourneyForm({ ...journeyForm, [key]: event.target.checked })}
                      />
                      {label}
                    </label>
                  ))}
                </div>
                <div className="variant-editor">
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">Steps</p>
                      <h2>Follow-up timing and copy</h2>
                    </div>
                    <button type="button" className="ghost-button" onClick={addJourneyStep}>
                      Add Step
                    </button>
                  </div>
                  {journeyForm.steps.map((step, index) => (
                    <div key={`journey-step-${index}`} className="variant-row variant-row--wide">
                      <input
                        type="number"
                        value={step.delay_value}
                        onChange={(event) => updateJourneyStep(index, 'delay_value', event.target.value)}
                        placeholder="Delay"
                      />
                      <select
                        value={step.delay_unit}
                        onChange={(event) => updateJourneyStep(index, 'delay_unit', event.target.value)}
                      >
                        <option value="minutes">Minutes</option>
                        <option value="hours">Hours</option>
                        <option value="days">Days</option>
                      </select>
                      <select
                        value={step.message_type}
                        onChange={(event) => updateJourneyStep(index, 'message_type', event.target.value)}
                      >
                        {JOURNEY_MESSAGE_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <label className="toggle-pill">
                        <input
                          type="checkbox"
                          checked={Boolean(step.active)}
                          onChange={(event) => updateJourneyStep(index, 'active', event.target.checked)}
                        />
                        Active
                      </label>
                      <button type="button" className="ghost-button" onClick={() => removeJourneyStep(index)}>
                        Remove
                      </button>
                      <textarea
                        rows="2"
                        value={step.message_text}
                        onChange={(event) => updateJourneyStep(index, 'message_text', event.target.value)}
                        placeholder="Follow-up message text"
                      />
                    </div>
                  ))}
                </div>
                <div className="toolbar">
                  <button type="submit">{editingJourneyId ? 'Update Journey' : 'Save Journey'}</button>
                  <button type="button" className="ghost-button" onClick={resetJourneyForm}>
                    Clear
                  </button>
                </div>
              </form>
            </article>
          </div>
        </section>
      ) : null}

      {selectedTimeline ? (
        <aside className="timeline-drawer">
          <div className="timeline-drawer__header">
            <div>
              <p className="eyebrow">Customer Journey</p>
              <h2>{selectedTimeline.customer?.name || selectedTimeline.customer?.phone || 'Customer'}</h2>
              <p>{selectedTimeline.customer?.phone || ''}</p>
            </div>
            <button type="button" className="ghost-button" onClick={() => setSelectedTimeline(null)}>
              Close
            </button>
          </div>
          {selectedTimeline.current_state ? (
            <article className="timeline-row">
              <small>Current state</small>
              <strong>
                {(selectedTimeline.current_state.owner || 'ai').replaceAll('_', ' ')}
                {selectedTimeline.current_state.flow_id ? ` • ${selectedTimeline.current_state.flow_id}` : ''}
              </strong>
              <p>
                {selectedTimeline.current_state.owner_reason || 'No owner reason'}
                {selectedTimeline.current_state.flow_step ? ` • ${selectedTimeline.current_state.flow_step}` : ''}
              </p>
              {selectedTimeline.current_state.last_activity ? (
                <span className="label-chip label-chip--neutral">Last activity {formatDateTime(selectedTimeline.current_state.last_activity)}</span>
              ) : null}
              {selectedTimeline.current_state.latent_handoff?.product_key ? (
                <span className="label-chip label-chip--neutral">
                  Pending handoff: {selectedTimeline.current_state.latent_handoff.product_key}
                </span>
              ) : null}
            </article>
          ) : null}
          {(selectedTimeline.queued_followups || []).length ? (
            <article className="timeline-row">
              <small>Queued follow-ups</small>
              <strong>{selectedTimeline.queued_followups.length} pending</strong>
              <p>
                {selectedTimeline.queued_followups
                  .slice(0, 3)
                  .map((item) => `${item.followup_stage} • ${formatDateTime(item.scheduled_at)}`)
                  .join(' | ')}
              </p>
            </article>
          ) : null}
          <div className="timeline-stack">
            {(selectedTimeline.timeline || []).map((item, index) => (
              <article key={`${item.at}-${index}`} className="timeline-row">
                <small>{formatDateTime(item.at)}</small>
                <strong>{item.type.replaceAll('_', ' ')}</strong>
                <p>{item.text}</p>
                {item.status ? <span className="label-chip label-chip--neutral">{item.status}</span> : null}
              </article>
            ))}
          </div>
        </aside>
      ) : null}
    </div>
  );
}
