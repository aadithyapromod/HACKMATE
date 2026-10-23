import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v2/:path*",
        destination: "http://127.0.0.1:8000/api/v2/:path*",
      },
    ];
  },
};

export default nextConfig;
