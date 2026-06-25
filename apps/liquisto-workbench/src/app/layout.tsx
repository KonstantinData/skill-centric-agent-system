import type { Metadata } from "next";
import { BottomNav } from "@/components/chrome/bottom-nav";
import { Sidebar } from "@/components/chrome/sidebar";
import { ThemeScript } from "@/components/chrome/theme-script";
import { TopBar } from "@/components/chrome/top-bar";
import { getUserEmail } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Liquisto Workbench",
  description: "SCAS-based Liquisto operations workbench",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const userEmail = await getUserEmail();

  return (
    <html lang="de" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body>
        <div className="app-shell">
          <Sidebar />
          <div className="min-w-0">
            <main className="app-main">
              <TopBar userEmail={userEmail} />
              {children}
            </main>
          </div>
          <BottomNav />
        </div>
      </body>
    </html>
  );
}
