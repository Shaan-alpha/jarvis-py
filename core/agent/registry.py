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


def _to_bool(value):
    """Coerce an LLM-supplied value to bool. Accepts real bools, numbers, and
    the usual string spellings; naive bool('false') would wrongly be True."""

    if isinstance(value, bool):

        return value

    if isinstance(value, (int, float)):

        return bool(value)

    text = str(value).strip().lower()

    if text in ("true", "yes", "1", "on"):

        return True

    if text in ("false", "no", "0", "off", ""):

        return False

    raise ValueError(f"not a boolean: {value!r}")


_COERCERS = {
    "str": str,
    "int": int,
    "float": float,
    "bool": _to_bool,
}


def coerce_and_validate(spec, raw_args):

    if raw_args is None:

        raw_args = {}

    result = {}

    for pname, pspec in spec.params.items():

        if pname in raw_args and raw_args[pname] is not None:

            coercer = _COERCERS.get(pspec.type, str)

            try:

                result[pname] = coercer(raw_args[pname])

            except (TypeError, ValueError):

                return {}, f"param {pname!r} not coercible to {pspec.type}"

        elif pspec.required:

            return {}, f"missing required param {pname!r}"

        else:

            result[pname] = pspec.default

    return result, None
