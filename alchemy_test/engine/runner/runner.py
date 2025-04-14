import json
import os
from typing import TYPE_CHECKING, Any, Dict

from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.engine.files.filehandler import FileHandler
from alchemy_test.utils.uuidmixin import UUIDMixin

import alchemy_test.engine.files.repo as repo

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.engine.process import ProcessHandler


class Runner(UUIDMixin, ExecArgsMixin):

    __slots__ = ["_idx", "_parent", "_call_args", "_uuid", "_files", "_remote_status", "_result"]

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

        self._uuid = self.generate_uuid(self.call_args)

        self._files = FileHandler()
        self._files.add_file(self.local_dir, self.remote_dir, "jobscript", f"{self.name}-jobscript.sh")
        self._files.add_file(self.local_dir, self.remote_dir, "runfile", f"{self.name}-runfile.py")

        self._files.add_file(self.local_dir, self.remote_dir, "resultfile", f"{self.name}-result.json", send=False)

        self._remote_status = []
        self._result = None

    def __repr__(self) -> str:
        return self.name

    @property
    def idx(self) -> int:
        return self._idx

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
    def files(self) -> FileHandler:
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
        return global_args
    
    @property
    def runline(self) -> str:
        """
        Returns the string necessary to execute this runner
        """
        return f"{self.url.submitter} {self.files.jobscript.name}"

    def stage(self) -> bool:
        """
        Perform staging

        This Phase creates all necessary files and stages them within the local staging directory
        """
        # ensure the local staging dir exists
        print(f"Staging {self}")
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)
        
        # generate and add the per-runner lines
        self.parent.files.master.write(f"export sourcedir=$PWD\nrm -rf {self.parent.files.manifest.name}")

        nstaged = 0
        for runner in self.parent.runners:
            self.parent.files.master.append(runner.runline)

            runner.files.jobscript.write(f"{runner.url.python} {runner.files.runfile.name}")

            # write the actual run file

            # script proper
            runscript = [
                "import importlib.util, os, sys, time",
                "remote_path = os.path.expandvars('$sourcedir')",
                f"path = os.path.join(remote_path, '{runner.parent.files.repo.name}')",
                "spec = importlib.util.spec_from_file_location('repo', path)",
                "repo = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(repo)\n",
                f"manifest = repo.Manifest(instance_uuid='{runner.short_uuid}', filename='{runner.parent.files.manifest.name}')",
                "manifest.runner_mode = True",
                # need to add this instance of the manifest for the function
                "repo.manifest = manifest",
                "starttime = int(time.time())",
                "manifest.write('started')",
                "vmaj, vmin, vpat, *extra = sys.version_info",
                "if vmaj < 3:",
                "\tmanifest.write('failed - Python Version')",
                '\traise RuntimeError(f"Python version {vmaj}.{vmin}.{vpat} < 3.x.x")',
                f"call_args = {runner.call_args}",  # direct python dict serialisation only right now
                f"try:\n\tresult = repo.{runner.parent.function.name}(**call_args)",
                "except Exception:\n\tmanifest.write('failed')",
                "\traise",
                "else:",
                f"\tlast_reported_starttime = manifest.last_time('started').get('"  # comma
                f"{runner.short_uuid}', -1)",
                "\tif last_reported_starttime <= starttime: # no output for outdated run",
                "\t\tmanifest.write('completed')",
                f"\t\tmanifest.dump_json"  # no comma
                f"(result, '{runner.files.resultfile.name}')",
            ]
            runner.files.runfile.write("\n".join(runscript))
            nstaged += 1

        if nstaged == 0:
            print("Staged 0 runners")
            return False

        # write out the repository
        with open(repo.__file__, "r") as o:
            self.parent.files.repo.write(o.read())
        self.parent.files.repo.append("\n### Main Function ###\n")
        self.parent.files.repo.append(self.parent.function.raw_source)

        print(f"Staged {nstaged}/{len(self.parent.runners)} Runners")

        return True

    def transfer(self):
        """
        Perform a transfer

        Transfers the content of the local staging dir to the remote directories as needed
        """
        print(f"Transferring {self}")
        self.stage()

        for runner in self.parent.runners:
            for file in runner.files.files_to_send:
                self.url.transport.queue_for_push(file)
        
        for file in self.parent.files.files_to_send:
            self.url.transport.queue_for_push(file)

        self.url.transport.transfer()

    def run(self):
        """
        Performs the remote execution

        ssh into the remote and execute the calculations as specified
        """
        print(f"Running using {self} as the master")
        self.transfer()

        self.parent._run_cmd = self.url.cmd(f"cd {self.remote_dir} && {self.url.shell} {self.parent.files.master.name}")

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
        if self.files.resultfile.exists_local:
            with open(self.files.resultfile.local, "r") as o:
                self._result = json.load(o)
