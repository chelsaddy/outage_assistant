// Every dashboard page and /api/* call needs a signed-in staff session.
// - Pages without a session redirect to /login.
// - /api/* without a session gets 401. With one, the request is forwarded to the FastAPI API
//   (see the rewrite in next.config.ts) carrying DASHBOARD_API_TOKEN. The token is added here on
//   the server, so the browser never sees it, and the session cookie is not forwarded.
import { NextResponse, type NextRequest } from "next/server";
import { readSession, SESSION_COOKIE } from "@/lib/session";

export function middleware(req: NextRequest) {
  const session = readSession(req.cookies.get(SESSION_COOKIE)?.value);
  const { pathname, search } = req.nextUrl;

  if (pathname.startsWith("/api/")) {
    if (!session) {
      return NextResponse.json(
        { detail: "Your session has expired. Sign in again." },
        { status: 401, headers: { "x-session-expired": "1" } },
      );
    }
    const headers = new Headers(req.headers);
    headers.set("authorization", `Bearer ${process.env.DASHBOARD_API_TOKEN ?? ""}`);
    headers.delete("cookie");
    return NextResponse.next({ request: { headers } });
  }

  if (!session) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  runtime: "nodejs",
  // Everything except the login page, the login/logout routes and static assets.
  matcher: ["/((?!login|auth/|_next/static|_next/image|favicon.ico).*)"],
};
