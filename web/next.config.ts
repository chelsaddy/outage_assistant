import type { NextConfig } from "next";

// The browser talks to /api/*, and Next.js forwards it to the FastAPI tools API.
// Same origin for the browser, so the API needs no CORS setup.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

// Sent on every response: no framing (clickjacking), no MIME sniffing, no referrer leaks to other
// sites, and no camera/microphone/location access.
const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone", // self-contained server for the Docker image (web/Dockerfile)
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
  experimental: {
    // POST /chat waits for several model calls; the default 30s proxy timeout is too short.
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
