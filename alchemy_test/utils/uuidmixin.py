import hashlib
from typing import Any

from alchemy_test.utils.format_iterable import format_iterable


class UUIDMixin:
    
    _uuid = NotImplemented

    @property
    def uuid(self) -> str:
        return self._uuid
    
    @property
    def short_uuid(self) -> str:
        return self.uuid[:8]
    
    def generate_uuid(self, input: Any) -> str:
        """
        Generates and sets a UUID string from an input

        Args:
            string:
                input string
        Returns:
            (str) UUID
        """
        if not isinstance(input, str):
            input = format_iterable(input)
        h = hashlib.sha256()
        h.update(bytes(input, "utf-8"))

        uuid = str(h.hexdigest())

        self._uuid = uuid

        return uuid
