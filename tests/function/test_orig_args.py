import pytest

from alchemy_test.storage.function import Function


def basic(x):
    return x


def typehint(x: int) -> str:
    return str(x)


@pytest.mark.parametrize("fn", [basic, typehint])
def test_orig_args(fn):
    tmp_fn = Function(fn)

    assert tmp_fn.orig_args == ["x"]
