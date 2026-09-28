import argparse
import os
import re
import subprocess
import sys
import threading
import time

from functools import partial

from config.settings import (
    SESSION_TIMEOUT
)

from core.speech.engine import (
    speak,
    speak_sync,
    command,
    stop_speaking
)

from core.speech.tts_queue import (
    start_tts_queue,
    stop_tts_queue,
    wait_until_done_or_barge_in,
    clear_queue
)

from core.speech.openwakeword_listener import (
    detect_wake_word
)

from core.utils.helpers import (
    wishMe
)

from core.utils.logger import (
    logger
)

from core.utils import metrics

from core.ai.ollama_engine import (
    ask_llm,
    cancel_generation
)

from core.memory.profile_extractor import (
    extract_personal_info
)

from core.memory.profile_memory import (
    update_profile
)

from core.router.intent_router import (
    resolve_keyword_tool
)

from core.state.session_manager import (
    SessionManager
)

from core.agent.tool_agent import (
    decide_tool
)

from core.agent.tool_executor import (
    execute_tool
)

from core.agent.loader import (
    init_tools
)

from core.tasks.task_manager import (
    TaskManager
)

from core.tasks.task_parser import (
    duration_words,
    parse_reminder
)

from core.speech.reply import (
    respond
)

from core.state.conversation import (
    conversation,
    is_no,
    is_yes,
    match_command
)

from core.hud import events

import config.settings as settings

from core.paths import is_frozen

from core.text import normalize

from core.warmup import warm_start

from core.setup.checks import check_microphone

from core.setup.first_run import (
    is_first_run,
    run_checks,
    pull_model,
)


EXIT_WORDS = [
    "bye",
    "goodbye",
    "exit",
    "shutdown",
    "stop listening",
]


# Whole words only. Plain substring containment ended the session on ordinary
# speech that merely contains an exit word ("i exited the app" -> "exit"), so
# Jarvis went quiet mid-conversation instead of answering.
_EXIT_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in EXIT_WORDS) + r")\b"
)


def is_exit_command(query):
    """True when the utterance explicitly ends the session."""

    return _EXIT_PATTERN.search(query) is not None


def _spawn(target, *args, **kwargs):
    """Run `target` on a daemon thread. A seam, so tests can run it inline."""

    thread = threading.Thread(
        target=target,
        args=args,
        kwargs=kwargs,
        daemon=True,
    )

    thread.start()

    return thread


def _reply(raw_query, value):
    """Speak + show one reply and remember it for follow-ups."""

    reply = respond(value)

    if reply is not None:

        conversation.add_turn(raw_query, reply.say)

    return reply


def _handle_pending(query, raw_query):
    """A pending confirmation: 'yes' runs it, 'no' cancels it, anything else
    lets it lapse (and the query routes normally). True when consumed."""

    if not conversation.has_pending():

        return False

    action = conversation.take_pending()

    if action is None:

        return False

    if is_yes(query):

        _reply(raw_query, action.run())

        return True

    if is_no(query):

        _reply(raw_query, "Cancelled.")

        return True

    logger.info(f"Confirmation for {action.description!r} lapsed")

    return False


def _handle_conversation(query):
    """'repeat that' / 'tell me more'. True when handled."""

    command = match_command(query)

    if command == "repeat":

        respond(conversation.last_reply or "I haven't said anything yet.")

        return True

    if command != "more":

        return False

    last = conversation.last_query

    if not last:

        respond("Tell me more about what?")

        return True

    events.emit("state", state="thinking")

    response = ask_llm(last, detailed=True)

    if response:

        conversation.add_turn(last, response)

    return True


def process_query(query, task_manager, source="voice", raw_query=None):
    """Route one recognized/typed query through the pipeline.

    `source` is "voice" or "text". `query` is normalized (lowercased) for
    matching; `raw_query` is the original utterance (defaults to `query`) and is
    passed to the routers so content tools (write_clipboard/write_file/search)
    keep their original case. Session/exit-word handling stays in the voice
    loop; this function only does profile capture, reminders, intent routing,
    the tool agent, and the LLM fallback.
    """

    if raw_query is None:

        raw_query = query

    # Start the per-turn latency timeline; end_turn() in the finally logs the
    # stage summary and emits a HUD metrics event on every exit path.
    metrics.start_turn(source)

    try:

        if _handle_pending(query, raw_query):

            return

        if _handle_conversation(query):

            return

        personal_info = extract_personal_info(query)

        if personal_info:

            update_profile(
                personal_info["key"],
                personal_info["value"]
            )

            logger.info(f"Profile Updated: {personal_info}")

        reminder = parse_reminder(query)

        if reminder:

            task_manager.add_reminder_in_minutes(
                reminder["minutes"],
                reminder["message"]
            )

            logger.info(f"Reminder Created: {reminder}")

            _reply(
                raw_query,
                f"Reminder set for {duration_words(reminder['minutes'])}."
            )

            return

        call = resolve_keyword_tool(query, raw_query)

        if call is None:

            # Only the LLM path needs "thinking" — the keyword path is instant.
            events.emit("state", state="thinking")

            call = decide_tool(query, raw_query)

        metrics.mark("routed")

        if call is not None:

            logger.info(f"Executed Tool: {call.name} args={call.args}")

            _reply(raw_query, execute_tool(call))

            return

        events.emit("state", state="thinking")

        logger.info("Generating LLM response")

        # The raw text: case and punctuation help the model understand.
        response = ask_llm(raw_query)

        logger.info("LLM response generated")

        # ask_llm returns "" when it was superseded by a newer query (barge-in)
        # or could not reach Ollama; don't record an empty turn.
        if response:

            conversation.add_turn(raw_query, response)

    finally:

        metrics.end_turn()


def _select_mic():
    """Pick an input device for the session. Returns False if none found."""

    result = check_microphone()

    if not result["ok"]:

        logger.error(result["detail"])

        print(result["detail"])

        return False

    settings.INPUT_DEVICE_INDEX = result["index"]

    # Wake word listens on a WASAPI-preferred device, STT on an MME/DirectSound
    # one (see core.setup.checks); same mic, host best-suited to each consumer.
    settings.WAKE_DEVICE_INDEX = result.get("wake_index", result["index"])

    logger.info(
        f"Mic: STT device {settings.INPUT_DEVICE_INDEX}, "
        f"wake device {settings.WAKE_DEVICE_INDEX}"
    )

    return True


def _hud_on_text_query(session, task_manager, text):

    logger.info(f"HUD text query received: {text!r}")

    # Keep the raw text (case + punctuation) for content tools; the lowercased
    # copy is only used for command matching.
    raw = (text or "").strip()

    query = normalize(raw)

    if not query:

        return

    # Barge-in: a new typed query interrupts whatever Jarvis is currently
    # saying. Stop the current utterance and drop anything still queued so the
    # new answer doesn't play behind the old one.
    logger.info("Barge-in: cancel generation + stop_speaking + clear_queue")

    cancel_generation()

    stop_speaking()

    clear_queue()

    session.activate()

    # Off the WS thread so a slow generation doesn't block the socket (and so
    # the next typed query can interrupt this one).
    _spawn(process_query, query, task_manager, source="text", raw_query=raw)


def _hud_on_wake(session):

    session.activate()

    speak("Yes Boss?")


def _hud_on_stop():

    # Cancel first: stopping the voice alone let the stream keep queueing the
    # rest of the answer, which then played on.
    cancel_generation()

    stop_speaking()

    clear_queue()


def _hud_on_shutdown(task_manager):
    """Full shutdown from the HUD close button: stop the background services
    (TTS playback + queue, reminders) and hard-exit the process. The HUD closes
    its own window separately, so the backend and HUD both terminate and nothing
    is left running (the mic is released)."""

    logger.info("HUD requested shutdown; stopping services and exiting")

    try:

        stop_speaking()

        clear_queue()

        stop_tts_queue()

        task_manager.stop()

    except Exception:

        logger.exception("Error during shutdown cleanup")

    # Hard exit: the voice loop is a blocking while-True (on the main thread when
    # not frozen), so there's no clean signal to unwind it from this WS-thread
    # handler. Services are stopped above; os._exit takes the rest of the threads.
    os._exit(0)


def _hud_on_run_checks():

    for result in run_checks():

        events.emit("check", **result)


def _hud_on_pull_model(_requested=None):

    # Always the configured model: the page's value is only a label, and
    # trusting it would let any WS client choose what gets downloaded.
    model = settings.MODEL_NAME

    # `ollama pull` runs for minutes; off-thread so progress streams live
    # instead of blocking the WS asyncio loop.
    def _pull():

        try:

            pull_model(
                model,
                on_progress=lambda line: events.emit("pull_progress", line=line)
            )

        finally:

            # Always signal completion, even if the pull raised — otherwise the
            # wizard's pull log strands with no "done" transition.
            events.emit("pull_done")

    _spawn(_pull)


def _hud_on_save_name(name):

    from core.hud import ws_server

    update_profile("name", name or "Boss")

    # Setup is done: a reconnecting or reloaded HUD must not reopen the wizard.
    ws_server.set_wizard_mode(False)

    events.emit("setup_complete")


def _hud_handlers(session, task_manager):
    """Build the HUD WebSocket command handlers, bound to this session. Handlers
    are module-level functions wired here via partial so _start_hud stays flat."""

    return {
        "text_query": partial(_hud_on_text_query, session, task_manager),
        "wake": partial(_hud_on_wake, session),
        "stop": _hud_on_stop,
        "shutdown": partial(_hud_on_shutdown, task_manager),
        "run_checks": _hud_on_run_checks,
        "pull_model": _hud_on_pull_model,
        "save_name": _hud_on_save_name,
    }


def _start_hud(session, task_manager, wizard=False):
    """Enable the HUD event bus, wire commands, start servers, spawn the UI."""

    from core.hud import ws_server, stats

    events.enable()

    ws_server.register_handlers(**_hud_handlers(session, task_manager))

    # Carry the wizard flag in the WS `ready` handshake so a slow-starting HUD
    # that connects after _start_hud runs still opens the wizard (a one-shot
    # show_wizard broadcast would race the client connecting).
    ws_server.set_wizard_mode(wizard)

    ws_server.start_in_thread()

    stats.start()

    if is_frozen():

        # Frozen = single process. pywebview's GUI loop MUST own the main
        # thread, so we cannot launch the window here (we're already past
        # main()'s setup). Signal main() to run the voice loop on a background
        # thread and call window.launch() itself on the main thread.
        return True

    subprocess.Popen(
        [sys.executable, "-m", "hud"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    return False


def _print_paths_report():
    """Print where bundled assets and writable data resolve, and whether the
    asset paths exist. A build diagnostic for verifying a frozen one-folder
    package finds its models + HUD UI. Prints; never raises for missing paths."""

    from core.paths import resource_dir, user_data_dir

    checks = [
        ("VOSK_MODEL_PATH", settings.VOSK_MODEL_PATH),
        ("WAKE_MODEL_PATH", settings.WAKE_MODEL_PATH),
        ("hud/web", os.path.join(str(resource_dir()), "hud", "web")),
    ]

    print(f"frozen:        {is_frozen()}")

    print(f"resource_dir:  {resource_dir()}")

    print(f"user_data_dir: {user_data_dir()}")

    all_ok = True

    for name, path in checks:

        exists = os.path.exists(path)

        all_ok = all_ok and exists

        print(f"  [{'OK' if exists else 'MISSING'}] {name}: {path}")

    print("RESULT: all bundled asset paths exist" if all_ok
          else "RESULT: MISSING bundled asset paths")


def main():

    logger.info("Starting Jarvis...")

    init_tools()

    parser = argparse.ArgumentParser(description="Jarvis voice assistant")

    parser.add_argument(
        "--hud",
        action="store_true",
        help="Launch the desktop HUD"
    )

    parser.add_argument(
        "--check-paths",
        action="store_true",
        help="Print resolved asset/data paths and exit (build diagnostic)"
    )

    args = parser.parse_args()

    if args.check_paths:

        _print_paths_report()

        return

    start_tts_queue()

    # Preload the LLM + embedder off-thread so the first real query isn't a cold
    # start; overlaps with the greeting and mic selection below. Best-effort.
    warm_start()

    time.sleep(1)

    # Greet synchronously so the startup banner finishes before the wake-word
    # loop (or HUD launch) can call stop_speaking() and cut it off. wishMe
    # previously used async speak() and got truncated, especially when frozen.
    wishMe(speak_sync)

    session = SessionManager(
        timeout=SESSION_TIMEOUT
    )

    task_manager = TaskManager()

    task_manager.start()

    logger.info("Task Manager Started")

    if not _select_mic():

        speak_sync("I can't find a microphone. Please connect one and relaunch.")

        stop_tts_queue()

        return

    first_run = is_first_run()

    hud_on_main_thread = False

    if args.hud or first_run:

        hud_on_main_thread = _start_hud(session, task_manager, wizard=first_run)

    if hud_on_main_thread:

        # Frozen + HUD: the voice loop runs on a daemon thread so the main
        # thread is free for pywebview's GUI loop (which it requires). Closing
        # the HUD window ends webview.start() and the process exits, taking the
        # daemon voice thread with it.
        from hud import window

        threading.Thread(
            target=_voice_loop,
            args=(session, task_manager),
            daemon=True,
        ).start()

        window.launch()

        stop_tts_queue()

        return

    _voice_loop(session, task_manager)


def _voice_loop(session, task_manager):

    while True:

        try:

            if not session.active:

                detect_wake_word()

                logger.info("Wake word activated")

                stop_speaking()

                speak("Yes Boss?")

                session.activate()

                events.emit("wake")

                continue

            if wait_until_done_or_barge_in():

                logger.info("Barge-in: user interrupted")

                cancel_generation()

            events.emit("state", state="listening")

            raw = command()

            if raw == "none":

                if session.is_expired():

                    logger.info("Session expired")

                    speak("Going back to sleep.")

                    session.deactivate()

                    conversation.clear()

                    events.emit("state", state="idle")

                continue

            query = normalize(raw)

            if not query:

                continue

            logger.info(f"User Query: {raw}")

            print(f"\nUser: {raw}")

            events.emit("transcript", role="user", text=raw)

            session.update_interaction()

            if is_exit_command(query):

                logger.info("Session manually ended")

                stop_speaking()

                speak("Going back to sleep.")

                session.deactivate()

                conversation.clear()

                events.emit("state", state="idle")

                continue

            process_query(query, task_manager, raw_query=raw)

        except KeyboardInterrupt:

            logger.info("Jarvis shutting down gracefully")

            print("\nShutting down Jarvis gracefully...")

            stop_tts_queue()

            stop_speaking()

            break

        except Exception as e:

            logger.exception(f"Main Loop Error: {e}")

            time.sleep(1)


if __name__ == "__main__":

    main()

    sys.exit()
