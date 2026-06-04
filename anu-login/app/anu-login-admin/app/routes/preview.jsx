import { Form, useActionData, useLoaderData, useNavigation } from "react-router";
import {
  getAdminDashboard,
  getAdminSettings,
  getBackendBaseUrl,
  getLeadExportUrl,
  getLeads,
  updateAdminSettings,
} from "../anu-login-backend.server";

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  const search = url.searchParams.get("search") || "";

  try {
    const [settings, dashboard, leads] = await Promise.all([
      getAdminSettings(),
      getAdminDashboard(),
      getLeads(search),
    ]);

    return {
      backendBaseUrl: getBackendBaseUrl(),
      exportUrl: getLeadExportUrl(search),
      search,
      settings,
      dashboard,
      leads,
      backendError: null,
    };
  } catch (error) {
    return {
      backendBaseUrl: getBackendBaseUrl(),
      exportUrl: getLeadExportUrl(search),
      search,
      settings: null,
      dashboard: null,
      leads: null,
      backendError: error instanceof Error ? error.message : "Could not reach the Anu login backend.",
    };
  }
};

export const action = async ({ request }) => {
  const formData = await request.formData();
  const currentSettings = await getAdminSettings();

  const toString = (key) => String(formData.get(key) || "").trim();
  const toBoolean = (key) => formData.get(key) === "on";
  const toInteger = (key, fallback = 0) => {
    const value = Number.parseInt(toString(key), 10);
    return Number.isFinite(value) ? value : fallback;
  };
  const currentBasil = currentSettings.basil_checkout || {};

  const payload = {
    coupon_code: toString("coupon_code"),
    privacy_policy_url: toString("privacy_policy_url"),
    terms_of_service_url: toString("terms_of_service_url"),
    support_email: toString("support_email"),
    google: {
      ...currentSettings.google,
      enabled: false,
      one_tap_enabled: false,
    },
    otp: {
      ...currentSettings.otp,
      enabled: false,
    },
    truecaller: {
      ...currentSettings.truecaller,
      enabled: false,
    },
    features: {
      email_enabled: toBoolean("feature_email_enabled"),
      widget_enabled: toBoolean("feature_widget_enabled"),
      auto_shopify_sync: toBoolean("feature_auto_shopify_sync"),
      export_enabled: toBoolean("feature_export_enabled"),
    },
    basil_checkout: {
      ...currentBasil,
      enabled: toBoolean("basil_enabled"),
      program_label: toString("basil_program_label") || "Basil Checkout",
      free_delivery_threshold: toInteger("basil_free_delivery_threshold", currentBasil.free_delivery_threshold || 649),
      gift_threshold: toInteger("basil_gift_threshold", currentBasil.gift_threshold || 1449),
      delivery_value: toInteger("basil_delivery_value", currentBasil.delivery_value || 80),
      gift_value: toInteger("basil_gift_value", currentBasil.gift_value || 200),
      delivery_label: toString("basil_delivery_label") || "Free delivery",
      gift_label: toString("basil_gift_label") || "Free gift",
      complete_label: toString("basil_complete_label") || "Rewards unlocked",
      rewards_heading: toString("basil_rewards_heading") || "Your rewards",
      rewards_copy: toString("basil_rewards_copy") || "Track delivery and gift checkpoints as your cart grows.",
      upsell_heading: toString("basil_upsell_heading") || "Add a best-seller",
      upsell_copy: toString("basil_upsell_copy") || "Small add-ons that move you closer to the next reward.",
      delivery_unlocked_toast: toString("basil_delivery_unlocked_toast") || "Free delivery unlocked",
      gift_unlocked_toast: toString("basil_gift_unlocked_toast") || "Gift unlocked",
      add_to_cart_toast: toString("basil_add_to_cart_toast") || "Cart updated",
    },
  };

  try {
    const settings = await updateAdminSettings(payload);
    return { ok: true, message: "Basil settings saved.", settings };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Could not save Basil settings.",
    };
  }
};

export default function PreviewRoute() {
  const { backendBaseUrl, exportUrl, search, settings, dashboard, leads, backendError } = useLoaderData();
  const actionData = useActionData();
  const navigation = useNavigation();
  const isSaving = navigation.state === "submitting";
  const summaryItems = dashboard ? Object.entries(dashboard.provider_breakdown || {}) : [];
  const basil = settings?.basil_checkout || {};

  return (
    <main style={pageStyle}>
      <div style={heroStyle}>
        <div>
          <p style={eyebrowStyle}>Local preview</p>
          <h1 style={titleStyle}>Basil Checkout admin</h1>
          <p style={subtitleStyle}>
            Configure cart rewards, motion messages, and lead capture settings before opening the embedded app in Shopify.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gap: "16px" }}>
        {actionData?.message ? (
          <Banner ok={actionData.ok}>{actionData.message}</Banner>
        ) : null}

        {backendError ? <Banner ok={false}>{backendError}</Banner> : null}

        <Section title="Connection overview">
          <FieldGrid>
            <ReadOnlyStat label="Backend base URL" value={backendBaseUrl} />
            <ReadOnlyStat label="Export URL" value={exportUrl} href={exportUrl} />
          </FieldGrid>
          <div style={{ display: "grid", gap: "10px", marginTop: "16px", color: "#475467", fontSize: "14px", lineHeight: 1.55 }}>
            <p style={{ margin: 0 }}>Captured phone numbers land in the Anu backend first and show up below in Recent leads within seconds.</p>
            <p style={{ margin: 0 }}>Use Export CSV for manual review. When Shopify sync is enabled and healthy, the backend also attempts to attach each lead to a Shopify customer record.</p>
          </div>
        </Section>

        {!settings ? (
          <Section title="Backend connection needed">
            <p style={{ margin: 0 }}>
              The preview route is ready, but it could not reach the Anu backend.
            </p>
          </Section>
        ) : (
          <Form method="post" style={{ display: "grid", gap: "16px" }}>
            <Section title="Core settings">
              <FieldGrid>
                <TextField name="coupon_code" label="Coupon code" defaultValue={settings.coupon_code} />
                <TextField name="support_email" label="Support email" defaultValue={settings.support_email} />
                <TextField name="privacy_policy_url" label="Privacy policy URL" defaultValue={settings.privacy_policy_url} />
                <TextField name="terms_of_service_url" label="Terms of service URL" defaultValue={settings.terms_of_service_url} />
              </FieldGrid>
            </Section>

            <Section title="Feature toggles">
              <CheckboxRow>
                <CheckboxField name="feature_email_enabled" label="Optional post-reveal email capture" defaultChecked={settings.features.email_enabled} />
                <CheckboxField name="feature_widget_enabled" label="Floating widget" defaultChecked={settings.features.widget_enabled} />
                <CheckboxField name="feature_auto_shopify_sync" label="Sync into Shopify customers" defaultChecked={settings.features.auto_shopify_sync} />
                <CheckboxField name="feature_export_enabled" label="Enable CSV export" defaultChecked={settings.features.export_enabled} />
              </CheckboxRow>
              <p style={{ margin: "12px 0 0", color: "#475467", fontSize: "13px", lineHeight: 1.5 }}>
                Google, OTP, and Truecaller controls are hidden here for now. This preview only keeps the live phone-first popup settings and lead operations.
              </p>
              <p style={{ margin: "12px 0 0", color: "#475467", fontSize: "13px", lineHeight: 1.5 }}>
                Even when Shopify sync is off, captured numbers still stay available below in Recent leads and through the CSV export.
              </p>
            </Section>

            <Section title="Basil Checkout cart">
              <CheckboxRow>
                <CheckboxField name="basil_enabled" label="Enable Basil Checkout reward system" defaultChecked={basil.enabled ?? true} />
              </CheckboxRow>
              <FieldGrid>
                <TextField name="basil_program_label" label="Program label" defaultValue={basil.program_label || "Basil Checkout"} />
                <TextField name="basil_free_delivery_threshold" label="Free delivery threshold (Rs)" defaultValue={basil.free_delivery_threshold || 649} />
                <TextField name="basil_gift_threshold" label="Gift threshold (Rs)" defaultValue={basil.gift_threshold || 1449} />
                <TextField name="basil_delivery_value" label="Delivery value (Rs)" defaultValue={basil.delivery_value || 80} />
                <TextField name="basil_gift_value" label="Gift value (Rs)" defaultValue={basil.gift_value || 200} />
                <TextField name="basil_delivery_label" label="Delivery label" defaultValue={basil.delivery_label || "Free delivery"} />
                <TextField name="basil_gift_label" label="Gift label" defaultValue={basil.gift_label || "Free gift"} />
                <TextField name="basil_complete_label" label="Complete label" defaultValue={basil.complete_label || "Rewards unlocked"} />
                <TextField name="basil_rewards_heading" label="Rewards heading" defaultValue={basil.rewards_heading || "Your rewards"} />
                <TextField name="basil_upsell_heading" label="Upsell heading" defaultValue={basil.upsell_heading || "Add a best-seller"} />
                <TextField name="basil_add_to_cart_toast" label="Cart updated motion text" defaultValue={basil.add_to_cart_toast || "Cart updated"} />
                <TextField name="basil_delivery_unlocked_toast" label="Delivery unlocked motion text" defaultValue={basil.delivery_unlocked_toast || "Free delivery unlocked"} />
                <TextField name="basil_gift_unlocked_toast" label="Gift unlocked motion text" defaultValue={basil.gift_unlocked_toast || "Gift unlocked"} />
              </FieldGrid>
              <div style={{ display: "grid", gap: "12px", marginTop: "12px" }}>
                <TextAreaField name="basil_rewards_copy" label="Rewards copy" defaultValue={basil.rewards_copy || "Track delivery and gift checkpoints as your cart grows."} />
                <TextAreaField name="basil_upsell_copy" label="Upsell copy" defaultValue={basil.upsell_copy || "Small add-ons that move you closer to the next reward."} />
              </div>
            </Section>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit" style={primaryButtonStyle} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save Basil settings"}
              </button>
            </div>
          </Form>
        )}

        <Section title="Lead snapshot">
          <StatsGrid>
            <StatCard label="Total leads" value={String(dashboard?.total_leads || 0)} />
            <StatCard label="Leads today" value={String(dashboard?.today_leads || 0)} />
            <StatCard label="Active search" value={search || "All leads"} />
          </StatsGrid>

          <div style={{ marginTop: "16px" }}>
            <h3 style={{ margin: "0 0 8px" }}>Lead source mix</h3>
            {summaryItems.length ? (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {summaryItems.map(([provider, total]) => (
                  <span key={provider} style={chipStyle}>
                    {provider}: {total}
                  </span>
                ))}
              </div>
            ) : (
              <p style={{ margin: 0 }}>No provider data yet.</p>
            )}
          </div>
        </Section>

        <Section title="Recent leads">
          <p style={{ margin: "0 0 12px", color: "#475467", fontSize: "13px", lineHeight: 1.5 }}>
            This is the first place to verify collected numbers. Each successful popup submission is stored here with its phone, optional email, coupon, and Shopify customer link status.
          </p>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "12px", flexWrap: "wrap" }}>
            <Form method="get" style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <input name="search" defaultValue={search} placeholder="Search name, email, or phone" style={inputStyle} />
              <button type="submit" style={secondaryButtonStyle}>Search</button>
            </Form>
            <a href={exportUrl} target="_blank" rel="noreferrer" style={secondaryButtonAnchorStyle}>
              Export CSV
            </a>
          </div>

          {leads?.items?.length ? (
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <TableHeader>Created</TableHeader>
                    <TableHeader>Source</TableHeader>
                    <TableHeader>Name</TableHeader>
                    <TableHeader>Email</TableHeader>
                    <TableHeader>Phone</TableHeader>
                    <TableHeader>Coupon</TableHeader>
                    <TableHeader>Shopify customer</TableHeader>
                    <TableHeader>Page</TableHeader>
                  </tr>
                </thead>
                <tbody>
                  {leads.items.map((lead) => (
                    <tr key={lead.id}>
                      <TableCell>{formatDate(lead.created_at)}</TableCell>
                      <TableCell>{lead.provider}</TableCell>
                      <TableCell>{lead.name || "-"}</TableCell>
                      <TableCell>{lead.email || "-"}</TableCell>
                      <TableCell>{lead.phone || "-"}</TableCell>
                      <TableCell>{lead.coupon_code || "-"}</TableCell>
                      <TableCell>{lead.customer_id || "-"}</TableCell>
                      <TableCell>{lead.page_type || "-"}</TableCell>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ margin: 0 }}>No leads captured yet.</p>
          )}
        </Section>
      </div>
    </main>
  );
}

function Banner({ children, ok }) {
  return (
    <div
      style={{
        borderRadius: "14px",
        padding: "12px 14px",
        background: ok ? "#e7f7ed" : "#fceaea",
        color: ok ? "#0d6832" : "#8e1f0b",
      }}
    >
      {children}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section style={sectionStyle}>
      <h2 style={{ margin: "0 0 16px", fontSize: "20px" }}>{title}</h2>
      {children}
    </section>
  );
}

function ReadOnlyStat({ label, value, href }) {
  return (
    <div style={readOnlyStatStyle}>
      <div style={{ fontSize: "12px", color: "#616161", marginBottom: "6px" }}>{label}</div>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" style={{ color: "#0f172a", wordBreak: "break-all" }}>
          {value}
        </a>
      ) : (
        <div style={{ wordBreak: "break-all", color: "#0f172a" }}>{value}</div>
      )}
    </div>
  );
}

function FieldGrid({ children }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: "12px",
      }}
    >
      {children}
    </div>
  );
}

function CheckboxRow({ children }) {
  return <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", marginBottom: "12px" }}>{children}</div>;
}

function TextField({ label, name, defaultValue = "" }) {
  return (
    <label style={fieldLabelStyle}>
      <span>{label}</span>
      <input name={name} defaultValue={defaultValue} style={inputStyle} />
    </label>
  );
}

function TextAreaField({ label, name, defaultValue = "" }) {
  return (
    <label style={fieldLabelStyle}>
      <span>{label}</span>
      <textarea name={name} defaultValue={defaultValue} style={{ ...inputStyle, minHeight: "140px", resize: "vertical" }} />
    </label>
  );
}

function CheckboxField({ label, name, defaultChecked = false }) {
  return (
    <label style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
      <input type="checkbox" name={name} defaultChecked={defaultChecked} />
      <span>{label}</span>
    </label>
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

function StatCard({ label, value }) {
  return (
    <div style={{ border: "1px solid #d8d8d8", borderRadius: "12px", padding: "14px", background: "#ffffff" }}>
      <div style={{ fontSize: "12px", color: "#616161", marginBottom: "6px" }}>{label}</div>
      <div style={{ fontSize: "24px", fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function TableHeader({ children }) {
  return <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #d8d8d8" }}>{children}</th>;
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

  return date.toLocaleString();
}

const pageStyle = {
  minHeight: "100vh",
  padding: "32px 20px 48px",
  background: "linear-gradient(180deg, #f6f3eb 0%, #ffffff 42%)",
  fontFamily: "Inter, sans-serif",
  color: "#111827",
};

const heroStyle = {
  maxWidth: "1100px",
  margin: "0 auto 20px",
  padding: "24px",
  borderRadius: "24px",
  background: "#fff9e7",
  border: "1px solid #f2e2aa",
};

const eyebrowStyle = {
  margin: "0 0 8px",
  color: "#8a6d1b",
  fontSize: "12px",
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

const titleStyle = {
  margin: "0 0 8px",
  fontSize: "36px",
  lineHeight: 1.05,
};

const subtitleStyle = {
  margin: 0,
  maxWidth: "760px",
  color: "#475467",
  fontSize: "16px",
  lineHeight: 1.55,
};

const sectionStyle = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "20px",
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "20px",
  boxShadow: "0 18px 40px rgba(15, 23, 42, 0.05)",
};

const readOnlyStatStyle = {
  border: "1px solid #d8d8d8",
  borderRadius: "12px",
  padding: "14px",
  background: "#fcfcfd",
};

const fieldLabelStyle = {
  display: "grid",
  gap: "6px",
  fontWeight: 600,
  fontSize: "13px",
};

const inputStyle = {
  width: "100%",
  minHeight: "40px",
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid #c9cccf",
  font: "inherit",
  boxSizing: "border-box",
  background: "#ffffff",
};

const primaryButtonStyle = {
  minHeight: "40px",
  padding: "0 16px",
  border: 0,
  borderRadius: "10px",
  background: "#111827",
  color: "#ffffff",
  font: "inherit",
  fontWeight: 600,
  cursor: "pointer",
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

const chipStyle = {
  display: "inline-flex",
  padding: "6px 10px",
  borderRadius: "999px",
  background: "#f3f4f6",
  fontSize: "12px",
  fontWeight: 600,
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "14px",
};