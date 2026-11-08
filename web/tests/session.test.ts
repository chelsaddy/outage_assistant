import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { freshEnv } from "./helpers";

beforeEach(() => freshEnv());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

const load = () => import("@/lib/session");

describe("session cookie", () => {
  it("round-trips the username", async () => {
    const { createSession, readSession } = await load();
    expect(readSession(createSession("admin"))).toEqual({ user: "admin" });
  });

  it("rejects a tampered payload", async () => {
    const { createSession, readSession } = await load();
    const [, sig] = createSession("admin").split(".");
    const forged = Buffer.from(JSON.stringify({ u: "admin", exp: 9_999_999_999 })).toString("base64url");
    expect(readSession(`${forged}.${sig}`)).toBeNull();
  });

  it("rejects a session signed with another secret", async () => {
    const { createSession } = await load();
    const token = createSession("admin");
    freshEnv({ SESSION_SECRET: "y".repeat(48) });
    const { readSession } = await load();
    expect(readSession(token)).toBeNull();
  });

  it("expires after 8 hours", async () => {
    vi.useFakeTimers();
    const { createSession, readSession, SESSION_MAX_AGE } = await load();
    const token = createSession("admin");
    vi.advanceTimersByTime((SESSION_MAX_AGE - 1) * 1000);
    expect(readSession(token)).not.toBeNull();
    vi.advanceTimersByTime(2000);
    expect(readSession(token)).toBeNull();
  });

  it("rejects everything when SESSION_SECRET is unset", async () => {
    const { createSession } = await load();
    const token = createSession("admin");
    freshEnv({ SESSION_SECRET: undefined });
    const { readSession } = await load();
    expect(readSession(token)).toBeNull();
  });

  it.each([undefined, "", "garbage", "a.b", "a.b.c"])("rejects malformed cookie %j", async (value) => {
    const { readSession } = await load();
    expect(readSession(value)).toBeNull();
  });
});
