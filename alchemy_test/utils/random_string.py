import random
from typing import List


def random_string(length: int = 16) -> str:
    """Creates a random string of hexadecimal characters of len `len`"""
    choices = list(range(9)) + ["a", "b", "c", "d", "e", "f"]
    output: List[str] = []
    for _ in range(length):
        output.append(str(random.choice(choices)))

    return "".join(output)
