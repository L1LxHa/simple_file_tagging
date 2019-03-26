import pytest

from file_tags import tags as tagger
from file_tags import exception, util


def test_tag_object_creation():
    valid_tag_names = [
        "a",
        "abc",
        "1",
        "12345689",
        "a2",
        "abcd23459",
        "tag{0}with{0}separators".format(tagger.TAG_WORD_SEP),
        "tag.with-nonstandard_separators",
        " surrounded by whitespace   ",
        " {0}starting_with{1}a{1}hash22 ".format(
            tagger.TAG_START_CHAR, tagger.TAG_WORD_SEP
        ),
        " {0} starting_with+a.hash".format(tagger.TAG_START_CHAR),
    ]
    for tag_name in valid_tag_names:
        # Assigning to '_' so that inspecting the variable via pytest's '--showlocals' is possible.
        _ = tagger.Tag(tag_name)

    invalid_tag_names = [
        "",
        " ",
        " " * 20,
        "\t",
        "\t" * 20,
        tagger.TAG_WORD_SEP,
        tagger.TAG_START_CHAR,
        ".-+'#@:\"?,\\/()[]{{}}^%$@*={}{}".format(
            tagger.TAG_WORD_SEP, tagger.TAG_START_CHAR
        ),
    ]
    for tag_name in invalid_tag_names:
        with pytest.raises(exception.Error):
            # Assigning to '_' so that inspecting the variable via pytest's '--showlocals' is possible.
            _ = tagger.Tag(tag_name)

    assert tagger.Tag("a").name == "a"
    assert tagger.Tag(" a  ").name == "a"
    assert tagger.Tag("1").name == "1"
    assert tagger.Tag("12345").name == "12345"
    assert tagger.Tag(" 12345 ").name == "12345"
    assert tagger.Tag(
        "tag{0}with{0}separators".format(tagger.TAG_WORD_SEP)
    ).name == "tag{0}with{0}separators".format(tagger.TAG_WORD_SEP)
    assert tagger.Tag(
        "tag.with-nonstandard_separators"
    ).name == "tag{0}with{0}nonstandard{0}separators".format(tagger.TAG_WORD_SEP)
    assert tagger.Tag(
        " {0}starting_with{1}a{1}hash22 ".format(
            tagger.TAG_START_CHAR, tagger.TAG_WORD_SEP
        )
    ).name == "starting{0}with{0}a{0}hash22".format(tagger.TAG_WORD_SEP)
    assert tagger.Tag(
        "multiple___separators{0}{0}{0}{0}z".format(tagger.TAG_WORD_SEP)
    ).name == "multiple{0}separators{0}z".format(tagger.TAG_WORD_SEP)
    assert tagger.Tag(
        " {0} starting_with+a.hash".format(tagger.TAG_START_CHAR)
    ).name == "starting{0}witha{0}hash".format(tagger.TAG_WORD_SEP)


def test_tagged_file_tag_parsing():
    # No tags.
    tagged_file = tagger.TaggedFile("/home/abc/random.jpg")
    assert len(tagged_file.tags) == 0
    tagged_file = tagger.TaggedFile(
        "/home/abc/random{0}faketag.jpg".format(tagger.TAG_START_CHAR)
    )
    assert len(tagged_file.tags) == 0

    # One tag.
    tagged_file = tagger.TaggedFile(
        "/home/abc/random {0}tag.jpg".format(tagger.TAG_START_CHAR)
    )
    expected_tags = {tagger.Tag("tag")}
    assert tagged_file.tags == expected_tags

    tagged_file = tagger.TaggedFile("/home/abc/{0}tag".format(tagger.TAG_START_CHAR))
    expected_tags = {tagger.Tag("tag")}
    assert tagged_file.tags == expected_tags

    tagged_file = tagger.TaggedFile(
        "/home/abc/{0}tag.jpg".format(tagger.TAG_START_CHAR)
    )
    expected_tags = {tagger.Tag("tag")}
    assert tagged_file.tags == expected_tags

    # Two equivalent tags, should get deduplicated.
    tagged_file = tagger.TaggedFile(
        "/home/abc/random {0}tag {0}tag.jpg".format(tagger.TAG_START_CHAR)
    )
    expected_tags = {tagger.Tag("tag")}
    assert tagged_file.tags == expected_tags

    # Tags all over the place.
    tagged_file = tagger.TaggedFile(
        "/home/abc/sfd {0}tag1 random {0}tag2 {0}tag3   {0}tag4 .jpg".format(
            tagger.TAG_START_CHAR
        )
    )
    expected_tags = {
        tagger.Tag(tag_name) for tag_name in {"tag1", "tag2", "tag3", "tag4"}
    }
    assert tagged_file.tags == expected_tags

    # Extra TAG_START_CHAR symbols.
    tagged_file = tagger.TaggedFile(
        "/home/abc/sfd {0}tag1 ran{0}do{0}{0}m {0}tag2 {0}tag3 {0}{0}d  {0}tag4 .jpg".format(
            tagger.TAG_START_CHAR
        )
    )
    expected_tags = {
        tagger.Tag(tag_name) for tag_name in {"tag1", "tag2", "tag3", "tag4"}
    }
    assert tagged_file.tags == expected_tags


def test_tagged_file_renaming():
    # Need to preserve the original file name as much as possible.
    paths = [
        "justfilename",
        "justfilename.ext",
        "/home/abc/basicname",
        "/home/abc/basicname.ext",
        "/home/abc/[dsdf] long weird name    whitespace {}tag.jpg".format(
            tagger.TAG_START_CHAR
        ),
    ]
    for path in paths:
        assert tagger.TaggedFile(path).new_path == util.normalize_path(path)

    # Tags need to be normalized to be put at the end.
    path_in = "justfilename {0}tag".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}tag".format(tagger.TAG_START_CHAR)
    assert tagger.TaggedFile(path_in).new_path == util.normalize_path(path_out)

    path_in = "{0}tag justfilename".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}tag".format(tagger.TAG_START_CHAR)
    assert tagger.TaggedFile(path_in).new_path == util.normalize_path(path_out)

    # Tags need to be normalized to be sorted alphabetically.
    path_in = "justfilename {0}tagC {0}tagB {0}tagA".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}tagA {0}tagB {0}tagC".format(tagger.TAG_START_CHAR)
    assert tagger.TaggedFile(path_in).new_path == util.normalize_path(path_out)

    path_in = "{0}tagC justfilename {0}tagA {0}tagB".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}tagA {0}tagB {0}tagC".format(tagger.TAG_START_CHAR)
    assert tagger.TaggedFile(path_in).new_path == util.normalize_path(path_out)

    path_in = "{0}ABCKKK justfilename {0}CBA {0}ABCD {0}L".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}ABCD {0}ABCKKK {0}CBA {0}L".format(
        tagger.TAG_START_CHAR
    )
    assert tagger.TaggedFile(path_in).new_path == util.normalize_path(path_out)


def test_tagless_name_from_file_name():
    # Properly get rid of whitespace.
    file_name_in = "justfilename {0}tag".format(tagger.TAG_START_CHAR)
    file_name_out = "justfilename"
    assert tagger.TaggedFile._tagless_name_from_file_name(file_name_in) == file_name_out

    file_name_in = "{0}tag justfilename".format(tagger.TAG_START_CHAR)
    file_name_out = "justfilename"
    assert tagger.TaggedFile._tagless_name_from_file_name(file_name_in) == file_name_out

    file_name_in = "{0}tag justfilename {0}tag".format(tagger.TAG_START_CHAR)
    file_name_out = "justfilename"
    assert tagger.TaggedFile._tagless_name_from_file_name(file_name_in) == file_name_out

    # Preserve original whitespace, sans .strip().
    file_name_in = "justfilename something  else {0}tag some more  {0}tag".format(
        tagger.TAG_START_CHAR
    )
    file_name_out = "justfilename something  else some more"
    assert tagger.TaggedFile._tagless_name_from_file_name(file_name_in) == file_name_out

    file_name_in = "text    {0}tag     text".format(tagger.TAG_START_CHAR)
    file_name_out = "text        text"
    assert tagger.TaggedFile._tagless_name_from_file_name(file_name_in) == file_name_out


def test_tagged_file_actions():
    # Adding a new tag to a tagless file.
    path_in = "justfilename"
    path_out = "justfilename {0}abc".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.add_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    path_in = "justfilename.ext"
    path_out = "justfilename {0}abc.ext".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.add_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    # Adding a new tag to an already-tagged file.
    path_in = "justfilename {0}1".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.add_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    path_in = "{0}1 justfilename".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.add_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    # Adding a tag that's already present in the file.
    path_in = "justfilename {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.add_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    # Removing a tag.
    path_in = "justfilename {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}1".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.remove_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    path_in = "justfilename {0}cfk {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}1 {0}cfk".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.remove_tag(tagger.Tag("abc"))
    assert tagged_file.new_path == util.normalize_path(path_out)

    # Removing a non-existant tag.
    path_in = "justfilename {0}cfk {0}1 {0}abc".format(tagger.TAG_START_CHAR)
    path_out = "justfilename {0}1 {0}abc {0}cfk".format(tagger.TAG_START_CHAR)
    tagged_file = tagger.TaggedFile(path_in)
    tagged_file.remove_tag(tagger.Tag("sdfjidjfsdifsidfisjf"))
    assert tagged_file.new_path == util.normalize_path(path_out)
