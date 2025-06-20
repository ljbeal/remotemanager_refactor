import os
import pytest

@pytest.fixture(scope="function", autouse=True)
def use_temp_dir(tmpdir: str):
    os.chdir(tmpdir)
