import Image from "next/image";

export function TopBar({ userEmail }: { userEmail: string }) {
  return (
    <header className="mb-5 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 lg:hidden">
        <Image src="/logo.svg" alt="das küchenhaus" width={132} height={45} priority />
      </div>
      <div className="hidden lg:block">
        <p className="text-sm font-bold text-[var(--muted)]">CRM-Portal</p>
      </div>
      <div className="min-w-0 rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-right text-sm">
        <p className="font-bold">Angemeldet</p>
        <p className="truncate text-[var(--muted)]">{userEmail || "E-Mail nicht verfügbar"}</p>
      </div>
    </header>
  );
}
