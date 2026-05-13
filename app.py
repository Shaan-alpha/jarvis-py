import sys
import threading
import time

from config.settings import (
    SESSION_TIMEOUT
)

from core.speech.engine import (
    speak,
    command,
    stop_speaking
)

from core.speech.tts_queue import (
    start_tts_queue,
    stop_tts_queue
)

from core.speech.openwakeword_listener import (
    detect_wake_word
)

from core.speech.offline_recognizer import (
    warm_up as warm_up_offline
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


def main():

    logger.info("Starting Jarvis...")

    wishMe(speak)

    start_tts_queue()

    threading.Thread(
        target=warm_up_offline,
        daemon=True
    ).start()

    time.sleep(1)

    session = SessionManager(
        timeout=SESSION_TIMEOUT
    )

    task_manager = TaskManager()

    task_manager.start()

    logger.info("Task Manager Started")

    while True:

        try:

            if not session.active:

                detect_wake_word()

                logger.info("Wake word activated")

                stop_speaking()

                speak("Yes Boss?")

                session.activate()

                continue

            stop_speaking()

            query = command()

            if query == "none":

                if session.is_expired():

                    logger.info("Session expired")

                    speak("Going back to sleep.")

                    session.deactivate()

                continue

            query = query.lower().strip()

            logger.info(f"User Query: {query}")

            print(f"\nUser: {query}")

            session.update_interaction()

            if any(
                word in query
                for word in EXIT_WORDS
            ):

                logger.info("Session manually ended")

                stop_speaking()

                speak("Going back to sleep.")

                session.deactivate()

                continue

            personal_info = extract_personal_info(query)

            if personal_info:

                update_profile(
                    personal_info["key"],
                    personal_info["value"]
                )

                logger.info(
                    f"Profile Updated: {personal_info}"
                )

            reminder = parse_reminder(query)

            if reminder:

                task_manager.add_reminder_in_minutes(
                    reminder["minutes"],
                    reminder["message"]
                )

                logger.info(
                    f"Reminder Created: {reminder}"
                )

                speak(
                    f"Reminder set for "
                    f"{reminder['minutes']} minutes."
                )

                continue

            # -------------------- #
            # FAST PATH: keyword intent router
            # -------------------- #

            handler = route_intent(query)

            if handler:

                try:

                    logger.info(
                        f"Intent Handler: {handler.__name__}"
                    )

                    _run_intent_handler(handler, query)

                except Exception as e:

                    logger.exception(f"Intent Error: {e}")

                    speak(
                        "Something went wrong "
                        "while executing that command."
                    )

                continue

            # -------------------- #
            # SLOW PATH: LLM tool agent
            # -------------------- #

            tool = decide_tool(query)

            if tool != "none":

                logger.info(f"Executed Tool: {tool}")

                response = execute_tool(tool)

                if response:

                    speak(response)

                continue

            # -------------------- #
            # FALLBACK: LLM chat
            # -------------------- #

            logger.info("Generating LLM response")

            response = ask_llm(query)

            logger.info("LLM response generated")

            save_memory(query, response)

            logger.info("Conversation saved to memory")

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
