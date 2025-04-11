from typing import Any, Callable

from alchemy_test.storage.function import Function


class Process:

    __slots__ = ["_function"]

    def __init__(self, function: Callable[..., Any], **run_args: Any) -> None:
        self._function = Function(function)

    def __repr__(self) -> str:
        # return a string representation of this Process instance
        return f"Process({self._function})"

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # "direct" call for now, until we implement remote methods
        # call the function with the provided arguments
        result = self.function(*args, **kwargs)
        # return the result of the function
        return result
    
    @property
    def function(self) -> Function:
        # return the function object associated with this Process instance
        return self._function


def process(**run_args: Any) -> Callable[..., Any]:
    """
    Decorator stub to generate a Process class from a function

    Wraps the function, returning a Process which contains it
    """
    def decorate(function: Callable[..., Any]) -> Process:
        return Process(function, **run_args)
    return decorate


if __name__ == "__main__":

    @process(url="foo")
    def test(x: int) -> int:
        return x
    
    print(test)
