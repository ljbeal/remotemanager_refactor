"""Verbosity enables deeper verbose levels than True and False"""

from typing import Union

_default_level = 1

class Verbosity:
    """
    Class to store verbosity information

    Initialise with Verbosity(level), where level is the integer level

    Printing can be requested with Verbose.print(msg, level)

    If the verbose level is set above `level`, the message will be printed

    args:
        level (int, bool, Verbosity):
            level above which to print
    """

    __slots__ = ["_level"]

    def __init__(self, level: Union[None, int, bool, "Verbosity"] = None):
        if level is None:
            level = _default_level
        # see if the level passed is already a Verbose instance
        elif isinstance(level, Verbosity):
            level = level.value
        elif isinstance(level, bool):
            level = int(level)

        self._level: int = level

    def __repr__(self) -> str:
        return f"Verbosity({self.level})"

    def __bool__(self) -> bool:
        return self.level != 0
    
    @property
    def level(self) -> int:
        return self._level

    def _prepare_other_for_comparison(self, other: object) -> int:
        if isinstance(other, self.__class__):
            return other.level
        if isinstance(other, int):
            return other
        raise ValueError("Unsupported type for comparison")

    def __eq__(self, other: object) -> bool:
        return self.level == self._prepare_other_for_comparison(other)

    def __lt__(self, other: object) -> bool:
        return self.level < self._prepare_other_for_comparison(other)

    def __le__(self, other: object) -> bool:
        return self.level <= self._prepare_other_for_comparison(other)

    def __gt__(self, other: object) -> bool:
        return self.level > self._prepare_other_for_comparison(other)

    def __ge__(self, other: object) -> bool:
        return self.level >= self._prepare_other_for_comparison(other)

    @property
    def value(self) -> int:
        """Alias for self.level"""
        return self.level

    def print(self, message: str, level: int, end: str = "\n"):
        """
        Request that a message be printed. Compares against the set
        verbosity level before printing.

        Args:
            message (str):
                message to print
            level (int):
                If this number is higher priority than (lower numeric value)
                (or equal to) the set limit, print
            end (str):
                print(..., end= ...) hook
        """
        # print(f'request {message[:24]} @ {atlevel}')
        if self and self.level >= level:
            print(message, end=end)


class VerboseMixin:
    
    _verbose = Verbosity(1)

    @property
    def verbose(self) -> Verbosity:
        """Verbose property"""
        return self._verbose
    
    @verbose.setter
    def verbose(self, value: Union[None, int, bool, Verbosity]) -> None:
        """Verbosity setter"""
        self._verbose = Verbosity(value)
