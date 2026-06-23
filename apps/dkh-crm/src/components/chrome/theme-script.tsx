export function ThemeScript() {
  const code = `
(() => {
  try {
    const preference = window.localStorage.getItem("dkh-crm-theme") || "system";
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = preference === "dark" || (preference === "system" && systemDark) ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.themePreference = preference;
  } catch {
    document.documentElement.dataset.theme = "light";
    document.documentElement.dataset.themePreference = "system";
  }
})();
`;

  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
