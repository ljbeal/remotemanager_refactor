import pytest

from alchemy_test.storage.function import Function


@pytest.fixture
def test(inp):
    return inp.strip()


fn = Function(test)

print(fn("test"))
