from enum import Enum


class RunnerState(Enum):
    CREATED = 0
    STAGED = 1
    TRANSFERRED = 2
    SUBMITTED = 3
    RUNNING = 4
    COMPLETED = 5
    FAILED = 6

    def __lt__(self, other: "RunnerState"):
        return self.value < other.value

    def __le__(self, other: "RunnerState"):
        return self.value <= other.value

    def __gt__(self, other: "RunnerState"):
        return self.value > other.value

    def __ge__(self, other: "RunnerState"):
        return self.value >= other.value

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value)

    def __ne__(self, value: object) -> bool:
        return super().__ne__(value)
