"""One path for every reply: queue it for speech and show it in the HUD.

Tool results, reminder confirmations and fired reminders all come through here,
so the HUD caption and orb state match what Jarvis says, and the voice loop's
wait-for-speech covers them (the mic no longer opens over Jarvis's own voice).
"""

from core.agent.registry import (
    Reply
)

from core.hud import events

from core.speech.tts_queue import (
    add_to_queue
)


def as_reply(value):
    """A tool result (str or Reply) as a Reply; None stays None."""

    if value is None:

        return None

    if isinstance(value, Reply):

        return value

    text = str(value)

    return Reply(say=text, show=text)


def respond(value):
    """Show `value` in the HUD and queue it for speech. Returns the Reply, or
    None when there was nothing to say."""

    reply = as_reply(value)

    if reply is None or not (reply.say or reply.show):

        return None

    events.emit("assistant_done", full_text=reply.show or reply.say)

    if reply.say:

        add_to_queue(reply.say)

    return reply


def announce_reminder(message):
    """A reminder fired: toast it in the HUD and queue it behind any reply
    (speak() used to cut off whatever Jarvis was saying)."""

    events.emit("reminder_fired", message=message)

    add_to_queue(f"Reminder. {message}")
