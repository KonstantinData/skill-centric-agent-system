"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { navItems } from "@/lib/workbench-data";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden min-h-screen flex-col border-r border-[var(--border)] bg-[var(--chrome-surface)] px-4 py-5 lg:flex">
      <Link href="/" className="mb-7 block w-full">
        <Image
          src="/khh-logo.png"
          alt="Kinderhaus Heuschrecken"
          width={500}
          height={113}
          sizes="216px"
          className="h-auto w-full"
          priority
        />
      </Link>
      <nav className="grid gap-1">
        {navItems.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-h-10 items-center gap-3 rounded-lg px-3 text-sm font-bold text-[var(--muted)]",
                active && "bg-[var(--surface-soft)] text-[var(--foreground)]",
              )}
            >
              <Icon size={17} aria-hidden />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <Link
        href="/cdn-cgi/access/logout"
        className="mt-auto flex min-h-10 items-center gap-3 rounded-lg border border-transparent px-3 text-sm font-bold text-[var(--muted)] hover:border-[var(--border)] hover:bg-[var(--surface-soft)] hover:text-[var(--foreground)]"
      >
        <LogOut size={17} aria-hidden />
        <span>Abmelden</span>
      </Link>
    </aside>
  );
}
