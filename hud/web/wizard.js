// wizard.js — first-run setup panel (global Wizard object used by app.js).
window.Wizard = (() => {
  const MAX_LOG = 2000;
  const $ = (id) => document.getElementById(id);
  let model = "phi3";

  function setModel(name, size) {
    model = name || model;
    $("wizard-pull").textContent = "Pull " + model + (size ? " (" + size + ")" : "");
  }

  function refreshStartGate() {
    $("wizard-start").disabled = $("wizard-checks").querySelectorAll(".check-fail").length > 0;
  }

  function runChecks(send) {
    $("wizard-checks").innerHTML = "";
    $("wizard-pull").classList.add("hidden");
    refreshStartGate();
    send({ type: "run_checks" });
  }

  function showWizard(send) {
    $("wizard").classList.remove("hidden");
    document.body.classList.add("wizard-open");
    runChecks(send);
  }

  function onCheck(result) {
    const li = document.createElement("li");
    li.textContent = result.detail || result.name;
    li.className = result.ok ? "check-ok" : "check-fail";
    $("wizard-checks").appendChild(li);
    if (result.name === "model" && !result.ok) $("wizard-pull").classList.remove("hidden");
    refreshStartGate();
  }

  function onPullProgress(line) {
    const log = $("wizard-pull-log");
    log.classList.remove("hidden");
    log.textContent = (log.textContent + "\n" + line).slice(-MAX_LOG);
    log.scrollTop = log.scrollHeight;
  }

  function onPullDone(send) {
    $("wizard-pull-log").classList.add("hidden");
    $("wizard-pull-log").textContent = "";
    runChecks(send);
  }

  function onSetupComplete() {
    $("wizard").classList.add("hidden");
    document.body.classList.remove("wizard-open");
  }

  function wireButtons(send) {
    $("wizard-pull").addEventListener("click", () => send({ type: "pull_model", model }));
    $("wizard-recheck").addEventListener("click", () => runChecks(send));
    $("wizard-form").addEventListener("submit", (e) => {
      e.preventDefault();
      if ($("wizard-start").disabled) return;
      send({ type: "save_name", name: ($("wizard-name").value || "").trim() });
    });
  }

  return { setModel, showWizard, onCheck, onPullProgress, onPullDone, onSetupComplete, wireButtons };
})();
