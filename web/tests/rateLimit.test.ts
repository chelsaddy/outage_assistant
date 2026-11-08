import { describe, expect, it } from "vitest";
import { clientIp, RateLimiter } from "@/lib/rateLimit";

describe("RateLimiter", () => {
  it("allows up to the limit, then reports seconds until the oldest hit expires", () => {
    const rl = new RateLimiter(2, 60_000);
    rl.record("a", 0);
    rl.record("a", 10_000);
    expect(rl.retryAfter("a", 20_000)).toBe(40);
    expect(rl.retryAfter("b", 20_000)).toBe(0);
  });

  it("slides the window", () => {
    const rl = new RateLimiter(1, 60_000);
    rl.record("a", 0);
    expect(rl.retryAfter("a", 59_999)).toBe(1);
    expect(rl.retryAfter("a", 60_000)).toBe(0);
  });

  it("clear() resets one key only", () => {
    const rl = new RateLimiter(1, 60_000);
    rl.record("a", 0);
    rl.record("b", 0);
    rl.clear("a");
    expect(rl.retryAfter("a", 1)).toBe(0);
    expect(rl.retryAfter("b", 1)).toBeGreaterThan(0);
  });
});

describe("clientIp", () => {
  const req = (xff?: string) => new Request("http://x", { headers: xff ? { "x-forwarded-for": xff } : {} });
  it("takes the first X-Forwarded-For entry", () => expect(clientIp(req("1.2.3.4, 10.0.0.1"))).toBe("1.2.3.4"));
  it("falls back to 'unknown'", () => expect(clientIp(req())).toBe("unknown"));
});
