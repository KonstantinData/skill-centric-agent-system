"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden border-r border-[var(--border)] bg-white/90 p-5 lg:block">
      <Link href="/" className="mb-8 block">
        <Image src="/logo.svg" alt="das küchenhaus" width={180} height={61} priority />
      </Link>
      <nav className="grid gap-2">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-bold text-[var(--muted)]",
                active && "bg-[var(--surface-soft)] text-[var(--foreground)]",
              )}
            >
              <Icon size={18} aria-hidden />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
