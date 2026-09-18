/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/:path*`,
      },
      {
        source: '/projects/:path*',
        destination: `${apiBase}/projects/:path*`,
      },
      {
        source: '/script/:path*',
        destination: `${apiBase}/script/:path*`,
      },
      {
        source: '/timeline/:path*',
        destination: `${apiBase}/timeline/:path*`,
      },
      {
        source: '/qa/:path*',
        destination: `${apiBase}/qa/:path*`,
      },
      {
        source: '/media/:path*',
        destination: `${apiBase}/media/:path*`,
      },
      {
        source: '/library/:path*',
        destination: `${apiBase}/library/:path*`,
      },
      {
        source: '/cost/:path*',
        destination: `${apiBase}/cost/:path*`,
      },
      {
        source: '/audit/:path*',
        destination: `${apiBase}/audit/:path*`,
      },
      {
        source: '/workflow/:path*',
        destination: `${apiBase}/workflow/:path*`,
      },
      {
        source: '/campaign/:path*',
        destination: `${apiBase}/campaign/:path*`,
      },
      {
        source: '/thumbnail/:path*',
        destination: `${apiBase}/thumbnail/:path*`,
      },
      {
        source: '/render/:path*',
        destination: `${apiBase}/render/:path*`,
      },
      {
        source: '/subtitles/:path*',
        destination: `${apiBase}/subtitles/:path*`,
      },
    ];
  },
};

export default nextConfig;
