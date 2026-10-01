import type { NextConfig } from "next";

// Static export for GitHub Pages, where the site lives under /turnaround. The same base path is the
// default here so that a plain `npm run build` produces what Pages serves and what the Playwright
// tests load; set NEXT_PUBLIC_BASE_PATH to an empty string to build for the root of a domain.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/turnaround";

// The live API. The workflow passes the TURNAROUND_API_URL repository variable, which is empty until
// someone sets it, so an empty value falls back to the deployed address. The end to end build points
// it at the test server's mock, which refuses HEAD and answers a first 503.
const api = process.env.NEXT_PUBLIC_TURNAROUND_API || "https://turnaround-flights-api.fly.dev";

const config: NextConfig = {
  output: "export",
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
    NEXT_PUBLIC_TURNAROUND_API: api,
  },
};

export default config;
