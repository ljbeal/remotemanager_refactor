from typing import Any, Callable, Dict


class Process:

    __slots__ = ["_function"]

    def __init__(self, function: Callable[..., Any], **run_args: Dict[Any, Any]) -> None:
        print(f"Creating Process wrapper for function {function}")
        print(f"Run args: {run_args}")

        self._function = function


def process(**run_args: Dict[Any, Any]) -> Callable[..., Any]:
    """
    Decorator stub to generate a Process class from a function

    Wraps the function, returning a Process which contains it
    """
    def decorate(function: Callable[..., Any]) -> Process:
        return Process(function, **run_args)
    return decorate


if __name__ == "__main__":

    @process()
    def test(x: int) -> int:
        return x
    
    print(test)
