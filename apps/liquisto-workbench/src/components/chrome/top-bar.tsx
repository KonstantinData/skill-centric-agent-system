import Image from "next/image";
import { Command, Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

export function TopBar({ userEmail }: { userEmail: string }) {
  return (
    <header className="mb-5 flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
        <Image
          src="/liquisto-logo.png"
          alt="Liquisto"
          width={36}
          height={36}
          className="lg:hidden"
          priority
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-black">Liquisto Business Platform</p>
          <p className="truncate text-xs font-bold text-[var(--muted)]">
            liquisto.cloud · Business processes
          </p>
        </div>
      </div>
      <div className="hidden min-w-[280px] max-w-[520px] flex-1 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--field-surface)] px-3 py-2 text-sm text-[var(--muted)] md:flex">
        <Search size={16} aria-hidden />
        <span className="truncate">Search inventory, initiatives, or partners</span>
        <Command className="ml-auto" size={15} aria-hidden />
      </div>
      <div className="flex min-w-0 items-center gap-2">
        <ThemeToggle />
        <div className="hidden min-w-0 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-right text-sm sm:block">
          <p className="font-bold">Signed in</p>
          <p className="truncate text-[var(--muted)]">
            {userEmail || "Cloudflare Access"}
          </p>
        </div>
      </div>
    </header>
  );
}
