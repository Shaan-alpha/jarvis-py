// waveform.js — bar waveform fed by `level` events, decays when idle.
const Waveform = (() => {
  const canvas = document.getElementById("wave");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const N = 24;
  const bars = new Array(N).fill(0);

  function accent() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue("--accent2").trim() || "#1aa0e6";
  }

  function push(rms) {
    bars.push(Math.max(0, Math.min(1, rms)));
    if (bars.length > N) bars.shift();
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const bw = W / N;
    ctx.fillStyle = accent();
    for (let i = 0; i < bars.length; i++) {
      bars[i] *= 0.92; // decay
      const h = Math.max(2, bars[i] * H);
      ctx.fillRect(i * bw + 1, (H - h) / 2, bw - 2, h);
    }
    requestAnimationFrame(draw);
  }
  draw();
  return { push };
})();
