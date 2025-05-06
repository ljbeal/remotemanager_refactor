import re

import logging
from typing import Dict, List, Tuple, Union

logger = logging.getLogger(__name__)


class Flags:
    """
    Basic but flexible handler for terminal command flags

    Allows for inplace modification:

    >>> f = Flags('abcdd')
    >>> f -= 'd'
    >>> f.flags
    >>> '-abcd'

    Arguments:
        initial_flags (str):
            initial base flags to be used and modified if needed
    """

    def __init__(self, initial_flags: Union[str, List[str]] = ""):
        self._flags: Dict[str, List[str]] = {}
        if not isinstance(initial_flags, str):
            iflags = " ".join(initial_flags)
        else:
            iflags = initial_flags

        logger.debug("creating Flags with initial flags %s", iflags)

        self.flags = iflags

    def __repr__(self):
        return self.flags

    def _add(self, section: str):
        raw, prefix = self.parse_string(section)
        if prefix == "-":
            self.ensure_prefix_exists(prefix)
            self._flags["-"] += list(raw)
        else:
            self.ensure_prefix_exists(prefix)
            self._flags[prefix].append(raw)

        logger.debug("adding %s to flags. Flags are now %s", raw, self.flags)

    def __add__(self, other: str):
        sections = other.split(" ")
        for section in sections:
            self._add(section)

    def __iadd__(self, other: str):
        self.__add__(other)
        logger.debug("adding %s to flags inplace. Flags are now %s", other, self.flags)
        return self

    def _sub(self, section: str):
        raw, prefix = self.parse_string(section)
        if prefix == "-":
            for char in raw:
                try:
                    self._flags["-"].remove(char)
                except ValueError:
                    pass
        else:
            try:
                self._flags["--"].remove(raw)
            except ValueError:
                pass

        logger.debug("subtracting %s from flags. Flags are now %s", raw, self.flags)

    def __sub__(self, other: str):
        """Subtract unique flags in `other` once."""
        sections = other.split(" ")
        for section in sections:
            self._sub(section)

    def __isub__(self, other: str):
        self.__sub__(other)
        logger.debug(
            "subtracting %s from flags inplace. Flags are now %s", other, self.flags
        )
        return self

    def ensure_prefix_exists(self, prefix: str):
        """Ensures that the prefix exists in the internal storage, creating
        it if not"""
        if prefix not in self._flags:
            self._flags[prefix] = []

    def parse_string(self, string: str) -> Tuple[str, str]:
        """
        Takes a string, and strips away any non-alphanumeric chars.
        Returns True in secondary return if this is a verbose flag

        Args:
            string (str):
                input flags

        Returns (str, bool):
            filtered input
            True if this is a verbose flag
        """
        raw = strip_non_alphanumeric(string)
        num = string.count("-")

        # special case
        if num == 0:
            num = 1

        return raw, "-" * num

    @property
    def flags(self) -> str:
        """Returns the fully qualified flags as a string"""
        if sum([len(f) for f in self._flags.values()]) == 0:
            logger.info("sum of lens is 0, returning ''")
            return ""
        logger.info("creating string from internal flags %s", self._flags)
        output: List[str] = []
        for prefix, flags in self._flags.items():
            if prefix == "-":
                output.append("-" + "".join(flags))
            else:
                output.append(prefix + f" {prefix}".join(flags))

        string = " ".join(output)
        logger.info("done -> %s", string)
        return string

    @flags.setter
    def flags(self, inp: str):
        """Set the flags to the new input

        Arguments:
            inp (str):
                new flags to use (will overwrite old ones)
        """
        self._flags = {}
        self.__add__(inp)


def strip_non_alphanumeric(string: str) -> str:
    """
    remove any non-alphanumeric strings from input string

    Args:
        string (str):
            input string

    Returns (str):
        input string, sans any non-alphanumeric chars

    """
    pattern = re.compile(r"[\W_]+", re.UNICODE)  # noqa: W605

    return pattern.sub("", string)
