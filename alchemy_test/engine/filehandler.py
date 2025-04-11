from typing import List

from alchemy_test.storage.trackedfile import TrackedFile


class FileHandler:

    __slots__ = ["_files"]
    
    def __init__(self, local_dir: str, remote_dir: str, filenames: List[str]):
        
        self._files = {}
        for name in filenames:
            tmp = TrackedFile(local_path=local_dir, remote_path=remote_dir, file=name)
            self._files[tmp.importstr] = tmp

    def __getattribute__(self, name):
        if name != "_files" and name in self._files:
            return self._files[name]
        return object.__getattribute__(self, name)

    @property
    def files(self) -> List[TrackedFile]:
        return list(self._files.values())
