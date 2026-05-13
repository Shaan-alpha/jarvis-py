# pyrefly: ignore [missing-import]
from core.actions.system_actions import (
    open_calculator,
    volume_up,
    volume_down,
    mute_volume
)


def execute_tool(tool_name):

    if tool_name == "open_calculator":

        open_calculator()

        return "Opening calculator."

    elif tool_name == "increase_volume":

        volume_up()

        return "Increasing volume."

    elif tool_name == "decrease_volume":

        volume_down()

        return "Decreasing volume."

    elif tool_name == "mute_volume":

        mute_volume()

        return "Muting volume."

    return "Unknown tool."