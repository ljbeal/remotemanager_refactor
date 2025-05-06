"""
Handles file transfer via the `scp` protocol
"""

import logging
import os
from typing import TYPE_CHECKING, Any, List, Union

from alchemy_test.transport.transport import Transport
from alchemy_test.utils.ensure_list import ensure_list

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.connection.url import URL


logger = logging.getLogger(__name__)


class scp(Transport):
    """
    Class to handle file transfers using the scp protocol

    Args:
        url (URL):
            url to extract remote address from
    """

    def __init__(self, url: Union["URL", None], *args: Any, **kwargs: Any):
        super().__init__(url=url, *args, **kwargs)

        # flags can be exposed, to utilise their flexibility
        flags = kwargs.pop("flags", "r")
        if not isinstance(flags, str):
            raise ValueError("flags must be a string")
        self.flags = flags

        self._transfers = {}

    @staticmethod
    def _format_for_cmd(folder: str, inp: List[str]) -> str:
        """
        Formats a list into a bash expandable command with brace expansion

        Args:
            folder (str):
                the dir to copy to/from
            inp (list):
                list of items to compress

        Returns (str):
            formatted cmd
        """

        def scp_join(files: List[str]):
            if len(files) > 1:
                return os.path.join(folder, "{" + ",".join(files) + "}")
            return os.path.join(folder, files[0])

        if isinstance(inp, str):
            raise ValueError(
                "files is stringtype, was a transfer forced into the queue?"
            )

        inp = ensure_list(inp)

        if ":" not in folder:
            return scp_join(inp)
        remote, folder = folder.split(":")
        return f'{remote}:"{scp_join(inp)}"'

    def cmd(self, primary: str, secondary: str) -> str:
        password = ""
        if self.url.passfile is not None:
            password = f"{self.url.passfile} "

        sshkey = ""
        if self.url.keyfile is not None:
            sshkey = f"-i {self.url.keyfile} "

        # scp needs a target directory that exists, and will not create one
        # thus, we should always create the tree, to be safe
        if ":" in secondary:
            mkdir = (
                self.url.utils.mkdir(
                    Transport.get_remote_dir(secondary), dry_run=True
                ).cmd
                + " && "
            )
        else:
            mkdir = ""
            if not os.path.exists(secondary):
                os.makedirs(secondary)
        # This can be done as a direct f-string, but is left in this format for
        # demonstration purposes
        cmd = "{create}{password}scp {sshkey}{flags} {primary} {secondary}"
        base = cmd.format(
            create=mkdir,
            password=password,
            flags=self.flags,
            sshkey=sshkey,
            primary=primary,
            secondary=secondary,
        )
        logger.debug(f'returning formatted cmd: "{base}"')
        return base
