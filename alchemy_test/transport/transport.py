"""
Baseclass for any file transfer
"""

import logging
import os.path
from typing import TYPE_CHECKING, Dict, List, Union

from alchemy_test.connection.cmd import CMD
from alchemy_test.storage.trackedfile import TrackedFile
from alchemy_test.utils.ensure_list import ensure_list
from alchemy_test.utils.ensure_dir import ensure_dir
from alchemy_test.utils.flags import Flags
from alchemy_test.utils.verbosity import VerboseMixin, Verbosity

# TYPE_CHECKING is false at runtime, so does not cause a circular dependency
if TYPE_CHECKING:
    from alchemy_test.connection.url import URL

logger = logging.getLogger(__name__)


class Transport(VerboseMixin):
    """
    Baseclass for file transfer

    Args:
        url (URL):
            url to extract remote address from
        dir_mode:
            compatibility mode for systems that do not accept multiple explicit
            files per transfer, copies files to a directory then pulls it
    """

    _do_not_package = ["_url"]

    def __init__(
        self,
        url: Union[URL, None],
        dir_mode: bool = False,
        flags: Union[str, None] = None,
        verbose: Union[None, int, bool, "Verbosity"] = None,
    ):
        self.verbose = verbose
        self._remote_address: Union[str, None] = None

        if url is None:
            # deferred import required to prevent circular import issue with URL
            from alchemy_test.connection.url import URL

            url = URL()

        self._url = url
        self.set_remote(url)

        if flags is not None:
            self._flags = Flags(str(flags))
        else:
            self._flags = Flags()

        self._transfers: Dict[str, List[str]] = {}
        self._cmds = []
        self._request_stream = False

        self._dir_mode = dir_mode

    @property
    def dir_mode(self) -> bool:
        return self._dir_mode

    @dir_mode.setter
    def dir_mode(self, mode: bool):
        self._dir_mode = mode

    def queue_for_push(
        self, 
        files: Union[List[str], str, TrackedFile], 
        local: Union[str, None] = None, 
        remote: Union[str, None] = None
    ) -> None:
        """
        Queue file(s) for sending (pushing)

        Args:
            files (list[str], str, TrackedFile):
                list of files (or file) to add to push queue
            local (str):
                local/origin folder for the file(s)
            remote (str):
                remote/destination folder for the file(s)
        Returns:
            None
        """
        if isinstance(files, TrackedFile):
            logger.info("adding TrackedFile %s to PUSH queue)", files.name)
            self.add_transfer(files.name, files.local_dir, files.remote_dir, "push")
            return
        logger.info(
            "adding to PUSH queue)",
        )
        self.add_transfer(files, local, remote, "push")

    def queue_for_pull(
        self, 
        files: Union[List[str], str, TrackedFile], 
        local: Union[str, None] = None, remote: 
        Union[str, None] = None
    ) -> None:
        """
        Queue file(s) for retrieving (pulling)

        Args:
            files (list[str], str, TrackedFile):
                list of files (or file) to add to pull queue
            local (str):
                local/destination folder for the file(s)
            remote (str):
                remote/origin folder for the file(s)
        Returns:
            None
        """
        if isinstance(files, TrackedFile):
            logger.info("adding TrackedFile %s to PULL queue)", files.name)
            self.add_transfer(files.name, files.remote_dir, files.local_dir, "pull")
            return
        logger.info(
            "adding to PULL queue)",
        )
        self.add_transfer(files, remote, local, "pull")

    def add_transfer(
        self,
        files: Union[List[str], str],
        origin: Union[str, None],
        target: Union[str, None],
        mode: str,
    ):
        """
        Create a transfer to be executed. The ordering of the origin/target
        files should be considered as this transport instance being a
        "tunnel" between wherever it is executed (origin), and the destination
        (target)

        Args:
            files (list[str], str):
                list of files (or file) to add to pull queue
            origin (str):
                origin folder for the file(s)
            target (str):
                target folder for the file(s)
            mode (str: "push" or "pull"):
                transfer mode. Chooses where the remote address is placed
        Returns:
            None
        """
        modes = ("push", "pull")
        if mode.lower() not in modes:
            raise ValueError(f"mode must be one of {modes}")

        if origin is None:
            origin = "."
        if target is None:
            target = "."

        if mode == "push":
            # ensure dir-type, otherwise split_pair removes a directory
            origin = os.path.join(os.path.abspath(origin), "")
            pair = f"{origin}>{self._add_address(target)}"
        else:
            target = os.path.join(os.path.abspath(target), "")
            pair = f"{self._add_address(origin)}>{target}"

        files = [os.path.split(f)[1] for f in ensure_list(files)]

        logger.info(
            "adding transfer: %s -> %s",
            Transport.split_pair(pair)[0],
            Transport.split_pair(pair)[1],
        )
        logger.info("for files %s", files)

        if pair in self._transfers:
            self._transfers[pair] = list(set(self._transfers[pair]).union(set(files)))
        else:
            self._transfers[pair] = list(set(files))

    def _add_address(self, dir: str) -> str:
        """
        Adds the remote address to the dir `dir` if it exists

        Args:
            dir (str):
                remote dir to have address appended

        Returns:
            (str) dir
        """
        dir = os.path.join(dir, "")  # ensure there's a trailing slash for split_pair
        if self.address is None:  # type: ignore
            return dir
        return f"{self.address}:{dir}"

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

        if isinstance(inp, str):
            raise ValueError(
                "files is stringtype, was a transfer forced into the queue?"
            )

        if len(inp) > 1:
            return os.path.join(folder, "{" + ",".join(inp) + "}")
        return os.path.join(folder, inp[0])

    @property
    def transfers(self) -> Dict[str, List[str]]:
        """
        Return the current transfer dict

        Returns (dict):
            {paths: files} transfer dict
        """
        return {k: sorted(list(v)) for k, v in self._transfers.items()}

    def print_transfers(self):
        """
        Print a formatted version of the current queued transfers

        Returns:
            None
        """
        i = 0
        for pair, files in self.transfers.items():
            i += 1
            print(
                f"transfer {i}:"
                f"\norigin: {Transport.split_pair(pair)[0]}"
                f"\ntarget: {Transport.split_pair(pair)[1]}"
            )
            j = 0
            for file in files:
                j += 1
                print(f"\t({j}/{len(files)}) {file}")

    @property
    def address(self) -> Union[str, None]:
        """
        return the remote address

        Returns (str):
            the remote address
        """
        return self._remote_address

    @address.setter
    def address(self, remote_address: str):
        """
        set the remote address

        Returns:
            None
        """
        self._remote_address = remote_address

    @property
    def url(self) -> "URL":
        if self._url is not None:  # type: ignore
            return self._url

        from alchemy_test.connection.url import URL
        return URL()

    @url.setter
    def url(self, url: URL):
        self._url = url

    def set_remote(self, url: Union[URL, None] = None):
        """
        set the remote address with a URL object

        Returns:
            None
        """
        logger.info("setting rsync url to %s", url)
        if url is None:
            logger.info(
                "url is None, setting None",
            )
            self._remote_address = None
        elif url.is_local:
            logger.info(
                "url is local, setting None",
            )
            self._remote_address = None
        else:
            logger.info(
                "url okay, setting)",
            )
            self._remote_address = url.userhost
            self.url = url

    @property
    def flags(self) -> Flags:
        return self._flags

    @flags.setter
    def flags(self, new: str):
        self._flags = Flags(str(new))

    def cmd(self, primary: str, secondary: str) -> str:
        """
        Returns a formatted command for issuing transfers. It is left to
        the developer to implement this method when adding more transport
        classes.

        The implementation should take two strings as arguments, `primary` and
        `secondary`:

        Args:
            primary (str):
                The source folder, containing the files for transfer. Input will be
                semi-formatted already in bash form.

                e.g.
                directory_name/{file1,file2,file3,...,fileN}

            secondary (str):
                The destination folder for the files

        At its most basic:

        ```
        def cmd(self, primary, secondary):
            cmd = "command {primary} {secondary}"
            base = cmd.format(primary=primary,
                                    secondary=secondary)
            return base
        ```

        You can, of course, extend upon this. View the included transport
        methods for ideas on how to do this.

        Returns (str):
            formatted command for issuing a transfer
        """
        raise NotImplementedError

    def transfer(
        self,
        dry_run: bool = False,
        prepend: bool = True,
        raise_errors: bool = True,
        dir_mode: Union[bool, None] = None,
        verbose: Union[None, int, bool, Verbosity] = None,
    ) -> List[CMD]:
        """
        Perform the actual transfer

        Args:
            dry_run (bool):
                do not perform command, just return the command(s) to be
                executed
            prepend (bool):
                enable forced cmd prepending
            raise_errors (bool):
                will not raise any stderr if False
            dir_mode:
                compatibility mode for systems that do not accept multiple explicit
                files per transfer, copies files to a directory then pulls it

        Returns (str, None):
            the dry run string, or None
        """
        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose

        logger.info("executing a transfer")

        if dir_mode is None:
            dir_mode = self._dir_mode

        commands = []
        tmp_dirs = {}  # temporary directory storage if we're running dir_mode
        for pair, files in self.transfers.items():
            primary, secondary = Transport.split_pair(pair)

            if dir_mode and len(files) > 1:
                # directory based compatibility mode.
                # First, create a temp dir to copy files to using cp -r
                # Then set the primary to this dir, and files to "*"
                local = ":" not in primary

                if not local:
                    tmp_remote, tmp_primary = primary.split(":")
                else:
                    tmp_remote = None
                    tmp_primary = primary

                last = [item for item in tmp_primary.split(os.sep) if item != ""][-1]
                tmp_dirname = f"tmp_copy_{last}"
                self.url.cmd(
                    f"mkdir -p {tmp_dirname} && cp -r "
                    f"{self._format_for_cmd(tmp_primary, files)} {tmp_dirname}",
                    prepend=prepend,
                    raise_errors=raise_errors,
                    local=local,
                )

                if tmp_remote is not None:
                    primary = f"{tmp_remote}:{tmp_dirname}"
                else:
                    primary = tmp_dirname

                files = ["*"]

                tmp_dirs[tmp_dirname] = local

            primary = self._format_for_cmd(primary, files)

            base_cmd = self.cmd(primary=primary, secondary=secondary)

            commands.append(base_cmd)

        if dry_run:
            self._cmds: List[CMD] = [
                self.url.cmd(cmd, dry_run=True, local=True, prepend=prepend)
                for cmd in commands
            ]
            return self._cmds

        nfiles = sum(len(filelist) for filelist in self.transfers.values())
        if nfiles == 0:
            verbose.print("No Transfer Required", level=1)
            return []

        filestr = "File" if nfiles == 1 else "Files"

        msg = ["Transferring", str(nfiles), filestr]

        ntransfers = len(self.transfers)
        if ntransfers > 1:
            msg += ["in", str(ntransfers), "Transfers"]

        end = "\n" if self._request_stream else "... "

        verbose.print(" ".join(msg), end=end, level=1)
        try:
            self._cmds = [
                self.url.cmd(
                    cmd,
                    local=True,
                    prepend=prepend,
                    verbose=verbose,
                    raise_errors=raise_errors,
                    stream=self._request_stream,
                )
                for cmd in commands
            ]
        except Exception as ex:
            # Comlete status print and raise the exception
            verbose.print("Error", level=1)
            raise ex
        else:
            verbose.print("Done", level=1)
        # wipe the transfer queue
        self.wipe_transfers()

        # clean up if we have created temporary dirs
        for dir, local in tmp_dirs.items():
            self.url.cmd(
                f"rm -rf {dir}", prepend=prepend, raise_errors=raise_errors, local=local
            )
        return self._cmds

    def wipe_transfers(self):
        logger.info("wiping transfers")
        self._transfers = {}

    @property
    def cmds(self):
        return self._cmds

    @staticmethod
    def split_pair(pair: str) -> list[str]:
        """
        Convert a "dir>dir" string into list format

        Args:
            pair (str):
                "dir>dir" string to be split

        Returns (list):
            [dir, dir]

        """
        return [ensure_dir(os.path.split(p)[0]) for p in pair.split(">")]

    @staticmethod
    def get_remote_dir(path: str) -> str:
        if ":" not in path:
            return path
        return path.split(":")[1]
