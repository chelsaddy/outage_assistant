import { NextResponse } from "next/server";
import { createSession, SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";
import { loginConfigured, verifyCredentials } from "@/lib/staffAuth";

export async function POST(req: Request) {
  if (!loginConfigured()) {
    return NextResponse.json(
      { detail: "Dashboard login is not configured. Set DASHBOARD_USER, DASHBOARD_PASSWORD and SESSION_SECRET." },
      { status: 503 },
    );
  }

  let username = "";
  let password = "";
  try {
    const body = await req.json();
    username = String(body?.username ?? "");
    password = String(body?.password ?? "");
  } catch {
    return NextResponse.json({ detail: "Expected a JSON body." }, { status: 400 });
  }

  const user = await verifyCredentials(username, password);
  if (!user) return NextResponse.json({ detail: "Wrong username or password." }, { status: 401 });

  const https = req.headers.get("x-forwarded-proto") === "https" || new URL(req.url).protocol === "https:";
  const res = NextResponse.json({ user });
  res.cookies.set(SESSION_COOKIE, createSession(user), {
    httpOnly: true,     // not readable from page scripts
    sameSite: "lax",    // not sent on cross-site POST/PATCH, so other sites can't act as staff
    secure: https,
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  return res;
}
