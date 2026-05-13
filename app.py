import sys
import time

from core.speech.engine import speak, command
from core.speech.wake_listener import detect_wake_word

from core.utils.helpers import wishMe

from core.llm.ollama_engine import ask_llm
from core.memory.memory_engine import save_memory

from core.router.intent_router import route_intent
from core.state.session_manager import SessionManager


EXIT_WORDS = [
    "bye",
    "goodbye",
    "exit",
    "shutdown",
    "stop listening",
]


def main():

    wishMe(speak)

    time.sleep(1)

    session = SessionManager(timeout=20)

    while True:

        try:

            # -------------------- #
            # SLEEP MODE
            # -------------------- #

            if not session.active:

                print("\nWaiting for wake word...")

                if detect_wake_word():

                    speak("Yes Boss?")

                    session.activate()

                continue

            # -------------------- #
            # ACTIVE SESSION MODE
            # -------------------- #

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

            if any(word in query for word in EXIT_WORDS):

                speak("Going back to sleep.")

                session.deactivate()

                continue

            # -------------------- #
            # ROUTE INTENTS
            # -------------------- #

            handler = route_intent(query)

            if handler:

                try:

                    # Browser intent special handling
                    if handler.__name__ == "handle_browser":

                        handler(query, speak, command)

                    else:

                        handler(query, speak)

                except Exception as e:

                    print(f"Intent Error: {e}")

                    speak(
                        "Something went wrong while executing that command."
                    )

                continue

            # -------------------- #
            # LLM FALLBACK
            # -------------------- #

            speak("Thinking")

            response = ask_llm(query)

            save_memory(query, response)

            print(f"Jarvis: {response}")

            speak(response)

        except KeyboardInterrupt:

            print("\nShutting down Jarvis gracefully...")

            break

        except Exception as e:

            print(f"Main Loop Error: {e}")

            time.sleep(1)


if __name__ == "__main__":

    main()

    sys.exit()