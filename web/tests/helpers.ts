import { vi } from "vitest";

export const ENV = {
  DASHBOARD_USER: "admin",
  DASHBOARD_PASSWORD: "correct-horse-battery",
  SESSION_SECRET: "x".repeat(48),
  DASHBOARD_API_TOKEN: "dashboard-token",
};

/** Set the dashboard env and reload modules, so module-level limiters start empty. */
export function freshEnv(overrides: Record<string, string | undefined> = {}) {
  vi.resetModules();
  for (const [k, v] of Object.entries({ ...ENV, ...overrides })) {
    if (v === undefined) vi.stubEnv(k, "");
    else vi.stubEnv(k, v);
  }
}

export function loginRequest(body: unknown, ip = "10.0.0.1"): Request {
  return new Request("http://localhost:3000/auth/login", {
    method: "POST",
    headers: { "content-type": "application/json", "x-forwarded-for": ip },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

export const goodLogin = { username: ENV.DASHBOARD_USER, password: ENV.DASHBOARD_PASSWORD };
export const badLogin = { username: ENV.DASHBOARD_USER, password: "wrong" };
