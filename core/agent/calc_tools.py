"""The calculator tool (router-only). Parsing lives in core.calc."""

from core.agent.registry import (
    Reply,
    tool
)

from core.calc import (
    evaluate,
    format_number,
    pretty,
    spoken_to_expression
)


@tool(
    "calculate",
    "Work out an arithmetic expression",
    params={
        "expression": {
            "type": "str",
            "required": True,
            "desc": "the maths to work out, e.g. 25 * 17",
        }
    },
    llm=False,
)
def calculate(expression):

    expression = spoken_to_expression(expression) or expression

    try:

        value = evaluate(expression)

    except ZeroDivisionError:

        return "That's undefined."

    except OverflowError:

        return "That number is too big for me."

    except (ValueError, SyntaxError, TypeError):

        return "I couldn't work that out."

    result = format_number(value)

    return Reply(say=f"That's {result}.", show=f"{pretty(expression)} = {result}")
