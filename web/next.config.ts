import type { NextConfig } from "next";

// The browser talks to /api/*, and Next.js forwards it to the FastAPI tools API.
// Same origin for the browser, so the API needs no CORS setup.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
  experimental: {
    // POST /chat waits for several model calls; the default 30s proxy timeout is too short.
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
