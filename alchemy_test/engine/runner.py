from typing import TYPE_CHECKING, Any, Dict

from alchemy_test.utils.uuidmixin import UUIDMixin

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.engine.process import Process


class Runner(UUIDMixin):

    __slots__ = ["_parent", "_call_args", "_exec_args", "_uuid"]

    def __init__(
            self,
            parent: Process,
            call_arguments: Dict[Any, Any], 
            exec_arguments: Dict[Any, Any]
        ):
        self._parent = parent
        self._call_args = call_arguments
        self._exec_args = exec_arguments

        self._uuid = self.generate_uuid(self.call_args)

    @property
    def parent(self) -> Process:
        return self._parent
    
    @property
    def uuid(self) -> str:
        return self._uuid
    
    @property
    def short_uuid(self) -> str:
        return self.uuid[:8]
    
    @property
    def call_args(self) -> Dict[Any, Any]:
        return self._call_args
    
    @property
    def exec_args(self) -> Dict[Any, Any]:
        return self._exec_args

    def stage(self):
        """
        Perform staging

        This Phase creates all necessary files and stages them within the local staging directory
        """
        pass

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
