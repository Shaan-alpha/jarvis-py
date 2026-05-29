// theme.js — applies server theme events; manual override persists locally.
const Theme = (() => {
  const KEY = "jarvis-theme-override"; // "auto" | "cyan" | "gold" | "frost"
  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }
  function override() {
    return localStorage.getItem(KEY) || "auto";
  }
  function setOverride(v) {
    localStorage.setItem(KEY, v);
  }
  function onServerTheme(theme) {
    if (override() === "auto") apply(theme);
  }
  // If a manual override is set, apply it immediately on load.
  const o = override();
  if (o !== "auto") apply(o);
  return { apply, override, setOverride, onServerTheme };
})();
