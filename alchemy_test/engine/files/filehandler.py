from typing import List

from alchemy_test.storage.trackedfile import TrackedFile


class FileHandler:

    __slots__ = ["_files"]
    
    def __init__(self):
        
        self._files = {}

    def add_file(self, local_dir, remote_dir, endpoint, filename):
        self._files[endpoint] = TrackedFile(local_dir, remote_dir, filename)

    def __getattribute__(self, name):
        if name != "_files" and name in self._files:
            return self._files[name]
        return object.__getattribute__(self, name)

    @property
    def files(self) -> List[TrackedFile]:
        return list(self._files.values())
