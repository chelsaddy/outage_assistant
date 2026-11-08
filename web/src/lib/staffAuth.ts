// Who may sign in to the dashboard. Server-only.
//
// Today: one shared staff account from DASHBOARD_USER / DASHBOARD_PASSWORD.
// This is the single place to swap in the organization's directory later: replace the body of
// verifyCredentials() with an LDAP bind, or replace the login form with an SSO (OIDC/SAML) redirect
// whose callback calls createSession() with the user's identity. Nothing else needs to change.
import { safeEqual } from "@/lib/session";

export function loginConfigured(): boolean {
  return Boolean(process.env.DASHBOARD_USER && process.env.DASHBOARD_PASSWORD &&
    (process.env.SESSION_SECRET ?? "").length >= 32);
}

/** Returns the signed-in username, or null if the credentials are wrong. */
export async function verifyCredentials(username: string, password: string): Promise<string | null> {
  const userOk = safeEqual(username, process.env.DASHBOARD_USER ?? "");
  const passOk = safeEqual(password, process.env.DASHBOARD_PASSWORD ?? "");
  return userOk && passOk ? username : null;
}
