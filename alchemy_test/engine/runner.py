import os
from typing import TYPE_CHECKING, Any, Dict

from alchemy_test.engine.execmixin import ExecArgsMixin
from alchemy_test.utils.uuidmixin import UUIDMixin

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.engine.process import ProcessHandler


class Runner(UUIDMixin, ExecArgsMixin):

    __slots__ = ["_parent", "_call_args", "_uuid"]

    def __init__(
            self,
            parent: "ProcessHandler",
            call_arguments: Dict[Any, Any], 
            exec_arguments: Dict[Any, Any]
        ):
        self._parent = parent
        self._call_args = call_arguments
        self._exec_args = exec_arguments

        self._uuid = self.generate_uuid(self.call_args)

    @property
    def parent(self) -> "ProcessHandler":
        return self._parent
    
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
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)

    def transfer(self):
        """
        Perform a transfer

        Transfers the content of the local staging dir to the remote directories as needed
        """
        pass

    def run(self):
        """
        Performs the remote execution

        ssh into the remote and execute the calculations as specified
        """
        pass
