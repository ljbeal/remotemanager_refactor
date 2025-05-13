from typing import Any, Dict


class ExecArgsMixin:
    """
    This mixin class handles execution args like directories and environment variables

    Also makes common args available and provides defaults for them
    """
    
    _exec_args: Dict[Any, Any] = {}

    @property
    def exec_args(self) -> Dict[Any, Any]:
        return self._exec_args
    
    @property
    def local_dir(self) -> str:
        return self.exec_args.get("local_dir", "temp_process_local")
    
    @property
    def remote_dir(self) -> str:
        return self.exec_args.get("remote_dir", "temp_process_remote")
    
    @property
    def skip(self) -> bool:
        return self.exec_args.get("skip", True)
