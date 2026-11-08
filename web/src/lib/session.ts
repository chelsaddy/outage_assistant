// Signed session cookie for dashboard staff. Server-only (middleware and route handlers).
//
// The cookie is `<payload>.<signature>`: payload is base64url JSON { u: username, exp: unix seconds },
// signature is HMAC-SHA256 of the payload with SESSION_SECRET. Nothing secret is stored in it;
// the signature just stops anyone forging or extending a session.
import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE = "oa_session";
export const SESSION_MAX_AGE = 8 * 60 * 60; // one shift

const secret = () => process.env.SESSION_SECRET ?? "";
const sign = (data: string) => createHmac("sha256", secret()).update(data).digest("base64url");

export function createSession(user: string): string {
  const exp = Math.floor(Date.now() / 1000) + SESSION_MAX_AGE;
  const payload = Buffer.from(JSON.stringify({ u: user, exp })).toString("base64url");
  return `${payload}.${sign(payload)}`;
}

export function readSession(token: string | undefined): { user: string } | null {
  if (!token || !secret()) return null;
  const [payload, sig] = token.split(".");
  if (!payload || !sig) return null;
  if (!safeEqual(sig, sign(payload))) return null;
  try {
    const { u, exp } = JSON.parse(Buffer.from(payload, "base64url").toString());
    if (typeof u !== "string" || typeof exp !== "number" || exp < Date.now() / 1000) return null;
    return { user: u };
  } catch {
    return null;
  }
}

/** Constant-time string comparison (hashing first makes the lengths equal). */
export function safeEqual(a: string, b: string): boolean {
  const h = (s: string) => createHash("sha256").update(s).digest();
  return timingSafeEqual(h(a), h(b));
}
