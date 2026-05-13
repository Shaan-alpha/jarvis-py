import sys
import time

from config.settings import (
    SESSION_TIMEOUT
)

from core.speech.engine import (
    speak,
    command,
    stop_speaking
)

from core.speech.openwakeword_listener import (
    detect_wake_word
)

from core.speech.tts_queue import (
    start_tts_queue,
    stop_tts_queue
)

from core.utils.helpers import (
    wishMe
)

from core.ai.ollama_engine import (
    ask_llm
)

from core.memory.semantic_memory import (
    save_memory
)

from core.router.intent_router import (
    route_intent
)

from core.state.session_manager import (
    SessionManager
)

# pyrefly: ignore [missing-import]
from core.agent.tool_agent import (
    decide_tool
)

# pyrefly: ignore [missing-import]
from core.tools.tool_executor import (
    execute_tool
)


EXIT_WORDS = [
    "bye",
    "goodbye",
    "exit",
    "shutdown",
    "stop listening",
]


def main():

    wishMe(speak)

    start_tts_queue()

    time.sleep(1)

    session = SessionManager(
        timeout=SESSION_TIMEOUT
    )

    while True:

        try:

            # -------------------- #
            # SLEEP MODE
            # -------------------- #

            if not session.active:

                if detect_wake_word():

                    stop_speaking()

                    speak("Yes Boss?")

                    session.activate()

                continue

            # -------------------- #
            # ACTIVE SESSION MODE
            # -------------------- #

            stop_speaking()

            query = command()

            if query == "none":

                if session.is_expired():

                    speak("Going back to sleep.")

                    session.deactivate()

                continue

            print(f"\nUser: {query}")

            session.update_interaction()

            # -------------------- #
            # EXIT COMMANDS
            # -------------------- #

            if any(
                word in query
                for word in EXIT_WORDS
            ):

                stop_speaking()

                speak("Going back to sleep.")

                session.deactivate()

                continue

            # -------------------- #
            # AI TOOL AGENT
            # -------------------- #

            tool = decide_tool(query)

            if tool != "none":

                response = execute_tool(tool)

                speak(response)

                continue

            # -------------------- #
            # LEGACY INTENT ROUTER
            # -------------------- #

            handler = route_intent(query)

            if handler:

                try:

                    if (
                        handler.__name__
                        == "handle_browser"
                    ):

                        handler(
                            query,
                            speak,
                            command
                        )

                    else:

                        handler(
                            query,
                            speak
                        )

                except Exception as e:

                    print(
                        f"Intent Error: {e}"
                    )

                    speak(
                        "Something went wrong while executing that command."
                    )

                continue

            # -------------------- #
            # LLM FALLBACK
            # -------------------- #

            response = ask_llm(query)

            save_memory(
                query,
                response
            )

        except KeyboardInterrupt:

            print(
                "\nShutting down Jarvis gracefully..."
            )

            stop_tts_queue()

            stop_speaking()

            break

        except Exception as e:

            print(
                f"Main Loop Error: {e}"
            )

            time.sleep(1)


if __name__ == "__main__":

    main()

    sys.exit()