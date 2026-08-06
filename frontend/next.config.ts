import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
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
