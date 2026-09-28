// orb.js — drives the CSS fluid orb: a smoothed audio level (--level) and the
// flow speed per state. The rAF loop only runs while there is something to
// animate, and state changes adjust playback rate instead of restarting the
// animations (changing animation-duration made the blobs jump).
const Orb = (() => {
  const el = document.getElementById("orb");
  const reduced = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  const RATES = { idle: 0.5, listening: 1.2, thinking: 1.8, speaking: 2.4 };

  let target = 0;
  let level = 0;
  let flashUntil = 0;
  let running = false;
  let state = "idle";

  function setState(next) {
    state = next;
    if (!el) return;
    el.dataset.state = next;
    const rate = RATES[next] || 1;
    if (el.getAnimations) el.getAnimations({ subtree: true }).forEach((a) => a.updatePlaybackRate(rate));
  }

  function flash() {
    flashUntil = performance.now() + 320;
    kick();
  }

  // Mic level. Ignored while idle: that's only room noise from the wake-word loop.
  function audio(rms) {
    if (state === "idle") return;
    target = Math.max(target, Math.min(1, rms || 0));
    kick();
  }

  function kick() {
    if (running || !el || reduced) return;
    running = true;
    requestAnimationFrame(tick);
  }

  function tick(now) {
    target *= 0.9;
    level += (target - level) * 0.22;
    const shown = now < flashUntil ? Math.min(1, level + 0.4) : level;
    if (shown < 0.002 && target < 0.002 && now >= flashUntil) {
      level = 0;
      el.style.setProperty("--level", "0");
      running = false;
      return;
    }
    el.style.setProperty("--level", shown.toFixed(3));
    requestAnimationFrame(tick);
  }

  setState("idle");
  return { setState, flash, audio };
})();
