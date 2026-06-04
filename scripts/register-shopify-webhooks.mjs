/**
 * Register all required Shopify webhooks for Pure Leven CRM
 * Run: node scripts/register-shopify-webhooks.mjs
 */
import { spawnSync } from 'node:child_process';

const STORE = 'rwxtic-gz.myshopify.com';
const WEBHOOK_BASE_URL = 'https://track.pureleven.com/api/crm/webhooks/shopify';

function executeStore({ query, variables, allowMutations = false }) {
  const args = ['store', 'execute', '--store', STORE, '--json', '--query', query];
  if (allowMutations) args.push('--allow-mutations');
  if (variables) args.push('--variables', JSON.stringify(variables));

  const result = spawnSync('shopify', args, {
    cwd: process.cwd(),
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || 'Shopify CLI command failed');
  }

  return JSON.parse(result.stdout);
}

// Fetch existing webhooks to avoid duplicates
async function getExistingWebhooks() {
  const result = executeStore({
    query: `{
      webhookSubscriptions(first: 50) {
        edges {
          node {
            id
            topic
            endpoint {
              __typename
              ... on WebhookHttpEndpoint {
                callbackUrl
              }
            }
          }
        }
      }
    }`
  });
  return result.webhookSubscriptions?.edges?.map(e => e.node) || [];
}

// Delete a webhook by ID
function deleteWebhook(id) {
  const result = executeStore({
    allowMutations: true,
    query: `mutation webhookSubscriptionDelete($id: ID!) {
      webhookSubscriptionDelete(id: $id) {
        deletedWebhookSubscriptionId
        userErrors { field message }
      }
    }`,
    variables: { id }
  });
  const errors = result.webhookSubscriptionDelete?.userErrors;
  if (errors?.length) throw new Error(JSON.stringify(errors));
  return result.webhookSubscriptionDelete?.deletedWebhookSubscriptionId;
}

// Create a webhook subscription
function createWebhook(topic) {
  const result = executeStore({
    allowMutations: true,
    query: `mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
      webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
        webhookSubscription {
          id
          topic
          endpoint {
            __typename
            ... on WebhookHttpEndpoint {
              callbackUrl
            }
          }
        }
        userErrors { field message }
      }
    }`,
    variables: {
      topic,
      webhookSubscription: {
        callbackUrl: WEBHOOK_BASE_URL,
        format: 'JSON',
      }
    }
  });

  const errors = result.webhookSubscriptionCreate?.userErrors;
  if (errors?.length) throw new Error(JSON.stringify(errors));
  return result.webhookSubscriptionCreate?.webhookSubscription;
}

// Topics required for CRM to work
const REQUIRED_TOPICS = [
  'CUSTOMERS_CREATE',
  'CUSTOMERS_UPDATE',
  'ORDERS_CREATE',
  'ORDERS_PAID',
  'ORDERS_FULFILLED',
  'ORDERS_CANCELLED',
  'CHECKOUTS_CREATE',
];

async function main() {
  console.log(`\n📡 Registering Shopify webhooks → ${WEBHOOK_BASE_URL}\n`);

  // Step 1: Get existing webhooks
  console.log('🔍 Fetching existing webhooks...');
  const existing = await getExistingWebhooks();
  console.log(`   Found ${existing.length} existing webhook(s)`);

  // Step 2: Remove any old webhooks pointing to our CRM endpoint (clean slate)
  const stale = existing.filter(w =>
    w.endpoint?.callbackUrl === WEBHOOK_BASE_URL
  );
  if (stale.length > 0) {
    console.log(`\n🗑️  Removing ${stale.length} stale webhook(s) pointing to ${WEBHOOK_BASE_URL}...`);
    for (const w of stale) {
      deleteWebhook(w.id);
      console.log(`   ✓ Deleted: ${w.topic}`);
    }
  }

  // Step 3: Register all required topics
  console.log(`\n✅ Registering ${REQUIRED_TOPICS.length} webhook subscriptions...`);
  const results = [];
  for (const topic of REQUIRED_TOPICS) {
    try {
      const created = createWebhook(topic);
      console.log(`   ✓ ${topic} → ${created.endpoint?.callbackUrl}`);
      results.push({ topic, status: 'created', id: created.id });
    } catch (err) {
      console.error(`   ✗ ${topic}: ${err.message}`);
      results.push({ topic, status: 'error', error: err.message });
    }
  }

  // Summary
  const ok = results.filter(r => r.status === 'created').length;
  const fail = results.filter(r => r.status === 'error').length;
  console.log(`\n📊 Done: ${ok} registered, ${fail} failed`);

  if (fail === 0) {
    console.log('\n🚀 All webhooks active. Shopify will now push:');
    console.log('   customers/create  → CRM creates customer + welcome email + journey enrollment');
    console.log('   customers/update  → CRM updates customer profile');
    console.log('   orders/create     → CRM records order event');
    console.log('   orders/paid       → CRM records payment, triggers post-purchase journey');
    console.log('   orders/fulfilled  → CRM records fulfillment');
    console.log('   orders/cancelled  → CRM records cancellation');
    console.log('   checkouts/create  → CRM records cart abandonment trigger');
  } else {
    process.exit(1);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
