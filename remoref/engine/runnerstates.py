import datetime
from typing import Optional, Union

from remoref.engine.repo import date_format


valid_states = {
    "CREATED": 0,
    "STAGED": 1,
    "TRANSFERRED": 2,
    "SUBMITTED": 3,
    "RUNNING": 4,
    "COMPLETED": 5,
    "FAILED": 5,
}


class State:
    __slots__ = ["state", "value", "_ts"]

    def __init__(
        self, state: str, timestamp: Optional[Union[int, float]] = None
    ) -> None:
        state = state.upper()

        if state not in valid_states:
            raise ValueError(f"State ({state}) must be one of:\n{valid_states}")

        self.state = state
        self.value = valid_states[state]

        if timestamp is not None:
            self._ts = int(timestamp)
        else:
            self._ts = -1

    def __repr__(self) -> str:
        return f"State({self.state}, timestamp={self._ts})"

    def __str__(self) -> str:
        return f"State {self.state} @ {self.time}"

    def __lt__(self, other: "State") -> bool:
        return self.value < other.value

    def __le__(self, other: "State") -> bool:
        return self.value <= other.value

    def __gt__(self, other: "State") -> bool:
        return self.value > other.value

    def __ge__(self, other: "State") -> bool:
        return self.value >= other.value

    def __eq__(self, value: object) -> bool:
        if isinstance(value, State):
            return self.value == value.value
        return False

    def __ne__(self, value: object) -> bool:
        return super().__ne__(value)

    @property
    def failed(self) -> bool:
        return self.state == "FAILED"

    @property
    def timestamp(self) -> int:
        return self._ts

    @property
    def time(self) -> str:
        return datetime.datetime.fromtimestamp(self.timestamp).strftime(date_format)
