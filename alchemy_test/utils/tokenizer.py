"""Module to store the tokenizer class"""

import tokenize
from typing import List, Tuple, Union


class Tokenizer:
    """
    tokenize.generate_tokens() requires a file-like object to function

    This class mimics this behaviour by raising StopIteration once the
    end of the content is reached.
    """

    __slots__ = ["content", "row", "_tokens", "_names", "_numbers"]

    def __init__(self, content: str):
        self.content = content.split("\n")
        self.row = 0

        self._names: Union[List[str], None] = None
        self._numbers: Union[List[str], None] = None

        self._tokens: List[Tuple[int, str]] = []
        self.tokenize()

    def __call__(self) -> Union[str, StopIteration]:
        if self.row == len(self.content):
            self.row = 0  # reset
            raise StopIteration
        line = self.content[self.row]
        self.row += 1
        return line

    def tokenize(self) -> List[Tuple[int, str]]:
        """Runs the tokenization"""
        if len(self._tokens) == 0:
            for token in tokenize.generate_tokens(self): # type: ignore
                self._tokens.append((token.type, token.string.strip()))
        return self._tokens

    @property
    def tokens(self) -> List[Tuple[int, str]]:
        """
        Returns all stored tokens

        list format is [(type, string), ...]
        """
        return self._tokens

    @property
    def names(self) -> List[str]:
        """Returns the derived name list"""
        if self._names is None:
            tmp: List[str] = []
            for token in self.tokens:
                if token[0] == 1 and token[1] not in tmp:
                    tmp.append(token[1])
            self._names = tmp
        return self._names

    @property
    def numbers(self) -> List[str]:
        """Returns a list of all numbers in the source"""
        if self._numbers is None:
            tmp: List[str] = []
            for token in self.tokens:
                if token[0] == 2 and token[1] not in tmp:
                    tmp.append(token[1])
            self._numbers = tmp
        return self._numbers

    def exchange_name(self, a: str, b: str):
        """
        Exchanges name a with name b
        """
        for i, token in enumerate(self.tokens):
            if token[1] == a:
                self._tokens[i] = (token[0], b)
        self._names = None  # invalidate the name cache

    @property
    def source(self):
        """
        Regenerate the source from the stored tokens

        untokenize is... unreliable, since it focuses on the
        repeatability of the round trip

        So we should reconstruct manually

        Key tokens:
        0: End marker
        1: Name
        2: Number
        3: String
        4: Newline
        5: Indent
        6: Dedent

        Returns:
            (str): reconstructed source
        """
        indent = 0
        output: List[str] = []
        tmp: List[str] = []
        for i, (ttype, token) in enumerate(self.tokens):
            if ttype in (0, 4):
                output.append("    " * indent + "".join(tmp))
                tmp = []
                continue
            if ttype == 5:
                output.append("    " * indent + "".join(tmp))
                tmp = []
                indent += 1
                continue
            if ttype == 6:
                output.append("    " * indent + "".join(tmp))
                tmp = []
                indent -= 1

            # If the current token is a registered name, and is followed
            # immediately by another, add a space to separate them
            try:
                nexttype = self.tokens[i + 1][0]
            except AttributeError:
                nexttype = 0

            if token in self.names and nexttype == 1:
                token += " "

            tmp.append(token)

        return "\n".join(output).strip()
