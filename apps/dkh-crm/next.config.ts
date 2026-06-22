import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: process.cwd(),
  async redirects() {
    return [
      {
        source: "/uebersicht.php",
        destination: "/",
        permanent: true,
      },
      {
        source: "/termine.php",
        destination: "/termine",
        permanent: true,
      },
      {
        source: "/aufgaben.php",
        destination: "/aufgaben",
        permanent: true,
      },
      {
        source: "/emails.php",
        destination: "/emails",
        permanent: true,
      },
      {
        source: "/kunden.php",
        destination: "/kunden",
        permanent: true,
      },
      {
        source: "/vorgaenge.php",
        destination: "/vorgaenge",
        permanent: true,
      },
      {
        source: "/admin.php",
        destination: "/admin",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
