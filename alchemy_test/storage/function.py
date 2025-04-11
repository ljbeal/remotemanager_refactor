import importlib.util
import inspect
import os
import re
from typing import Any, Callable, Dict, List, Union

from alchemy_test.utils.tokenizer import Tokenizer
from alchemy_test.utils.uuidmixin import UUIDMixin


_SCRIPT_TEMPLATE = """
{function}

if __name__ == '__main__':
\tkwargs = {args}

\tresult = {name}(**kwargs)
"""

SIG_END_REGEX = re.compile(r"\).*:")

ARGS_REGEX_PATTERN = r"(\s|\()(\*{1}[\w]+)"
KWARGS_REGEX_PATTERN = r"(\s|\()(\*{2}[\w]+)"


def line_is_end_of_function(line: str) -> bool:
    """Returns True if the line is the end of a function definition"""
    return re.search(SIG_END_REGEX, line) is not None


class Function(UUIDMixin):
    """
    Serialise function to an executable python file for transfer

    Args:
        func:
            python function for serialisation
    """

    __slots__ = ["_uuid", "_source", "_fname", "_signature", "_arglist"]

    def __init__(self, func: Union[Callable[..., Any], str], force_self: bool = False):

        # collect the source, name and signature
        if isinstance(func, str):
            source = func
            # need to extract the name and signature
            name = re.search(r"def\s(\w+)\(", source)
            if name is None:
                raise ValueError(f"Could not find function name in source code {source}")            
            name = name.group(1)

            signature_cache: List[str] = []
            for line in func.split("\n"):
                line = line.split("#", maxsplit=1)[0]
                if line.startswith("def"):
                    # drop the "def funcname(", keep the signature
                    line = line.split("(", maxsplit=1)[1]

                signature_cache.append(line)
                if line_is_end_of_function(line):
                    # if we've reached the end of the signature, break
                    break

            signature = "\n".join(signature_cache).strip(":")

        else:
            source = inspect.getsource(func)
            name = func.__name__
            signature = inspect.signature(func)

        if name in ["remote_load", "remote_dump"]:
            raise ValueError(f'function name "{name}" is protected')

        tmp: List[str] = []
        indent = -1
        is_self = force_self  # default to False, allow forcing
        append = False  # don't begin the append until we hit the `def ...` line
        for line in source.split("\n"):
            if indent == -1 and line.strip().startswith("def"):
                if "(self" in line:
                    is_self = True
                append = True
                indent = line.index("def")

            if append:
                tmp.append(line[indent:])

        source = "\n".join(tmp).strip()

        self._signature = Function.prepare_signature(signature, is_self=is_self)
        self._arglist: Union[List[str], None] = None
        self._fname: str = name

        rawsig = Function.get_raw_signature(source)

        source = self.replace_signature(source, rawsig, self.signature)

        if "**" not in source:  # check only for ** logic, since it could be renamed
            raise RuntimeError(f"**kwarg insertion failed for function:\n{source}")

        self._source = source

        self._uuid = self.generate_uuid(self._source)

    def __call__(self, *args: Any, **kwargs: Any):
        return self.object(*args, **kwargs)

    @staticmethod
    def get_raw_signature(source: str):
        """
        Strips the signature as it is typed.
        inspect.signature does some formatting which can cause replacement to
        break in some conditions

        Args:
            source (str):
                raw source

        Returns:
            (str): raw signature as typed
        """
        definition: List[str] = []
        for line in source.split("\n"):
            line = line.split("#")[0].strip()
            # we need to split from the function name for the raw signature
            if "(" in line:
                # split from first ( and up,
                # then join for any tuples defined as default
                line = "(" + "(".join(line.split("(")[1:])

            # appending the final ":" causes issues, strip that in a safe
            # manner then append
            definition.append(line.rstrip(" ").rstrip(":"))

            # we've reached the end of the definition
            if line.endswith(":"):
                break

        return "\n".join(definition)

    @staticmethod
    def prepare_signature(signature: Union[str, inspect.Signature], is_self: bool = False) -> str:
        """
        Inserts *args and **kwargs into any signature that does not already
        have it

        Args:
            sig:
                inspect.signature(func)
            is_self:
                inspect.signature ignores `self`, yet we want to preserve it.
                Adds the argument if True

        Returns:
            (str): formatted sig
        """
        if isinstance(signature, str):
            match = re.compile(r"->[^)]*:")
            return_annotation = re.findall(match, signature + ":")

            if len(return_annotation) == 0:
                return_annotation = None
            else:
                return_annotation = return_annotation[0].strip("->").strip(":").strip()

            signature = signature[: signature.rindex(")")]
            signature = signature.strip("(")
            args = [a.strip() for a in signature.split(",") if a.strip() != ""]
        else:
            args = [str(a) for a in signature.parameters.values()]

            return_annotation = signature.return_annotation

            # if return_annotation is None, we can't call "__name__" on it directly
            if return_annotation is not None:
                return_annotation = return_annotation.__name__
            else:
                return_annotation = "None"

        if return_annotation == "_empty":
            return_annotation = None

        if is_self and "self" not in args:
            args = ["self"] + args

        has_args = re.search(ARGS_REGEX_PATTERN, f"({signature})") is not None
        has_kwargs = re.search(KWARGS_REGEX_PATTERN, f"({signature})") is not None

        if not has_args:
            if has_kwargs:
                args.insert(-1, "*args")
            else:
                args.append("*args")

        if not has_kwargs:
            args.append("**kwargs")

        signature = f'({", ".join(args)})'
        if return_annotation is None:
            return signature
        return f"{signature} -> {return_annotation}"

    def replace_signature(self, source: str, rawsig: str, signature: str) -> str:
        """
        Performs replacement of the original "raw" signature
        with one with inserted *args, **kwargs
        """
        if len(rawsig.split("\n")) == 1:
            # direct replacement
            return source.replace(rawsig, signature, 1)
        # if we have multiple lines, we can recreate the "true" signature
        output: List[str] = []
        append = True
        replaced = False
        for line in source.split("\n"):
            if "def" in line and not replaced:
                output.append(f"def {self.name}{self.signature}:")
                append = False
                replaced = True

            if append:
                output.append(line.rstrip())
            else:
                append = line_is_end_of_function(line)

        return "\n".join(output)

    @property
    def name(self) -> str:
        """
        Function name
        """
        return self._fname

    @property
    def raw_source(self) -> str:
        """
        Function source
        """
        return self._source

    @property
    def source(self) -> str:
        """
        Function source

        Returns:
            (str): source code
        """
        return self._source

    @property
    def return_annotation(self) -> Union[str, None]:
        if "->" in self.signature:
            return self.signature.split("->")[-1].strip()
        return None

    @property
    def signature(self) -> str:
        return self._signature

    @property
    def args(self) -> List[str]:
        """returns a list of arguments, without annotations or defaults"""
        if self._arglist is not None:
            return self._arglist

        names = Tokenizer(self.signature).names

        args_name = re.search(ARGS_REGEX_PATTERN, self.signature)
        if args_name is None:
            raise ValueError(f"Invalid signature: {self.signature}")
        args_name = args_name.groups()[-1].strip()

        kwargs_name = re.search(KWARGS_REGEX_PATTERN, self.signature)
        if kwargs_name is None:
            raise ValueError(f"Invalid signature: {self.signature}")
        kwargs_name = kwargs_name.groups()[-1].strip()

        # extract everything up to but not including *args, **kwargs and annotation
        names = names[: names.index(args_name.strip("*"))]

        # if we strip all spaces from the signature, then valid tokens must
        # present in the form ",{token}" or "({token}"
        compact = self.signature.replace(" ", "")
        output: List[str] = []
        for token in names:
            if f",{token}" in compact or f"({token}" in compact:
                output.append(token)
        output += [args_name, kwargs_name]
        self._arglist = output  # cache the args
        return output

    @property
    def object(self):
        """
        Recreates the function object by writing out the source, and importing.

        Returns:
            typing.Callable:
                the originally passed function
        """

        tmp_file = ""
        try:
            tmp_file = os.path.abspath(f"{self.uuid}.py")

            with open(tmp_file, "w+") as o:
                o.write(self.source)

            spec = importlib.util.spec_from_file_location(self.uuid, tmp_file)
            if spec is None:
                raise RuntimeError("Failed to create spec for import")
            if spec.loader is None:
                raise RuntimeError("Failed to create spec loader for import")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            func_object = getattr(module, f"{self.name}")

        finally:
            os.remove(tmp_file)

        return func_object

    def dump_to_string(self, args: Union[Dict[Any, Any], None]) -> str:
        """
        Dump this function to a serialised string, ready to be written to a
        python file

        Args:
            args (dict):
                arguments to be used for this dumped run

        Returns:
            (str):
                serialised file
        """

        if args is None:
            args = {}

        return _SCRIPT_TEMPLATE.format(
            function= self.source, name = self.name, args = args
        )
