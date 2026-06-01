# Jarvis plugins

Drop a `*.py` file in this folder (or in `%APPDATA%\JarvisAI\plugins` when
running the packaged app) and Jarvis picks up its tools on the next launch —
no core edits required.

## Contract

A plugin is any module that registers one or more tools with the `@tool`
decorator:

```python
import random

from core.agent.registry import tool


@tool(
    "roll_dice",                       # unique tool name (its words also act as
                                       # trigger keywords for the action gate)
    "Roll an N-sided die",             # description shown to the selector LLM
    params={                           # optional; omit for a parameterless tool
        "sides": {"type": "int", "required": False, "default": 6,
                  "desc": "number of sides"},
    },
)
def roll_dice(sides=6):
    return f"You rolled a {random.randint(1, sides)} on a {sides}-sided die."
```

- Supported param `type`s: `"str"`, `"int"`.
- The handler returns a short string Jarvis speaks back (or `None`).
- Files whose name starts with `_` are ignored.
- A plugin that raises on import is logged and skipped — it won't crash Jarvis.

## Trust

Plugins are **trusted local code** and run in Jarvis's own process — exactly
like an editor extension you choose to install. Only add plugins you trust.
