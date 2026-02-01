import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === 'production';
const repoName = 'TORONTOEVENTS_ANTIGRAVITY';
// DEPLOY_TARGET: 'sftp' = root paths (findtorontoevents.ca/); 'github' = subdirectory (/TORONTOEVENTS_ANTIGRAVITY/)
// Default 'sftp' so plain `npm run build` is safe for FTP root; use DEPLOY_TARGET=github for subdirectory build.
// Subdirectory deployment: basePath + assetPrefix (see Next.js subdirectory deployment guide).
const deployTarget = process.env.DEPLOY_TARGET || 'sftp';

const nextConfig: NextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  basePath: (isProd && deployTarget === 'github') ? `/TORONTOEVENTS_ANTIGRAVITY` : '',
  assetPrefix: (isProd && deployTarget === 'github') ? `/TORONTOEVENTS_ANTIGRAVITY` : '',
  trailingSlash: true,
  // Use separate output so root (sftp) and subpath (github) builds coexist; deploy uses build/ for root, build-github/ for TORONTOEVENTS_ANTIGRAVITY/
  distDir: (isProd && deployTarget === 'github') ? 'build-github' : 'build',
};

export default nextConfig;
