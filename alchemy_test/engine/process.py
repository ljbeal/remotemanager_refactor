import time
from typing import Any, Callable, Dict, List, Optional, Union
import warnings

from alchemy_test.connection.cmd import CMD
from alchemy_test.connection.url import URL
from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.engine.files.filehandler import ExtraFilesMixin, FileHandlerBaseClass
from alchemy_test.engine.files.repo import Manifest
from alchemy_test.engine.runnerstates import RunnerState
from alchemy_test.storage.function import Function
from alchemy_test.engine.runner.runner import Runner
from alchemy_test.storage.trackedfile import TrackedFile
from alchemy_test.utils.uuidmixin import UUIDMixin
from alchemy_test.utils.verbosity import VerboseMixin, Verbosity


class ProcessFileHandler(FileHandlerBaseClass):
    """
    Extends the filehandler to contain Process related files
    """

    __slots__ = ["master", "repo", "manifest"]

    def __init__(
            self,
            master: TrackedFile,
            repo: TrackedFile,
            manifest: TrackedFile,
            ):
        super().__init__()

        self.master = master
        self.repo = repo
        self.manifest = manifest

        self._files = {
            "master": True,
            "repo": True,
            "manifest": None,
        }


class ProcessHandler(UUIDMixin, ExecArgsMixin, ExtraFilesMixin, VerboseMixin):
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

    def __init__(
            self,
            function: Callable[..., Any],
            name: Union[str, None] = None,
            url: Union[URL, None] = None,
            verbose: Union[Verbosity, int, bool, None] = None,
            extra_files_send: Optional[List[Union[str, TrackedFile]]] = None,
            extra_files_recv: Optional[List[Union[str, TrackedFile]]] = None,
            **exec_args: Any
        ) -> None:
        self._verbose = self.validate_verbose(verbose)

        self._function = Function(function)
        self._uuid = self.function.uuid

        self._exec_args: Dict[Any, Any] = {
            "asynchronous": True,
            "local_dir": "temp_local",
            "remote_dir": "temp_remote",
        }

        self._exec_args.update(exec_args)

        if name is None:
            name = f"Process-{self.function.name}"
        self._name = name

        self._runners: Dict[str, Runner] = {}

        self._files = ProcessFileHandler(
            master = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-master.sh"),
            repo = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-repository.py"),
            manifest = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-manifest.txt"),
        )

        if extra_files_send is not None:
            for file in extra_files_send:
                self.add_extra_send(file)
        if extra_files_recv is not None:
            for file in extra_files_recv:
                self.add_extra_recv(file)

        self._url = url

        self.run_cmd: Union[CMD, None] = None

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
    def url(self) -> URL:
        if self._url is None:
            self._url = URL()
        return self._url
    
    @property
    def files(self) -> ProcessFileHandler:
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
    
    @property
    def states(self) -> List[RunnerState]:
        """
        Returns the list of states associated with this process
        """
        return [r.state for r in self.runners]
    
    def add_runner(self, call_args: Dict[Any, Any], exec_args: Dict[Any, Any]) -> bool:
        """
        Adds a new runner to the process with the given arguments
        """
        runner = Runner(idx=len(self.runners), parent=self, call_arguments=call_args, exec_arguments=exec_args)

        if runner.uuid not in self._runners:
            self._runners[runner.uuid] = runner

            return True
        return False
    
    def prepare(self, **args: Any):
        """
        Prepares the process with the given exec arguments and call arguments
        """
        verbose = self.validate_verbose(args.get("verbose", None))
        # extract the "call args" from the original function arguments
        # any remaining args go into the "exec_args"
        call_args: Dict[Any, Any] = {}        
        for arg in self.function.orig_args:
            call_args[arg] = args.pop(arg, None)

        verbose.print(f"created runner with exec args: {args}", 3)

        self.add_runner(call_args=call_args, exec_args=args)

    def stage(self, verbose: Union[Verbosity, None] = None,  **exec_args: Any) -> bool:
        self._temp_exec_args = exec_args
        return self.runners[0].stage(verbose=verbose)
    
    def transfer(self, verbose: Union[Verbosity, None] = None, **exec_args: Any) -> bool:
        self._temp_exec_args = exec_args
        return self.runners[0].transfer(verbose=verbose)
    
    def run(self, verbose: Union[Verbosity, None] = None,  **exec_args: Any) -> bool:
        """
        Either runs a single runner with the given args, or runs all prepared runners

        Returns:
            bool: True if the process was executed, False otherwise (in a skip or no-runner situation)
        """
        self._temp_exec_args = exec_args
        return self.runners[0].run(verbose=verbose)

    def read_remote_manifest(self):
        cmd = self.url.cmd(f"cd {self.remote_dir} && cat {self.files.manifest.name}", raise_errors=False)

        if cmd.stderr is not None and "No such file or directory" in cmd.stderr:
            return

        for runner in self.runners:
            manifest = Manifest(content=cmd.stdout, uuid=runner.short_uuid)

            for state in manifest.state_list:
                truestate = getattr(RunnerState, state.upper(), None)
                if truestate is None:
                    warnings.warn(f"Unknown state '{state.upper()}' for runner {runner.short_uuid}")
                    continue

                runner.state = truestate

            runner.stdout = manifest.stdout
            runner.stderr = manifest.stderr

    @property
    def is_finished(self):
        error = None
        if self.run_cmd is not None:
            error = self.run_cmd.communicate(ignore_errors=True)["stderr"]

        if error is not None and error.strip() != "":
            raise RuntimeError(f"Encountered an error during submission:\n{error}")
        
        if self.run_cmd is not None and self.run_cmd.stderr is not None:
            if self.run_cmd.stderr.strip() != "":
                raise RuntimeError(f"Encountered an error during submission: {self.run_cmd.stderr}")

        self.read_remote_manifest()

        return [r.is_finished for r in self.runners]

    @property
    def all_finished(self):
        return all(self.is_finished)

    def wait(self, interval: Union[int, float] = 1, timeout: int = 10) -> None:
        has_run = False
        for runner in self.runners:
            if runner.state >= RunnerState.RUNNING:
                has_run = True
                break
        
        if not has_run:
            return

        dt = 0
        while dt < timeout:
            dt += interval

            if self.all_finished:
                return

            time.sleep(interval)

        raise RuntimeError("Wait Timed out")

    def fetch_results(self) -> bool:
        fetched = False
        for runner in self.runners:
            if runner.is_finished:
                for file in runner.files.files_to_recv:
                    self.url.transport.queue_for_pull(file)
                fetched = True
        
        self.url.transport.transfer()

        for runner in self.runners:
            runner.read_local_files()

        return fetched
    
    @property
    def results(self) -> List[Any]:
        return [r.result for r in self.runners]


def Process(**run_args: Any) -> Callable[..., Any]:
    """
    Decorator stub to generate a Process class from a function

    Wraps the function, returning a Process which contains it
    """
    def decorate(function: Callable[..., Any]) -> ProcessHandler:
        return ProcessHandler(function, **run_args)
    return decorate
