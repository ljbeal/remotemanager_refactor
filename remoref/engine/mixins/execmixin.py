from typing import Any, Dict, Union

from remoref.engine.runnerstates import RunnerState


class ExecMixin:
    """
    This mixin class handles execution args like directories and environment variables

    Also makes common args available and provides defaults for them
    """

    _exec_args: Dict[Any, Any] = {}
    _temp_exec_args: Dict[Any, Any] = {}
    _stdout = None
    _stderr = None

    _state = RunnerState.CREATED

    @property
    def exec_args(self) -> Dict[Any, Any]:
        cache = self._exec_args.copy()
        cache.update(self._temp_exec_args)
        return cache

    @property
    def local_dir(self) -> str:
        return self.exec_args.get("local_dir", "temp_process_local")

    @property
    def remote_dir(self) -> str:
        return self.exec_args.get("remote_dir", "temp_process_remote")

    @property
    def skip(self) -> bool:
        return self.exec_args.get("skip", True)

    @property
    def stdout(self) -> Union[None, str]:
        return self._stdout

    @stdout.setter
    def stdout(self, stdout: str) -> None:
        self._stdout = stdout

    @property
    def stderr(self) -> Union[None, str]:
        return self._stderr

    @stderr.setter
    def stderr(self, stderr: str) -> None:
        self._stderr = stderr

    @property
    def state(self) -> RunnerState:
        return self._state

    @state.setter
    def state(self, value: RunnerState):
        if not isinstance(value, RunnerState):  # type: ignore
            raise ValueError(f"Expected a RunnerState, got {value}")
        self._state = value
