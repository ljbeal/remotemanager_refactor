from typing import Any


def ensure_list(inp: Any = None, semantic: bool = False) -> list:
    """
    Ensure that `inp` is list-type

    .. note::
        None is a special case, returning an empty list, rather than [None]

    Args:
        inp:
            list, string, object to be processed
        semantic (bool):
            attempts to treat comma (or space) separated strings as lists
            e.g. "a,b,c" will return ["a", "b", "c"]

    Returns (list):
        Either inserts the object into a list, or returns the list-like inp
    """
    if inp is None:
        return []
    if isinstance(inp, dict):
        return [inp]
    if isinstance(inp, (list, tuple, set)):
        return list(inp)
    if isinstance(inp, (str, int, float)) and not semantic:
        return [inp]

    if semantic and isinstance(inp, str):
        # a "semantic" list is used for situations like template `replaces`
        # and should handle comma/space separated "lists" in a string
        if "," in inp:
            splitchar = ","
        else:
            splitchar = None
        return [item.strip() for item in inp.split(splitchar)]

    try:
        return list(inp) # type: ignore
    except TypeError:
        return [inp]
