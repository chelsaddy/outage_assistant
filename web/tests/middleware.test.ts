import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ENV, freshEnv } from "./helpers";

beforeEach(() => freshEnv());
afterEach(() => vi.unstubAllEnvs());

async function load() {
  const { middleware } = await import("@/middleware");
  const { createSession } = await import("@/lib/session");
  const cookie = (user = "admin") => `oa_session=${createSession(user)}`;
  return { middleware, cookie };
}

const request = (path: string, init: { method?: string; cookie?: string; headers?: Record<string, string> } = {}) =>
  new NextRequest(`http://localhost:3000${path}`, {
    method: init.method ?? "GET",
    headers: { ...(init.cookie ? { cookie: init.cookie } : {}), ...init.headers },
  });

/** The request headers the middleware forwards upstream (NextResponse.next({ request: { headers } })). */
function forwarded(res: Response) {
  const names = (res.headers.get("x-middleware-override-headers") ?? "").split(",").filter(Boolean);
  return Object.fromEntries(names.map((n) => [n, res.headers.get(`x-middleware-request-${n}`)]));
}

describe("pages", () => {
  it("redirects to /login without a session, remembering where you were", async () => {
    const { middleware } = await load();
    const res = middleware(request("/tickets?status=open"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login?next=%2Ftickets%3Fstatus%3Dopen");
  });

  it("lets a signed-in user through", async () => {
    const { middleware, cookie } = await load();
    const res = middleware(request("/tickets", { cookie: cookie() }));
    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("treats a forged cookie as signed out", async () => {
    const { middleware } = await load();
    const res = middleware(request("/", { cookie: "oa_session=eyJ1IjoiYWRtaW4ifQ.forged" }));
    expect(res.status).toBe(307);
  });
});

describe("/api/*", () => {
  it("returns 401 with x-session-expired without a session", async () => {
    const { middleware } = await load();
    const res = middleware(request("/api/tickets"));
    expect(res.status).toBe(401);
    expect(res.headers.get("x-session-expired")).toBe("1");
  });

  it("ignores an Authorization header sent by the browser when signed out", async () => {
    const { middleware } = await load();
    const res = middleware(request("/api/tickets", { headers: { authorization: `Bearer ${ENV.DASHBOARD_API_TOKEN}` } }));
    expect(res.status).toBe(401);
  });

  it("forwards with the API token and without the session cookie", async () => {
    const { middleware, cookie } = await load();
    const res = middleware(request("/api/tickets", {
      cookie: cookie(),
      headers: { authorization: "Bearer something-the-browser-sent" },
    }));
    expect(res.status).toBe(200);
    const headers = forwarded(res);
    expect(headers.authorization).toBe(`Bearer ${ENV.DASHBOARD_API_TOKEN}`);
    expect(headers).not.toHaveProperty("cookie");
  });
});

describe("staff chat limit", () => {
  const chat = (cookie: string) => request("/api/chat", { method: "POST", cookie });

  it("allows 20 messages a minute per staff member, then 429 with Retry-After", async () => {
    const { middleware, cookie } = await load();
    const admin = cookie("admin");
    for (let i = 0; i < 20; i++) expect(middleware(chat(admin)).status).toBe(200);
    const blocked = middleware(chat(admin));
    expect(blocked.status).toBe(429);
    expect(Number(blocked.headers.get("retry-after"))).toBeGreaterThan(0);
  });

  it("counts each staff member separately", async () => {
    const { middleware, cookie } = await load();
    for (let i = 0; i < 20; i++) middleware(chat(cookie("admin")));
    expect(middleware(chat(cookie("admin"))).status).toBe(429);
    expect(middleware(chat(cookie("kavita"))).status).toBe(200);
  });

  it("doesn't limit reads", async () => {
    const { middleware, cookie } = await load();
    const admin = cookie();
    for (let i = 0; i < 20; i++) middleware(chat(admin));
    expect(middleware(request("/api/conversations", { cookie: admin })).status).toBe(200);
    expect(middleware(request("/api/chat", { cookie: admin })).status).toBe(200); // GET isn't a message
  });

  it("follows STAFF_CHAT_PER_MINUTE", async () => {
    freshEnv({ STAFF_CHAT_PER_MINUTE: "2" });
    const { middleware, cookie } = await load();
    const admin = cookie();
    expect([0, 1, 2].map(() => middleware(chat(admin)).status)).toEqual([200, 200, 429]);
  });
});
