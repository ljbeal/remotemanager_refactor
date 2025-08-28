import re
from typing import List, Optional, Union


default_ignore: List[str] = [r"(?i)(?:set|setting)\s?locale"]


def validate_error(stderr: Union[None, str], ignore: Optional[List[str]] = None) -> bool:
    """
    Given a stderr, run a list of "ignore" regex strings against it

    If any of these match, invalidate the error by returning False

    A good case of this is the perl `locale` error. Since it's never a valid
    reason to stop a run, we can safely ignore it by default
    """
    if stderr is None or stderr == "":
        return False
    
    if ignore is None:
        ignore = []

    for case in default_ignore + ignore:
        search = re.compile(case, flags=re.MULTILINE | re.IGNORECASE)
        match = re.search(search, stderr)

        if match is not None:
            return False
        
    return True
