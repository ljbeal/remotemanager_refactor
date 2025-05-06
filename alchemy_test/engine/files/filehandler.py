from typing import Dict, List

from alchemy_test.storage.trackedfile import TrackedFile


class FileHandlerBaseClass:
    """
    Stub class allows deferral of file access on Process from
    obj.file to obj.files.file
    """

    __slots__ = ["_files"]
    
    def __init__(self):        
        self._files: Dict[str, TrackedFile] = {}

    @property
    def files(self) -> List[TrackedFile]:
        return list(self._files.values())

    @property
    def files_to_send(self) -> List[TrackedFile]:
        return NotImplemented
