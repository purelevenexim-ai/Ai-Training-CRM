import { AppProvider } from "@shopify/shopify-app-react-router/react";
import { useState } from "react";
import { Form, useActionData, useLoaderData } from "react-router";
import { login } from "../../shopify.server";
import { loginErrorMessage } from "./error.server";

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  const shop = url.searchParams.get("shop") || "";
  const errors = loginErrorMessage(await login(request));

  return { errors, shop };
};

export const action = async ({ request }) => {
  const formData = await request.formData();
  const shop = String(formData.get("shop") || "").trim();
  const errors = loginErrorMessage(await login(request));

  return {
    errors,
    shop,
  };
};

export default function Auth() {
  const loaderData = useLoaderData();
  const actionData = useActionData();
  const [shop, setShop] = useState(actionData?.shop || loaderData.shop || "");
  const { errors } = actionData || loaderData;

  return (
    <AppProvider embedded={false}>
      <s-page>
        <Form method="post">
          <s-section heading="Reconnect Anu Login Admin">
            <s-paragraph>
              Reauthorize the app with your Shopify store so Anu Login Admin can load customer-tagged leads.
            </s-paragraph>
            <s-text-field
              name="shop"
              label="Shop domain"
              details="example.myshopify.com"
              value={shop}
              onChange={(e) => setShop(e.currentTarget.value)}
              autocomplete="on"
              error={errors.shop}
            ></s-text-field>
            <s-button type="submit">Log in</s-button>
          </s-section>
        </Form>
      </s-page>
    </AppProvider>
  );
}
