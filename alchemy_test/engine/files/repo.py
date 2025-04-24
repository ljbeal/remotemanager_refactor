"""
This repository is the master file that handles runtime on the remote machine.

It should stand by itself and have minimal dependencies to maximise transferability.
"""
date_format = "%Y-%m-%d %H:%M:%S %Z"
manifest_filename = "{manifest_filename}"


class Controller:
    """
    Main runtime controller
    """
    def __init__(self, uuid: str):
        self.uuid = uuid
