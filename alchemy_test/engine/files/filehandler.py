from typing import List

from alchemy_test.storage.trackedfile import TrackedFile


class FileHandler:

    __slots__ = ["_files", "_do_not_send"]
    
    def __init__(self):
        
        self._files = {}
        self._do_not_send = []

    def add_file(self, local_dir, remote_dir, endpoint, filename, send: bool = True):
        self._files[endpoint] = TrackedFile(local_dir, remote_dir, filename)
        if not send:
            self._do_not_send.append(endpoint)

    def __getattribute__(self, name):
        if name != "_files" and name in self._files:
            return self._files[name]
        return object.__getattribute__(self, name)

    @property
    def files(self) -> List[TrackedFile]:
        return list(self._files.values())
    
    @property
    def files_to_send(self) -> List[TrackedFile]:
        return [f for e, f in self._files.items() if e not in self._do_not_send]
