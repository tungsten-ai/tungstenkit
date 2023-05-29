/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // output:"export",
  // distDir: 'dist',  
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    ignoreBuildErrors: true,
  },
}

module.exports = nextConfig
