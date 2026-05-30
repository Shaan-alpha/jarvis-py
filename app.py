import argparse
import os
import subprocess
import sys
import threading
import time

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
    wait_until_done_or_barge_in
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

from core.ai.ollama_engine import (
    ask_llm
)

from core.memory.semantic_memory import (
    save_memory
)

from core.memory.profile_extractor import (
    extract_personal_info
)

from core.memory.profile_memory import (
    update_profile
)

from core.router.intent_router import (
    route_intent
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

from core.tasks.task_manager import (
    TaskManager
)

from core.tasks.task_parser import (
    parse_reminder
)

from core.hud import events

import config.settings as settings

from core.paths import is_frozen

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


def _run_intent_handler(handler, query):

    if handler.__name__ == "handle_browser":

        handler(query, speak, command)

    else:

        handler(query, speak)


def process_query(query, task_manager, source="voice"):
    """Route one recognized/typed query through the pipeline.

    `source` is "voice" or "text". Session/exit-word handling stays in the
    voice loop; this function only does profile capture, reminders, intent
    routing, the tool agent, and the LLM fallback.
    """

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

        speak(
            f"Reminder set for "
            f"{reminder['minutes']} minutes."
        )

        return

    handler = route_intent(query)

    if handler:

        try:

            logger.info(f"Intent Handler: {handler.__name__}")

            _run_intent_handler(handler, query)

        except Exception as e:

            logger.exception(f"Intent Error: {e}")

            speak(
                "Something went wrong "
                "while executing that command."
            )

        return

    events.emit("state", state="thinking")

    tool = decide_tool(query)

    if tool != "none":

        logger.info(f"Executed Tool: {tool}")

        response = execute_tool(tool)

        if response:

            speak(response)

        return

    logger.info("Generating LLM response")

    response = ask_llm(query)

    logger.info("LLM response generated")

    # ask_llm returns "" when it was superseded by a newer query (barge-in) or
    # could not reach Ollama; don't persist an empty turn.
    if response:

        save_memory(query, response)

        logger.info("Conversation saved to memory")


def _select_mic():
    """Pick an input device for the session. Returns False if none found."""

    result = check_microphone()

    if not result["ok"]:

        logger.error(result["detail"])

        print(result["detail"])

        return False

    settings.INPUT_DEVICE_INDEX = result["index"]

    return True


def _start_hud(session, task_manager, wizard=False):
    """Enable the HUD event bus, wire commands, start servers, spawn the UI."""

    from core.hud import ws_server, stats
    from core.speech.tts_queue import clear_queue

    events.enable()

    def _on_text_query(text):

        text = (text or "").lower().strip()

        if not text:

            return

        # Barge-in: a new typed query interrupts whatever Jarvis is currently
        # saying. Stop the current utterance and drop anything still queued so
        # the new answer doesn't play behind the old one.
        stop_speaking()

        clear_queue()

        session.activate()

        # Run off the WS thread so a slow generation doesn't block the socket
        # (and so the next typed query can interrupt this one). ask_llm's
        # generation token ensures a superseded stream abandons itself.
        threading.Thread(
            target=process_query,
            args=(text, task_manager),
            kwargs={"source": "text"},
            daemon=True,
        ).start()

    def _on_wake():

        session.activate()

        speak("Yes Boss?")

    def _on_stop():

        stop_speaking()

        clear_queue()

    def _on_run_checks():

        for result in run_checks():

            events.emit("check", **result)

    def _on_pull_model(model):

        # `ollama pull` runs for minutes; doing it inline would block the WS
        # asyncio loop (and the broadcaster), so the queued pull_progress events
        # would not stream live. Run it off-thread and signal completion.
        def _pull():

            try:

                pull_model(
                    model,
                    on_progress=lambda line: events.emit("pull_progress", line=line)
                )

            finally:

                # Always signal completion, even if the pull raised — otherwise
                # the wizard's pull log strands with no "done" transition.
                events.emit("pull_done")

        threading.Thread(target=_pull, daemon=True).start()

    def _on_save_name(name):

        update_profile("name", name or "Boss")

        events.emit("setup_complete")

    ws_server.register_handlers(
        text_query=_on_text_query,
        wake=_on_wake,
        stop=_on_stop,
        run_checks=_on_run_checks,
        pull_model=_on_pull_model,
        save_name=_on_save_name,
    )

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

            events.emit("state", state="listening")

            query = command()

            if query == "none":

                if session.is_expired():

                    logger.info("Session expired")

                    speak("Going back to sleep.")

                    session.deactivate()

                    events.emit("state", state="idle")

                continue

            query = query.lower().strip()

            logger.info(f"User Query: {query}")

            print(f"\nUser: {query}")

            events.emit("transcript", role="user", text=query)

            session.update_interaction()

            if any(
                word in query
                for word in EXIT_WORDS
            ):

                logger.info("Session manually ended")

                stop_speaking()

                speak("Going back to sleep.")

                session.deactivate()

                events.emit("state", state="idle")

                continue

            process_query(query, task_manager)

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
