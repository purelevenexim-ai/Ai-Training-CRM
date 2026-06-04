/**
 * WhatsApp Panel — Template messaging via Wabis + Meta WhatsApp Cloud
 * Templates auto-sync every 30 min from /api/crm/whatsapp/templates
 * Variables extracted from template_json ({{1}}, {{2}} format)
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';

const API_BASE = 'https://track.pureleven.com/api';
const SYNC_INTERVAL = 30 * 60 * 1000;

function countdownStr(nextSyncAt) {
  const diff = Math.max(0, nextSyncAt - Date.now());
  const m = Math.floor(diff / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function highlightVars(text) {
  if (!text) return null;
  const parts = text.split(/(\{\{\d+\}\})/g);
  return parts.map((p, i) =>
    /^\{\{\d+\}\}$/.test(p)
      ? <mark key={i} style={{ background: '#fef9c3', borderRadius: '3px', padding: '0 2px', fontWeight: 700, color: '#854d0e' }}>{p}</mark>
      : p
  );
}

export default function WhatsAppPanel() {
  const [channel, setChannel]             = useState('meta');
  const [phone, setPhone]                 = useState('919447744583');
  const [wabisTemplates, setWabisTemplates] = useState([]);
  const [metaTemplates, setMetaTemplates]  = useState([]);
  const [metaConfigured, setMetaConfigured] = useState(false);
  const [syncing, setSyncing]             = useState(false);
  const [syncError, setSyncError]         = useState(null);
  const [lastSynced, setLastSynced]       = useState(null);
  const [nextSyncAt, setNextSyncAt]       = useState(null);
  const [countdown, setCountdown]         = useState('');
  const [selectedId, setSelectedId]       = useState(null);
  const [params, setParams]               = useState([]);
  const [sending, setSending]             = useState(false);
  const [result, setResult]               = useState(null);
  const [log, setLog]                     = useState([]);
  const [tab, setTab]                     = useState('send');
  const [headerImageUrl, setHeaderImageUrl] = useState('');
  const [newTpl, setNewTpl]               = useState({ name: '', category: 'MARKETING', language: 'en_US', body: '', header: '', footer: '' });
  const syncTimerRef = useRef(null);
  const countdownRef = useRef(null);

  const syncTemplates = useCallback(async (showSpinner = true, forceRefresh = false) => {
    if (showSpinner) setSyncing(true);
    setSyncError(null);
    try {
      const url = `${API_BASE}/crm/whatsapp/templates${forceRefresh ? '?refresh=true' : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const wabis = Array.isArray(data.wabis) ? data.wabis : [];
      const meta  = Array.isArray(data.meta)  ? data.meta  : [];
      const preferredChannel = meta.length > 0 ? 'meta' : 'wabis';
      setWabisTemplates(wabis);
      setMetaTemplates(meta);
      setMetaConfigured(!!data.meta_configured);
      setLastSynced(new Date());
      setNextSyncAt(Date.now() + SYNC_INTERVAL);
      if (selectedId == null) {
        const initialTemplates = preferredChannel === 'meta' ? meta : wabis;
        setChannel(preferredChannel);
        if (initialTemplates.length > 0) {
          setSelectedId(initialTemplates[0].id);
          setParams(Array(initialTemplates[0].total_vars || 0).fill(''));
        }
      }
    } catch (e) {
      setSyncError(e.message);
    } finally {
      setSyncing(false);
    }
  }, [selectedId]);

  useEffect(() => {
    syncTemplates();
    syncTimerRef.current = setInterval(() => syncTemplates(false), SYNC_INTERVAL);
    return () => clearInterval(syncTimerRef.current);
  }, []); // eslint-disable-line

  useEffect(() => {
    countdownRef.current = setInterval(() => {
      if (nextSyncAt) setCountdown(countdownStr(nextSyncAt));
    }, 1000);
    return () => clearInterval(countdownRef.current);
  }, [nextSyncAt]);

  const templates = channel === 'wabis' ? wabisTemplates : metaTemplates;
  const activeTpl = templates.find(t => String(t.id) === String(selectedId)) || null;

  const varSlots = useMemo(() => {
    if (!activeTpl) return [];
    const slots = [];
    let idx = 0;
    const addSlots = (comp, compLabel) => {
      if (!comp) return;
      for (let v = 1; v <= (comp.vars || 0); v++) {
        const ex = comp.examples?.[v - 1] || '';
        const label = activeTpl.var_labels?.[String(idx + 1)] || ex || `Param ${idx + 1}`;
        slots.push({ idx, compLabel, varNum: v, placeholder: ex, label });
        idx++;
      }
    };
    addSlots(activeTpl.header, 'Header');
    addSlots(activeTpl.body, 'Body');
    (activeTpl.buttons || []).forEach((btn, bi) => addSlots(btn, `Button ${bi + 1}`));
    return slots;
  }, [activeTpl]);

  useEffect(() => {
    if (!activeTpl) return;
    setParams(p => {
      const size = activeTpl.total_vars || 0;
      if (p.length === size) return p;
      return Array(size).fill('').map((_, i) => p[i] ?? '');
    });
  }, [activeTpl]);

  const selectTemplate = useCallback((id) => {
    setSelectedId(id);
    setResult(null);
    setHeaderImageUrl('');
    const tpl = templates.find(t => String(t.id) === String(id));
    if (tpl) setParams(Array(tpl.total_vars || 0).fill(''));
  }, [templates]);

  const handleChannelSwitch = (ch) => {
    setChannel(ch);
    setSelectedId(null);
    setParams([]);
    setResult(null);
    const list = ch === 'wabis' ? wabisTemplates : metaTemplates;
    if (list.length > 0) {
      setSelectedId(list[0].id);
      setParams(Array(list[0].total_vars || 0).fill(''));
    }
  };

  const handleSend = async () => {
    if (!phone.trim() || !activeTpl) return;
    setSending(true);
    setResult(null);
    try {
      let url, body;
      if (channel === 'wabis') {
        url  = `${API_BASE}/crm/wabis/send`;
        const sendPayload = { phone: phone.replace(/\D/g, ''), template_id: activeTpl.id, template_name: activeTpl.name, params: params.filter(Boolean) };
        if (headerImageUrl.trim()) sendPayload.header_image_url = headerImageUrl.trim();
        body = JSON.stringify(sendPayload);
      } else {
        url  = `${API_BASE}/crm/meta-wa/send`;
        body = JSON.stringify({ phone: phone.replace(/\D/g, ''), template: activeTpl.name, params: params.filter(Boolean), phone_number_id: '', language_code: activeTpl.locale || 'en_US' });
      }
      const res  = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
      const json = await res.json().catch(() => ({ detail: res.statusText }));
      setResult({ ok: res.ok, data: json, channel, name: activeTpl.name });
      setLog(prev => [{ id: Date.now(), channel, phone: phone.replace(/\D/g, ''), template: activeTpl.name, params: [...params], ok: res.ok, ts: new Date().toLocaleTimeString(), response: json }, ...prev.slice(0, 49)]);
    } catch (e) {
      setResult({ ok: false, data: { detail: e.message }, channel, name: activeTpl?.name });
    } finally {
      setSending(false);
    }
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: '980px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: '0 0 4px', fontSize: '22px', fontWeight: 700, color: '#1f2937' }}>WhatsApp Messaging</h2>
          <p style={{ margin: 0, fontSize: '13px', color: '#6b7280' }}>Templates auto-sync from Wabis &amp; Meta WhatsApp Cloud every 30 minutes.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {lastSynced && <span style={{ fontSize: '11px', color: '#9ca3af' }}>Synced {lastSynced.toLocaleTimeString()} · next {countdown}</span>}
          <button onClick={() => syncTemplates(true, true)} disabled={syncing} title="Force refresh and clear cache" style={{ padding: '7px 14px', borderRadius: '6px', border: '1px solid #d1d5db', background: syncing ? '#f9fafb' : 'white', cursor: syncing ? 'default' : 'pointer', fontSize: '12px', fontWeight: 600, color: '#374151' }}>
            {syncing ? 'Syncing…' : '⟳ Sync Now'}
          </button>
        </div>
      </div>

      {syncError && <div style={{ marginBottom: '16px', padding: '10px 14px', background: '#fef2f2', borderRadius: '6px', border: '1px solid #fecaca', fontSize: '13px', color: '#dc2626' }}>Sync error: {syncError}</div>}

      {/* Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: '2px solid #e5e7eb', marginBottom: '24px', gap: '20px' }}>
        <div style={{ display: 'flex', gap: '4px' }}>
          {[['send', '📤 Send Message'], ['create', '✏️ New Template']].map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)} style={{ padding: '10px 20px', border: 'none', background: 'none', cursor: 'pointer', fontSize: '14px', fontWeight: 700, color: tab === t ? '#10b981' : '#6b7280', borderBottom: tab === t ? '2px solid #10b981' : '2px solid transparent', marginBottom: '-2px' }}>{label}</button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', paddingBottom: '10px', display: 'flex', gap: '16px', alignItems: 'center' }}>
          {wabisTemplates.length > 0 && <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 500 }}>Wabis: {wabisTemplates.length} templates</span>}
          {metaTemplates.length > 0 && <span style={{ fontSize: '11px', color: '#3b82f6', fontWeight: 500 }}>Meta: {metaTemplates.length} templates</span>}
        </div>
      </div>

      {tab === 'send' && (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px', alignItems: 'start' }}>
          {/* Left: Template Browser */}
          <div>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              {[
                { id: 'wabis', label: 'Wabis', sub: `${wabisTemplates.length} templates`, color: '#10b981' },
                { id: 'meta',  label: 'Meta WA', sub: metaConfigured ? `${metaTemplates.length} templates` : 'Not configured', color: '#3b82f6' },
              ].map(ch => (
                <button key={ch.id} onClick={() => handleChannelSwitch(ch.id)} style={{ flex: 1, padding: '10px 12px', borderRadius: '8px', cursor: 'pointer', textAlign: 'left', border: channel === ch.id ? `2px solid ${ch.color}` : '2px solid #e5e7eb', background: channel === ch.id ? ch.color + '0f' : 'white' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: channel === ch.id ? ch.color : '#374151' }}>{ch.label}</div>
                  <div style={{ fontSize: '11px', color: '#9ca3af' }}>{ch.sub}</div>
                </button>
              ))}
            </div>

            {channel === 'meta' && !metaConfigured && (
              <div style={{ padding: '12px 14px', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', marginBottom: '12px', fontSize: '12px', color: '#1e40af', lineHeight: 1.6 }}>
                <strong>Meta WA not configured.</strong><br />
                Set on VPS:<br />
                <code style={{ background: '#dbeafe', padding: '1px 4px', borderRadius: '3px' }}>META_WABA_ID</code> — WhatsApp Business Account ID<br />
                <code style={{ background: '#dbeafe', padding: '1px 4px', borderRadius: '3px' }}>META_WA_TOKEN</code> — System User token with <code>whatsapp_business_management</code> scope
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '540px', overflowY: 'auto', paddingRight: '2px' }}>
              {syncing && templates.length === 0
                ? <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af', fontSize: '13px' }}>Loading templates…</div>
                : templates.length === 0
                  ? <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af', fontSize: '13px' }}>No templates found</div>
                  : (
                    <>
                      {/* Status summary bar */}
                      {channel === 'wabis' && (() => {
                        const ready = templates.filter(t => !t.send_issue).length;
                        const needsImg = templates.filter(t => t.send_issue === 'image_header').length;
                        const locale = templates.filter(t => t.send_issue === 'locale_mismatch').length;
                        return (
                          <div style={{ display: 'flex', gap: '6px', marginBottom: '4px', flexWrap: 'wrap' }}>
                            {ready > 0 && <span style={{ fontSize: '10px', fontWeight: 700, color: '#166534', background: '#f0fdf4', padding: '3px 8px', borderRadius: '10px', border: '1px solid #bbf7d0' }}>✓ {ready} ready</span>}
                            {needsImg > 0 && <span style={{ fontSize: '10px', fontWeight: 700, color: '#92400e', background: '#fff7ed', padding: '3px 8px', borderRadius: '10px', border: '1px solid #fed7aa' }}>⚠ {needsImg} need image</span>}
                            {locale > 0 && <span style={{ fontSize: '10px', fontWeight: 700, color: '#7c3aed', background: '#fdf4ff', padding: '3px 8px', borderRadius: '10px', border: '1px solid #e9d5ff' }}>✗ {locale} locale error</span>}
                          </div>
                        );
                      })()}
                    {templates.map(tpl => (
                    <div key={tpl.id} onClick={() => selectTemplate(tpl.id)} style={{ padding: '11px 13px', background: 'white', borderRadius: '8px', cursor: 'pointer', border: String(tpl.id) === String(selectedId) ? '2px solid #10b981' : tpl.send_issue ? '1px solid #fde68a' : '1px solid #e5e7eb', boxShadow: String(tpl.id) === String(selectedId) ? '0 0 0 3px rgba(16,185,129,0.1)' : '0 1px 2px rgba(0,0,0,0.04)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '5px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: String(tpl.id) === String(selectedId) ? '#059669' : '#1f2937', wordBreak: 'break-all', lineHeight: 1.3 }}>{tpl.name}</div>
                        <span style={{ padding: '1px 6px', borderRadius: '10px', fontSize: '9px', fontWeight: 700, background: (tpl.category||'').includes('tilit') ? '#eff6ff' : '#fdf4ff', border: `1px solid ${(tpl.category||'').includes('tilit') ? '#bfdbfe' : '#e9d5ff'}`, color: (tpl.category||'').includes('tilit') ? '#1e40af' : '#7c3aed', whiteSpace: 'nowrap', marginLeft: '6px', flexShrink: 0 }}>
                          {tpl.category}
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#6b7280', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {tpl.body?.meta_text || tpl.body?.text || ''}
                      </div>
                      <div style={{ display: 'flex', gap: '5px', marginTop: '5px', flexWrap: 'wrap', alignItems: 'center' }}>
                        {!tpl.send_issue && <span style={{ fontSize: '10px', color: '#166534', background: '#f0fdf4', padding: '1px 5px', borderRadius: '8px', fontWeight: 700 }}>✓ Ready</span>}
                        {tpl.send_issue === 'image_header' && <span style={{ fontSize: '10px', color: '#92400e', background: '#fff7ed', padding: '1px 5px', borderRadius: '8px', fontWeight: 700, border: '1px solid #fed7aa' }}>⚠ Needs image</span>}
                        {tpl.send_issue === 'locale_mismatch' && <span style={{ fontSize: '10px', color: '#7c3aed', background: '#fdf4ff', padding: '1px 5px', borderRadius: '8px', fontWeight: 700, border: '1px solid #e9d5ff' }}>✗ Locale issue</span>}
                        {tpl.total_vars > 0 && <span style={{ fontSize: '10px', color: '#92400e', background: '#fef9c3', padding: '1px 5px', borderRadius: '8px', fontWeight: 600 }}>{tpl.total_vars} var{tpl.total_vars !== 1 ? 's' : ''}</span>}
                        {tpl.buttons?.length > 0 && <span style={{ fontSize: '10px', color: '#1e40af', background: '#eff6ff', padding: '1px 5px', borderRadius: '8px', fontWeight: 600 }}>{tpl.buttons.length} btn{tpl.buttons.length !== 1 ? 's' : ''}</span>}
                        {tpl.header_format && tpl.header_format !== 'none' && tpl.header_format !== 'text' && <span style={{ fontSize: '10px', color: '#374151', background: '#f3f4f6', padding: '1px 5px', borderRadius: '8px', fontWeight: 600 }}>{tpl.header_format.toUpperCase()}</span>}
                        <span style={{ fontSize: '10px', color: '#9ca3af', marginLeft: 'auto' }}>{tpl.locale}</span>
                      </div>
                    </div>
                  ))}
                  </>
                  )
              }
            </div>
          </div>

          {/* Right: Compose */}
          {activeTpl ? (
            <div style={{ background: 'white', borderRadius: '10px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)', padding: '24px' }}>
              {/* Preview bubble */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Template Preview</span>
                  <span style={{ fontSize: '11px', color: '#9ca3af' }}>{activeTpl.locale} · {activeTpl.category}</span>
                </div>
                <div style={{ background: '#e5ddd5', borderRadius: '10px', padding: '12px' }}>
                  <div style={{ background: '#dcf8c6', borderRadius: '8px 8px 8px 0', padding: '12px 14px', maxWidth: '380px', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
                    {activeTpl.header?.text && (
                      <div style={{ fontWeight: 700, fontSize: '13px', color: '#1f2937', marginBottom: '6px', lineHeight: 1.4 }}>
                        {activeTpl.header.format === 'TEXT' ? highlightVars(activeTpl.header.text) : `[${activeTpl.header.format}]`}
                      </div>
                    )}
                    <div style={{ fontSize: '13px', color: '#1f2937', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{highlightVars(activeTpl.body?.meta_text || activeTpl.body?.text || '')}</div>
                    {activeTpl.footer?.text && <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '6px' }}>{activeTpl.footer.text}</div>}
                    {activeTpl.buttons?.length > 0 && (
                      <div style={{ marginTop: '10px', borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {activeTpl.buttons.map((btn, i) => (
                          <div key={i} style={{ fontSize: '12px', fontWeight: 600, color: '#059669', padding: '4px 10px', borderRadius: '14px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(5,150,105,0.3)' }}>{btn.text}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <hr style={{ margin: '0 0 20px', border: 'none', borderTop: '1px solid #f3f4f6' }} />

              {/* Phone */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Recipient Phone <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '11px' }}>— E.164, no + or spaces</span></label>
                <input type="text" value={phone} onChange={e => setPhone(e.target.value)} placeholder="919447744583" style={inputStyle} />
              </div>

              {/* Variable inputs */}
              {varSlots.length > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '8px' }}>Variables ({varSlots.length}) <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '11px' }}>— values injected into <mark style={{ background: '#fef9c3', borderRadius: '3px', padding: '0 3px', fontWeight: 700, color: '#854d0e' }}>&#123;&#123;n&#125;&#125;</mark> placeholders</span></label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {varSlots.map(slot => (
                      <div key={slot.idx} style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '8px', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: '#374151' }}>{slot.compLabel} {'{{'}{slot.varNum}{'}}'}</div>
                          <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '1px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{slot.label}</div>
                        </div>
                        <input type="text" value={params[slot.idx] ?? ''} onChange={e => { const u = [...params]; u[slot.idx] = e.target.value; setParams(u); }} placeholder={slot.placeholder || slot.label} style={inputStyle} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {varSlots.length === 0 && !activeTpl?.send_issue && (
                <div style={{ padding: '10px 14px', background: '#f0fdf4', borderRadius: '6px', fontSize: '12px', color: '#166534', marginBottom: '16px' }}>No variables required — sends as-is.</div>
              )}

              {/* Image URL input for IMAGE-header templates */}
              {activeTpl?.send_issue === 'image_header' && (
                <div style={{ marginBottom: '16px', padding: '14px', background: '#fff7ed', borderRadius: '8px', border: '1px solid #fed7aa' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#92400e', marginBottom: '8px' }}>⚠ Image header — provide an image URL</div>
                  <div style={{ fontSize: '11px', color: '#a16207', marginBottom: '8px', lineHeight: 1.5 }}>
                    This template has an image header. Paste a public image URL below to send it.
                    The template in Wabis has no default image stored.
                  </div>
                  <input
                    type="url"
                    value={headerImageUrl}
                    onChange={e => setHeaderImageUrl(e.target.value)}
                    placeholder="https://pureleven.com/cdn/shop/files/product-banner.jpg"
                    style={inputStyle}
                  />
                  {!headerImageUrl.trim() && (
                    <div style={{ fontSize: '11px', color: '#dc2626', marginTop: '4px' }}>Image URL required to send this template.</div>
                  )}
                </div>
              )}

              {/* Locale mismatch warning */}
              {activeTpl?.send_issue === 'locale_mismatch' && (
                <div style={{ marginBottom: '16px', padding: '14px', background: '#fdf4ff', borderRadius: '8px', border: '1px solid #e9d5ff' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#7c3aed', marginBottom: '6px' }}>✗ Locale mismatch — cannot send</div>
                  <div style={{ fontSize: '11px', color: '#6d28d9', lineHeight: 1.5 }}>
                    Template body appears to be Malayalam but is registered in Wabis as <strong>en_US</strong>.
                    Meta will reject the send request.<br /><br />
                    <strong>Fix options:</strong><br />
                    1. In Wabis dashboard → Templates → edit this template → change locale to <code style={{ background: '#ede9fe', padding: '1px 4px', borderRadius: '3px' }}>ml</code><br />
                    2. Or recreate the template in Meta with the correct language selected.
                  </div>
                </div>
              )}

              <button
                onClick={handleSend}
                disabled={sending || !phone.trim() || activeTpl?.send_issue === 'locale_mismatch' || (activeTpl?.send_issue === 'image_header' && !headerImageUrl.trim())}
                style={{ padding: '12px 32px', borderRadius: '8px', border: 'none', cursor: (sending || !phone.trim() || activeTpl?.send_issue === 'locale_mismatch' || (activeTpl?.send_issue === 'image_header' && !headerImageUrl.trim())) ? 'not-allowed' : 'pointer', background: (sending || !phone.trim() || activeTpl?.send_issue === 'locale_mismatch' || (activeTpl?.send_issue === 'image_header' && !headerImageUrl.trim())) ? '#9ca3af' : channel === 'wabis' ? '#10b981' : '#3b82f6', color: 'white', fontSize: '15px', fontWeight: 700, width: '100%', marginTop: '4px' }}>
                {sending ? 'Sending…' : channel === 'wabis' ? '📤 Send via Wabis' : '📤 Send via Meta WA'}
              </button>

              {result && (
                <div style={{ marginTop: '16px', padding: '14px 16px', borderRadius: '8px', background: result.ok ? '#f0fdf4' : '#fef2f2', border: `1px solid ${result.ok ? '#bbf7d0' : '#fecaca'}` }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: result.ok ? '#166534' : '#991b1b', marginBottom: '6px' }}>
                    {result.ok ? `✓ Sent "${result.name}"` : `✗ Failed`} via {result.channel === 'wabis' ? 'Wabis' : 'Meta WA'}
                  </div>
                  <pre style={{ margin: 0, fontSize: '11px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: '100px', overflowY: 'auto', color: result.ok ? '#14532d' : '#7f1d1d' }}>{JSON.stringify(result.data, null, 2)}</pre>
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: '#9ca3af', fontSize: '14px', background: 'white', borderRadius: '10px', border: '1px dashed #e5e7eb' }}>← Select a template to compose</div>
          )}
        </div>
      )}

      {tab === 'create' && (
        <CreateTemplatePane newTpl={newTpl} onChange={setNewTpl} />
      )}

      {/* Send Log */}
      {log.length > 0 && (
        <div style={{ marginTop: '28px', background: 'white', borderRadius: '10px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
          <div style={{ padding: '12px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#1f2937' }}>Send History ({log.length})</span>
            <button onClick={() => setLog([])} style={{ padding: '5px 12px', border: '1px solid #d1d5db', borderRadius: '6px', background: '#f9fafb', cursor: 'pointer', fontSize: '11px', fontWeight: 600, color: '#374151' }}>Clear</button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  {['Time', 'Channel', 'Phone', 'Template', 'Params', 'Status'].map(h => (
                    <th key={h} style={{ padding: '8px 14px', textAlign: 'left', fontSize: '10px', fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid #e5e7eb' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {log.map(e => (
                  <tr key={e.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 14px', color: '#9ca3af' }}>{e.ts}</td>
                    <td style={{ padding: '8px 14px' }}><span style={{ padding: '2px 7px', borderRadius: '10px', fontSize: '10px', fontWeight: 700, background: e.channel === 'wabis' ? '#f0fdf4' : '#eff6ff', color: e.channel === 'wabis' ? '#166534' : '#1e40af' }}>{e.channel === 'wabis' ? 'Wabis' : 'Meta WA'}</span></td>
                    <td style={{ padding: '8px 14px', fontFamily: 'monospace', color: '#374151' }}>+{e.phone}</td>
                    <td style={{ padding: '8px 14px', color: '#374151', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.template}</td>
                    <td style={{ padding: '8px 14px', color: '#6b7280', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.params.filter(Boolean).join(', ') || '—'}</td>
                    <td style={{ padding: '8px 14px' }}><span style={{ padding: '2px 7px', borderRadius: '10px', fontSize: '10px', fontWeight: 700, background: e.ok ? '#f0fdf4' : '#fef2f2', color: e.ok ? '#166534' : '#991b1b' }}>{e.ok ? 'Sent ✓' : 'Failed ✗'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function CreateTemplatePane({ newTpl, onChange }) {
  const varCount = (newTpl.body.match(/\{\{\d+\}\}/g) || []).length;
  const [creating, setCreating] = React.useState(false);
  const [createMsg, setCreateMsg] = React.useState(null);
  
  const handleSaveTemplate = async () => {
    if (!newTpl.name.trim() || !newTpl.body.trim()) {
      setCreateMsg({ ok: false, text: 'Template name and body are required' });
      return;
    }
    
    setCreating(true);
    setCreateMsg(null);
    try {
      const res = await fetch('https://track.pureleven.com/api/crm/whatsapp/create-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTpl)
      });
      const data = await res.json();
      if (res.ok) {
        setCreateMsg({ ok: true, text: `✓ Saved locally as "${newTpl.name}". Now submit to Meta for approval via Meta WhatsApp Manager.` });
        onChange({ name: '', category: 'MARKETING', language: 'en_US', body: '', header: '', footer: '' });
      } else {
        setCreateMsg({ ok: false, text: data.detail || 'Failed to save template' });
      }
    } catch (e) {
      setCreateMsg({ ok: false, text: e.message });
    } finally {
      setCreating(false);
    }
  };
  
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px', alignItems: 'start' }}>
      <div style={{ background: 'white', borderRadius: '10px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)', padding: '24px' }}>
        <h3 style={{ margin: '0 0 20px', fontSize: '15px', fontWeight: 700, color: '#374151' }}>New WhatsApp Template</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div style={{ marginBottom: '0' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Template Name <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '11px' }}>— lowercase_underscore</span></label>
            <input value={newTpl.name} onChange={e => onChange({ ...newTpl, name: e.target.value.toLowerCase().replace(/\s/g, '_') })} placeholder="e.g. order_confirmation" style={inputStyle} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Category</label>
            <select value={newTpl.category} onChange={e => onChange({ ...newTpl, category: e.target.value })} style={inputStyle}>
              <option value="MARKETING">Marketing</option>
              <option value="UTILITY">Utility</option>
              <option value="AUTHENTICATION">Authentication</option>
            </select>
          </div>
        </div>
        <div style={{ marginTop: '16px' }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Language</label>
          <select value={newTpl.language} onChange={e => onChange({ ...newTpl, language: e.target.value })} style={{ ...inputStyle, width: '200px' }}>
            <option value="en_US">English (US)</option>
            <option value="en_GB">English (UK)</option>
            <option value="hi">Hindi</option>
            <option value="ml">Malayalam</option>
          </select>
        </div>
        <div style={{ marginTop: '16px' }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Header <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '11px' }}>— optional, ≤60 chars</span></label>
          <input value={newTpl.header} onChange={e => onChange({ ...newTpl, header: e.target.value })} maxLength={60} placeholder="Optional header text" style={inputStyle} />
        </div>
        <div style={{ marginTop: '16px' }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Body <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '11px' }}>— use {'{{1}}'}, {'{{2}}'} for variables</span></label>
          <textarea value={newTpl.body} onChange={e => onChange({ ...newTpl, body: e.target.value })} placeholder={"Hello {{1}},\n\nYour order {{2}} has been placed.\n\nThank you!"} rows={6} style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.6 }} />
          {varCount > 0 && <div style={{ fontSize: '11px', color: '#92400e', marginTop: '4px' }}>{varCount} variable{varCount !== 1 ? 's' : ''}: {Array.from({ length: varCount }, (_, i) => `{{${i+1}}}`).join(', ')}</div>}
        </div>
        <div style={{ marginTop: '16px' }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Footer <span style={{ fontWeight: 400, color: '#9ca3af', fontSize: '11px' }}>— optional, ≤60 chars, no variables</span></label>
          <input value={newTpl.footer} onChange={e => onChange({ ...newTpl, footer: e.target.value })} maxLength={60} placeholder="Optional footer" style={inputStyle} />
        </div>
        <div style={{ marginTop: '20px', padding: '12px 14px', background: '#fffbeb', borderRadius: '6px', border: '1px solid #fde68a', fontSize: '12px', color: '#92400e', lineHeight: 1.7 }}>
          <strong>Approval flow:</strong> Save template locally → verify → submit to Meta WhatsApp Manager for review (~24h) → once approved, click Sync Now to fetch it.
        </div>
        
        {createMsg && <div style={{ marginTop: '16px', padding: '10px 12px', background: createMsg.ok ? '#f0fdf4' : '#fef2f2', borderRadius: '6px', border: `1px solid ${createMsg.ok ? '#86efac' : '#fecaca'}`, fontSize: '12px', color: createMsg.ok ? '#166534' : '#dc2626' }}>{createMsg.text}</div>}
        
        <div style={{ marginTop: '14px', display: 'flex', gap: '10px' }}>
          <button onClick={handleSaveTemplate} disabled={creating || !newTpl.name.trim() || !newTpl.body.trim()} style={{ padding: '10px 20px', borderRadius: '7px', background: '#10b981', color: 'white', border: 'none', fontSize: '13px', fontWeight: 700, cursor: (creating || !newTpl.name.trim() || !newTpl.body.trim()) ? 'default' : 'pointer', opacity: (creating || !newTpl.name.trim() || !newTpl.body.trim()) ? 0.6 : 1 }}>
            {creating ? 'Saving…' : '✓ Save Template'}
          </button>
          <a href="https://business.facebook.com/wa/manage/message-templates/" target="_blank" rel="noopener noreferrer" style={{ padding: '10px 20px', borderRadius: '7px', background: '#1877f2', color: 'white', textDecoration: 'none', fontSize: '13px', fontWeight: 700, display: 'inline-block' }}>Open Meta WhatsApp Manager ↗</a>
        </div>
      </div>

      {/* Live preview */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>Live Preview</div>
        <div style={{ background: '#e5ddd5', borderRadius: '12px', padding: '16px', minHeight: '200px' }}>
          {(newTpl.header || newTpl.body || newTpl.footer) ? (
            <div style={{ background: '#dcf8c6', borderRadius: '8px 8px 8px 0', padding: '12px 14px', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
              {newTpl.header && <div style={{ fontWeight: 700, fontSize: '13px', color: '#1f2937', marginBottom: '6px' }}>{highlightVars(newTpl.header)}</div>}
              <div style={{ fontSize: '13px', color: '#1f2937', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{newTpl.body ? highlightVars(newTpl.body) : <span style={{ color: '#9ca3af' }}>Body text…</span>}</div>
              {newTpl.footer && <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '6px' }}>{newTpl.footer}</div>}
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#9ca3af', paddingTop: '40px', fontSize: '13px' }}>Fill in the form to preview</div>
          )}
        </div>
        {newTpl.name && (
          <div style={{ marginTop: '10px', fontSize: '11px', color: '#6b7280', fontFamily: 'monospace', lineHeight: 1.8 }}>
            name: {newTpl.name}<br/>
            category: {newTpl.category}<br/>
            language: {newTpl.language}
          </div>
        )}
      </div>
    </div>
  );
}

const inputStyle = {
  padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: '6px',
  fontSize: '13px', width: '100%', fontFamily: 'inherit', boxSizing: 'border-box',
  outline: 'none', color: '#1f2937', background: 'white',
};
