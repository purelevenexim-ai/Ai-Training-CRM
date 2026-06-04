#!/usr/bin/env node
/**
 * wabis_export_node.js
 * Full Wabis chat export using Node.js + Playwright with fs.writeFileSync
 * 
 * Uses existing browser session cookies to authenticate
 * Exports 726+ conversations as per-customer CSV files
 */

const { chromium } = require('playwright');
const fs   = require('fs');
const path = require('path');

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const BASE_URL    = 'https://bot.wabis.in';
const XSRF_TOKEN  = 'FUc5cWYVEvXFRKtHPXM1CmjYTH1N3RTlg96zQgzO';
const PHPSESSID   = 'gvd75cnu5spujqfkh0th38rpca';
const TEAM_MEMBERS = '{"71206":"Admin","168004":"Sunitha"}';
const OUTPUT_DIR  = path.join(__dirname, 'customer_chats');
const DELAY_MS    = 350;

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function safeFilename(name, phone) {
  const clean = (name || 'Unknown').replace(/[^\w\s\-]/g, '').replace(/\s+/g, '_').slice(0, 40);
  return `${clean}_${phone}.csv`;
}

function csvEscape(val) {
  const s = String(val ?? '');
  if (s.includes(',') || s.includes('"') || s.includes('\n') || s.includes('\r')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

async function main() {
  console.log('='.repeat(60));
  console.log('  Wabis Chat Exporter — Per-Customer CSV');
  console.log(`  Output: ${OUTPUT_DIR}`);
  console.log('='.repeat(60));
  
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
  });
  
  // Inject session cookies
  await context.addCookies([
    { name: 'XSRF-TOKEN', value: XSRF_TOKEN, domain: 'bot.wabis.in', path: '/' },
    { name: 'PHPSESSID',  value: PHPSESSID,  domain: 'bot.wabis.in', path: '/' },
  ]);
  
  const page = await context.newPage();
  
  // Navigate to get CSRF meta token
  console.log('\nConnecting to Wabis...');
  await page.goto(`${BASE_URL}/all/livechat`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  
  const metaToken = await page.evaluate(() =>
    document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
  );
  const xsrf = await page.evaluate(() =>
    decodeURIComponent(document.cookie.match(/XSRF-TOKEN=([^;]+)/)?.[1] || '')
  );
  
  console.log(`CSRF token: ${metaToken ? metaToken.slice(0, 20) + '...' : 'MISSING!'}`);
  if (!metaToken) {
    console.error('ERROR: Could not get CSRF token. Session may have expired.');
    await browser.close();
    return;
  }
  
  // ── Step 1: Collect all conversations ──────────────────────────────────────
  console.log('\n[1/2] Fetching conversation list...');
  const allConvs = [];
  let start = 0;
  
  while (true) {
    const convs = await page.evaluate(async ({ token, xsrf, start, teamMembers }) => {
      const body = new URLSearchParams({
        _token: token, whatsapp_bot_id: 'all', telegram_bot_id: 'all',
        message_type: 'all', start: String(start), order_by_id: 'last_interacted_at',
        'channel_list[]': 'all', start_filter_date: '', end_filter_date: '',
        team_member_list: teamMembers
      });
      const resp = await fetch('/all/livechat/conversation/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest',
          'X-XSRF-TOKEN': xsrf
        },
        body: body.toString()
      });
      const html = await resp.text();
      const convs = [];
      const pat = /<li[^>]*open_conversation[^>]*>/g;
      let m;
      while ((m = pat.exec(html)) !== null) {
        const tag = m[0];
        const get = (attr) => { const r = new RegExp(attr + '="([^"]*)"'); return r.exec(tag)?.[1] ?? ''; };
        if (get('thread_id')) convs.push({
          thread_id: get('thread_id'), from_user: get('from_user'),
          from_user_id: get('from_user_id'), omni_bot_id: get('omni_bot_id'),
          omni_bot_name: get('omni_bot_name'), data_id: get('data_id')
        });
      }
      return convs;
    }, { token: metaToken, xsrf, start, teamMembers: TEAM_MEMBERS });
    
    if (!convs.length) break;
    allConvs.push(...convs);
    console.log(`  Page ${Math.floor(start/50) + 1}: ${convs.length} convs (total: ${allConvs.length})`);
    if (convs.length < 50) break;
    start += 50;
    await page.waitForTimeout(DELAY_MS);
  }
  
  console.log(`\n  Total: ${allConvs.length} conversations`);
  
  // ── Step 2: Fetch messages and write CSVs ──────────────────────────────────
  console.log('\n[2/2] Fetching messages and writing CSVs...');
  
  let successCount = 0;
  let errorCount   = 0;
  const summaryRows = [];
  
  for (let i = 0; i < allConvs.length; i++) {
    const conv = allConvs[i];
    const prefix = `  [${String(i+1).padStart(3,'0')}/${allConvs.length}] ${conv.from_user} (${conv.thread_id})`;
    
    try {
      const msgs = await page.evaluate(async ({ token, xsrf, conv, teamMembers }) => {
        const body = new URLSearchParams({
          _token: token, thread_id: conv.thread_id,
          whatsapp_bot_id: conv.omni_bot_id, telegram_bot_id: conv.omni_bot_id,
          from_user_id: conv.from_user_id, last_message_id: '',
          media_type: 'fb', data_key: '', has_unseen: 'true',
          team_member_list: teamMembers
        });
        const resp = await fetch('/whatsapp/livechat/conversation/single', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'X-XSRF-TOKEN': xsrf
          },
          body: body.toString()
        });
        const j = await resp.json();
        const html = j.str || '';
        const msgs = [];
        const pattern = /<div\s+class="(chat-item\s+chat-(?:left|right))[^"]*"/g;
        let m;
        while ((m = pattern.exec(html)) !== null) {
          const direction = m[1].includes('chat-left') ? 'customer' : 'bot_agent';
          const pos = m.index;
          const snippet = html.slice(pos, pos + 3000);
          const msgTypeM = /message_type="([^"]*)"/.exec(snippet);
          const msgIdM   = /message_id="([^"]*)"/.exec(snippet);
          const tsM      = /class="put-time[^"]*"[^>]*>([^<]+)</.exec(snippet);
          const ctM      = /class="chat-text[^"]*"[^>]*>([\s\S]*?)(?=<div\s+(?:id=|class="(?:chat-item|d-flex\s|row[\s"]+|mt-|chat-footer))|$)/.exec(snippet);
          let text = '';
          if (ctM) text = ctM[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 1000);
          msgs.push({
            sender:     direction,
            type:       msgTypeM?.[1] || 'text',
            message_id: msgIdM?.[1]  || '',
            timestamp:  tsM?.[1]?.trim() || '',
            text
          });
        }
        return msgs;
      }, { token: metaToken, xsrf, conv, teamMembers: TEAM_MEMBERS });
      
      // Write CSV file
      const filename = safeFilename(conv.from_user, conv.thread_id);
      const filepath = path.join(OUTPUT_DIR, filename);
      
      let csv = `# Customer: ${conv.from_user}\n# Phone: ${conv.thread_id}\n# Bot: ${conv.omni_bot_name}\n# Exported: ${new Date().toISOString().slice(0,16)}\n`;
      csv += 'timestamp,sender,type,message,message_id\n';
      for (const msg of msgs) {
        csv += [csvEscape(msg.timestamp), csvEscape(msg.sender), csvEscape(msg.type), csvEscape(msg.text), csvEscape(msg.message_id)].join(',') + '\n';
      }
      fs.writeFileSync(filepath, csv, 'utf8');
      
      successCount++;
      summaryRows.push({ customer: conv.from_user, phone: conv.thread_id, messages: msgs.length, file: filename });
      console.log(`${prefix}: ${msgs.length} msgs`);
      
    } catch (e) {
      errorCount++;
      console.log(`${prefix}: ERROR - ${e.message}`);
    }
    
    await page.waitForTimeout(DELAY_MS);
  }
  
  // Write summary
  let summaryCSV = 'customer,phone,messages,file\n';
  for (const row of summaryRows) {
    summaryCSV += [csvEscape(row.customer), csvEscape(row.phone), row.messages, csvEscape(row.file)].join(',') + '\n';
  }
  fs.writeFileSync(path.join(OUTPUT_DIR, 'EXPORT_SUMMARY.csv'), summaryCSV, 'utf8');
  
  await browser.close();
  
  console.log('\n' + '='.repeat(60));
  console.log(`  Export complete!`);
  console.log(`  ✓ Success: ${successCount} files`);
  console.log(`  ✗ Errors:  ${errorCount}`);
  console.log(`  Summary:   ${OUTPUT_DIR}/EXPORT_SUMMARY.csv`);
  console.log('='.repeat(60));
}

main().catch(console.error);
