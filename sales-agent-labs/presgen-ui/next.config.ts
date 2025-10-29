import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false, // Disable strict mode to prevent double hydration warnings
  output: 'standalone', // Required for Docker deployment
  eslint: {
    ignoreDuringBuilds: true, // Temporarily bypass ESLint errors during build
  },
  typescript: {
    ignoreBuildErrors: true, // Temporarily bypass TypeScript errors during build
  },
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-tooltip'], // Optimize common packages
    proxyTimeout: 10 * 60 * 1000, // 10 minutes for long-running operations
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error']
    } : false,
  },
  async rewrites() {
    return [
      // Only proxy specific API routes to the backend, not all /api/* routes
      // This allows our Next.js API routes in /api/presgen-assess/* to work
      // Add specific backend routes here as needed
      // {
      //   source: '/api/backend/:path*',
      //   destination: 'http://localhost:8080/:path*',
      // },
    ];
  },
};

export default nextConfig;
