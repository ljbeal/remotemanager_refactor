import pytest

from remotemanager.storage.function import Function


@pytest.fixture
def test(inp):
    return inp.strip()


fn = Function(test)

print(fn("test"))
