# pylint: disable=unused-wildcard-import
from typing import *

import logging.handlers
import os
import re
import textwrap
import time

from file_tags import exception


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def validate_paths(paths: List[str]) -> List[str]:
    out_paths = []
    err_paths = []
    for path in paths:
        path = normalize_path(path)
        if not os.path.exists(path):
            err_paths.append(path)
            continue
        out_paths.append(path)
    if err_paths:
        raise exception.Error(
            "While validating paths: The following paths don't exist ({}/{}):"
            "\n{}".format(
                len(err_paths),
                len(paths),
                "\n".join(
                    " [{}]: '{}'".format(i, path) for i, path in enumerate(err_paths, 1)
                ),
            )
        )
    return out_paths


def sanitize_file_name(file_name: str) -> str:
    return "".join(char for char in file_name if char.isalnum() or char in "-. ")


def normalize_path(path: str) -> str:
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def setup_terminal_logging(logger, level=logging.INFO) -> None:
    logging.Formatter.converter = time.gmtime
    if os.name == "nt":
        terminal_handler = AlignedLoggingStreamHandler()
        terminal_formatter = logging.Formatter(
            "%(asctime)s %(levelname)s | %(message)s", datefmt="%m-%d %H:%M:%S"
        )
    else:
        terminal_handler = ColoredLoggingStreamHandler()
        terminal_formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s", datefmt="%m-%d %H:%M:%S"
        )
    terminal_handler.setFormatter(terminal_formatter)
    terminal_handler.setLevel(level)
    logger.addHandler(terminal_handler)


class AlignedLoggingStreamHandler(logging.StreamHandler):
    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in levels:
            message = message.replace(level, "{:>8}".format(level), 1)
        return message


class ColoredLoggingStreamHandler(logging.StreamHandler):
    def format(self, record):
        level_colors = [
            ("DEBUG", 30),
            ("INFO", 70),
            ("WARNING", 202),
            ("ERROR", 196),
            ("CRITICAL", 198),
        ]
        level_shortened = {
            "DEBUG": "DEB",
            "INFO": "INFO",
            "WARNING": "WARN",
            "ERROR": "ERR",
            "CRITICAL": "CRIT",
        }
        clr_template = "\033[38;5;{}m"
        message = logging.StreamHandler.format(self, record)
        for level, color in level_colors:
            message = clr_template.format(247) + message
            message = message.replace(
                level,
                "{clr}{lvl:<4}{after}{reset}".format(
                    clr=clr_template.format(color),
                    lvl=level_shortened[level],
                    after="\033[0m {}|".format(clr_template.format(239)),
                    reset="\033[0m",
                ),
                1,
            )
        return message


def fmt_err(err) -> str:
    basic_fmt = "[{err}] {msg}".format(err=err.__class__.__qualname__, msg=err)
    if isinstance(err, exception.Error):
        return textwrap.indent(basic_fmt, prefix=" " * 6).strip()
    return basic_fmt


def get_file_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()[1:].strip()


def get_file_name_no_extension(file_path: str) -> str:
    return os.path.basename(os.path.splitext(file_path)[0])


def trim_repeating_whitespace(text: str) -> str:
    """
    Remove consecutive repeats of whitespace from `text`.

    Examples:
        f(" " * 3) -> " "
        f(" 1  1 ") -> " 1 1 "
    """
    output = []
    previous_text_char = ""
    for text_char in text:
        if text_char.isspace() and text_char == previous_text_char:
            continue
        output.append(text_char)
        previous_text_char = text_char
    return "".join(output)


def trim_repeating_character(char: str, text: str) -> str:
    """
    Remove consecutive repeats of character `char` from `text`.

    Examples:
        f("A", "AAA") -> "A"
        f("1", "ab111ab1" -> "ab1ab1"

    Raises:
        ValueError when the value of `char` is not a single character.
    """

    if len(char) != 1:
        raise ValueError(
            "Invalid value of parameter 'char': expected a single character string, got: '{}'".format(
                char
            )
        )
    output = []
    previous_text_char = ""
    for text_char in text:
        if text_char == char and text_char == previous_text_char:
            continue
        output.append(text_char)
        previous_text_char = text_char
    return "".join(output)
