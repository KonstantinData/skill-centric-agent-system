import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: process.cwd(),
  async redirects() {
    return [
      {
        source: "/uebersicht.php",
        destination: "/",
        permanent: false,
      },
      {
        source: "/index.php",
        destination: "/",
        permanent: false,
      },
      {
        source: "/termine.php",
        destination: "/termine",
        permanent: false,
      },
      {
        source: "/aufgaben.php",
        destination: "/aufgaben",
        permanent: false,
      },
      {
        source: "/emails.php",
        destination: "/emails",
        permanent: false,
      },
      {
        source: "/kunden.php",
        destination: "/kunden",
        permanent: false,
      },
      {
        source: "/vorgaenge.php",
        destination: "/vorgaenge",
        permanent: false,
      },
      {
        source: "/admin.php",
        destination: "/admin",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
