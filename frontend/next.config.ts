import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Enable standalone output for production Docker builds
  output: 'standalone',
};

export default nextConfig;
