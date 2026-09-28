// theme.js — applies the time-of-day theme (from the URL fragment on first
// paint, then server events); a manual override persists locally.
const Theme = (() => {
  const KEY = "jarvis-theme-override"; // "auto" | "cyan" | "gold" | "frost"
  const THEMES = ["cyan", "gold", "frost"];

  function apply(theme) {
    if (THEMES.includes(theme)) document.documentElement.setAttribute("data-theme", theme);
  }
  function override() {
    try { return localStorage.getItem(KEY) || "auto"; } catch (e) { return "auto"; }
  }
  function setOverride(value) {
    try { localStorage.setItem(KEY, value); } catch (e) { /* storage unavailable */ }
  }
  function onServerTheme(theme) {
    if (override() === "auto") apply(theme);
  }

  const chosen = override();
  if (chosen !== "auto") apply(chosen);
  else apply(new URLSearchParams(location.hash.replace(/^#/, "")).get("theme"));

  return { apply, override, setOverride, onServerTheme };
})();
