// app.js — connect to the core, render events, send commands.
(() => {
  const params = new URLSearchParams(location.search);
  const WS_URL = params.get("ws") || "ws://127.0.0.1:8765";

  const pill = document.getElementById("pill");
  const capUser = document.getElementById("cap-user");
  const capJarvis = document.getElementById("cap-jarvis");
  const stModel = document.getElementById("st-model");
  const stCpu = document.getElementById("st-cpu");
  const stBatt = document.getElementById("st-batt");
  const stNet = document.getElementById("st-net");
  const form = document.getElementById("form");
  const input = document.getElementById("input");

  let ws = null;
  let backoff = 500;

  function setState(state) {
    pill.textContent = state;
    if (window.Orb) Orb.setState(state);
  }

  function handle(evt) {
    switch (evt.type) {
      case "ready":
        if (evt.state) setState(evt.state);
        if (evt.theme) Theme.onServerTheme(evt.theme);
        break;
      case "state": setState(evt.state); break;
      case "wake": if (window.Orb) Orb.flash(); break;
      case "transcript":
        capUser.textContent = "You: " + evt.text;
        capJarvis.textContent = "";
        break;
      case "assistant_token":
        capJarvis.textContent += evt.text;
        break;
      case "assistant_done":
        if (evt.full_text) capJarvis.textContent = "Jarvis: " + evt.full_text;
        break;
      case "theme": Theme.onServerTheme(evt.theme); break;
      case "level": if (window.Waveform) Waveform.push(evt.rms); break;
      case "stats":
        stModel.textContent = evt.model || "—";
        stCpu.textContent = "CPU " + Math.round(evt.cpu) + "%";
        stBatt.textContent = evt.battery_pct == null
          ? "—" : Math.round(evt.battery_pct) + "%" + (evt.charging ? " ⚡" : "");
        stNet.textContent = evt.online ? "online" : "offline";
        break;
      case "reminder_fired":
        capJarvis.textContent = "Reminder: " + evt.message;
        break;
      case "error":
        capJarvis.textContent = "⚠ " + evt.message;
        break;
    }
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  function connect() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => { backoff = 500; };
    ws.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (e) {} };
    ws.onclose = () => {
      setState("idle");
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 5000);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    capUser.textContent = "You: " + text;
    capJarvis.textContent = "";
    send({ type: "text_query", text });
    input.value = "";
  });

  connect();
})();
