"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type ThemePreference = "system" | "light" | "dark";

const STORAGE_KEY = "dkh-crm-theme";

function applyTheme(preference: ThemePreference) {
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const resolved = preference === "system" ? (systemDark ? "dark" : "light") : preference;
  root.dataset.theme = resolved;
  root.dataset.themePreference = preference;
}

export function ThemeToggle() {
  const [preference, setPreference] = useState<ThemePreference>("system");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const initial: ThemePreference =
      stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
    setPreference(initial);
    applyTheme(initial);

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncSystem = () => {
      if ((window.localStorage.getItem(STORAGE_KEY) || "system") === "system") {
        applyTheme("system");
      }
    };
    media.addEventListener("change", syncSystem);
    return () => media.removeEventListener("change", syncSystem);
  }, []);

  function updatePreference(next: ThemePreference) {
    setPreference(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  }

  const Icon = preference === "dark" ? Moon : preference === "light" ? Sun : Monitor;
  const label =
    preference === "dark"
      ? "Dark Mode aktiv"
      : preference === "light"
        ? "Light Mode aktiv"
        : "Systemmodus aktiv";
  const next = preference === "system" ? "dark" : preference === "dark" ? "light" : "system";

  return (
    <button
      type="button"
      className="btn btn-secondary h-10 w-10 p-0"
      aria-label={`${label}. Theme wechseln`}
      title={`${label}. Klicken zum Wechseln.`}
      onClick={() => updatePreference(next)}
    >
      <Icon size={17} aria-hidden="true" />
    </button>
  );
}
