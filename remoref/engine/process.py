import re
import time
from typing import Any, Callable, Dict, List, Optional, Union
import warnings

from remotemanager.connection.cmd import CMD
from remotemanager.connection.url import URL
from remoref.engine.mixins.execmixin import ExecMixin
from remoref.engine.mixins.filehandler import ExtraFilesMixin, FileHandlerBaseClass
from remoref.engine.repo import Manifest
from remoref.engine.runnerstates import State, valid_states
from remoref.engine.runner import Runner
from remotemanager.storage.function import Function
from remotemanager.storage.trackedfile import TrackedFile
from remotemanager.utils.uuid import UUIDMixin
from remotemanager.utils.verbosity import VerboseMixin, Verbosity
from remoref.engine.exceptions import RunnerFailedError, SubmissionError


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


class ProcessHandler(UUIDMixin, ExecMixin, ExtraFilesMixin, VerboseMixin):
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
        **exec_args: Any,
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
            master=TrackedFile(
                self.local_dir, self.remote_dir, f"{self.name}-master.sh"
            ),
            repo=TrackedFile(
                self.local_dir, self.remote_dir, f"{self.name}-repository.py"
            ),
            manifest=TrackedFile(
                self.local_dir, self.remote_dir, f"{self.name}-manifest.txt"
            ),
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
    def states(self) -> List[State]:
        """
        Returns the list of states associated with this process
        """
        return [r.state for r in self.runners]

    def add_runner(self, call_args: Dict[Any, Any], exec_args: Dict[Any, Any]) -> bool:
        """
        Adds a new runner to the process with the given arguments
        """
        runner = Runner(
            idx=len(self.runners),
            parent=self,
            call_arguments=call_args,
            exec_arguments=exec_args,
        )

        if runner.uuid not in self._runners:
            self._runners[runner.uuid] = runner

            return True
        return False

    def prepare(self, *args: Any, **kwargs: Any):
        """
        Prepares the process with the given exec arguments and call arguments
        """
        if len(args) != 0:
            raise ValueError("Prepare must be called with keyword arguments")
        verbose = self.validate_verbose(kwargs.get("verbose", None))
        # extract the "call args" from the original function arguments
        # any remaining args go into the "exec_args"
        call_args: Dict[Any, Any] = {}
        for arg in self.function.orig_args:
            call_args[arg] = kwargs.pop(arg, None)

        verbose.print(f"created runner with exec args: {kwargs}", 3)

        self.add_runner(call_args=call_args, exec_args=kwargs)

    def stage(self, verbose: Union[Verbosity, None] = None, **exec_args: Any) -> bool:
        time.sleep(1)
        self._temp_exec_args = exec_args

        self.state = State("STAGED", time.time())

        return self.runners[0].stage(verbose=verbose)

    def transfer(
        self, verbose: Union[Verbosity, None] = None, **exec_args: Any
    ) -> bool:
        self._temp_exec_args = exec_args

        self.state = State("TRANSFERRED", time.time())

        return self.runners[0].transfer(verbose=verbose)

    def run(self, verbose: Union[Verbosity, None] = None, **exec_args: Any) -> bool:
        """
        Either runs a single runner with the given args, or runs all prepared runners

        Returns:
            bool: True if the process was executed, False otherwise (in a skip or no-runner situation)
        """
        self._temp_exec_args = exec_args

        success = self.runners[0].run(verbose=verbose)
        # a successful master execution should echo the short uuid of the Process
        if success and self.run_cmd is not None:
            self.run_cmd.communicate(ignore_errors=True)

            if self.run_cmd.stderr is not None and self.run_cmd.stderr != "":
                raise SubmissionError(
                    f"Encountered an error during submission:\n{self.run_cmd.stderr}"
                )

            elif self.short_uuid not in str(self.run_cmd.stdout):
                raise SubmissionError(
                    "Master script did not return the correct signal. File may be corrupt."
                )

        return success

    def run_direct(
        self,
        interval: int = 5,
        timeout: int = 300,
        verbose: Optional[Union[int, bool, Verbosity]] = None,
        **runner_args: Dict[Any, Any],
    ) -> List[Any]:
        verbose = self.validate_verbose(verbose=verbose)

        self.prepare(verbose=verbose, **runner_args)
        self.run(verbose=verbose)

        time.sleep(1)
        self.wait(interval=interval, timeout=timeout)
        self.fetch_results()

        return self.results

    def read_remote_manifest(self):
        cmd = self.url.cmd(
            f"cd {self.remote_dir} && cat {self.files.manifest.name}",
            raise_errors=False,
        )

        if cmd.stderr is not None and "No such file or directory" in cmd.stderr:
            # no file yet
            return

        for item in self.runners + [self]:
            manifest = Manifest(content=cmd.stdout, uuid=item.short_uuid)

            for ts, state in manifest.states:
                if state not in valid_states:
                    warnings.warn(
                        f"Unknown state '{state}' for runner {item.short_uuid}"
                    )
                    continue

                item.state = State(state, ts)

            if item.state.failed:
                if isinstance(item, Runner):
                    item._result = RunnerFailedError(manifest.stderr)  # type: ignore
                else:
                    raise SubmissionError(manifest.stderr)

            item.stdout = manifest.stdout
            item.stderr = manifest.stderr

    @property
    def is_finished(self) -> List[bool]:
        self.read_remote_manifest()

        # Check for submission errors
        if self.files.master.content is not None:
            # This checks for errors with the actual submitter
            submission_line_no = 0  # collect the line which deals with submission
            for i, line in enumerate(self.files.master.content.split("\n")):
                if line.endswith("# submission line"):
                    submission_line_no = i + 1
                    break
            # now see if we get a "command not found" at that line no.
            if self.stderr is not None:
                match = re.compile(f".*line {submission_line_no}:.*command not found")
                if re.match(match, self.stderr) is not None:
                    raise SubmissionError(f"Encountered an error during submisson. Is the submitter '{self.url.submitter}' correct?")

        states = [r.is_finished for r in self.runners]

        if all(states):
            self.state = State("COMPLETED", time.time())

        return states

    @property
    def all_finished(self):
        return all(self.is_finished)

    def wait(self, interval: Union[int, float] = 1, timeout: int = 10) -> None:
        has_run = False
        for runner in self.runners:
            if runner.state >= State("RUNNING"):
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
        transfer = False
        for runner in self.runners:
            if not runner.is_finished:
                continue

            if not runner.state.failed:
                for file in runner.files.files_to_recv:
                    self.url.transport.queue_for_pull(file)
                transfer = True

        if transfer:
            self.url.transport.transfer()

        for runner in self.runners:
            runner.read_local_files()

        return transfer

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
