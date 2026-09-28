import pytest

from core import calc
from core.agent import calc_tools
from core.agent.registry import Reply


@pytest.mark.parametrize("words,digits", [
    ("twenty five times seventeen", "25 times 17"),
    ("one hundred and five plus three", "105 plus 3"),
    ("three point five over two", "3.5 over 2"),
    ("a thousand divided by eight", "1000 divided by 8"),
    ("two million", "2000000"),
    ("open notepad", "open notepad"),
])
def test_words_to_numbers(words, digits):
    assert calc.words_to_numbers(words) == digits


@pytest.mark.parametrize("spoken,value", [
    ("25 times 17", 425),
    ("twenty five times seventeen", 425),
    ("25*17", 425),
    ("2 + 2", 4),
    ("10 minus 4", 6),
    ("100 divided by 8", 12.5),
    ("2 to the power of 10", 1024),
    ("2^8", 256),
    ("5 squared", 25),
    ("square root of 144", 12),
    ("15 percent of 200", 30),
    ("10 mod 3", 1),
    ("1,000 plus 1", 1001),
    ("6 x 7", 42),
])
def test_spoken_maths_evaluates(spoken, value):
    expression = calc.spoken_to_expression(spoken)
    assert expression is not None
    assert calc.evaluate(expression) == value


@pytest.mark.parametrize("text", ["open notepad", "what is python", "5g", "hello", "5", "i have 2 kids and 3 dogs"])
def test_non_maths_is_rejected(text):
    assert calc.parse_math(text) is None


@pytest.mark.parametrize("expression", ["__import__('os')", "2 ** 1000", "open('x')", "a + 1"])
def test_evaluator_refuses_anything_but_arithmetic(expression):
    with pytest.raises((ValueError, SyntaxError)):
        calc.evaluate(expression)


def test_parse_math_strips_question_words():
    assert calc.parse_math("What's 25 times 17?") == "25 * 17"
    assert calc.parse_math("calculate 2 + 2") == "2 + 2"


def test_format_number():
    assert calc.format_number(425.0) == "425"
    assert calc.format_number(12.5) == "12.5"
    assert calc.format_number(1 / 3) == "0.3333"


def test_calculate_says_short_and_shows_the_working():
    result = calc_tools.calculate("25 times 17")
    assert result == Reply(say="That's 425.", show="25 × 17 = 425")


def test_calculate_division_by_zero():
    assert calc_tools.calculate("5 divided by 0") == "That's undefined."
