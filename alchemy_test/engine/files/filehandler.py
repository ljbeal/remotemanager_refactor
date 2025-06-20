from typing import Dict, List

from alchemy_test.storage.trackedfile import TrackedFile


class FileHandlerBaseClass:
    """
    Stub class allows deferral of file access on Process from
    obj.file to obj.files.file

    Subclass from this and overrride the `_file` property

    _files should be a dictionary of endpoints and a boolean flag indicating that 
    this file is important for excecution

    For example:
    
    self._files = {
        "jobscript": True,
        "result": False
    }

    self.jobscript = TrackedFile(...)
    self.result = TrackedFile(...)

    Note then that `jobscript` and `result` must also exist within the object
    """

    __slots__ = ["_files"]
    
    def __init__(self):        
        self._files: Dict[str, bool] = {}

    @property
    def files(self) -> List[TrackedFile]:
        return [getattr(self, n) for n in self._files.keys()]

    @property
    def files_to_send(self) -> List[TrackedFile]:        
        return [getattr(self, n) for n, k in self._files.items() if k]
