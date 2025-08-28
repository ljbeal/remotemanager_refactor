import pytest

from remoref.utils.validate_stderr import validate_error

# these strings are valid locale error strings, and should be skipped
fake_strings = [
    """received the following stderr:
perl: warning: Setting locale failed.
perl: warning: Please check that your locale settings:
	LANGUAGE = (unset),
	LC_ALL = (unset),
	LANG = "C.UTF-8"
    are supported and installed on your system.
perl: warning: Falling back to the standard locale ("C").""",
    "/etc/profile.d/lang.sh: line 19: warning: setlocale: LC_CTYPE: cannot change locale (UTF-8): No such file or directory",
    "SetLocale",
    "setLocale",
    "Setlocale",
    "setting locale",
    "settingLocale",
]

# these strings are probably "real" errors, and should be raised
real_strings = ["'locale' could not be found",
               "file 'locale' exists",
               "locale: command not found",
               "set"]

@pytest.mark.parametrize("string", fake_strings)
def test_fake(string: str):
    assert not validate_error(string)


@pytest.mark.parametrize("string", real_strings)
def test_real(string: str):
    assert validate_error(string)
