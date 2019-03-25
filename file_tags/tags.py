#! /usr/bin/env python3
# Formatted with black (https://github.com/ambv/black).

"""
Simple file tagging.

The tags are stored in file names. Here are the characteristics of this approach:
  * Cons:
     * The amount/length of the tags is hard-limited by the given filesystem's
       max filename length.
     * Easy to lose information when moving files between filesystems with different
       filename lengths.
  * Pros:
     * Very simple.
     * No possibility of tags getting lost - they're always attached to the file.
     * Can be manually edited without needing special tools or knowledge.
     * Standard UNIX tools work great, e.g. grep.

Example file name without tags:
  * 'Picture 002.jpg'
And with:
  * 'Picture 002 #flowers #flying-whales #wallpaper.jpg'
"""

import argparse
import collections
import contextlib
import datetime
import functools
import json
import logging
import os
import random
import re
import sys
import textwrap
import time
from typing import *

from file_tags import exception
from file_tags import util


VERSION = "0.0.1 2018-11-10"
TAG_START_CHAR = "#"
TAG_WORD_SEP = "-"
TAG_REGEX = r"({0}[a-z0-9-]+)".format(TAG_START_CHAR)


log = logging.getLogger()
log.setLevel(logging.DEBUG)


class TagAction:
    def __init__(self, value: str) -> None:
        self.value = self.normalize_value(value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, '"{}"'.format(self.value))

    def __hash__(self):
        return hash(self.value)

    def normalize_value(self, value: str) -> str:
        normalized_value = value.lower().strip()
        if normalized_value == "add":
            return "add"
        if normalized_value in ("remove", "rm", "delete", "del"):
            return "remove"
        raise exception.Error(
            "While normalizing tag action value [1]: [2]."
            "\n [1]: '{0}'"
            "\n [2]: 'Unknown tag action value '{0}'.'".format(value)
        )


@functools.total_ordering
class Tag:
    def __init__(self, name: str) -> None:
        self.name = self.normalize_name(name)
        self.value = TAG_START_CHAR + self.name

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, '"{}"'.format(self.name))

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            raise NotImplementedError
        return self.name == other.name

    def __gt__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            raise NotImplementedError
        return ord(self.name[0]) > ord(other.name[0])

    def normalize_name(self, name: str) -> str:
        normalized_name = name.lower().strip()
        common_separators = {"-", "_", ".", " "}
        for common_separator in common_separators:
            normalized_name = normalized_name.replace(common_separator, TAG_WORD_SEP)
        normalized_name = "".join(
            char for char in normalized_name if char.isalnum() or char == TAG_WORD_SEP
        )
        if not normalized_name:
            raise exception.Error(
                "While normalizing tag name [1]: [2]."
                "\n [1]: '{}'"
                "\n [2]: 'Post-normalization name is empty.'".format(name)
            )
        return normalized_name.strip()


class TaggedFile:
    def __init__(self, path: str) -> None:
        self.path = path
        self.name = os.path.basename(self.path)
        self.tags = self.parsed_tags(self.name)
        self.tagless_name = self.parsed_tagless_name(self.name)

    def __str__(self) -> str:
        return str(
            {
                "path": '"{}"'.format(self.path),
                "tags": ['"{}"'.format(tag) for tag in self.tags],
            }
        )

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, '"{}"'.format(self.path))

    @property
    def new_name(self) -> str:
        # fmt: off
        name = util.trim_repeating_whitespace(
            "{name}{tags}".format(
                name=util.get_file_name_no_extension(self.tagless_name),
                tags=" {}".format(" ".join(tag.value for tag in sorted(self.tags)))
                    if self.tags else "",
            )
        ).strip()
        # fmt: on
        extension = util.get_file_extension(self.tagless_name)
        return "{name}{ext}".format(
            name=name, ext=".{}".format(extension) if extension else ""
        ).strip()

    @property
    def new_path(self) -> str:
        return os.path.join(os.path.dirname(self.path), self.new_name)

    def write(self) -> None:
        current_path = self.path
        new_path = self.new_path
        if new_path == current_path:
            return
        try:
            os.rename(current_path, new_path)
        except OSError as err:
            raise exception.Error(
                "While renaming a file from [1] to [2]: [3]."
                "\n [1]: '{}'"
                "\n [2]: '{}'"
                "\n [3]: '{}'".format(current_path, new_path, err)
            )

    def add_tag(self, tag: Tag) -> None:
        self.tags.add(tag)

    def remove_tag(self, tag: Tag) -> None:
        self.tags.discard(tag)

    def parsed_tagless_name(self, file_name: str) -> str:
        try:
            file_name = re.sub(TAG_REGEX, "", file_name)
        except exception.InvalidRegexError as err:
            raise exception.Error(
                "While parsing the tagless file name based on tags starting with [1] "
                "from file name [2]: [3]."
                "\n [1]: '{}'"
                "\n [2]: '{}'"
                "\n [3]: '{}'".format(
                    TAG_START_CHAR, file_name, util.fmt_err(err)
                )
            )
        except exception.MatchFailedError:
            pass
        return util.trim_repeating_whitespace(file_name).strip()

    def parsed_tags(self, file_name: str) -> Set:
        err_template = (
            "While parsing tags starting with [1] from file name [2]: [3]."
            "\n [1]: '{}'"
            "\n [2]: '{}'"
            "\n [3]: '{{}}'".format(TAG_START_CHAR, file_name)
        )
        try:
            tag_names = re.findall(TAG_REGEX, file_name)
        except exception.InvalidRegexError as err:
            raise exception.Error(err_template.format(util.fmt_err(err)))
        except exception.MatchFailedError:
            return set()
        tags = set()
        for tag_name in tag_names:
            try:
                tags.add(Tag(tag_name))
            except exception.Error as err:
                continue
        return tags


class Config:
    def __init__(
        self,
        action: TagAction,
        in_interactive_mode: bool,
        no_action: bool,
        tags: Set[Tag],
        tagged_files: Set[TaggedFile],
    ) -> None:
        self.action = action
        self.in_interactive_mode = in_interactive_mode
        self.no_action = no_action
        self.tags = tags
        self.tagged_files = tagged_files

    @classmethod
    def from_command_line_args(cls, command_line_args: List):
        if not command_line_args:
            command_line_args.append("-h")

        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=(
                "description:{}".format(
                    textwrap.indent(
                        "{0}" "\nRequires Python 3.5+".format(__doc__), "    "
                    )
                )
            ),
        )

        parser.add_argument(
            "action",
            choices=["add", "remove", "rm"],
            help="what tag action to perform on the files",
        )
        parser.add_argument(
            "tags",
            help=(
                "what tag(s) to use. To specify multiple tags "
                "separate them with commas, e.g. tag1,tag2,tag3"
            ),
        )
        parser.add_argument("file_paths", nargs="+", help="files to handle")

        parser.add_argument(
            "-n", "--no-action", help="don't rename files", action="store_true"
        )
        parser.add_argument(
            "-i", "--interactive", help="ask before renaming files", action="store_true"
        )

        parser.add_argument(
            "-v", "--version", action="version", version=VERSION, help="show version"
        )
        parsed = parser.parse_args(command_line_args)

        try:
            file_paths = util.validated_paths(parsed.file_paths)
            tags = {Tag(tag) for tag in parsed.tags.split(",")}
        except exception.Error as err:
            log.error(util.fmt_err(err))
            sys.exit(1)

        return cls(
            action=TagAction(parsed.action),
            in_interactive_mode=parsed.interactive,
            no_action=parsed.no_action,
            tags=tags,
            tagged_files={TaggedFile(file_path) for file_path in file_paths},
        )


def run(command_line_args: List) -> None:
    util.setup_terminal_logging(log)
    try:
        main(Config.from_command_line_args(command_line_args))
    except KeyboardInterrupt:
        print()
        log.info("Interrupted by the user, exiting ...")
        sys.exit(130)
    except exception.Error as err:
        log.error(util.fmt_err(err))
        sys.exit(1)
    except Exception as err:
        log.critical(util.fmt_err(err), exc_info=True)
        sys.exit(1)


def main(config: Config) -> None:
    log.info("Tags: {}".format(", ".join(tag.name for tag in config.tags)))
    log.info("Action: {}".format(config.action))
    log.info("File count: {}".format(len(config.tagged_files)))

    for tagged_file in config.tagged_files:
        for tag in config.tags:
            if config.action.value == "add":
                tagged_file.add_tag(tag)
            elif config.action.value == "remove":
                tagged_file.remove_tag(tag)

    changed_tagged_files = {
        file for file in config.tagged_files if file.name != file.new_name
    }
    if not changed_tagged_files:
        log.info("Exiting ... (no files to rename)")
        sys.exit(0)

    list_files(changed_tagged_files)

    if config.no_action:
        log.info("Exiting ... (--no-action)")
        sys.exit(0)

    if config.in_interactive_mode:
        answer = input("Rename the files? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            log.info("Exiting ... (answered no)")
            sys.exit(130)

    log.info("Renaming the files ...")
    try:
        rename_files(changed_tagged_files)
    except exception.Error as err:
        log.error(util.fmt_err(err))
        log.error("Exiting ... (failed to rename a file, please retry)")
        sys.exit(1)
    log.info("Files successfully renamed.")


def list_files(tagged_files: Set[TaggedFile]) -> None:
    log.info("Files to change [{}]:".format(len(tagged_files)))
    files_to_show_count = 10
    tagged_files_to_show = list(tagged_files)
    random.shuffle(tagged_files_to_show)
    tagged_files_to_show = tagged_files_to_show[0:files_to_show_count]
    for tagged_file in sorted(tagged_files_to_show, key=lambda f: f.path):
        log.info(" - '{}'".format(tagged_file.path))
        name = tagged_file.name
        new_name = tagged_file.new_name
        if new_name != name:
            longest_name = new_name
            if len(name) > len(new_name):
                longest_name = name
            longest_name_char_len = len(str(len(longest_name)))
            log.info(
                "   <- [{:{}}] '{}'".format(len(name), longest_name_char_len, name)
            )
            log.info(
                "   -> [{:{}}] '{}'".format(
                    len(new_name), longest_name_char_len, new_name
                )
            )
    if len(tagged_files) > len(tagged_files_to_show):
        log.info(" [...]")


def rename_files(tagged_files: Set[TaggedFile]) -> None:
    renamed_files: Set = set()
    for tagged_file in tagged_files:
        try:
            tagged_file.write()
        except exception.Error as err:
            raise exception.Error(
                "While renaming file {}/{}: [1]."
                "\n [1]: '{}'".format(
                    len(renamed_files) + 1,
                    len(tagged_files),
                    util.fmt_err(err),
                )
            )
        else:
            renamed_files.add(tagged_file)


if __name__ == "__main__":
    run(sys.argv[1:])
