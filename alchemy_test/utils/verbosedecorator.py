"""Mixin class to provide underlying verbose properties"""

from typing import Union

from alchemy_test.utils.verbosity import Verbosity


# pylint: disable=protected-access
def make_verbose(cls: type):
    """
    Adds the correct verbose properties to the class cls

    Args:
        cls:
            class to treat

    Returns:
        cls, modified
    """

    def get_verbose(self: type) -> Verbosity:
        """
        Return the current verbosity setting

        Returns:
            (Verbosity): current verbosity
        """
        if not isinstance(self._verbose, Verbosity):  # type: ignore
            self._verbose = Verbosity(self._verbose)  # type: ignore
        return self._verbose

    def set_verbose(self: type, verbose: Union[None, int, bool, Verbosity]) -> None:
        """
        Verbosity setter
        """
        self._verbose = Verbosity(verbose)

    cls._verbose = Verbosity()

    prop = property(fset=set_verbose, fget=get_verbose, doc="Verbose property")
    cls.verbose = prop

    return cls
