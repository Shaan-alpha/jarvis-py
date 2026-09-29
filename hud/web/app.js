// app.js — connect to the Jarvis core, render its events, send commands.
(() => {
  const params = new URLSearchParams(location.hash.replace(/^#/, ""));
  const WS_URL = params.get("ws") || new URLSearchParams(location.search).get("ws") || "ws://127.0.0.1:8765";
  const LABELS = { idle: "Say “Hey Jarvis”", listening: "Listening…", thinking: "Thinking…", speaking: "Speaking" };
  const HISTORY_MAX = 20;

  const $ = (id) => document.getElementById(id);
  const body = document.body;
  const pill = $("pill");
  const capUser = $("cap-user");
  const capJarvis = $("cap-jarvis");
  const caps = document.querySelector(".caps");
  const chip = $("chip");
  const chipModel = $("chip-model");
  const form = $("form");
  const input = $("input");
  const toast = $("toast");

  let ws = null;
  let backoff = 500;
  let failures = 0;
  let ignoreTokens = false;   // set by Stop: drop tokens already in flight
  let toastTimer = null;
  const history = [];
  let historyIndex = -1;

  function setState(state) {
    body.dataset.state = state;
    if (body.dataset.link === "up") pill.textContent = LABELS[state] || state;
    if (window.Orb) Orb.setState(state);
  }

  function setLink(up) {
    body.dataset.link = up ? "up" : "down";
    pill.textContent = up ? (LABELS[body.dataset.state] || "") : "Connecting…";
  }

  function refreshCaps() {
    const has = !!(capUser.textContent || capJarvis.textContent);
    caps.classList.toggle("filled", has);
    body.classList.toggle("has-caps", has);
  }

  // Keep the newest text in view, unless the user scrolled up to read.
  function follow() {
    if (caps.scrollHeight - caps.scrollTop - caps.clientHeight < 32) caps.scrollTop = caps.scrollHeight;
  }

  function popIn(el) {
    el.classList.remove("pop");
    void el.offsetWidth;
    el.classList.add("pop");
  }

  function showUser(text) {
    ignoreTokens = false;
    capUser.textContent = text;
    capJarvis.textContent = "";
    capJarvis.classList.remove("err");
    popIn(capUser);
    refreshCaps();
    caps.scrollTop = 0;
  }

  function showReply(text, isError) {
    if (!capJarvis.textContent) popIn(capJarvis);
    capJarvis.textContent = text;
    capJarvis.classList.toggle("err", !!isError);
    refreshCaps();
    follow();
  }

  function showToast(text) {
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.hidden = true; }, 8000);
  }

  function showStats(evt) {
    chipModel.textContent = evt.model || "—";
    chip.classList.toggle("online", !!evt.online);
    const battery = evt.battery_pct == null
      ? "no battery"
      : Math.round(evt.battery_pct) + "%" + (evt.charging ? " charging" : "");
    chip.title = (evt.online ? "Online" : "Offline") + " · CPU " + Math.round(evt.cpu) + "% · " + battery;
  }

  function onReady(evt) {
    setLink(true);
    failures = 0;
    if (evt.state) setState(evt.state);
    if (evt.theme) Theme.onServerTheme(evt.theme);
    if (evt.model) chipModel.textContent = evt.model;
    if (evt.model && window.Wizard) Wizard.setModel(evt.model, evt.model_size);
    if (evt.wizard && window.Wizard) Wizard.showWizard(send);
  }

  function onToken(text) {
    if (ignoreTokens) return;
    if (!capJarvis.textContent) popIn(capJarvis);
    capJarvis.classList.remove("err");
    capJarvis.textContent += text;
    refreshCaps();
    follow();
  }

  function handle(evt) {
    switch (evt.type) {
      case "ready": onReady(evt); break;
      case "state": setState(evt.state); break;
      case "wake": if (window.Orb) Orb.flash(); break;
      case "transcript": showUser(evt.text); break;
      case "assistant_token": onToken(evt.text); break;
      case "assistant_done": if (!ignoreTokens && evt.full_text) showReply(evt.full_text, false); break;
      case "error": showReply(evt.message, true); break;
      case "reminder_fired": showToast("⏰ " + evt.message); break;
      case "theme": Theme.onServerTheme(evt.theme); break;
      case "level": if (window.Orb) Orb.audio(evt.rms); break;
      case "stats": showStats(evt); break;
      case "check": if (window.Wizard) Wizard.onCheck(evt); break;
      case "pull_progress": if (window.Wizard) Wizard.onPullProgress(evt.line); break;
      case "pull_done": if (window.Wizard) Wizard.onPullDone(send); break;
      case "setup_complete": if (window.Wizard) Wizard.onSetupComplete(); break;
    }
  }

  function isOpen() {
    return !!ws && ws.readyState === WebSocket.OPEN;
  }

  function send(obj) {
    if (!isOpen()) return false;
    ws.send(JSON.stringify(obj));
    return true;
  }

  function connect() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => { backoff = 500; };
    ws.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (e) { /* ignore bad event */ } };
    ws.onclose = () => {
      setLink(false);
      failures += 1;
      if (failures === 5) {
        showReply("Can't reach the Jarvis core at " + WS_URL + ". Is another Jarvis already running?", true);
      }
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 5000);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) { /* already closed */ } };
  }

  function stop() {
    ignoreTokens = true;
    send({ type: "stop" });
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    if (!isOpen()) {
      // Keep the text so it isn't lost; say why nothing happened.
      showReply("Jarvis core is not running.", true);
      return;
    }
    showUser(text);
    send({ type: "text_query", text });
    history.unshift(text);
    history.length = Math.min(history.length, HISTORY_MAX);
    historyIndex = -1;
    input.value = "";
  });

  $("stop").addEventListener("click", stop);

  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" && historyIndex + 1 < history.length) {
      historyIndex += 1;
      input.value = history[historyIndex];
      e.preventDefault();
    } else if (e.key === "ArrowDown" && historyIndex >= 0) {
      historyIndex -= 1;
      input.value = historyIndex >= 0 ? history[historyIndex] : "";
      e.preventDefault();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (input.value) input.value = "";   // first Esc clears the box
    else stop();                          // then Esc stops speech
  });

  $("min").addEventListener("click", () => {
    if (window.pywebview && pywebview.api) pywebview.api.minimize();
  });

  // Close: tell the core to shut down (releases the mic, stops every thread),
  // then close this window so the HUD process exits too.
  $("close").addEventListener("click", () => {
    send({ type: "shutdown" });
    setTimeout(() => {
      if (window.pywebview && pywebview.api) pywebview.api.quit();
    }, 180);
  });

  // Pause the orb's animations while the window is hidden/minimized.
  document.addEventListener("visibilitychange", () => body.classList.toggle("paused", document.hidden));

  window.addEventListener("focus", () => input.focus());

  connect();
  if (window.Wizard) Wizard.wireButtons(send);
  input.focus();
})();
