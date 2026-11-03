import { defineConfig, devices } from "@playwright/test";

const DATABASE_URL =
  process.env.DATABASE_URL ??
  "postgresql+psycopg://postgres@localhost:55301/orderflow";
const API = "http://localhost:8301";
const WEB = "http://localhost:5301";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: WEB,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "mobile",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: [
    {
      command:
        "uv run alembic upgrade head && uv run python -m app.seed && " +
        "uv run uvicorn app.main:app --host 127.0.0.1 --port 8301",
      cwd: "../backend",
      url: `${API}/api/health`,
      env: { DATABASE_URL },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      cwd: "../frontend",
      url: WEB,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
