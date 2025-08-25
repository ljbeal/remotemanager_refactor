class SubmissionError(Exception):
    """
    Exception to track submission failure

    Args:
        message:
            error message
    """

    def __init__(self, message: str) -> None:
        self.messsage = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"SubmissionError({self.messsage})"


class RunnerFailedError(Exception):
    """
    Exception to be raised in lieu of a missing result due to a failure.

    Args:
        message:
            error message
    """

    def __init__(self, message: str) -> None:
        self.messsage = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"RunnerFailedError({self.messsage})"
