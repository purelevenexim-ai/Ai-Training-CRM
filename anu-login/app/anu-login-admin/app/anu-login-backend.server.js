const backendBaseUrl = (process.env.ANU_LOGIN_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const backendAdminSecret = (process.env.ANU_LOGIN_ADMIN_SECRET || "").trim();

function getAdminHeaders(extraHeaders = {}) {
  return {
    ...(backendAdminSecret ? { "X-Anu-Admin-Secret": backendAdminSecret } : {}),
    ...extraHeaders,
  };
}

async function backendFetch(path, options = {}) {
  const response = await fetch(`${backendBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Backend request failed with status ${response.status}`);
  }

  if ((response.headers.get("content-type") || "").includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export function getBackendBaseUrl() {
  return backendBaseUrl;
}

export function getLeadExportUrl(search = "") {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return `${backendBaseUrl}/api/admin/leads/export${query}`;
}

export async function getAdminSettings() {
  return backendFetch("/api/admin/settings", {
    headers: getAdminHeaders(),
  });
}

export async function updateAdminSettings(payload) {
  return backendFetch("/api/admin/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
    headers: getAdminHeaders(),
  });
}

export async function getAdminDashboard() {
  return backendFetch("/api/admin/dashboard", {
    headers: getAdminHeaders(),
  });
}

export async function getLeads(search = "") {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return backendFetch(`/api/leads${query}`, {
    headers: getAdminHeaders(),
  });
}

export async function getShopifyConnectionStatus() {
  return backendFetch("/api/admin/shopify-connection", {
    headers: getAdminHeaders(),
  });
}

export async function syncShopifyConnection(payload) {
  return backendFetch("/api/admin/shopify-connection", {
    method: "PUT",
    body: JSON.stringify(payload),
    headers: getAdminHeaders(),
  });
}