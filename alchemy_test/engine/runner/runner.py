import os
from typing import TYPE_CHECKING, Any, Dict

from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.engine.filehandler import FileHandler
from alchemy_test.utils.uuidmixin import UUIDMixin

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.engine.process import ProcessHandler


class Runner(UUIDMixin, ExecArgsMixin):

    __slots__ = ["_idx", "_parent", "_call_args", "_uuid", "_files"]

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

    def __repr__(self) -> str:
        return self.name

    @property
    def idx(self) -> int:
        return self._idx

    @property
    def parent(self) -> "ProcessHandler":
        return self._parent
    
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

    def stage(self):
        """
        Perform staging

        This Phase creates all necessary files and stages them within the local staging directory
        """
        # ensure the local staging dir exists
        print(f"Staging {self}")
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)
        
        self.parent.files.master.write("master file")
        self.parent.files.repo.write("repo file")

        self.files.runfile.write("run file")
        self.files.jobscript.write("jobscript file")

    def transfer(self):
        """
        Perform a transfer

        Transfers the content of the local staging dir to the remote directories as needed
        """
        print(f"Transferring {self}")
        pass

    def run(self):
        """
        Performs the remote execution

        ssh into the remote and execute the calculations as specified
        """
        print(f"Running using {self} as the master")
        self.stage()
        self.transfer()
