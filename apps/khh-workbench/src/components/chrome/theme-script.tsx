export function ThemeScript() {
  const script = `
    try {
      const stored = localStorage.getItem("khh-workbench-theme");
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      if (stored === "dark" || (!stored && prefersDark)) {
        document.documentElement.dataset.theme = "dark";
      }
    } catch {}
  `;

  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
