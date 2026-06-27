"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { khhTenantWorkbenchDefinition } from "@scas/tenant-workbench-domain/khh";
import { createNavigationViewModel } from "@scas/tenant-workbench-ui";
import { resolveIcon } from "@/lib/icons";
import { cn } from "@/lib/utils";

const navItems = createNavigationViewModel(khhTenantWorkbenchDefinition.navigation);

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
          const Icon = resolveIcon(item.iconId);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "nav-link",
                active && "nav-link-active",
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
        className="nav-link mt-auto"
      >
        <LogOut size={17} aria-hidden />
        <span>Abmelden</span>
      </Link>
    </aside>
  );
}
