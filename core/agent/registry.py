from dataclasses import dataclass

from typing import Callable

from core.utils.logger import (
    logger
)


@dataclass(frozen=True)
class ParamSpec:

    type: str = "str"

    required: bool = True

    desc: str = ""

    default: object = None


@dataclass(frozen=True)
class ToolSpec:

    name: str

    description: str

    params: dict          # name -> ParamSpec

    handler: Callable


@dataclass(frozen=True)
class ToolCall:

    name: str

    args: dict


_REGISTRY = {}


def register(spec):

    if spec.name in _REGISTRY:

        logger.warning(f"Tool {spec.name!r} re-registered; overwriting")

    _REGISTRY[spec.name] = spec


def get(name):

    return _REGISTRY.get(name)


def all_tools():

    return list(_REGISTRY.values())


def clear():

    _REGISTRY.clear()


def tool(name, description, params=None):

    param_specs = {}

    for pname, pmeta in (params or {}).items():

        param_specs[pname] = ParamSpec(
            type=pmeta.get("type", "str"),
            required=pmeta.get("required", True),
            desc=pmeta.get("desc", ""),
            default=pmeta.get("default", None),
        )

    def decorator(func):

        register(
            ToolSpec(
                name=name,
                description=description,
                params=param_specs,
                handler=func,
            )
        )

        return func

    return decorator
