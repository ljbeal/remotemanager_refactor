import os
import shutil
from typing import Any, Callable, List
import pytest

from alchemy_test.engine.process import ProcessHandler
from alchemy_test.utils.random_string import random_string


class BaseTestClass:

    files: List[str] = []
    processes: List[ProcessHandler] = []

    @pytest.fixture(scope="function", autouse=True)
    def wrap(self):
        # print("Initialising test")
        self.setUp()

        yield  # test runs here

        print("Tearing down class")
        self.tearDown()

    def setUp(self):
        self.files = []

    def tearDown(self):
        """Clean up"""

        for process in self.processes:
            try_remove(process.local_dir)
            try_remove(process.remote_dir)

        for file in self.files:
            try_remove(file)

        self.files = []
    
    def create_process(self, function: Callable[..., Any]) -> ProcessHandler:
        """Create a process handler"""
        salt = random_string()
        ps = ProcessHandler(function, name=salt, remote_dir=f"temp_remote_{salt}", local_dir=f"temp_local_{salt}")
        self.processes.append(ps)
        return ps
    
    @property
    def ps(self) -> ProcessHandler:
        """Return the last created process handler"""
        return self.processes[-1]


def try_remove(f: str):
    """
    Attempt to move file or directory f
    """
    try:
        os.remove(f)
    except IsADirectoryError:
        shutil.rmtree(f)
    except FileNotFoundError:
        pass
