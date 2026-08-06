import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Standalone output: the production Docker stage (docker/Dockerfile.frontend's
  // `prod` target) copies just .next/standalone + .next/static + public,
  // running `node server.js` — no node_modules or full source in the final
  // image. Harmless in dev mode (Milestone D's `dev` target ignores it).
  output: "standalone",
  // Docker dev container: bind-mounted source, hot reload via polling
  // (Windows host + Linux container bind mounts don't always deliver
  // inotify events reliably) — see docker/Dockerfile.frontend.
  webpack: (config) => {
    config.watchOptions = {
      poll: 1000,
      aggregateTimeout: 300,
    };
    return config;
  },
};

export default nextConfig;
