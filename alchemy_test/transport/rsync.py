"""
Handles file transfer via the `rsync` protocol
"""

import logging
import os.path
import pathlib
import re
from typing import TYPE_CHECKING, Any, Dict, List, Union

from alchemy_test.transport.transport import Transport
from alchemy_test.utils.version import Version

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.connection.url import URL


logger = logging.getLogger(__name__)

VERSION_REGEX = r"version.(\d\.\d\.\d)"
RSYNC_MIN_VERSION = "3.0.0"
TRANSPORT_CHANGE_DOCS_URL = (
    "https://l_sim.gitlab.io/remotemanager/tutorials/E7_Changing_Transport.html"
)


class rsync(Transport):
    """
    Class for `rsync` protocol

    Args:
        checksum (bool):
            Adds checksum arg, which if ``True`` will add ``--checksum`` flag to
            parameters
        progress (bool):
            request streaming of rsync --progress stdout
    """

    def __init__(self, url: Union[URL, None], *args: List[Any], **kwargs: Dict[Any, Any]):
        super().__init__(url=url, *args, **kwargs)

        self.check_version()

        # flags can be exposed, to utilise their flexibility
        flags = kwargs.pop("flags", "auvh")
        if not isinstance(flags, str):
            raise ValueError("flags must be a string")
        self.flags = flags

        if kwargs.get("checksum", True):
            self._flags += "--checksum"

        if "progress" in kwargs and kwargs["progress"]:
            logger.debug("rsync progress requested")
            self._flags += "--progress"
            self._request_stream = True

        logger.info("created new rsync transport")

    def check_version(
        self, collect_only: bool = False, min_version: Union[str, None] = None
    ) -> Version:
        """
        Queries the installed rsync version and checks that it is recent enough

        Does nothing if the version could not be detected, so should be considered a
        "soft" check, rather than a true safety feature.

        Args:
            collect_only (bool):
                Does not perform a check if True. Defaults to False
            min_version (str):
                override the minimum version (used for testing)

        Returns:
            Version
        """
        if min_version is not None:
            print(
                f"Warning: rsync check_version is being run "
                f"with a modified min version: {min_version}"
            )
        else:
            min_version = RSYNC_MIN_VERSION

        content = self.url.cmd("rsync --version", local=True).stdout
        search = re.search(pattern=VERSION_REGEX, string=str(content))

        if search is None:
            return Version("0.0.0")

        version = Version(search.group(1))

        if not collect_only and version < Version(min_version):
            raise RuntimeError(
                f"rsync version ({version}) is less than the required {min_version}\n"
                "Please update your install, or swap to a different Transport\n"
                "More info can be found here: "
                f"{TRANSPORT_CHANGE_DOCS_URL}"  # noqa: E501
            )

        return version

    def cmd(self, primary: str,  secondary: str) -> str:
        if self.url.passfile and self.url.keyfile:
            raise RuntimeError(
                "rsync appears to have an issue when "
                "specifying sshpass AND ssh-key. Either set up "
                "your ssh config and remove the keyfile or use "
                "transport.scp"
            )

        password = ""
        if self.url.passfile is not None:
            password = f'--rsh="{self.url.passfile} ssh" '

        insert = ""
        if self.url.ssh_insert != "":
            insert = f'-e "ssh {self.url.ssh_insert}" '

        cmd = "rsync {flags} {ssh_insert}{password}{inner_dir}{primary} {secondary}"
        inner_dir = ""
        if len(pathlib.Path(secondary).parts) > 1:
            # the target is a nested dir. If the whole tree doesn't exist,
            # rsync will throw an error
            if ":" in secondary:
                # target is a remote folder, use the --rsync-path hack
                inner_dir = (
                    f'--rsync-path="mkdir -p '
                    f'{Transport.get_remote_dir(secondary)} && rsync" '
                )
            elif not os.path.exists(secondary):
                os.makedirs(secondary)

        base = cmd.format(
            flags=self.flags,
            ssh_insert=insert,
            password=password,
            primary=primary,
            secondary=secondary,
            inner_dir=inner_dir,
        )
        logger.debug(f'returning formatted cmd: "{base}"')
        return base
