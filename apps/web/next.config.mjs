/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for the single otter/platform Docker image.
  output: "standalone",
};

export default nextConfig;
