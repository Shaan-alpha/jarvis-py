"""Offline arithmetic for spoken or typed maths — no eval, no LLM.

Vosk (offline STT) writes numbers as words, so number words are converted
first; then spoken operators become symbols, and a whitelist AST evaluator
computes the result.
"""

import ast
import math
import operator
import re


_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}

_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_SCALES = {"thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9}

MAX_EXPONENT = 100

MAX_LENGTH = 200


def _is_number_word(token):

    return token in _UNITS or token in _TENS or token == "hundred" or token in _SCALES


def _run_value(run):

    total, current, decimals = 0, 0, None

    for token in run:

        if decimals is not None:

            decimals += str(_UNITS[token])

        elif token == "point":

            decimals = ""

        elif token in _UNITS:

            current += _UNITS[token]

        elif token in _TENS:

            current += _TENS[token]

        elif token == "hundred":

            current = max(current, 1) * 100

        elif token in _SCALES:

            total += max(current, 1) * _SCALES[token]

            current = 0

    value = str(total + current)

    return f"{value}.{decimals}" if decimals else value


def words_to_numbers(text):
    """'twenty five' -> '25', 'one hundred and five' -> '105',
    'three point five' -> '3.5', 'a thousand' -> '1000'."""

    tokens = text.split()

    out, run = [], []

    for i, token in enumerate(tokens):

        following = tokens[i + 1] if i + 1 < len(tokens) else ""

        joins_run = (
            _is_number_word(token)
            or (run and token == "and" and _is_number_word(following))
            or (run and token == "point" and following in _UNITS)
            or (token == "a" and following in ("hundred", "thousand", "million"))
        )

        if joins_run:

            if token not in ("and", "a"):

                run.append(token)

            continue

        if run:

            out.append(_run_value(run))

            run = []

        out.append(token)

    if run:

        out.append(_run_value(run))

    return " ".join(out)


_NUMBER = r"\d+(?:\.\d+)?"

_PERCENT_OF = re.compile(rf"({_NUMBER})\s*(?:%|percent)\s+of\s+({_NUMBER})")

_SQRT = re.compile(rf"\bsquare root of\s+({_NUMBER})")

# Order matters: multi-word phrases before the single words they contain.
_OPERATORS = (
    (r"\bmultiplied by\b", " * "),
    (r"\bdivided by\b", " / "),
    (r"\b(?:raised )?to the power of\b", " ** "),
    (r"\braised to\b", " ** "),
    (r"\bsquared\b", " ** 2"),
    (r"\bcubed\b", " ** 3"),
    (r"\bplus\b", " + "),
    (r"\bminus\b", " - "),
    (r"\btimes\b", " * "),
    (r"\bmod(?:ulo)?\b", " % "),
    (r"(?<=\d)\s*(?:x|into)\s*(?=[\d(])", " * "),
    (r"(?<=\d)\s+over\s+(?=[\d(])", " / "),
    (r"×", " * "),
    (r"÷", " / "),
    (r"\^", " ** "),
    (r"\bpercent\b|%(?!\s*[\d(])", " / 100"),
)

_ALLOWED = re.compile(r"^[\d\s.+\-*/%()]*$")

_HAS_OPERATION = re.compile(r"[\d)]\s*(?:\*\*|[+\-*/%])\s*[\d(\-]|sqrt\(")


def spoken_to_expression(text):
    """'twenty five times seventeen' -> '25 * 17'; None when it isn't maths."""

    text = words_to_numbers((text or "").lower().strip().rstrip("?.! "))

    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)

    text = _PERCENT_OF.sub(r"(\1 / 100 * \2)", text)

    text = _SQRT.sub(r"sqrt(\1)", text)

    for pattern, symbol in _OPERATORS:

        text = re.sub(pattern, symbol, text)

    text = re.sub(r"\s+", " ", text).strip()

    if not _ALLOWED.match(text.replace("sqrt", "")):

        return None

    if not _HAS_OPERATION.search(text):

        return None

    return text


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval(node):

    if isinstance(node, ast.Constant) and type(node.value) in (int, float):

        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:

        left, right = _eval(node.left), _eval(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:

            raise ValueError("exponent too large")

        return _BINARY[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:

        return _UNARY[type(node.op)](_eval(node.operand))

    is_sqrt = (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "sqrt" and len(node.args) == 1 and not node.keywords
    )

    if is_sqrt:

        value = _eval(node.args[0])

        if value < 0:

            raise ValueError("square root of a negative number")

        return math.sqrt(value)

    raise ValueError("not arithmetic")


def evaluate(expression):
    """Evaluate plain arithmetic (numbers, + - * / % **, unary -, sqrt)."""

    if len(expression) > MAX_LENGTH:

        raise ValueError("expression too long")

    return _eval(ast.parse(expression, mode="eval").body)


def format_number(value):
    """425.0 -> '425', 12.5 -> '12.5', 1/3 -> '0.3333'."""

    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:

        value = int(value)

    if isinstance(value, int):

        return str(value) if abs(value) < 10 ** 15 else f"{value:.3e}"

    if abs(value) >= 1e15:

        return f"{value:.3e}"

    return f"{value:.4f}".rstrip("0").rstrip(".")


def pretty(expression):
    """'25 * 17' -> '25 × 17' for the HUD."""

    return expression.replace("**", "^").replace("*", "×").replace("/", "÷")


_QUESTION = re.compile(
    r"^\W*(?:(?:hey |ok )?jarvis\W+)?(?:please\s+)?"
    r"(?:what(?:'s|s| is)|calculate|compute|how much is|work out|solve)\s+(.+?)"
    r"(?:\s+(?:equals?|is))?[\s?.!]*$",
    re.IGNORECASE,
)


def parse_math(raw):
    """The arithmetic in a whole-utterance maths question, or None."""

    text = (raw or "").strip()

    match = _QUESTION.match(text)

    candidate = match.group(1) if match else text

    expression = spoken_to_expression(candidate)

    if expression is None:

        return None

    try:

        evaluate(expression)

    except ZeroDivisionError:

        return expression

    except (ValueError, SyntaxError, TypeError, OverflowError):

        return None

    return expression
