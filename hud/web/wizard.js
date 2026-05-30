// wizard.js — first-run setup wizard panel (plain-script, global Wizard object).
// Attach to window.Wizard so app.js can call Wizard.showWizard(send), etc.
window.Wizard = (() => {
  const MAX_LOG = 2000;

  function _checksEl()  { return document.getElementById("wizard-checks"); }
  function _wizardEl()  { return document.getElementById("wizard"); }
  function _pullBtn()   { return document.getElementById("wizard-pull"); }
  function _pullLog()   { return document.getElementById("wizard-pull-log"); }
  function _startBtn()  { return document.getElementById("wizard-start"); }
  function _nameInput() { return document.getElementById("wizard-name"); }

  function _refreshStartGate() {
    var fails = _checksEl().querySelectorAll(".check-fail").length;
    _startBtn().disabled = fails > 0;
  }

  function showWizard(send) {
    _checksEl().innerHTML = "";
    _wizardEl().classList.remove("hidden");
    send({ type: "run_checks" });
  }

  function onCheck(result) {
    var li = document.createElement("li");
    li.textContent = result.detail || result.name;
    li.className = result.ok ? "check-ok" : "check-fail";
    _checksEl().appendChild(li);
    if (result.name === "model" && !result.ok) {
      _pullBtn().classList.remove("hidden");
    }
    _refreshStartGate();
  }

  function onPullProgress(line) {
    var log = _pullLog();
    log.classList.remove("hidden");
    log.textContent = (log.textContent + "\n" + line).slice(-MAX_LOG);
    log.scrollTop = log.scrollHeight;
  }

  function onPullDone(send) {
    _checksEl().innerHTML = "";
    _pullBtn().classList.add("hidden");
    _pullLog().classList.add("hidden");
    _pullLog().textContent = "";
    send({ type: "run_checks" });
  }

  function onSetupComplete() {
    _wizardEl().classList.add("hidden");
  }

  // Wire buttons once DOM is ready.
  function _wireButtons(send) {
    _pullBtn().addEventListener("click", function () {
      send({ type: "pull_model", model: "phi3" });
    });
    _startBtn().addEventListener("click", function () {
      var name = (_nameInput().value || "").trim();
      send({ type: "save_name", name: name });
    });
  }

  return {
    showWizard: showWizard,
    onCheck: onCheck,
    onPullProgress: onPullProgress,
    onPullDone: onPullDone,
    onSetupComplete: onSetupComplete,
    wireButtons: _wireButtons,
  };
})();
