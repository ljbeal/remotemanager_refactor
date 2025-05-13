"""
This repository is the master file that handles runtime on the remote machine.

It should stand by itself and have minimal dependencies to maximise transferability.
"""
from datetime import datetime
import json
import sys
from typing import Dict, List, Union


date_format = "%Y-%m-%d %H:%M:%S"


class Manifest:
    """
    Handler for manifest related activities
    """
    def __init__(self, manifest_path: Union[str, None] = None, content: Union[str, None] = None, uuid: Union[str, None] = None):

        if manifest_path is None and content is None:
            raise ValueError("Either manifest_path or content must be provided")

        self.manifest_path = manifest_path
        self._content = content

        self.uuid = uuid or "FFFFFFFF"

    @property
    def content(self) -> str:
        if self._content is not None:
            return self._content

        if self.manifest_path is not None:
            with open(file=self.manifest_path, mode="r") as f:
                content = f.read()
            return content

        raise ValueError("Content read error, either manifest_path is missing or content is mangled")
    
    def now(self) -> str:
        """
        Get the current time in the correct format
        """
        return datetime.strftime(datetime.now(), date_format)

    def to_timestamp(self, timestring: str) -> int:
        """
        Convert a time string to timestamp
        """
        return int(datetime.strptime(timestring, date_format).timestamp())

    def log(self, string: str, mode: str = "state"):
        """
        Log a state to the manifest
        """
        if self.manifest_path is None:
            return  # can't log to a file if no manifest path is set
        
        if mode not in ["state", "stdout", "stderr"]:
            raise ValueError("Invalid mode. Must be 'state', 'stdout', or 'stderr'")
        
        string = f"{self.now()} [{self.uuid}] [{mode}] {string.strip()}\n"
        with open(self.manifest_path, "a+") as o:
            o.write(string)

    @property
    def data(self) -> Dict[str, List[str]]:
        """
        Retrieve all log entries for a given uuid

        Args:
            uuid (str):
                uuid of the log entry to retrieve
            string (Union[str, None]):
                Override the source material
        
        Returns:
            List[str]: list of log entries
        """
        log: Dict[str, List[str]] = {"state": [], "stdout": [], "stderr": []}
        for line in self.content.split("\n"):
            if f"[{self.uuid}]" in line:
                if "stdout" in line:
                    log["stdout"].append(line.strip())
                elif "stderr" in line:
                    log["stderr"].append(line.strip())
                else:
                    log["state"].append(line.strip())
        return log
    
    @property
    def stdout(self) -> str:
        data = self.data["stdout"]

        cache: List[str] = []
        for line in data:
            cache.append(line.split("[stdout] ")[-1])
        return "\n".join(cache)

    @property
    def stderr(self) -> str:
        data = self.data["stderr"]
        cache: List[str] = []
        for line in data:
            cache.append(line.split("[stderr] ")[-1])
        return "\n".join(cache)


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

        manifest_path = f"{self.process_name}-manifest.txt" if process_name is not None else None
        self.manifest = Manifest(manifest_path, uuid=self.uuid)
    
    @property
    def data_path(self) -> str:
        """
        Path to the data store
        """
        return f"{self.process_name}-data.py"

    def submit(self, function_name: str, uuid: str):
        """
        Submit a job
        """
        self.manifest.log("running")
        fn = getattr(sys.modules[__name__], function_name)
        call_args = json.loads(runner_data.get(uuid, {}))  # type: ignore

        try:
            result = fn(**call_args)
        except Exception as ex:
            self.manifest.log("failed")
            raise ex
        else:
            self.manifest.log("completed")

        try:
            with open(f"{self.runner_name}-result.json", "w+") as o:
                json.dump(result, o)
        except Exception as ex:
            self.manifest.log("serialisation error")
            raise ex


runner_data = {}  # placeholder runner_data. To be added in submission


if __name__ == "__main__":
    try:
        uuid = sys.argv[1]
        process_name = sys.argv[2]
        runner_name = sys.argv[3]
        function_name = sys.argv[4]
    except IndexError:
        raise ValueError("Repo must be called with uuid and process_name")

    c = Controller(uuid=uuid, runner_name=runner_name, process_name=process_name)

    c.submit(function_name, uuid)
