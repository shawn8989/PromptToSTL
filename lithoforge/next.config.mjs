/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    // Required for Three.js and related packages
    config.externals = config.externals || [];
    return config;
  },
};

export default nextConfig;
