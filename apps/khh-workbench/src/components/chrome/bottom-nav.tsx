"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems } from "@/lib/workbench-data";
import { cn } from "@/lib/utils";

const mobileItems = navItems.slice(0, 5);

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="mobile-nav fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-[var(--border)] px-2 py-1 lg:hidden">
      {mobileItems.map((item) => {
        const active =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "mobile-nav-link",
              active && "mobile-nav-link-active",
            )}
          >
            <Icon size={18} aria-hidden />
            <span className="max-w-full truncate">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
