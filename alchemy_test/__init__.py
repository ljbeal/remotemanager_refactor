import os
from alchemy_test.engine.process import Process


__all__ = ["Process"]

__version__ = "0.0.1"



def get_package_root() -> str:
    """returns the abspath to the package root directory"""
    return os.path.normpath(
        os.path.join(os.path.abspath(__file__), os.pardir, os.pardir)
    )
