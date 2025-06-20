import os
from typing import Dict, List, Union

from alchemy_test.storage.trackedfile import TrackedFile


class FileHandlerBaseClass:
    """
    Stub class allows deferral of file access on Process from
    obj.file to obj.files.file

    Subclass from this and overrride the `_file` property

    _files should be a dictionary of endpoints and a boolean flag indicating that 
    this file is important for excecution. Files marked with `True` will be sent with 
    `run()`, and files marked as `False` will be fetched with `fetch_results()`

    Mark as None for files that should not be transferred

    For example:
    
    self._files = {
        "jobscript": True,
        "result": False,
    }

    self.jobscript = TrackedFile(...)
    self.result = TrackedFile(...)

    Note then that `jobscript` and `result` must also exist within the object
    """

    __slots__ = ["_files", "extra_send", "extra_recv"]
    
    def __init__(self):        
        self._files: Dict[str, Union[None, bool]] = {}
        self.extra_send: List[TrackedFile] = []
        self.extra_recv: List[TrackedFile] = []

    @property
    def files(self) -> List[TrackedFile]:
        """
        Returns a list of internally defined files
        """
        return [getattr(self, n) for n in self._files.keys()]
    
    @property
    def all_files(self) -> List[TrackedFile]:
        """
        Returns a list of all files attached to this object
        """
        return self.files + self.extra_send + self.extra_recv

    @property
    def files_to_send(self) -> List[TrackedFile]:
        """
        Returns a list of all important files for job execution
        """  
        return [getattr(self, n) for n, k in self._files.items() if k] + self.extra_send

    @property
    def files_to_fetch(self) -> List[TrackedFile]:
        """
        Returns a list of all important files to collect after a run
        """
        return [getattr(self, n) for n, k in self._files.items() if (k is not None and not k)] + self.extra_recv


class ExtraFilesMixin:

    local_dir = NotImplemented
    remote_dir = NotImplemented

    files = FileHandlerBaseClass()
    
    def add_extra_send(self, file: Union[str, TrackedFile]) -> None:
        if isinstance(file, str):
            file = TrackedFile(os.getcwd(), self.remote_dir, file)
        self.files.extra_send.append(file)
    
    def add_extra_recv(self, file: Union[str, TrackedFile]) -> None:
        if isinstance(file, str):
            file = TrackedFile(self.local_dir, self.remote_dir, file)
        self.files.extra_recv.append(file)
