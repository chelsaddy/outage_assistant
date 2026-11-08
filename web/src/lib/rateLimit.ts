// In-memory sliding-window rate limits for the dashboard server. Server-only.
// Counts live in this process: fine for one dashboard server. With several, move them to Redis.

export class RateLimiter {
  private hits = new Map<string, number[]>();

  constructor(private limit: number, private windowMs: number) {}

  private prune(key: string, now: number): number[] {
    const q = (this.hits.get(key) ?? []).filter((t) => t > now - this.windowMs);
    this.hits.set(key, q);
    return q;
  }

  /** Seconds until the next hit is allowed; 0 if allowed now. */
  retryAfter(key: string, now = Date.now()): number {
    const q = this.prune(key, now);
    return q.length < this.limit ? 0 : Math.max(1, Math.ceil((q[0] + this.windowMs - now) / 1000));
  }

  record(key: string, now = Date.now()): void {
    this.prune(key, now).push(now);
    if (this.hits.size > 10_000) {
      for (const [k, q] of this.hits) if (!q.length || q[q.length - 1] <= now - this.windowMs) this.hits.delete(k);
    }
  }

  clear(key: string): void {
    this.hits.delete(key);
  }
}

const envInt = (name: string, fallback: number) => Number(process.env[name]) || fallback;

/**
 * Best-effort client IP. Next.js passes the client's own X-Forwarded-For through unchanged, so this
 * can be spoofed unless a reverse proxy in front overwrites it. Limits keyed on it are therefore
 * always paired with a global limit that spoofing can't get around.
 */
export function clientIp(req: Request): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0].trim() || "unknown";
}

export const tooMany = (retryAfter: number, detail: string) =>
  Response.json({ detail }, { status: 429, headers: { "Retry-After": String(retryAfter) } });

const FIFTEEN_MINUTES = 15 * 60 * 1000;

// Failed sign-ins only. Per IP, plus a cap for everyone together that bounds password guessing
// even if the IP is spoofed (at the cost of briefly blocking sign-in during an attack).
export const LOGIN_FAILURES_PER_IP = new RateLimiter(envInt("LOGIN_FAILURES_PER_IP", 5), FIFTEEN_MINUTES);
export const LOGIN_FAILURES_GLOBAL = new RateLimiter(envInt("LOGIN_FAILURES_GLOBAL", 30), FIFTEEN_MINUTES);

// Messages a signed-in staff member sends to the agent from the dashboard.
export const STAFF_CHAT_PER_MINUTE = new RateLimiter(envInt("STAFF_CHAT_PER_MINUTE", 20), 60 * 1000);
