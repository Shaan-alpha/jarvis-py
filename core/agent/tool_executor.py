from core.agent import (
    registry
)

from core.utils.logger import (
    logger
)


def execute_tool(call):

    spec = registry.get(call.name)

    if spec is None:

        logger.warning(f"No such tool: {call.name!r}")

        return None

    try:

        return spec.handler(**call.args)

    except Exception as e:

        logger.exception(f"Tool Execution Error: {e}")

        return "Tool execution failed."
