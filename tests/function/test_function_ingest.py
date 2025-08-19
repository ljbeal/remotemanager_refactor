import pytest

from remotemanager.storage.function import Function


def test_basic():
    """tests a simple function"""

    def fn():
        return

    string = """def fn():
    return"""

    assert Function(fn).signature == "(*args, **kwargs)"
    assert Function(string).signature == "(*args, **kwargs)"
    assert Function(fn).args == ["*args", "**kwargs"]
    assert Function(string).args == ["*args", "**kwargs"]


def test_ingest_none():
    with pytest.raises(TypeError):
        Function(None)


def test_arg():
    """tests basic with arg"""

    def fn(a):
        return a

    string = """def fn(a):
    return a"""

    assert Function(fn).signature == "(a, *args, **kwargs)"
    assert Function(string).signature == "(a, *args, **kwargs)"
    assert Function(fn).args == ["a", "*args", "**kwargs"]
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_args():
    """tests basic with args"""

    def fn(a, b):
        return a + b

    string = """def fn(a, b):
    return a + b"""

    assert Function(fn).signature == "(a, b, *args, **kwargs)"
    assert Function(string).signature == "(a, b, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_args_with_default():
    """tests basic with args"""

    def fn(a=10, b=5):
        return a + b

    string = """def fn(a=10, b=5):
    return a + b"""

    assert Function(fn).signature == "(a=10, b=5, *args, **kwargs)"
    assert Function(string).signature == "(a=10, b=5, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_args_placeholder():
    """tests basic with args placeholder"""

    def fn(*args):
        return

    string = """def fn(*args):
    return"""

    assert Function(fn).signature == "(*args, **kwargs)"
    assert Function(string).signature == "(*args, **kwargs)"
    assert Function(fn).args == ["*args", "**kwargs"]
    assert Function(string).args == ["*args", "**kwargs"]


def test_args_and_kwargs_placeholder():
    """tests basic with args placeholder"""

    def fn(*args, **kwargs):
        return

    string = """def fn(*args, **kwargs):
    return"""

    assert Function(fn).signature == "(*args, **kwargs)"
    assert Function(string).signature == "(*args, **kwargs)"
    assert Function(fn).args == ["*args", "**kwargs"]
    assert Function(string).args == ["*args", "**kwargs"]


def test_args_and_kwargs_placeholder_plus_arg():
    """tests basic with args placeholder and an arg"""

    def fn(a, *args, **kwargs):
        return a

    string = """def fn(a, *args, **kwargs):
    return a"""

    assert Function(fn).signature == "(a, *args, **kwargs)"
    assert Function(string).signature == "(a, *args, **kwargs)"
    assert Function(fn).args == ["a", "*args", "**kwargs"]
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_args_and_kwargs_placeholder_plus_args():
    """tests basic with args placeholder and args"""

    def fn(a, b, *args, **kwargs):
        return a + b

    string = """def fn(a, b, *args, **kwargs):
    return a + b"""

    assert Function(fn).signature == "(a, b, *args, **kwargs)"
    assert Function(string).signature == "(a, b, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_args_and_kwargs_placeholder_plus_args_with_default():
    """tests basic with args placeholder and args"""

    def fn(a=10, b=5, *args, **kwargs):
        return a + b

    string = """def fn(a=10, b=5, *args, **kwargs):
    return a + b"""

    assert Function(fn).signature == "(a=10, b=5, *args, **kwargs)"
    assert Function(string).signature == "(a=10, b=5, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_string_spec_with_extra_space():
    """tests for a bug where extra spaces after the signature would cause issues"""
    string = "def fn(a):  \n    return a"

    assert Function(string).signature == "(a, *args, **kwargs)"
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_string_spec_with_spaces_in_args():
    """Checks that spaces in signature do not break storage"""
    string = "def fn(a , *args , **kwargs ):\n    return a"

    assert Function(string).signature == "(a, *args, **kwargs)"
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_self():
    """check that self is preserved"""

    def fn(self, a):
        return a

    string = """def fn(self, a):
    return a"""

    assert Function(fn).signature == "(self, a, *args, **kwargs)"
    assert Function(string).signature == "(self, a, *args, **kwargs)"
    assert Function(fn).args == ["self", "a", "*args", "**kwargs"]
    assert Function(string).args == ["self", "a", "*args", "**kwargs"]


def test_type_hints():
    """Ensure that type hinting does not break anything"""

    def fn(a: int = 10, b: int = 5) -> int:
        return a + b

    string = """def fn(a: int = 10, b: int = 5) -> int:
    return a + b"""

    assert Function(fn).signature == "(a: int = 10, b: int = 5, *args, **kwargs) -> int"
    assert Function(string).signature == "(a: int = 10, b: int = 5, *args, **kwargs) -> int"
    assert Function(fn).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_tuple_default():
    """check that the tuple syntax does not break the signature replacement"""

    def fn(a: tuple = (10, 5)) -> tuple:
        return a

    string = """def fn(a: tuple = (10, 5)) -> tuple:
    return a"""

    assert Function(fn).signature == "(a: tuple = (10, 5), *args, **kwargs) -> tuple"
    assert Function(string).signature == "(a: tuple = (10, 5), *args, **kwargs) -> tuple"

    assert Function(fn).args == ["a", "*args", "**kwargs"]
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_multiline():
    # fmt: off
    def fn(a,
           b,
           c):
        return a + b + c
    # fmt: on

    string = """
def fn(a,
       b,
       c):
    return a + b + c
"""
    assert Function(fn).signature == "(a, b, c, *args, **kwargs)"
    assert Function(string).signature == "(a, b, c, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "c", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "c", "*args", "**kwargs"]


def test_multiline_inner_function():
    # fmt: off
    def fn(a,
           b,
           c):
        def inner_function(foo):
            return foo

        return inner_function(a + b + c)

    # fmt: on

    string = """
def fn(a,
       b,
       c):
    def inner_function(foo):
        return foo
    return inner_function(a + b + c)
"""

    assert Function(fn).signature == "(a, b, c, *args, **kwargs)"
    assert Function(string).signature == "(a, b, c, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "c", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "c", "*args", "**kwargs"]

    assert "def inner_function" in Function(fn).source
    assert "def inner_function" in Function(string).source


def test_multiline_commented():
    # fmt: off
    def fn(a,  # a
           b,  # b
           c,  # c
        ):
        return a + b + c
    # fmt: on

    string = """
def fn(a,  # a
       b,  # b
       c,  # c
    ):
    return a + b + c
"""

    convert = """def fn(a, b, c, *args, **kwargs):
    return a + b + c"""

    assert Function(fn).signature == "(a, b, c, *args, **kwargs)"
    assert Function(string).signature == "(a, b, c, *args, **kwargs)"

    assert Function(fn).source == convert
    assert Function(string).source == convert

    assert Function(fn).args == ["a", "b", "c", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "c", "*args", "**kwargs"]


def test_multiline_tuple_default():
    # fmt: off
    def fn(a,
           b=(1, 2, 3),
           c=('x', 'y', 'z')):
        return a + b + c
    # fmt: on

    string = """
def fn(a,
       b=(1, 2, 3),
       c=('x', 'y', 'z')):
    return a + b + c
"""
    assert Function(fn).signature == "(a, b=(1, 2, 3), c=('x', 'y', 'z'), *args, **kwargs)"
    assert (
            Function(string).signature == "(a, b=(1, 2, 3), c=('x', 'y', 'z'), *args, **kwargs)"
    )

    assert Function(fn).args == ["a", "b", "c", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "c", "*args", "**kwargs"]


def test_extended_multiline():
    # fmt: off
    def fn(
        a,
        b,
        c
    ):
        return a + b + c
    # fmt: on

    string = """
def fn(
    a,
    b,
    c
):
    return a + b + c
"""
    assert Function(fn).signature == "(a, b, c, *args, **kwargs)"
    assert Function(string).signature == "(a, b, c, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "c", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "c", "*args", "**kwargs"]


def test_comment_after_definition():
    """commenting after definition of a function shouldn't break the sig extraction"""

    def fn(a=10, b=5, *args, **kwargs):  # foo
        return a + b

    string = """def fn(a=10, b=5, *args, **kwargs):  # foo
    return a + b"""

    assert Function(fn).source == string
    assert Function(string).source == string
    assert Function(fn).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_bool_defaults():
    """
    args uses the Tokenizer module, which picks up entities like bool and True
    """

    def fn(a: bool = True):
        return a

    string = """
def fn(a: bool = True):
    return a"""

    string_mod = """def fn(a: bool = True, *args, **kwargs):
    return a"""

    assert Function(fn).source == string_mod
    assert Function(string).source == string_mod
    assert Function(fn).args == ["a", "*args", "**kwargs"]
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_return_annotation():
    """
    args uses the Tokenizer module, which picks up entities like bool and True
    """

    def fn(a: bool = True) -> bool:
        return a

    string = """
def fn(a: bool = True) -> bool:
    return a"""

    string_mod = """def fn(a: bool = True, *args, **kwargs) -> bool:
    return a"""

    assert Function(fn).source == string_mod
    assert Function(string).source == string_mod
    assert Function(fn).args == ["a", "*args", "**kwargs"]
    assert Function(string).args == ["a", "*args", "**kwargs"]


def test_return_annotation_search():
    """
    return_annotation can't just search for ->, because that's a valid string
    """

    def fn(right='->', *args, **kwargs):
        return right

    string = """def fn(right='->', *args, **kwargs):
    return right"""

    assert Function(fn).source == string
    assert Function(string).source == string
    assert Function(fn).args == ["right", "*args", "**kwargs"]
    assert Function(string).args == ["right", "*args", "**kwargs"]


def test_cache():
    """args is cached, make sure that calling it again doesn't cause issues"""

    def fn(a, b, c):
        return a + b + c

    string = """def fn(a, b, c):
    return a + b + c"""

    assert Function(fn).signature == "(a, b, c, *args, **kwargs)"
    assert Function(string).signature == "(a, b, c, *args, **kwargs)"
    assert Function(fn).args == ["a", "b", "c", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "c", "*args", "**kwargs"]

    assert Function(fn).args == Function(string).args


def test_class_fn_store():
    """Check that we can serialise the function of a class"""

    class Stub:

        def __init__(self):
            pass

        def function(self, *args, **kwargs) -> str:
            return 'foo'

    test = Stub()

    assert Function(test.function).source == """def function(self, *args, **kwargs) -> str:
    return 'foo'"""


def test_annotate_none():
    def typehints(a: int, b: str = 'none', **kwargs) -> None:
        # :
        return

    string = """def typehints(a: int, b: str = 'none', **kwargs) -> None:
    # :
    return"""

    string_mod = """def typehints(a: int, b: str = 'none', *args, **kwargs) -> None:
    # :
    return"""

    assert Function(typehints).source == string_mod
    assert Function(string).source == string_mod

    assert Function(typehints).args == ["a", "b", "*args", "**kwargs"]
    assert Function(string).args == ["a", "b", "*args", "**kwargs"]


def test_renamed_args_wildcard():
    def renamed_args(a: int, *new_args):
        return

    string = """def renamed_args(a: int, *new_args):
    return"""

    string_mod = """def renamed_args(a: int, *new_args, **kwargs):
    return"""

    assert Function(renamed_args).source == string_mod
    assert Function(string).source == string_mod

    assert Function(renamed_args).args == ["a", "*new_args", "**kwargs"]
    assert Function(string).args == ["a", "*new_args", "**kwargs"]


def test_renamed_kwargs_wildcard():
    def renamed_kwargs(a: float, **new_kwargs):
        return

    string = """def renamed_kwargs(a: float, **new_kwargs):
    return"""

    string_mod = """def renamed_kwargs(a: float, *args, **new_kwargs):
    return"""

    assert Function(renamed_kwargs).source == string_mod
    assert Function(string).source == string_mod

    assert Function(renamed_kwargs).args == ["a", "*args", "**new_kwargs"]
    assert Function(string).args == ["a", "*args", "**new_kwargs"]


def test_renamed_both_wildcards():
    def renamed_both(a: bool, *new_args, **new_kwargs):
        return

    string = """def renamed_both(a: bool, *new_args, **new_kwargs):
    return"""

    string_mod = """def renamed_both(a: bool, *new_args, **new_kwargs):
    return"""

    assert Function(renamed_both).source == string_mod
    assert Function(string).source == string_mod

    assert Function(renamed_both).args == ["a", "*new_args", "**new_kwargs"]
    assert Function(string).args == ["a", "*new_args", "**new_kwargs"]


def test_inner_function():
    """tests a simple function"""

    def fn(a):
        def inner_function(foo):
            return foo

        return inner_function(a)

    string = """def fn(a):
    def inner_function(foo):
        return foo
    return inner_function(a)"""

    assert Function(fn).signature == "(a, *args, **kwargs)"
    assert Function(string).signature == "(a, *args, **kwargs)"
    assert Function(fn).args == ["a", "*args", "**kwargs"]
    assert Function(string).args == ["a", "*args", "**kwargs"]

    assert "def inner_function" in Function(fn).source
    assert "def inner_function" in Function(string).source


def test_at_char():
    """tests a function containing the @ char"""

    def fn():
        # @ should not be ignored
        return

    string = """def fn():
    # @ should not be ignored
    return"""

    assert Function(fn).signature == "(*args, **kwargs)"
    assert Function(string).signature == "(*args, **kwargs)"
    assert Function(fn).args == ["*args", "**kwargs"]
    assert Function(string).args == ["*args", "**kwargs"]

    assert "@" in Function(fn).source
    assert "@" in Function(string).source


@pytest.mark.skip(reason=
                  "This 'works', but renames new_args, new_kwargs. "
                  "This is, however, bad syntax. Should we test for this?"
                  )
def test_renamed_both_wildcards_no_spaces():
    def renamed_both_nospace(a: bool, *new_args, **new_kwargs):
        return

    string = """def renamed_both_nospace(a:bool,*new_args,**new_kwargs):
    return"""

    string_mod = """def renamed_both_nospace(a: bool, *new_args, **new_kwargs):
    return"""

    assert Function(renamed_both_nospace).source == string_mod
    assert Function(string).source == string_mod

    assert Function(renamed_both_nospace).args == ["a", "*new_args", "**new_kwargs"]
    assert Function(string).args == ["a", "*new_args", "**new_kwargs"]
