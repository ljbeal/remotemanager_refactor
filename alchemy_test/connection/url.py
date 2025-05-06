"""
URL base class for connecting to remote systems
"""

import copy
import os
import time
from collections import deque
from typing import Any, Deque, Dict, List, Union, Tuple

from alchemy_test.connection.cmd import CMD
from alchemy_test.transport.rsync import rsync
from alchemy_test.transport.scp import scp
from alchemy_test.transport.transport import Transport
from alchemy_test.utils.ensure_list import ensure_list
from alchemy_test.utils.format_iterable import format_iterable
from alchemy_test.utils.random_string import random_string
from alchemy_test.utils.uuidmixin import UUIDMixin
from alchemy_test.utils.verbosity import VerboseMixin, Verbosity


LOCALHOST = "localhost"


class URL(UUIDMixin, VerboseMixin):
    """
    Container to store the url info for a Remote run

    The url should contain everything pertaining to the _remote_, allowing
    Dataset to be remote-agnostic

    Arguments:
        host (str):
            host address of the remote system
        user (str):
            username for the remote system
        port (int, str):
            port to connect to for ssh tunnels
        verbose (bool):
            base-verbosity for connections
        timeout (int):
            time to wait before issuing a timeout for cmd calls
        max_timeouts (int):
            number of times to attempt cmd communication in case of a timeout
        python (str):
            string used to initiate a python instance
        raise_errors (bool):
            set false to ignore errors by default in cmd calls
        passfile (str):
            absolute path to password file for sshpass calls
        envpass (str):
            environment variable containing absolute path to password file for
        sshpass_override (str):
            override the sshpass string
            sshpass calls
        cmd_history_depth (int):
            number of cmd calls to store history for
        landing_dir (str):
            set the directory which is treated as the ssh endpoint
        ssh_insert (str):
            any extra flags you wish to add to the ssh call
        quiet_ssh (bool):
            Option to add -q flag to ssh calls. This suppresses errors and warnings
            that machines can sometimes put on stderr, breaking runs. Defaults True
        kwargs:
            any extra args that may end up here from a Dataset or Computer are
            discarded
    """

    _do_not_package = ["_urlutils"]

    _submitter_default = "bash"

    def __init__(
        self,
        host: Union[str, None] = None,
        user: Union[str, None] = None,
        port: Union[int, None] = None,
        verbose: Union[None, int, bool, Verbosity] = None,
        timeout: int = 5,
        max_timeouts: int = 3,
        python: str = "python3",
        submitter: str = _submitter_default,
        shell: str = "bash",
        raise_errors: bool = True,
        keyfile: Union[str, None] = None,
        passfile: Union[str, None] = None,
        envpass: Union[str, None] = None,
        sshpass_override: Union[str, None] = None,
        cmd_history_depth: int = 10,
        landing_dir: Union[str, None] = None,
        ssh_insert: str = "",
        ssh_prepend: Union[str, None] = None,
        ssh_override: Union[str, None] = None,
        quiet_ssh: bool = True,
        shebang: str = "#!/bin/bash",
        transport: Union[None, rsync, scp] = None,
        **kwargs: Dict[Any, Any],
    ):
        self.verbose = verbose
        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose

        if host is None:
            if user is not None:
                raise ValueError(
                    f"user is set to {user}, but host is unset, "
                    f'did you mean to set host="{user}"?'
                )

            host = LOCALHOST
        elif "@" in host and user is None:
            user, host = host.split("@")

        self._conn = {"user": user, "host": host, "port": port}

        self.timeout = timeout
        self.max_timeouts = max_timeouts
        self._submitter = None
        self._shell = None
        self.submitter = submitter
        self.shell = shell

        self.python = python
        self.shebang = shebang

        self._home = None
        self._landing_override = landing_dir

        self._cmd_history_depth = cmd_history_depth
        self._cmd_history = deque(maxlen=self._cmd_history_depth)
        # explicit path takes precedent over environment variable
        if passfile is None and envpass is not None:
            passfile = os.environ[envpass]

        if "ignore_errors" in kwargs:
            raise_errors = not kwargs.pop("ignore_errors")

        self._keyfile = keyfile
        self._passfile = passfile
        self._passfile_override = sshpass_override

        self._raise_errors = raise_errors
        self._ssh_override = ssh_override
        self._ssh_prepend = ssh_prepend
        self._ssh_insert = ssh_insert
        self.quiet_ssh = quiet_ssh

        msg = f"new url created with url details:{format_iterable(self._conn)}"
        verbose.print(msg, level=2)

        self._callcount = 0

        self._latency = 0
        self._connection_test = None

        self._transport = self._validate_transport(transport)
        self.generate_uuid(self._conn)

    def __deepcopy__(self, memo: Dict[Any, Any]):
        """
        Prevents a failure when copying a URL that has cmds in the history

        Taken from this answer https://stackoverflow.com/a/15774013
        """
        self.reset_cmd_history()

        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

    @property
    def raise_errors(self) -> bool:
        return self._raise_errors

    @raise_errors.setter
    def raise_errors(self, r: bool):
        self._raise_errors = r

    @property
    def ignore_errors(self) -> bool:
        return not self.raise_errors

    @ignore_errors.setter
    def ignore_errors(self, ignore: bool):
        self._raise_errors = not ignore

    @property
    def call_count(self) -> int:
        return self._callcount

    @property
    def user(self) -> Union[str, None]:
        """
        Currently configured username
        """
        user = self._conn.get("user", None)
        if isinstance(user, str):
            return user
        return

    @user.setter
    def user(self, user: Union[str, None]):
        """
        Set the user attribute
        """
        self._conn["user"] = user

    @property
    def host(self) -> str:
        """
        Currently configured hostname
        """
        host = self._conn.get("host", None)
        if isinstance(host, str):
            return host
        return LOCALHOST

    @host.setter
    def host(self, host: Union[str, None]):
        """
        Set the host attribute
        """
        self._conn["host"] = host

    @property
    def port(self) -> int:
        """
        Currently configured port (defaults to 22)
        """
        port = self._conn["port"] or 22
        if not isinstance(port, int):
            raise ValueError("port must be an integer")
        return port

    @port.setter
    def port(self, port: int):
        """
        Set the host attribute
        """
        self._conn["port"] = port

    @property
    def userhost(self) -> str:
        """
        `user@host` string if possible, just `host` if user is not present
        """
        if self.user is None:
            return self.host
        else:
            return f"{self.user}@{self.host}"

    @property
    def ssh_insert(self) -> str:
        return self._ssh_insert

    @ssh_insert.setter
    def ssh_insert(self, val: str):
        self._ssh_insert = val

    @property
    def ssh_prepend(self) -> Union[str, None]:
        return self._ssh_prepend

    @ssh_prepend.setter
    def ssh_prepend(self, val: str):
        self._ssh_prepend = val

    @property
    def submitter(self) -> str:
        if self._submitter is not None:
            return self._submitter
        return self.shell

    @submitter.setter
    def submitter(self, submitter: str):
        self._submitter = submitter

    @property
    def shell(self) -> str:
        if self._shell is None:
            return "bash"
        return self._shell

    @shell.setter
    def shell(self, shell: str):
        if self.submitter == self._submitter_default:
            self.submitter = shell
        self._shell = shell

    @property
    def home(self) -> Union[str, None]:
        if self._home is None:
            self.gethome()
        return self._home

    def gethome(self) -> Union[str, None]:
        self._home = self.expandvars("$HOME")
        return self._home

    def clearhome(self):
        """
        Clear the home property

        Returns:
            None
        """
        self._home = None

    @property
    def landing_dir(self) -> str:
        if self._landing_override is not None:
            return self._landing_override

        return "$HOME"

    @landing_dir.setter
    def landing_dir(self, landing: str):
        self._landing_override = landing

    @property
    def transport(self) -> Union[rsync, scp]:
        if self._transport is None:  # type: ignore
            self._transport = self._get_default_transport()
        return self._transport

    def _validate_transport(
        self, transport: Union[None, rsync, scp]
    ) -> Union[rsync, scp]:
        if transport is None:
            transport = self._get_default_transport()
        return transport

    @transport.setter
    def transport(self, transport: Union[None, rsync, scp]):
        if transport is None:
            transport = self._get_default_transport()

        transport = self._validate_transport(transport)
        self._transport = transport
        self._transport.set_remote(self)

    def _get_default_transport(self) -> rsync:
        return rsync(url=self, verbose=self.verbose)

    @property
    def ssh(self) -> str:
        """
        ssh insert for commands on this connection
        """
        if self.is_local:
            return ""

        if self._ssh_override:
            return self._ssh_override

        ret: List[str] = []

        if self.passfile is not None:
            ret.append(self.passfile)

        if self.ssh_insert != "":
            ret.append(f"ssh {self.ssh_insert} -p {self.port}")
        else:
            ret.append(f"ssh -p {self.port}")

        if self.quiet_ssh:
            ret.append("-q")

        if self._keyfile:
            ret.append(f"-i {self.keyfile}")

        ret.append(self.userhost)

        return " ".join(ret)

    @ssh.setter
    def ssh(self, newssh: str) -> None:
        """
        Allows forced override of the ssh command

        Inserting extra flags into the ssh can be done as follows:

        >>> url = URL()
        >>> print(url.ssh)
        >>> "ssh"
        >>> url.ssh = "LANG=C " + url.ssh
        >>> print(url.ssh)
        >>> "LANG=C ssh"

        Args:
            newssh (str):
                new ssh string to insert

        Returns:
            None
        """
        self._ssh_override = newssh

    def clear_ssh_override(self):
        """
        Wipe any override applied to ssh. Can also be done by setting
        url.ssh = None

        Returns:
            None
        """
        self._ssh_override = None

    @property
    def keyfile(self) -> Union[str, None]:
        if self._keyfile is None:
            return
        p = self._keyfile.replace("~", os.environ["HOME"])
        if not os.path.isfile(p):
            raise RuntimeError(f"could not find ssh key file at {self._keyfile}")

        return self._keyfile

    @keyfile.setter
    def keyfile(self, file: str):
        self._keyfile = file

    @property
    def sshpass_override(self) -> Union[str, None]:
        return self._passfile_override

    @sshpass_override.setter
    def sshpass_override(self, override: str):
        self._passfile_override = override

    @property
    def passfile(self) -> Union[str, None]:
        """
        Returns the sshpass string

        .. versionadded:: 0.10.2
            No longer returns just the file, to facilitate overriding

        Returns:
            sshpass full string
        """
        if self._passfile_override is not None:
            return self._passfile_override

        if self._passfile is None:
            return

        p = self._passfile.replace("~", os.environ["HOME"])
        if not os.path.isfile(p):
            raise RuntimeError(f"could not find password file at {self._passfile}")

        return f"sshpass -f {self._passfile}"

    @passfile.setter
    def passfile(self, file: str):
        self._passfile = file

    def tunnel(
        self,
        local_port: int,
        remote_port: int,
        local_address:  Union[str, None] = None,
        background: bool = False,
        verbose: Union[None, int, Verbosity] = None,
        dry_run: bool = False,
    ) -> CMD:
        """
        Create a tunnel to the host, between the local and remote ports

        Args:
            local_port (int):
                port to open on the local side
            remote_port (int):
                port to access on the  remote side
            local_address (str):
                change the local address of the tunnel
            background (bool):
                creates the tunnel asynchronously if True (default False)
            verbose:
                override verbose setting for this call
            dry_run (bool):
                do not execute if True> Defaults to False

        Returns:
            CMD:
                The CMD instance responsible for the tunnel
        """

        def validate_port(p: Union[int, Any]) -> int:
            if not isinstance(p, int):
                raise ValueError(f"Port {p} is not int type")
            if p <= 1024:
                raise ValueError("Ports below 1024 are reserved for root")
            return p

        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose

        local_port = validate_port(local_port)
        remote_port = validate_port(remote_port)

        local_address = "" if local_address is None else local_address
        if not local_address.endswith(":"):
            local_address += ":"

        cmd = (
            f"{self.ssh} -N -L {local_address}{local_port}"
            f":{self.host}:{remote_port} {self.host}"
        )

        t = self.cmd(
            cmd, local=True, dry_run=dry_run, timeout=False, asynchronous=background
        )
        if not dry_run:
            verbose.print(
                f"Created a tunnel to host {self.host} with the command:\n"
                f"{cmd}\n"
                f"Tunnel PID: {t.pid}",
                level=1,
            )

        return t

    @property
    def is_local(self) -> bool:
        """
        True if this connection is purely local
        """
        host = self.host
        if host == LOCALHOST:
            return True
        elif host.startswith("127."):
            return True
        return False

    def ping(
        self,
        n: int = 5,
        timeout: int = 30,
        verbose: Union[None, int, bool, Verbosity] = None,
    ) -> float:
        """
        Perform and monitor a ping command

        Args:
            n (int): number of pings to aim for
            timeout (int): kill the process and return 0 if
                this period is elapsed

        Returns:
            (float) latency in ms
        """
        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose

        msg = f"pinging {self.host}"
        verbose.print(msg, level=2)

        tmpfile = f"ping_{random_string()}"

        def cleanup(process: CMD) -> None:
            process.kill(verbose=verbose)
            try:
                os.remove(tmpfile)
            except FileNotFoundError:
                pass

        ping = self.cmd(
            f"ping {self.host}", local=True, stdout=tmpfile, asynchronous=True
        )

        lines = []
        t0 = time.time()
        while len(lines) < n + 1:
            with open(tmpfile, mode="r", encoding="utf8") as o:
                lines = o.readlines()

            time.sleep(0.5)

            if time.time() - t0 > timeout:
                msg = f"ping timed out after {timeout} seconds"
                verbose.print(msg, 1)
                cleanup(ping)
                return -1

        cleanup(ping)

        times = []
        for line in lines[1:]:
            times.append(self._process_ping_line(line))

        avg = sum(times) / n
        msg = f"ping times: {times} -> {avg}"
        verbose.print(msg, level=2)
        return avg

    def _process_ping_line(self, line: str) -> float:
        """
        Function to parse the contents of a line output from a ping command

        Args:
            line (str):
                ping command line
        Returns:
            (float): ping time in seconds
        """
        timing = line.split("time=")[1].strip()  # get timing
        val, units = timing.split()

        if units != "ms":
            raise ValueError(f"Unknown ping units {units}")

        return float(val) * 1e-3  # convert to seconds

    def expandvars(self, string: str) -> Union[str, None]:
        """
        'echo' a string on the remote, returning the result

        Args:
            string:
                string to be expanded

        Returns:
            str
        """
        wrapped = f'bash -c "echo {string}"'

        return self.cmd(wrapped).stdout

    def cmd(
        self,
        cmd: str,
        asynchronous: bool = False,
        local: Union[bool, None] = None,
        stdout: Union[str, None] = None,
        stderr: Union[str, None] = None,
        timeout: Union[int, None] = None,
        max_timeouts: Union[int, None] = None,
        raise_errors: Union[bool, None] = None,
        dry_run: bool = False,
        prepend: bool = False,
        force_file: bool = False,
        landing_dir: Union[str, None] = None,
        stream: bool = False,
        verbose: Union[None, int, bool, Verbosity] = None,
    ) -> CMD:
        """
        Creates and executes a command

        Args:
            asynchronous (bool):
                run this command asynchronously
            cmd (str):
                command to execute
            local (bool, None):
                force a local or remote execution. Defaults to None
            stdout (str):
                optional file to redirect stdout to
            stderr (str):
                optional file to redirect stderr to
            timeout (int):
                time to wait before issuing a timeout
            max_timeouts (int):
                number of times to attempt communication in case of a timeout
            raise_errors (bool):
                override for global setting. Raise any stderr if encountered
            dry_run (bool):
                don't exec the command if True, just returns the string
            prepend (bool):
                always attempt to use ssh_prepend
            force_file (bool):
                passthrough for CMD force_file argument
            landing_dir:
                set the directory which is treated as the ssh endpoint
            stream:
                Attempts to stream the output as it arrives on stdout

        Returns (CMD):
            returned command instance
        """
        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose
        _remote_call = False
        if self._landing_override is not None or landing_dir is not None:
            ld = landing_dir or self.landing_dir
            cmd = f"cd {ld} && {cmd}"

        if local is not None and not local:
            cmd = f"{self.ssh} '{cmd}'"
            _remote_call = True
        elif local is None and not self.is_local:
            cmd = f"{self.ssh} '{cmd}'"
            _remote_call = True
        if raise_errors is None:
            raise_errors = self._raise_errors

        timeout = self.timeout if timeout is None else timeout
        max_timeouts = self.max_timeouts if max_timeouts is None else max_timeouts

        if self.ssh_prepend is not None:
            prep = self.ssh_prepend.strip()

            if prepend:
                cmd = f"{prep} {cmd}"
            elif _remote_call:
                cmd = f"{prep} {cmd}"

        thiscmd = CMD(
            cmd.strip(),
            asynchronous=asynchronous,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
            max_timeouts=max_timeouts,
            raise_errors=raise_errors,
            force_file=force_file,
            stream=stream,
            verbose=verbose,
        )

        if dry_run:
            return thiscmd

        thiscmd.exec()
        if not local:
            self._callcount += 1

        self._cmd_history.append(thiscmd)

        return thiscmd

    @property
    def cmd_history(self) -> Deque[CMD]:
        return self._cmd_history

    @property
    def cmd_history_depth(self):
        return self._cmd_history_depth

    def reset_cmd_history(self):
        self._cmd_history: Deque[CMD] = deque(maxlen=self._cmd_history_depth)

    @cmd_history_depth.setter
    def cmd_history_depth(self, newdepth: int):
        """
        Updates the history depth, and creates a new dequeue populated with as many of
        the existing cmds as possible

        Args:
            newdepth (int):
                new depth to capture
        Returns:

        """
        self._cmd_history_depth = newdepth

        newqueue: Deque[CMD] = deque(maxlen=self.cmd_history_depth)

        for item in self.cmd_history:
            newqueue.append(item)

        self._cmd_history = newqueue

    @property
    def utils(self) -> "URLUtils":
        """
        Handle for the URLUtils module
        """
        if getattr(self, "_urlutils", None) is None:
            self._urlutils = URLUtils(self)
        return self._urlutils

    def script(self, **kwargs: Dict[Any, Any]) -> str:
        raise NotImplementedError

    @staticmethod
    def download_file(file_url: str, filename: str, timeout: int = 120) -> None:
        """
        Download file at url `file_url` and write the content out to `filename`

        Args:
            file_url: url of file
            filename: name to write content to
        """
        import requests

        response = requests.get(file_url, timeout=timeout)

        if response.status_code == requests.codes.ok:
            # Save the file
            fld = os.path.split(filename)[0]
            if fld != "" and not os.path.exists(fld):
                os.makedirs(fld)

            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Grabbed file '{filename}'")
        else:
            raise RuntimeError(f"Could not find a file at: {file_url}")


class URLUtils:
    """
    Extra functions to go with the URL class, called via URL.utils

    As it requires a parent `URL` to function, and is instantiated with a
    `URL`, there is little to no purpose to using this class exclusively

    Arguments:
        parent (URL):
            parent class to provide utils to
    """

    def __init__(self, parent: URL):

        self._parent = parent

    def file_mtime(
        self,
        files: Union[List[str], str],
        local: Union[bool, None] = None,
        python: bool = False,
        ignore_empty: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Check file modification times of [files]

        Args:
            files (list):
                list of paths to files
            local (bool):
                force a local search
            python (bool):
                ensure python style search is used
            ignore_empty (bool):
                also check the filesize, ignoring empty files
            dry_run (bool):
                print command only

        Returns (dict):
            {file: mtime (unix)} dictionary
        """
        if local is None:
            local = self._parent.is_local

        files = ensure_list(files)
        times, _ = self._file_mtime(files, local, python, dry_run)

        if dry_run:
            # in this instance "times" is simply the command
            return times

        output = {}
        for file in files:
            if file in times:
                mtime = times[file][0]
                fsize = times[file][1]
                if ignore_empty and fsize == 0:
                    output[file] = None
                else:
                    output[file] = mtime
            else:
                output[file] = None

        return output

    def _file_mtime(
            self, 
            files: List[str], 
            local: bool, 
            python: bool, 
            dry_run: bool
            ) -> Tuple[Dict[str, Tuple[int, int]], str]:
        """
        Perform the "stat -c %Y" command on a list of files,
        returning the result. Uses a python command backup if this fails

        Args:
            files (list):
                list of files to check
            local (bool):
                force a local search
            python (bool):
                force the python override
            dry_run (bool):
                print command only

        Returns:
            dict[filename: (filemtime, filesize)]
            int: cmd error code
            str: cmd stderr
        """
        sep = ","

        def stat() -> Tuple[Dict[str, Tuple[int, int]], str, Union[int, None]]:
            basecmd = f"stat -c %n{sep}%Y{sep}%s"
            if len(files) == 1:
                cmd = f"{basecmd} {files[0]}"
            else:
                cmd = f"{basecmd} {{" + ",".join(files) + "}"

            ret = self._parent.cmd(
                cmd, local=local, raise_errors=False, dry_run=dry_run
            )

            if dry_run:
                print(ret.sent)
                return {}, "", None
            
            err = ret.stdout or ""

            times = {}
            for line in err.split("\n"):
                try:
                    fname = line.split(sep)[0]
                    mtime = int(float(line.split(sep)[1]))
                    fsize = int(float(line.split(sep)[2]))

                    times[fname] = (mtime, fsize)
                except IndexError:
                    pass

            return times, err, ret.returncode

        def pystat() -> Tuple[Dict[str, Tuple[int, int]], str]:
            ex = f"""import os
files={files}
for f in files:
\ttry: print(f'{{f}}{sep}{{os.stat(f).st_mtime}}{sep}{{os.stat(f).st_size}}')
\texcept FileNotFoundError: print(f)"""

            cmd = f'{self._parent.python} -c "{ex}"'

            ret = self._parent.cmd(
                cmd, local=local, raise_errors=False, dry_run=dry_run
            )

            if dry_run:
                print(ret.sent)
                return {}, ""

            if ret.stdout is None:
                raise RuntimeError("Failed to execute command (stdout is None)")
            err = ret.stdout or ""
            
            times = {}
            error = []
            for line in err.split("\n"):
                try:
                    fname = line.split(sep)[0]
                    mtime = int(float(line.split(sep)[1]))
                    fsize = int(float(line.split(sep)[2]))

                    times[fname] = (mtime, fsize)
                except IndexError:
                    error.append(line.strip())

            return times, "\n".join(error)

        files = ensure_list(files)

        if not python:
            t, e, returncode = stat()
            if returncode in [126, 127] or "illegal option" in e:
                return pystat()

            return t, e

        return pystat()

    def file_presence(
        self, 
        files: Union[List[str], str], 
        local: Union[bool, None] = None, 
        dry_run: bool = False
    ) -> Dict[str, bool]:
        """
        Search for a list of files, returning a boolean presence dict

        Args:
            files (list):
                list of paths to files
            local (bool):
                force a local search
            dry_run (bool):
                print command only

        Returns (dict):
            {file: present} dictionary
        """
        if local is None:
            local = self._parent.is_local

        files = ensure_list(files)

        times = self.file_mtime(files, local=local, dry_run=dry_run)

        if dry_run:
            return times

        return {f: times[f] is not None for f in files}

    def search_folder(
        self, 
        files: Union[List[str], str],
        folder: str, 
        local: Union[bool, None] = None, 
        dry_run: bool = False
    ) -> Dict[List[str], bool]:
        """
        Search `folder` for `files`, returning a boolean presence dict

        Arguments:
            files (list):
                list of filenames to check for. Optionally, a string for a
                single file
            folder (str):
                folder to scan
            local (bool):
                perform the scan locally (or remotely)
            dry_run (bool):
                print command only

        Returns (dict):
            {file: present} dictionary
        """
        if local is None:
            local = self._parent.is_local
        fpath = os.path.abspath(folder) if local else folder

        ls_return = self.ls(fpath, local=local, as_list=True, dry_run=dry_run)
        if isinstance(ls_return, CMD):
            raise RuntimeError("ls returned a CMD object")

        if dry_run:
            return ls_return

        scan = [os.path.basename(f) for f in ls_return]

        if isinstance(files, str):
            files = [files]

        ret = {file: os.path.basename(file) in scan for file in files}

        return ret

    def touch(
        self,
        file: str,
        local: Union[bool, None] = None,
        raise_errors: Union[bool, None] = None,
        dry_run: bool = False,
    ) -> CMD:
        """
        perform unix `touch`, creating or updating `file`

        Arguments:
            file (str):
                filename or path to file
            local (bool):
                force local (or remote) execution
            raise_errors (bool):
                raise any stderr encountered
            dry_run (bool):
                print command only

        Returns (CMD):
            CMD instance for the command
        """
        if local is None:
            local = self._parent.is_local
        fname = os.path.abspath(file) if local else file
        return self._parent.cmd(
            f"touch {fname}", local=local, raise_errors=raise_errors, dry_run=dry_run
        )

    def mkdir(
        self,
        file: str,
        local: Union[bool, None] = None,
        raise_errors: Union[bool, None] = None,
        dry_run: bool = False,
    ) -> CMD:
        """
        perform unix `mkdir -p`, creating a folder structure

        Arguments:
            file (str):
                name or path to folder
            local (bool):
                force local (or remote) execution
            raise_errors (bool):
                raise any stderr encountered
            dry_run (bool):
                print command only

        Returns (CMD):
            CMD instance for the command
        """
        if local is None:
            local = self._parent.is_local
        fname = os.path.abspath(file) if local else file
        return self._parent.cmd(
            f"mkdir -p {fname}", local=local, raise_errors=raise_errors, dry_run=dry_run
        )

    def ls(
        self,
        file: str,
        as_list: bool = True,
        local: Union[bool, None] = None,
        raise_errors: Union[bool, None] = None,
        dry_run: bool = False,
    ) -> Union[CMD, List[str]]:
        """
        Identify the files present on the directory

        Arguments:
            file (str):
                name or path to folder.
            as_list (bool):
                convert to a list format
            local (bool):
                force local (or remote) execution
            raise_errors (bool):
                raise any stderr encountered
            dry_run (bool):
                print command only

        Returns (CMD, list):
            CMD instance for the command, or the list if as_list is True
        """
        if local is None:
            local = self._parent.is_local
        fname = os.path.abspath(file) if local else file

        ret = self._parent.cmd(
            f"ls {fname}", local=local, raise_errors=raise_errors, dry_run=dry_run
        )
        err = ret.stdout or ""

        if as_list and not dry_run:
            ret = [f for f in err.split("\n") if f != ""]
        return ret
