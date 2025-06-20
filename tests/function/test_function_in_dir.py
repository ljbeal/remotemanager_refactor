import os
import subprocess

from alchemy_test import get_package_root


def test_exec_fn_in_dir():

    cmd = f"python3 {get_package_root()}/tests/function/data/fn_in_dir.py",
    stdout = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    ).communicate()[0]

    assert stdout.strip() == "test"
