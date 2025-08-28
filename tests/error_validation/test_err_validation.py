from remoref.utils.validate_stderr import validate_error


def test_none():
    assert not validate_error(None)


def test_empty():
    assert not validate_error("")


def test_extra():
    assert not validate_error("foo", ["foo"])
    assert validate_error("foo")
