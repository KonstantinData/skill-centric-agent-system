"use client";

import { Moon, SunMedium } from "lucide-react";

export function ThemeToggle() {
  return (
    <button
      type="button"
      className="icon-btn"
      title="Darstellung umschalten"
      aria-label="Darstellung umschalten"
      onClick={() => {
        const current = document.documentElement.dataset.theme;
        const next = current === "dark" ? "" : "dark";
        if (next) {
          document.documentElement.dataset.theme = next;
          localStorage.setItem("liquisto-workbench-theme", next);
        } else {
          delete document.documentElement.dataset.theme;
          localStorage.setItem("liquisto-workbench-theme", "light");
        }
      }}
    >
      <SunMedium className="theme-light-icon" size={18} aria-hidden />
      <Moon className="theme-dark-icon" size={18} aria-hidden />
    </button>
  );
}
