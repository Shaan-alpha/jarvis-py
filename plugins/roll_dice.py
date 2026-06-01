import random

from core.agent.registry import (
    tool
)


@tool(
    "roll_dice",
    "Roll an N-sided die",
    params={
        "sides": {
            "type": "int",
            "required": False,
            "default": 6,
            "desc": "number of sides",
        }
    },
)
def roll_dice(sides=6):

    return f"You rolled a {random.randint(1, sides)} on a {sides}-sided die."
