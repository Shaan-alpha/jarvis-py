// orb.js — drives the CSS fluid blob (Siri/ChatGPT-style). The visuals live in
// style.css (morphing, blurred, multi-colour gradient layers); this just feeds
// it a smoothed audio level (--level) and the current state, and exposes the
// Orb interface app.js expects: setState, flash, audio.
const Orb = (() => {
  const el = document.getElementById("orb");

  let audioTarget = 0;   // latest mic level (decays each frame)
  let audioLevel = 0;    // smoothed value pushed to --level
  let flashUntil = 0;

  function setState(s) { if (el) el.dataset.state = s; }
  function flash() { flashUntil = performance.now() + 320; }
  function audio(rms) { audioTarget = Math.max(audioTarget, Math.min(1, rms || 0)); }

  function tick() {
    audioTarget *= 0.90;
    audioLevel += (audioTarget - audioLevel) * 0.22;
    let level = audioLevel;
    if (performance.now() < flashUntil) level = Math.min(1, level + 0.4);
    if (el) el.style.setProperty("--level", level.toFixed(3));
    requestAnimationFrame(tick);
  }
  if (el) tick();

  return { setState, flash, audio };
})();
