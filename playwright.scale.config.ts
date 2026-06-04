/**
 * Playwright config for the 1000-scenario scale test suite.
 * Run: npx playwright test --config=playwright.scale.config.ts
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/scale-tests.spec.ts",
  timeout: 45000,
  expect: { timeout: 10000 },
  fullyParallel: true,
  retries: 0,
  workers: 10,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "scale-test-report" }],
    ["json", { outputFile: "scale-test-results.json" }],
  ],
  use: {
    baseURL: "https://ai.pureleven.com",
    extraHTTPHeaders: {
      Accept: "application/json",
    },
    screenshot: "only-on-failure",
    trace: "off",
  },
  projects: [
    {
      name: "api-scale",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
