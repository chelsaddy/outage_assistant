import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { badLogin, freshEnv, goodLogin, loginRequest } from "./helpers";

beforeEach(() => freshEnv());
afterEach(() => vi.unstubAllEnvs());

const load = async () => (await import("@/app/auth/login/route")).POST;

describe("POST /auth/login", () => {
  it("signs in with the right credentials and sets a locked-down cookie", async () => {
    const POST = await load();
    const res = await POST(loginRequest(goodLogin));
    expect(res.status).toBe(200);
    const cookie = res.headers.get("set-cookie") ?? "";
    expect(cookie).toMatch(/^oa_session=[\w-]+\.[\w-]+;/);
    expect(cookie).toMatch(/HttpOnly/i);
    expect(cookie).toMatch(/SameSite=lax/i);
    expect(cookie).toMatch(/Max-Age=28800/);
    expect(cookie).not.toMatch(/Secure/i); // plain http
  });

  it("marks the cookie Secure behind HTTPS", async () => {
    const POST = await load();
    const req = loginRequest(goodLogin);
    req.headers.set("x-forwarded-proto", "https");
    expect((await POST(req)).headers.get("set-cookie")).toMatch(/Secure/i);
  });

  it.each([
    ["wrong password", badLogin],
    ["wrong username", { username: "root", password: goodLogin.password }],
    ["empty body fields", {}],
  ])("rejects %s without a cookie", async (_, body) => {
    const POST = await load();
    const res = await POST(loginRequest(body));
    expect(res.status).toBe(401);
    expect(res.headers.get("set-cookie")).toBeNull();
  });

  it("rejects a non-JSON body", async () => {
    const POST = await load();
    expect((await POST(loginRequest("not json"))).status).toBe(400);
  });

  it.each(["DASHBOARD_PASSWORD", "DASHBOARD_USER"])("refuses to run when %s is unset", async (name) => {
    freshEnv({ [name]: undefined });
    const POST = await load();
    expect((await POST(loginRequest(goodLogin))).status).toBe(503);
  });

  it("refuses a SESSION_SECRET shorter than 32 characters", async () => {
    freshEnv({ SESSION_SECRET: "short" });
    const POST = await load();
    expect((await POST(loginRequest(goodLogin))).status).toBe(503);
  });
});

describe("failed sign-in limits", () => {
  it("blocks an IP after 5 failures, even with the right password, and says when to retry", async () => {
    const POST = await load();
    for (let i = 0; i < 5; i++) expect((await POST(loginRequest(badLogin, "1.1.1.1"))).status).toBe(401);
    const blocked = await POST(loginRequest(goodLogin, "1.1.1.1"));
    expect(blocked.status).toBe(429);
    expect(Number(blocked.headers.get("retry-after"))).toBeGreaterThan(800); // ~15 minutes
    expect(blocked.headers.get("set-cookie")).toBeNull();
  });

  it("keeps other IPs unaffected", async () => {
    const POST = await load();
    for (let i = 0; i < 5; i++) await POST(loginRequest(badLogin, "1.1.1.1"));
    expect((await POST(loginRequest(goodLogin, "2.2.2.2"))).status).toBe(200);
  });

  it("caps failures from everyone together, so rotating IPs doesn't help", async () => {
    freshEnv({ LOGIN_FAILURES_GLOBAL: "3" });
    const POST = await load();
    for (const ip of ["1.1.1.1", "2.2.2.2", "3.3.3.3"]) await POST(loginRequest(badLogin, ip));
    expect((await POST(loginRequest(goodLogin, "4.4.4.4"))).status).toBe(429);
  });

  it("only counts failures: successful sign-ins never lock anyone out", async () => {
    const POST = await load();
    for (let i = 0; i < 10; i++) expect((await POST(loginRequest(goodLogin, "1.1.1.1"))).status).toBe(200);
  });

  it("resets an IP's failures after it signs in", async () => {
    const POST = await load();
    for (let i = 0; i < 4; i++) await POST(loginRequest(badLogin, "1.1.1.1"));
    expect((await POST(loginRequest(goodLogin, "1.1.1.1"))).status).toBe(200);
    for (let i = 0; i < 4; i++) expect((await POST(loginRequest(badLogin, "1.1.1.1"))).status).toBe(401);
  });

  it("lets the IP back in once the window passes", async () => {
    vi.useFakeTimers();
    try {
      const POST = await load();
      for (let i = 0; i < 5; i++) await POST(loginRequest(badLogin, "1.1.1.1"));
      expect((await POST(loginRequest(goodLogin, "1.1.1.1"))).status).toBe(429);
      vi.advanceTimersByTime(15 * 60 * 1000 + 1);
      expect((await POST(loginRequest(goodLogin, "1.1.1.1"))).status).toBe(200);
    } finally {
      vi.useRealTimers();
    }
  });
});
