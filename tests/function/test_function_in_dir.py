import os
import subprocess


def test_exec_fn_in_dir():
    pwd = os.getcwd()
    print(pwd)
    cmd = f"python3 {pwd}/tests/function/data/fn_in_dir.py",
    stdout = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    ).communicate()[0]

    assert stdout.strip() == "test"
