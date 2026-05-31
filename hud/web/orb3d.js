// orb3d.js — the hero: a WebGL 3D energy orb (Three.js). A bright core inside a
// rotating particle shell + wireframe, with an additive glow halo. Reacts to
// state (idle/listening/thinking/speaking), to mic level via audio(), and to
// the cursor (parallax). Exposes the same Orb interface app.js expects
// (setState, flash) plus audio(). Falls back to a CSS orb if WebGL is missing.
const Orb = (() => {
  const mount = document.getElementById("orb");

  let state = "idle";
  let flashUntil = 0;
  let audioTarget = 0;   // latest mic level (decays)
  let audioLevel = 0;    // smoothed

  function setState(s) { state = s; }
  function flash() { flashUntil = performance.now() + 320; }
  function audio(rms) { audioTarget = Math.max(audioTarget, Math.min(1, rms || 0)); }

  function cssColor(name, fallback) {
    const v = getComputedStyle(document.documentElement)
      .getPropertyValue(name).trim();
    return v || fallback;
  }

  // ---- WebGL availability ------------------------------------------------
  let webgl = false;
  try {
    const probe = document.createElement("canvas");
    webgl = !!(window.THREE &&
      (probe.getContext("webgl") || probe.getContext("experimental-webgl")));
  } catch (e) { webgl = false; }

  if (!webgl) return cssFallback();

  // ---- Three.js scene ----------------------------------------------------
  try {
    const W = mount.clientWidth || 150;
    const H = mount.clientHeight || 150;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
    camera.position.z = 3.4;

    const group = new THREE.Group();
    scene.add(group);

    const colCore = new THREE.Color(cssColor("--accent", "#8be9ff"));
    const colShell = new THREE.Color(cssColor("--accent2", "#1aa0e6"));

    // Bright unlit core (no lights needed).
    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.62, 2),
      new THREE.MeshBasicMaterial({ color: colCore })
    );
    group.add(core);

    // Wireframe shell.
    const wire = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.96, 1),
      new THREE.MeshBasicMaterial({
        color: colShell, wireframe: true, transparent: true, opacity: 0.5
      })
    );
    group.add(wire);

    // Particle shell — points spread on a sphere (fibonacci), additive glow.
    const N = 520;
    const pos = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const phi = i * Math.PI * (3 - Math.sqrt(5));
      pos[i * 3] = Math.cos(phi) * r;
      pos[i * 3 + 1] = y;
      pos[i * 3 + 2] = Math.sin(phi) * r;
    }
    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({
      color: colCore,
      size: 0.05,
      map: dotTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    }));
    particles.scale.setScalar(1.18);
    group.add(particles);

    // Additive glow halo (a camera-facing sprite with a radial gradient).
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture(),
      color: colShell,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }));
    glow.scale.setScalar(3.4);
    scene.add(glow);

    // Mouse parallax.
    let mx = 0, my = 0;
    window.addEventListener("mousemove", (e) => {
      mx = (e.clientX / window.innerWidth) - 0.5;
      my = (e.clientY / window.innerHeight) - 0.5;
    });

    let colorTick = 0;

    function frame() {
      // Smooth the audio envelope; target decays so it tracks the live level.
      audioTarget *= 0.90;
      audioLevel += (audioTarget - audioLevel) * 0.25;

      // State drives base energy.
      let spin = 0.4, scale = 1.0, glowI = 0.55, wireOp = 0.35;
      if (state === "listening")      { spin = 0.9; scale = 1.06; glowI = 0.8;  wireOp = 0.55; }
      else if (state === "thinking")  { spin = 1.8; scale = 1.04; glowI = 0.9;  wireOp = 0.7; }
      else if (state === "speaking")  { spin = 1.4; scale = 1.10; glowI = 1.1;  wireOp = 0.8; }
      else                            { spin = 0.4; scale = 1.0;  glowI = 0.55; wireOp = 0.3; }

      const boost = audioLevel * 0.6 +
        (performance.now() < flashUntil ? 0.25 : 0);
      const targetScale = scale + boost;

      group.rotation.y += 0.004 * spin;
      group.rotation.x += 0.0016 * spin;
      particles.rotation.y -= 0.006 * spin;
      wire.rotation.y -= 0.003 * spin;

      group.scale.x += (targetScale - group.scale.x) * 0.12;
      group.scale.y = group.scale.z = group.scale.x;

      wire.material.opacity += (wireOp - wire.material.opacity) * 0.1;
      const gScale = 3.2 + glowI * 0.9 + boost;
      glow.scale.x += (gScale - glow.scale.x) * 0.1;
      glow.scale.y = glow.scale.x;
      glow.material.opacity = 0.5 + glowI * 0.35;

      // Parallax — ease the orb toward the cursor for a tactile 3D feel.
      group.position.x += ((mx * 0.5) - group.position.x) * 0.06;
      group.position.y += ((-my * 0.4) - group.position.y) * 0.06;

      // Refresh theme colours a few times a second (cheap, not every frame).
      if (++colorTick % 30 === 0) {
        colCore.set(cssColor("--accent", "#8be9ff"));
        colShell.set(cssColor("--accent2", "#1aa0e6"));
        core.material.color.copy(colCore);
        particles.material.color.copy(colCore);
        wire.material.color.copy(colShell);
        glow.material.color.copy(colShell);
      }

      renderer.render(scene, camera);
      requestAnimationFrame(frame);
    }
    frame();

    return { setState, flash, audio };
  } catch (e) {
    return cssFallback();
  }

  // ---- helpers -----------------------------------------------------------
  function dotTexture() {
    const c = document.createElement("canvas");
    c.width = c.height = 64;
    const g = c.getContext("2d");
    const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grd.addColorStop(0, "rgba(255,255,255,1)");
    grd.addColorStop(0.4, "rgba(255,255,255,0.6)");
    grd.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grd;
    g.fillRect(0, 0, 64, 64);
    const tex = new THREE.Texture(c);
    tex.needsUpdate = true;
    return tex;
  }

  function glowTexture() {
    const c = document.createElement("canvas");
    c.width = c.height = 256;
    const g = c.getContext("2d");
    const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    grd.addColorStop(0, "rgba(255,255,255,0.9)");
    grd.addColorStop(0.25, "rgba(255,255,255,0.35)");
    grd.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grd;
    g.fillRect(0, 0, 256, 256);
    const tex = new THREE.Texture(c);
    tex.needsUpdate = true;
    return tex;
  }

  // CSS-only fallback orb (no WebGL): a layered glowing disc that pulses.
  function cssFallback() {
    if (mount) {
      mount.classList.add("orb-fallback");
      const update = () => {
        mount.dataset.state = state;
        requestAnimationFrame(update);
      };
      update();
    }
    return { setState, flash, audio };
  }
})();
