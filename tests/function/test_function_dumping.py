import os

import pytest


from remotemanager.storage.function import Function
from remotemanager.utils import random_string
from remotemanager.connection.cmd import CMD


def square(a: int) -> int:
    return a * a


def none():
    return None


@pytest.mark.parametrize(
    "function,args,result",
    [
        (square, {"a": 5}, "25"),
        (none, None, "None"),
    ]
)
def test_dump(function, args, result):
    fn = Function(function)

    as_string = fn.dump_to_string(args)

    assert "__main__" in as_string

    file = f"{random_string()}.py"
    try:
        with open(file, "w+", encoding="utf8") as o:
            o.write(as_string + "\n\tprint(result)")  # need to dump to stdout

        cmd = CMD(f"python {file}")
        cmd.exec()

        assert cmd.stdout == result

    finally:
        os.remove(file)


def test_object():
    fn = Function(square)

    assert fn.object(5) == 25


def test_call():
    fn = Function(square)

    assert fn(5) == 25
