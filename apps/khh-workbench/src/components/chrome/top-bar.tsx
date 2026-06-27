import Image from "next/image";
import { ThemeToggle } from "./theme-toggle";

export function TopBar({ userEmail }: { userEmail: string }) {
  return (
    <header className="mb-5 flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3">
        <Image
          src="/khh-logo.png"
          alt="Kinderhaus Heuschrecken"
          width={36}
          height={36}
          className="lg:hidden"
          priority
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-black">Leitungs-Cockpit</p>
          <p className="truncate text-xs font-bold text-[var(--muted)]">
            Heute, Dienste, Fristen und Aufgaben
          </p>
        </div>
      </div>
      <div className="flex min-w-0 items-center gap-2">
        <ThemeToggle />
        <div className="top-user-pill hidden min-w-0 text-right text-sm sm:block">
          <p className="font-bold">Angemeldet</p>
          <p className="truncate text-[var(--muted)]">
            {userEmail || "Cloudflare Access"}
          </p>
        </div>
      </div>
    </header>
  );
}
