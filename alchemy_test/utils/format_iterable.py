from typing import Any, Dict, Iterable, List, Union


INDENT_CHAR = "   "


def format_iterable(
    iterable: Iterable[Any], 
    exclude: Union[List[str], str, None] = None, 
    print_types: bool = False, 
    indent: int = 1
) -> str:
    """
    Recursive formatting of an iterable, producing log-safe string

    Arguments:
        iterable (list, tuple, set, dict):
            iterable to sort
        exclude (list, optional):
            keys to exclude
        indent (int, optional):
            indent level for recursion

    Returns:
        (str):
            newline separated string
    """

    if exclude is None:
        exclude = []
    elif isinstance(exclude, str):
        exclude = [exclude]

    def treat_dict(inp: Dict[Any, Any]) -> str:
        ret: List[str] = []
        for a in sorted(inp.keys()):
            v = inp[a]

            if a not in exclude:
                if type(v) in dispatch.keys():
                    v = format_iterable(
                        iterable=v,
                        exclude=exclude,
                        print_types=print_types,
                        indent=indent + 1,
                    )
                content = f"{a}: {v}"
                if print_types:
                    content = f"{a}: {v} ({type(v)})"
                ret.append(INDENT_CHAR * indent + content)

        return "\n" + "\n".join(ret)

    def treat_iterable(inp: Iterable[Any]) -> str:
        ret: List[str] = []
        for v in inp:
            if v not in exclude:
                if type(v) in dispatch.keys():
                    v = format_iterable(iterable=v, exclude=exclude, indent=indent + 1)
                ret.append(INDENT_CHAR * (indent - 1) + f"- {v}")

        return "\n" + "\n".join(ret)

    def treat_printable(inp: str) -> str:
        return inp
    # can hit empty lists (often in recursion)
    # output looks nicer if they're output without formatting
    try:
        if len(iterable) == 0: # type: ignore
            return "\n" + INDENT_CHAR * indent + f"{iterable}"
    except TypeError:
        return treat_printable(iterable) # type: ignore

    dispatch = { # type: ignore
        dict: treat_dict,
        list: treat_iterable,
        tuple: treat_iterable,
        set: treat_iterable,
        str: treat_printable,
        type: treat_printable,
    }
    return dispatch[type(iterable)](iterable) # type: ignore
