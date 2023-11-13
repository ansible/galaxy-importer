from galaxy_importer.utils import string_utils


def test_removeprefix_startswith():
    assert "bar" == string_utils.removeprefix("foobar", "foo")


def test_removeprefix_doesnt_startswith():
    assert "foobar" == string_utils.removeprefix("foobar", "baz")
