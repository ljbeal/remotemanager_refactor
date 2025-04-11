from typing import Any, Callable, Dict, List, Union

from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.engine.filehandler import FileHandler
from alchemy_test.storage.function import Function
from alchemy_test.engine.runner.runner import Runner


class ProcessHandler(ExecArgsMixin):
    """
    Process is the main class used to tie Runners together

    It performs two main tasks:
     - User interace
     - Runner communication
    
    The first task is handled by being the main API endpoint that the user interacts with.

    In the background, there is little logic actually happening on the Process itself, as most is 
    deferred to the Runner.

    A Process can be created by the process decorator, which will handle the wrapping for you.
    """

    __slots__ = ["_function", "_runners", "_name", "_files"]

    def __init__(self, function: Callable[..., Any], name: Union[str, None] = None, **exec_args: Any) -> None:
        self._function = Function(function)

        self._exec_args = exec_args

        if name is None:
            name = f"Process-{self.function.name}"
        self._name = name

        self._runners: Dict[str, Runner] = {}

        self._files = FileHandler(
            local_dir=self.local_dir,
            remote_dir=self.remote_dir,
            filenames=["master.sh", "repo.py"],
        )
    

    def __repr__(self) -> str:
        # return a string representation of this Process instance
        return f"Process({self._function})"

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Performs a single run with the given args
        """
        # "direct" call for now, until we implement remote methods
        # call the function with the provided arguments
        result = self.function(*args, **kwargs)
        # return the result of the function
        return result
    
    @property
    def function(self) -> Function:
        """
        Returns the stored Function object
        """
        return self._function
    
    @property
    def name(self) -> str:
        """
        Returns the name of this process
        """
        return self._name
    
    @property
    def files(self) -> FileHandler:
        """
        Returns the FileHandler object associated with this process
        """
        return self._files
    
    @property
    def runners(self) -> List[Runner]:
        """
        Returns the list of runners associated with this process
        """
        return list(self._runners.values())
    
    def add_runner(self, call_args: Dict[Any, Any], exec_args: Dict[Any, Any]) -> bool:
        """
        Adds a new runner to the process with the given arguments
        """
        runner = Runner(idx=len(self.runners), parent=self, call_arguments=call_args, exec_arguments=exec_args)

        if runner.uuid not in self._runners:
            self._runners[runner.uuid] = runner

            return True
        return False
    
    def prepare(self, exec_args: Union[Dict[Any, Any], None] = None, **call_args):
        """
        Prepares the process with the given exec arguments and call arguments
        """
        if exec_args is None:
            exec_args = {}

        self.add_runner(call_args=call_args, exec_args=exec_args)
    
    def run(self) -> None:
        """
        Either runs a single runner with the given args, or runs all prepared runners

        Returns:
            bool: True if the process was executed, False otherwise (in a skip or no-runner situation)
        """
        self.runners[0].run()


def Process(**run_args: Any) -> Callable[..., Any]:
    """
    Decorator stub to generate a Process class from a function

    Wraps the function, returning a Process which contains it
    """
    def decorate(function: Callable[..., Any]) -> ProcessHandler:
        return ProcessHandler(function, **run_args)
    return decorate
