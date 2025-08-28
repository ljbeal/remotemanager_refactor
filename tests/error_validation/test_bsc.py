from remoref.utils.validate_stderr import validate_error


errors = """unload bsc/1.0 (PATH, MANPATH)
Set INTEL compilers as MPI wrappers backend
load mkl/2025.1 (LD_LIBRARY_PATH)
load PYTHON/3.12.1 (PATH, MANPATH, LD_LIBRARY_PATH, LIBRARY_PATH
PKG_CONFIG_PATH, C_INCLUDE_PATH, CPLUS_INCLUDE_PATH, PYTHONHOME, PYTHONPATH)
"""


def test_bsc_errors():
    assert not validate_error(errors, [r"\b(load|unload)\s+(\w+)\/.*"])
