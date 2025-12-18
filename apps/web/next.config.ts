import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: "standalone",

  // Disable image optimization in demo mode (no external image loader)
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
