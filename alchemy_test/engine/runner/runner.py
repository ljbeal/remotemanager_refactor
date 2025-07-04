import json
import os
from typing import TYPE_CHECKING, Any, Dict, List, Union

from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.engine.files.filehandler import ExtraFilesMixin, FileHandlerBaseClass
from alchemy_test.engine.runnerstates import RunnerState
from alchemy_test.storage.trackedfile import TrackedFile
from alchemy_test.utils.uuidmixin import UUIDMixin
from alchemy_test.utils.verbosity import VerboseMixin, Verbosity

import alchemy_test.engine.files.repo as repo

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.engine.process import ProcessHandler


class RunnerFileHandler(FileHandlerBaseClass):
    """
    Extends the filehandler to contain Process related files
    """

    def __init__(
            self,
            jobscript: TrackedFile,
            result: TrackedFile,
            ):
        super().__init__()

        self.jobscript = jobscript
        self.result = result

        self._files = {
            "jobscript": True,
            "result": False
        }


class Runner(UUIDMixin, ExecArgsMixin, ExtraFilesMixin, VerboseMixin):

    def __init__(
            self,
            idx: int,
            parent: "ProcessHandler",
            call_arguments: Dict[Any, Any], 
            exec_arguments: Dict[Any, Any],
        ):
        self._idx = idx
        self._parent = parent

        self._files = RunnerFileHandler(
            jobscript = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-jobscript.sh"),
            result = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-result.json")
        )

        for file in exec_arguments.pop("extra_files_send", []):
            self.add_extra_send(file)
        for file in exec_arguments.pop("extra_files_recv", []):
            self.add_extra_recv(file)
        
        self._remote_status: List[str] = []
        self._result = None
        
        self.stdout: str = ""
        self.stderr: str = ""
        
        self._call_args = call_arguments
        self._exec_args = exec_arguments

        self._uuid = self.generate_uuid(self.call_args)

        self._state = RunnerState.CREATED

    def __repr__(self) -> str:
        return self.name

    @property
    def idx(self) -> int:
        return self._idx
    
    @property
    def state(self) -> RunnerState:
        return self._state
    
    @state.setter
    def state(self, value: RunnerState):
        if not isinstance(value, RunnerState):  # type: ignore
            raise ValueError(f"Expected a RunnerState, got {value}")
        self._state = value

    @property
    def parent(self) -> "ProcessHandler":
        return self._parent
    
    @property
    def url(self):
        return self.parent.url
    
    @property
    def name(self) -> str:
        return f"{self.parent.name}-runner-{self.idx}"
    
    @property
    def files(self) -> RunnerFileHandler:
        return self._files
    
    @property
    def call_args(self) -> Dict[Any, Any]:
        return self._call_args
    
    @property
    def exec_args(self) -> Dict[Any, Any]:
        """
        Generates the exec args by combining the parent's exec args with the runner's own exec args
        """        
        global_args = self.parent.exec_args.copy()
        global_args.update(self._exec_args)
        global_args.update(self._temp_exec_args)
        return global_args
    
    @property
    def runline(self) -> str:
        """
        Returns the string necessary to execute this runner
        """
        runline =  f"{self.url.submitter} {self.files.jobscript.name}"
        if self.exec_args.get("asynchronous", True):
            runline += " &"
        return runline
    
    @property
    def execline(self) -> str:
        """
        Returns the string necessary to execute this runner
        """
        return f"{self.url.python} {self.parent.files.repo.name} {self.short_uuid} {self.parent.name} {self.name} {self.parent.function.name}"

    def assess_run(self, verbose: Union[Verbosity, None] = None) -> bool:
        """
        Assess whether this runner should be run
        """
        verbose = self.validate_verbose(verbose)

        verbose.print(f"Assessing run for {self}. State={self.state}", level=2)
        # if force, always run
        if self.exec_args.get("force", False):
            return True
        # skip=False should be equivalent to force=True
        if not self.exec_args.get("skip", True):
            return True
        # already staged
        if self.state >= RunnerState.STAGED:
            return False

        return True

    def stage(self, verbose: Union[Verbosity, None] = None, **exec_args: Any) -> bool:
        """
        Perform staging

        This Phase creates all necessary files and stages them within the local staging directory
        """
        verbose = self.validate_verbose(verbose)

        self._temp_exec_args = exec_args
        # ensure the local staging dir exists
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)
        # generate and add the per-runner lines to the master script
        master_content = [
            generate_format_fn(manifest_filename=self.parent.files.manifest.name),
            "export sourcedir=$PWD",
            f"rm -rf {self.parent.files.manifest.name}\n",
        ]
        # collect baseline repo content
        repo_prologue: List[str] = []
        repo_epilogue: List[str] = []
        with open(repo.__file__, "r") as o:
            prologue = True
            for line in o.readlines():
                if "# placeholder" in line:
                    continue
                if '__name__ == "__main__":' in line:
                    prologue = False
                if prologue:
                    repo_prologue.append(line)
                else:
                    repo_epilogue.append(line)
        # begin generating unique repo content with the main function
        repo_content: List[str] = [
            "### Main Function ###\n",
            self.parent.function.raw_source,
            "\n\n### Runner Inputs ###\n"
        ]
        # now deal with the runners themselves
        staged = 0
        # create a cache for the runner data
        runner_data = ["runner_data = {"]
        for runner in self.parent.runners:
            
            if not runner.assess_run():
                continue

            master_content.append(runner.runline)

            runner.files.jobscript.write(f"""\
export r_uuid='{runner.short_uuid}'
enable_redirect
echo "$(date -u +'{repo.date_format}') [{runner.short_uuid}] [state] submitted" >> "$sourcedir/{self.parent.files.manifest.name}"
{runner.execline}
""")

            dumped_args = json.dumps(runner.call_args)
            runner_data.append(f"\t'{runner.short_uuid}': '{dumped_args}',")

            runner.state = RunnerState.STAGED
            staged += 1
        
        if staged == 0:
            return False
        
        verbose.print(f"Staged {staged}/{len(self.parent.runners)} Runners", level=1)

        repo_content.append("\n".join(runner_data) + "\n}\n\n")
        
        # main file writing
        self.parent.files.master.write("\n".join(master_content))
        self.parent.files.repo.write("".join(repo_prologue + repo_content + repo_epilogue))
        
        return True

    def transfer(self, verbose: Union[Verbosity, None] = None, **exec_args: Any) -> bool:
        """
        Perform a transfer

        Transfers the content of the local staging dir to the remote directories as needed
        """
        verbose = self.validate_verbose(verbose)

        staged = self.stage(verbose=verbose, **exec_args)

        transferred = 0
        for runner in self.parent.runners:
            if not runner.exec_args.get("force", False):
                if runner.state >= RunnerState.TRANSFERRED:
                    continue

            for file in runner.files.files_to_send:
                runner.url.transport.queue_for_push(file)
                
                runner.state = RunnerState.TRANSFERRED
            
            transferred += 1

        if transferred == 0 and not staged:
            return False
        
        verbose.print(f"Transferring for {transferred}/{len(self.parent.runners)} Runners", level=1)
        
        for file in self.parent.files.files_to_send:
            self.url.transport.queue_for_push(file)

        self.url.transport.transfer()

        return True

    def run(self, verbose: Union[Verbosity, None] = None, **exec_args: Any) -> bool:
        """
        Performs the remote execution

        ssh into the remote and execute the calculations as specified
        """
        verbose = self.validate_verbose(verbose)

        verbose.print(f"Running using {self} as the master", level=2)
        transferred = self.transfer(verbose=verbose, **exec_args)

        asynchronous = False
        run = 0
        for runner in self.parent.runners:
            if not runner.exec_args.get("force", False):
                if runner.state >= RunnerState.RUNNING:
                    continue
                if runner.exec_args.get("asynchronous", True):
                    asynchronous = True
                run += 1

        if run == 0 and not transferred:
            return False
        
        verbose.print(f"Running {run}/{len(self.parent.runners)} Runners", level=1)

        self.parent.run_cmd = self.url.cmd(
            f"cd {self.remote_dir} && {self.url.shell} {self.parent.files.master.name}", 
            asynchronous=asynchronous
        )

        for runner in self.parent.runners:
            runner.state = RunnerState.RUNNING

        return True

    @property
    def is_finished(self) -> bool:
        return self.state >= RunnerState.COMPLETED
    
    @property
    def result(self) -> Any:
        return self._result
    
    def read_local_files(self) -> None:
        if self.files.result.exists_local:
            with open(self.files.result.local, "r") as o:
                self._result = json.load(o)


def generate_format_fn(manifest_filename: str) -> str:
    
        logwrite_fn = f"""\
enable_redirect() {{

  local timestr="$(date -u +'{repo.date_format}')"
  local file="$sourcedir/{manifest_filename}"

  exec > >(while IFS= read -r line; do echo "$timestr [$r_uuid] [stdout] $line" >> "$file"; done)
  exec 2> >(while IFS= read -r line; do echo "$timestr [$r_uuid] [stderr] $line" >> "$file"; done)
}}

export -f enable_redirect"""
        return logwrite_fn
