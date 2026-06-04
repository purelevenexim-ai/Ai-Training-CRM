/* eslint-disable react/prop-types */
import { boundary } from "@shopify/shopify-app-react-router/server";
import { Form, useLoaderData } from "react-router";
import { authenticate } from "../shopify.server";

const SHOPIFY_FORMS_ID = "987882";
const SHOPIFY_FORMS_TAG = `shopify-forms-${SHOPIFY_FORMS_ID}`;
const CUSTOMER_PAGE_SIZE = 25;
const REQUIRED_CUSTOMER_SCOPE = "read_customers";
const LEAD_DATE_FORMATTER = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: true,
  timeZone: "Asia/Kolkata",
});

function getShopHandle(shopDomain = "") {
  return shopDomain.replace(".myshopify.com", "");
}

function parseScopes(scopeValue = "") {
  return String(scopeValue)
    .split(",")
    .map((scope) => scope.trim())
    .filter(Boolean);
}

async function fetchGrantedAccessScopes(admin) {
  const response = await admin.graphql(`#graphql
    query AnuGrantedScopes {
      currentAppInstallation {
        accessScopes {
          handle
        }
      }
    }
  `);

  const payload = await response.json();

  if (payload.errors?.length) {
    throw new Error(payload.errors.map((error) => error.message).join(" "));
  }

  return (payload.data.currentAppInstallation?.accessScopes || [])
    .map((scope) => scope.handle)
    .filter(Boolean);
}

function buildCustomerQuery(search = "") {
  const trimmedSearch = search.trim();

  if (!trimmedSearch) {
    return `tag:${SHOPIFY_FORMS_TAG}`;
  }

  return `tag:${SHOPIFY_FORMS_TAG} ${trimmedSearch}`;
}

function getTodayCustomerQuery() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return `tag:${SHOPIFY_FORMS_TAG} created_at:>=${today.toISOString()}`;
}

async function fetchShopifyFormsCustomers(admin, search) {
  const query = `#graphql
    query AnuFormsCustomers($query: String!, $todayQuery: String!, $first: Int!) {
      customers(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
        edges {
          node {
            id
            displayName
            email
            phone
            createdAt
            tags
            emailMarketingConsent {
              marketingState
            }
            smsMarketingConsent {
              marketingState
            }
          }
        }
      }
      customersCount(query: $query) {
        count
        precision
      }
      todayCustomersCount: customersCount(query: $todayQuery) {
        count
        precision
      }
    }
  `;

  const response = await admin.graphql(query, {
    variables: {
      query: buildCustomerQuery(search),
      todayQuery: getTodayCustomerQuery(),
      first: CUSTOMER_PAGE_SIZE,
    },
  });

  const payload = await response.json();

  if (payload.errors?.length) {
    throw new Error(payload.errors.map((error) => error.message).join(" "));
  }

  return {
    customers: payload.data.customers.edges.map((edge) => edge.node),
    totalCount: payload.data.customersCount.count,
    totalPrecision: payload.data.customersCount.precision,
    todayCount: payload.data.todayCustomersCount.count,
    todayPrecision: payload.data.todayCustomersCount.precision,
  };
}

export const loader = async ({ request }) => {
  const { admin, session } = await authenticate.admin(request);
  const url = new URL(request.url);
  const search = url.searchParams.get("search") || "";
  const shopHandle = getShopHandle(session.shop);
  const appOrigin = process.env.SHOPIFY_APP_URL || url.origin;
  const fallbackScopes = parseScopes(session.scope);

  let installedScopes = fallbackScopes;

  try {
    installedScopes = await fetchGrantedAccessScopes(admin);
  } catch (error) {
    installedScopes = fallbackScopes;
  }

  const hasCustomerReadScope = installedScopes.includes(REQUIRED_CUSTOMER_SCOPE);

  if (!hasCustomerReadScope) {
    return {
      search,
      shopDomain: session.shop,
      shopHandle,
      appOrigin,
      installedScopes,
      hasCustomerReadScope,
      formsCustomers: null,
      formsAccessError: `The current app installation is missing ${REQUIRED_CUSTOMER_SCOPE}.`,
    };
  }

  try {
    const formsCustomers = await fetchShopifyFormsCustomers(admin, search);

    return {
      search,
      shopDomain: session.shop,
      shopHandle,
      appOrigin,
      installedScopes,
      hasCustomerReadScope,
      formsCustomers,
      formsAccessError: null,
    };
  } catch (error) {
    return {
      search,
      shopDomain: session.shop,
      shopHandle,
      appOrigin,
      installedScopes,
      hasCustomerReadScope,
      formsCustomers: null,
      formsAccessError: error instanceof Error ? error.message : "Could not load Shopify customer data.",
    };
  }
};

export default function Index() {
  const { search, shopDomain, shopHandle, appOrigin, installedScopes, hasCustomerReadScope, formsCustomers, formsAccessError } = useLoaderData();
  const customerQuery = buildCustomerQuery(search);
  const customersUrl = `https://admin.shopify.com/store/${shopHandle}/customers?query=${encodeURIComponent(customerQuery)}`;
  const formsUrl = `https://admin.shopify.com/store/${shopHandle}/apps/shopify-forms`;
  const reconnectUrl = `${appOrigin}/auth/login?shop=${encodeURIComponent(shopDomain)}`;
  const customers = formsCustomers?.customers || [];
  const installedScopesLabel = installedScopes.length ? installedScopes.join(", ") : "None recorded yet";

  return (
    <s-page heading="Basil leads">
      <div style={{ display: "grid", gap: "16px" }}>
        <s-section heading="Where the leads are saved">
          <div style={{ display: "grid", gap: "10px" }}>
            <p style={paragraphStyle}>
              The live popup submits phone numbers to Shopify Forms form <strong>{SHOPIFY_FORMS_ID}</strong>.
              Shopify saves successful entries as lead records in Shopify Customers on <strong>{shopDomain}</strong> with the tag <strong>{SHOPIFY_FORMS_TAG}</strong>.
            </p>
            <p style={paragraphStyle}>
              The popup also stores a small browser flag named <strong>anu-login:state</strong> after a successful capture, so that same visitor is not asked for the number again on later page views.
            </p>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <a href={formsUrl} target="_blank" rel="noreferrer" style={primaryButtonAnchorStyle}>Open Shopify Forms</a>
              <a href={customersUrl} target="_blank" rel="noreferrer" style={secondaryButtonAnchorStyle}>Open customer filter</a>
            </div>
          </div>
        </s-section>

        <s-section heading="Lead summary">
          {!hasCustomerReadScope ? (
            <div style={warningBoxStyle}>
              <strong>Reconnect customer access to load leads here.</strong>
              <p style={{ ...paragraphStyle, marginTop: "8px" }}>
                This installation does not currently have <strong>{REQUIRED_CUSTOMER_SCOPE}</strong>, so Basil Admin cannot read the phone-number leads saved by Shopify Forms.
              </p>
              <p style={{ ...paragraphStyle, marginTop: "8px" }}>
                Current scopes: <strong>{installedScopesLabel}</strong>
              </p>
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "12px" }}>
                <a href={reconnectUrl} target="_top" rel="noreferrer" style={primaryButtonAnchorStyle}>Reconnect customer access</a>
                <a href={customersUrl} target="_blank" rel="noreferrer" style={secondaryButtonAnchorStyle}>Open leads in Shopify</a>
              </div>
            </div>
          ) : formsAccessError ? (
            <div style={warningBoxStyle}>
              <strong>Lead data is not readable yet.</strong>
              <p style={{ ...paragraphStyle, marginTop: "8px" }}>{formsAccessError}</p>
              <p style={{ ...paragraphStyle, marginTop: "8px" }}>
                Shopify may still require protected customer data approval before this embedded dashboard can show phone numbers. The leads are still available in Shopify Forms and Customers using the links above.
              </p>
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "12px" }}>
                <a href={reconnectUrl} target="_top" rel="noreferrer" style={primaryButtonAnchorStyle}>Reconnect customer access</a>
                <a href={customersUrl} target="_blank" rel="noreferrer" style={secondaryButtonAnchorStyle}>Open leads in Shopify</a>
              </div>
            </div>
          ) : (
            <StatsGrid>
              <StatCard label="Total leads" value={formatCount(formsCustomers.totalCount, formsCustomers.totalPrecision)} />
              <StatCard label="Leads today" value={formatCount(formsCustomers.todayCount, formsCustomers.todayPrecision)} />
              <StatCard label="Forms tag" value={SHOPIFY_FORMS_TAG} compact />
            </StatsGrid>
          )}
        </s-section>

        <s-section heading="Recent leads">
          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "12px", flexWrap: "wrap" }}>
            <Form method="get" style={{ display: "flex", gap: "8px", flexWrap: "wrap", flex: "1 1 320px" }}>
              <input
                name="search"
                defaultValue={search}
                placeholder="Search phone, email, name, or tag"
                style={inputStyle}
              />
              <button type="submit" style={secondaryButtonStyle}>Search</button>
            </Form>
            <a href={customersUrl} target="_blank" rel="noreferrer" style={secondaryButtonAnchorStyle}>View in Shopify</a>
          </div>

          {!hasCustomerReadScope ? (
            <p style={paragraphStyle}>Reconnect customer access first, or use the filtered Shopify Customers link above to review leads immediately.</p>
          ) : formsAccessError ? (
            <p style={paragraphStyle}>Use Shopify Forms or the filtered Shopify Customers link above until customer-read access is available here.</p>
          ) : customers.length ? (
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <TableHeader>Created</TableHeader>
                    <TableHeader>Lead</TableHeader>
                    <TableHeader>Phone</TableHeader>
                    <TableHeader>Email</TableHeader>
                    <TableHeader>SMS consent</TableHeader>
                    <TableHeader>Email consent</TableHeader>
                    <TableHeader>Tags</TableHeader>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((customer) => (
                    <tr key={customer.id}>
                      <TableCell>{formatDate(customer.createdAt)}</TableCell>
                      <TableCell>{customer.displayName || "-"}</TableCell>
                      <TableCell>{customer.phone || "-"}</TableCell>
                      <TableCell>{customer.email || "-"}</TableCell>
                      <TableCell>{customer.smsMarketingConsent?.marketingState || "-"}</TableCell>
                      <TableCell>{customer.emailMarketingConsent?.marketingState || "-"}</TableCell>
                      <TableCell>{formatTags(customer.tags)}</TableCell>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={paragraphStyle}>No Shopify leads found for this Forms tag yet.</p>
          )}
        </s-section>
      </div>
    </s-page>
  );
}

function StatsGrid({ children }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: "12px",
      }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, compact = false }) {
  return (
    <div style={{ border: "1px solid #d8d8d8", borderRadius: "12px", padding: "14px", background: "#ffffff" }}>
      <div style={{ fontSize: "12px", color: "#616161", marginBottom: "6px" }}>{label}</div>
      <div style={{ fontSize: compact ? "16px" : "26px", fontWeight: 700, wordBreak: "break-word" }}>{value}</div>
    </div>
  );
}

function TableHeader({ children }) {
  return <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #d8d8d8", whiteSpace: "nowrap" }}>{children}</th>;
}

function TableCell({ children }) {
  return <td style={{ padding: "10px 12px", borderBottom: "1px solid #ededed", verticalAlign: "top" }}>{children}</td>;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return LEAD_DATE_FORMATTER.format(date);
}

function formatCount(count, precision) {
  return precision && precision !== "EXACT" ? `${count}+` : String(count || 0);
}

function formatTags(tags = []) {
  if (!tags.length) {
    return "-";
  }

  return tags.join(", ");
}

const paragraphStyle = {
  margin: 0,
  color: "#3f453f",
  fontSize: "13px",
  lineHeight: 1.5,
};

const inputStyle = {
  width: "min(100%, 360px)",
  minHeight: "40px",
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid #c9cccf",
  font: "inherit",
  boxSizing: "border-box",
};

const primaryButtonAnchorStyle = {
  minHeight: "40px",
  padding: "0 14px",
  borderRadius: "10px",
  border: "1px solid #075f3b",
  background: "#075f3b",
  color: "#ffffff",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  font: "inherit",
  fontWeight: 600,
  textDecoration: "none",
};

const secondaryButtonStyle = {
  minHeight: "40px",
  padding: "0 14px",
  borderRadius: "10px",
  border: "1px solid #c9cccf",
  background: "#ffffff",
  font: "inherit",
  cursor: "pointer",
};

const secondaryButtonAnchorStyle = {
  ...secondaryButtonStyle,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#111827",
  textDecoration: "none",
};

const warningBoxStyle = {
  borderRadius: "12px",
  padding: "14px",
  background: "#fff7e6",
  color: "#5f3f10",
  border: "1px solid #f1d39b",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "14px",
};

export const headers = (headersArgs) => {
  return boundary.headers(headersArgs);
};
