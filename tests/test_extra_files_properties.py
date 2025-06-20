from alchemy_test.engine.files.filehandler import ExtraFilesMixin, FileHandlerBaseClass
from alchemy_test.storage.trackedfile import TrackedFile


class ProxyFileHandler(FileHandlerBaseClass):
    def __init__(self, send: TrackedFile, recv: TrackedFile, none: TrackedFile):
        super().__init__()

        self._files = {
            "send": True,
            "recv": False,
            "none": None,
        }

        self.send = send
        self.recv = recv
        self.none = none


class ProxyObject(ExtraFilesMixin):
    def __init__(self, local_dir: str, remote_dir: str):
        self.local_dir = local_dir
        self.remote_dir = remote_dir

        self._files = ProxyFileHandler(
            send = TrackedFile(local_dir, remote_dir, "send"),
            recv = TrackedFile(local_dir, remote_dir, "recv"),
            none = TrackedFile(local_dir, remote_dir, "none"),
        )
    
    @property
    def files(self) -> ProxyFileHandler:
        return self._files


class TestFileHandlerProperties:
    def test_file_list(self):
        obj = ProxyObject("local", "remote")
        assert len(obj.files.files) == 3
        assert len(obj.files.all_files) == 3
    
    def test_file_send_list(self):
        obj = ProxyObject("local", "remote")
        assert len(obj.files.files_to_send) == 1
        assert len(obj.files.extra_send) == 0
    
    def file_recv_list(self):
        obj = ProxyObject("local", "remote")
        assert len(obj.files.files_to_recv) == 1
        assert len(obj.files.extra_recv) == 0


class TestFileHandlerPropertiesExtra:
    def test_file_list(self):
        obj = ProxyObject("local", "remote")

        obj.add_extra_send(TrackedFile(".", ".", "extra_send"))
        obj.add_extra_recv(TrackedFile(".", ".", "extra_recv"))

        assert len(obj.files.files) == 3
        assert len(obj.files.all_files) == 5
    
    def test_file_send_list(self):
        obj = ProxyObject("local", "remote")

        obj.add_extra_send(TrackedFile(".", ".", "extra_send"))
        obj.add_extra_recv(TrackedFile(".", ".", "extra_recv"))

        assert len(obj.files.files_to_send) == 2
        assert len(obj.files.extra_send) == 1
    
    def file_recv_list(self):
        obj = ProxyObject("local", "remote")

        obj.add_extra_send(TrackedFile(".", ".", "extra_send"))
        obj.add_extra_recv(TrackedFile(".", ".", "extra_recv"))

        assert len(obj.files.files_to_recv) == 2
        assert len(obj.files.extra_recv) == 1
