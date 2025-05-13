import json
import os
from typing import TYPE_CHECKING, Any, Dict, List

from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.engine.files.filehandler import FileHandlerBaseClass
from alchemy_test.engine.runnerstates import RunnerState
from alchemy_test.storage.trackedfile import TrackedFile
from alchemy_test.utils.uuidmixin import UUIDMixin

import alchemy_test.engine.files.repo as repo

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.engine.process import ProcessHandler


class RunnerFileHandler(FileHandlerBaseClass):
    """
    Extends the filehandler to contain Process related files
    """

    __slots__ =["jobscript", "result"]

    def __init__(
            self,
            jobscript: TrackedFile,
            result: TrackedFile,
            ):
        super().__init__()

        self.jobscript = jobscript
        self.result = result

        self._files = {
            "jobscript": jobscript,
            "result": result
        }

    @property
    def files_to_send(self) -> List[TrackedFile]:
        return [self.jobscript]


class Runner(UUIDMixin, ExecArgsMixin):

    __slots__ = [
        "_idx",
        "_parent",
        "_call_args",
        "_temp_exec_args",
        "_uuid",
        "_files",
        "_remote_status",
        "_result",
        "_state",
        "stdout",
        "stderr",
    ]

    def __init__(
            self,
            idx: int,
            parent: "ProcessHandler",
            call_arguments: Dict[Any, Any], 
            exec_arguments: Dict[Any, Any]
        ):
        self._idx = idx
        self._parent = parent
        self._call_args = call_arguments
        self._exec_args = exec_arguments
        self._temp_exec_args: Dict[Any, Any] = {}

        self._uuid = self.generate_uuid(self.call_args)

        self._files = RunnerFileHandler(
            jobscript = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-jobscript.sh"),
            result = TrackedFile(self.local_dir, self.remote_dir, f"{self.name}-result.json")
        )
        
        self._remote_status: List[str] = []
        self._result = None
        
        self.stdout: str = ""
        self.stderr: str = ""

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

    def assess_run(self) -> bool:
        """
        Assess whether this runner should be run
        """
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

    def stage(self, **exec_args: Dict[Any, Any]) -> bool:
        """
        Perform staging

        This Phase creates all necessary files and stages them within the local staging directory
        """
        self._temp_exec_args = exec_args
        # ensure the local staging dir exists
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)
        
        # generate and add the per-runner lines
        master_content = [
            generate_format_fn(manifest_filename=self.parent.files.manifest.name),
            "export sourcedir=$PWD",
            "rm -rf {self.parent.files.manifest.name}\n",
        ]

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

        repo_content: List[str] = [
            "### Main Function ###\n",
            self.parent.function.raw_source,
            "\n\n### Runner Inputs ###\n"
        ]

        runner_data = ["runner_data = {"]
        for runner in self.parent.runners:
            master_content.append(runner.runline)

            runner.files.jobscript.write(f"""\
export r_uuid='{runner.short_uuid}'
enable_redirect
echo "$(date -u +'{repo.date_format}') [{runner.short_uuid}] [status] submitted" >> "$sourcedir/{self.parent.files.manifest.name}"
{runner.execline}
""")

            dumped_args = json.dumps(runner.call_args)
            runner_data.append(f"\t'{runner.short_uuid}': '{dumped_args}',")

            runner.state = RunnerState.STAGED

        repo_content.append("\n".join(runner_data) + "\n}\n\n")
        
        # main file writing
        self.parent.files.master.write("\n".join(master_content))
        self.parent.files.repo.write("".join(repo_prologue + repo_content + repo_epilogue))
        
        return True

    def transfer(self, **exec_args: Dict[Any, Any]) -> bool:
        """
        Perform a transfer

        Transfers the content of the local staging dir to the remote directories as needed
        """
        print(f"Transferring {self}")
        self.stage(**exec_args)

        for runner in self.parent.runners:
            for file in runner.files.files_to_send:
                runner.url.transport.queue_for_push(file)
                
                runner.state = RunnerState.TRANSFERRED
        
        for file in self.parent.files.files_to_send:
            self.url.transport.queue_for_push(file)

        self.url.transport.transfer()

        return True

    def run(self, **exec_args: Dict[Any, Any]) -> bool:
        """
        Performs the remote execution

        ssh into the remote and execute the calculations as specified
        """
        print(f"Running using {self} as the master")
        self.transfer(**exec_args)

        self.parent.run_cmd = self.url.cmd(f"cd {self.remote_dir} && {self.url.shell} {self.parent.files.master.name}")

        for runner in self.parent.runners:
            runner.state = RunnerState.RUNNING

        return True

    @property
    def is_finished(self) -> bool:
        for line in self._remote_status[::-1]:
            if line.endswith("completed"):
                return True
        return False
    
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
