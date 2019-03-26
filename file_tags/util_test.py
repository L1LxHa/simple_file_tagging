import pytest

from file_tags import util
from file_tags import exception

ARBITRARY_LARGE_NUMBER = 20


def test_trim_repeating_character():
    # The input has to be a single character.
    with pytest.raises(ValueError):
        util.trim_repeating_character("", "text")
        util.trim_repeating_character("a" * ARBITRARY_LARGE_NUMBER, "text")

    assert util.trim_repeating_character("A", "") == ""
    assert util.trim_repeating_character("A", "abc") == "abc"
    assert util.trim_repeating_character("A", "aAbc") == "aAbc"
    assert util.trim_repeating_character("A", "aAbAc") == "aAbAc"
    # Make sure special regex characters don't affect the output.
    assert util.trim_repeating_character(".", "abc") == "abc"
    # Make sure no other repeated characters are removed.
    assert util.trim_repeating_character("A", "aa AA dddd") == "aa A dddd"

    assert util.trim_repeating_character("A", "AA") == "A"
    assert util.trim_repeating_character("A", "A" * ARBITRARY_LARGE_NUMBER) == "A"
    assert util.trim_repeating_character("A", "aAAbAAcAA") == "aAbAcA"


def test_trim_repeating_whitespace():
    assert util.trim_repeating_whitespace("") == ""
    assert util.trim_repeating_whitespace("a") == "a"
    assert util.trim_repeating_whitespace(" ") == " "
    assert util.trim_repeating_whitespace("  ") == " "
    assert util.trim_repeating_whitespace(" " * ARBITRARY_LARGE_NUMBER) == " "
    assert util.trim_repeating_whitespace(" a ") == " a "
    assert util.trim_repeating_whitespace("  a") == " a"
    assert util.trim_repeating_whitespace("  a  b  c ") == " a b c "
    assert util.trim_repeating_whitespace("\t") == "\t"
    assert util.trim_repeating_whitespace("\t\t") == "\t"
    assert util.trim_repeating_whitespace("\t" * ARBITRARY_LARGE_NUMBER) == "\t"
