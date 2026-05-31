// orb.js — animated state orb on a <canvas>. Scales to the canvas size and
// reads the theme accent vars so it stays in sync with the time-of-day theme.
const Orb = (() => {
  const canvas = document.getElementById("orb");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, cx = W / 2, cy = H / 2;
  const R = Math.min(W, H) / 2;            // outer radius budget
  const core = R * 0.52;                   // base core radius
  let state = "idle";
  let flashUntil = 0;
  let t = 0;

  function accent() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--accent2").trim() || "#1aa0e6";
  }
  function accentLight() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--accent").trim() || "#9af0ff";
  }

  function setState(s) { state = s; }
  function flash() { flashUntil = performance.now() + 250; }

  function draw() {
    t += 0.05;
    ctx.clearRect(0, 0, W, H);

    // Radius pulse keyed to state.
    let r = core;
    if (state === "listening")      r = core + Math.sin(t * 3) * (R * 0.10);
    else if (state === "thinking")  r = core + Math.sin(t * 6) * (R * 0.06);
    else if (state === "speaking")  r = core + Math.sin(t * 9) * (R * 0.16);
    else                            r = core * 0.92 + Math.sin(t * 1.5) * (R * 0.05);
    if (performance.now() < flashUntil) r += R * 0.18;

    // Outer glow.
    const glow = ctx.createRadialGradient(cx, cy, r * 0.3, cx, cy, R);
    glow.addColorStop(0, accent());
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Core sphere with a soft top-left highlight for a glassy bead look.
    const body = ctx.createRadialGradient(
      cx - r * 0.35, cy - r * 0.35, r * 0.15, cx, cy, r
    );
    body.addColorStop(0, accentLight());
    body.addColorStop(0.55, accent());
    body.addColorStop(1, accent());
    ctx.fillStyle = body;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();

    // Orbiting arc while thinking.
    if (state === "thinking") {
      ctx.strokeStyle = accentLight();
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r + R * 0.18, t % (Math.PI * 2), (t % (Math.PI * 2)) + 1.5);
      ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
  return { setState, flash };
})();
