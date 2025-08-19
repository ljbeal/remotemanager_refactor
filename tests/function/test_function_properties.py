import pytest

from remotemanager.storage.function import Function


def test_name():
    def test():
        return True

    fn = Function(test)

    assert fn.name == "test"


def test_protected_name():
    def remote_load():
        return True

    with pytest.raises(ValueError, match=r'function name "remote_load" is protected'):
        Function(remote_load)


def test_source():
    def test():
        return True

    string = """def test():
    return True"""

    expected = """def test(*args, **kwargs):
    return True"""

    fn_obj = Function(test)
    fn_str = Function(string)

    assert fn_obj.source == expected
    assert fn_str.source == expected

    assert fn_obj.raw_source == expected
    assert fn_str.raw_source == expected


def test_return_annotation():
    def test() -> bool:
        return True

    fn = Function(test)

    assert fn.return_annotation == "bool"


def test_return_annotation_empty():
    def test():
        return True

    fn = Function(test)

    assert fn.return_annotation is None


def test_arglist_cache():
    def test(a, b, c, d):
        return a + b + c + d

    fn = Function(test)

    assert fn.args == ["a", "b", "c", "d", "*args", "**kwargs"]  # this should cache the args

    assert fn._arglist is not None
    assert fn.args == ["a", "b", "c", "d", "*args", "**kwargs"]
