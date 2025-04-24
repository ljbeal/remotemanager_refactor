"""
This repository is the master file that handles runtime on the remote machine.

It should stand by itself and have minimal dependencies to maximise transferability.
"""
from datetime import datetime
import importlib
import importlib.util
import json
import sys
from typing import List, Union


date_format = "%Y-%m-%d %H:%M:%S %z"


class Controller:
    """
    Main runtime controller
    """
    def __init__(
        self, 
        uuid: str,
        runner_name: Union[str, None] = None,
        process_name: Union[str, None] = None,
    ):
        self.uuid = uuid
        self.process_name = process_name
        self.runner_name = runner_name

    def now(self) -> str:
        return datetime.strftime(datetime.now(), date_format)

    def to_timestamp(self, timestring: str) -> int:
        return int(datetime.strptime(timestring, date_format).timestamp())
    
    @property
    def manifest_path(self) -> str:
        return  f"{self.process_name}-manifest.txt"
    
    @property
    def data_path(self) -> str:
        return f"{self.process_name}-data.py"

    def log(self, string: str):
        if self.process_name is None:
            return
        string = f"{self.now()} [{self.uuid}] {string.strip()}\n"
        with open(self.manifest_path, "a+") as o:
            o.write(string)
    
    def get(self, uuid: str, string: Union[str, None] = None) -> List[str]:
        if string is not None:
            lines = string.split("\n")
        else:
            with open(self.manifest_path, "r") as o:
                lines = o.readlines()

        log: List[str] = []
        for line in lines:
            if uuid in line:
                log.append(line.strip())
        return log

    def submit(self, function_name: str):
        self.log("started")
        call_args = json.loads(getattr(data, f"runner_{self.uuid}_input"))
        function = getattr(data, function_name)

        try:
            result = function(**call_args)
        except Exception as ex:
            self.log("failed")
            raise ex
        else:
            self.log("completed")

        try:
            with open(f"{self.runner_name}-result.json", "w+") as o:
                json.dump(result, o)
        except Exception as ex:
            self.log("serialisation error")
            raise ex


if __name__ == "__main__":
    try:
        uuid = sys.argv[1]
        process_name = sys.argv[2]
        runner_name = sys.argv[3]
        function_name = sys.argv[4]
    except IndexError:
        raise ValueError("Repo must be called with uuid and process_name")

    c = Controller(uuid=uuid, runner_name=runner_name, process_name=process_name)

    spec = importlib.util.spec_from_file_location("data", c.data_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load data module {c.data_path}")
    data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(data)

    c.submit(function_name)
