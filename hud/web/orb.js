// orb.js — animated state orb on a <canvas>.
const Orb = (() => {
  const canvas = document.getElementById("orb");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, cx = W / 2, cy = H / 2;
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
    let base = 13;
    if (state === "listening") base = 13 + Math.sin(t * 3) * 2;
    else if (state === "thinking") base = 13 + Math.sin(t * 6) * 1.2;
    else if (state === "speaking") base = 14 + Math.sin(t * 9) * 3;
    else base = 12 + Math.sin(t * 1.5) * 1; // idle breathing
    if (performance.now() < flashUntil) base += 4;

    const grad = ctx.createRadialGradient(cx - 4, cy - 4, 2, cx, cy, base + 6);
    grad.addColorStop(0, accentLight());
    grad.addColorStop(0.5, accent());
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, base + 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = accent();
    ctx.beginPath();
    ctx.arc(cx, cy, base, 0, Math.PI * 2);
    ctx.fill();

    if (state === "thinking") {
      ctx.strokeStyle = accentLight();
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, base + 5, t % (Math.PI * 2), (t % (Math.PI * 2)) + 1.5);
      ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
  return { setState, flash };
})();
