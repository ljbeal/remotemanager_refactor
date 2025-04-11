import getpass
import logging
import os
import re
import signal
import subprocess
import threading
import time
import warnings
from types import TracebackType
from typing import Tuple, Union, Any, Type, Optional

from alchemy_test.utils.uuidmixin import UUIDMixin
from alchemy_test.utils.verbosedecorator import make_verbose
from alchemy_test.utils.verbosity import Verbosity

logger = logging.getLogger(__name__)


def _process_redirect_file(file) -> Union[str, None]:
    if file is not None:
        return os.path.abspath(file)
    return None


def _clean_output(output) -> Union[str, None]:
    """
    Wrapper for the string.strip() method, allowing None

    Args:
        output:
            string (or None) to be handled

    Returns (str, None):
        cleaned cmd output
    """
    if output is None:
        return None
    return output.strip()


def detect_locale_error(stderr):
    """
    Given a stderr output string `stderr`, will regex search for the locale errors

    Args:
        stderr:
            stderr text
    Returns:
        bool: True if the error appears to be a locale issue
    """
    match = r"(?i)(?:set|setting)\s?locale"

    return len(re.findall(match, stderr)) != 0


@make_verbose
class CMD(UUIDMixin):
    """
    This class stores a command to be executed, and the returned stdout, stderr

    Args:
        cmd (str):
            command to be executed
        asynchronous (bool):
            execute commands asynchronously
            defaults to False
        stdout (str):
            optional file to redirect stdout to
        stderr (str):
            optional file to redirect stderr to
        stream (bool):
            enables output streaming if True
        timeout (int):
            time to wait before issuing a timeout
        max_timeouts (int):
            number of times to attempt communication in case of a timeout
        force_file (bool):
            always use the fexec method if True
    """

    _do_not_package = ["_subprocess"]

    def __init__(
        self,
        cmd: str,
        asynchronous: bool = False,
        stdout: Union[str, None] = None,
        stderr: Union[str, None] = None,
        stream: bool = False,
        timeout: int = 5,
        max_timeouts: int = 3,
        raise_errors: bool = True,
        force_file: bool = False,
        verbose: Union[None, int, bool, "Verbosity"] = None,
    ):
        self.verbose = verbose
        self._uuid = self.generate_uuid(f"{time.time()} {cmd}")
        # command to execute
        self._cmd = cmd
        # settings
        self._async = asynchronous
        # force file-based exec
        self._force_file = force_file
        # stdout/stderr redirect
        if stderr is not None and stderr == stdout:
            raise_errors = False
            warnings.warn(
                "stderr and stdout are pointed at the same file, "
                "this will cause errors to be suppressed"
            )
        self._redirect = {
            "stdout": _process_redirect_file(stdout),
            "stderr": _process_redirect_file(stderr),
            "execfile": None,
        }
        self.stream = stream

        if not asynchronous:
            initmsg = "creating a new CMD instance"
        else:
            initmsg = "creating a new asynchronous CMD instance"

        logger.info(initmsg)

        # timeout info
        self.timeout = timeout
        self.max_timeouts = max_timeouts
        self._timeout_current_tries = 0

        # call duration storage
        self._duration = {}

        # prefer to raise an error, or continue
        self._raise_errors = raise_errors

        # supplementary data for post-exec
        self._subprocess = None
        self._cached = False
        self._stdout = None
        self._stderr = None
        self._returncode = None
        self._whoami = None
        self._pwd = None
        self._pid = None

    def __repr__(self):
        stdout = self.stdout if self.stdout is not None else self.cmd
        return stdout

    def __contains__(self, item: Any) -> bool:
        return self._cmd.__contains__(item)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        if self._subprocess is not None:
            print(f"Exiting context, killing pid {self.pid}")
            self.kill()

        return False  # returning True will suppress an exception

    @property
    def tempfile(self):
        return f"{self.short_uuid}.sh"

    @property
    def sent(self) -> str:
        """The command passed at initialisation"""
        return self._cmd

    @property
    def cmd(self) -> str:
        """Alias for init command"""
        return self._cmd

    @property
    def asynchronous(self) -> bool:
        """
        True if commands are to be executed asynchronously
        """
        return self._async

    @property
    def is_redirected(self) -> bool:
        """
        True if the cmd is redirected to a file
        """
        return any([self._redirect["stdout"], self._redirect["stderr"]])

    @property
    def redirect(self):
        return self._redirect

    def _get_return_attr(self, attr: str) -> Union[str, None]:
        # subprocess objects cannot be serialised, check if we are post-reserialisation
        if getattr(self, "_subprocess", None) is None:
            logger.warning("broken subprocess, getting attr _%s", attr)
            return getattr(self, f"_{attr}")

        return self.communicate()[attr]

    @property
    def cached(self) -> bool:
        return self._cached

    @property
    def stdout(self) -> str:
        """
        Directly returns the stdout from the cmd execution. Attempts
        to communicate with the subprocess in the case of an async run.

        Returns None if the command has not been executed yet.

        Returns (str):
            the stdout from the command execution
        """
        if self._stdout is not None:
            logger.info("returning cached stdout")
            return self._stdout
        self._stdout = self._get_return_attr("stdout")
        return self._stdout

    @property
    def stderr(self) -> str:
        """
        Directly returns the stderr from the cmd execution. Attempts
        to communicate with the subprocess in the case of an async run.

        Returns None if the command has not been executed yet.

        Returns (str):
            the stdout from the command execution
        """
        if self._stderr is not None:
            logger.info("returning cached stderr")
            return self._stderr
        self._stderr = self._get_return_attr("stderr")
        return self._stderr

    @property
    def pwd(self) -> str:
        """
        Present working directory at command execution

        Returns None if the command has not been executed yet.

        Returns (str):
            working dir of command execution
        """
        return self._pwd

    @property
    def whoami(self) -> str:
        """
        Present user at command execution

        Returns None if the command has not been executed yet.

        Returns (str):
            username who executed the command
        """
        return self._whoami

    @property
    def pid(self) -> int:
        """
        The Process ID of the spawned process

        Returns None if the command has not been executed yet.

        Returns (int):
            the PID of the spawned shell for this command
        """
        if self._subprocess is not None:
            return self._subprocess.pid
        return self._pid

    @property
    def returncode(self) -> Union[int, None]:
        """
        Attempt to retrieve the returncode of the subprocess. This call will
        not disturb an asynchronous run, returning None

        Returns (int, None):
                The exit status of the subprocess, None if it is still running.
                None otherwise.
        """
        if self._subprocess is not None:
            self._subprocess.poll()
            self._returncode = self._subprocess.returncode
        return self._returncode

    @property
    def is_finished(self) -> bool:
        """
        Returns True if this command has finished execution. This will NOT talk
        to the process, as to not disturb async runs, so will always return
        False in those instances

        Returns (bool):
                True if the command has completed
        """
        return self.returncode is not None

    @property
    def succeeded(self) -> Union[None, bool]:
        """
        True if the command successfully executed

        Returns:
            None if not finished, True if returncode is 0
        """
        if not self.is_finished:
            return None
        return self.returncode == 0

    @property
    def duration(self):
        return self._duration

    @property
    def latency(self):
        return self.duration["exec"]

    def exec(self, verbose: Union[None, int, bool, Verbosity] = None) -> None:
        """
        Executes the command, storing execution info and in the
        case of a non-async run; returned values

        Returns:
            None
        """
        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose
        self._whoami = getpass.getuser()
        self._pwd = os.getcwd()

        if self.is_redirected:
            out = self._redirect["stdout"]
            err = self._redirect["stderr"]
            stdout = open(out, "w+") if out is not None else None
            stderr = open(err, "w+") if err is not None else None
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        if self._force_file:
            return self._fexec(stdout, stderr, verbose)

        try:
            self._exec(stdout, stderr, verbose)
        except OSError as E:
            msg = "Encountered an OSError on exec, attempting file exec"
            warnings.warn(msg)
            logger.warning(E)
            logger.warning(msg)
            self._fexec(stdout, stderr, verbose)
        logger.debug("Done, process PID is %s", self.pid)

    def _exec(self, stdout, stderr, verbose) -> None:
        """
        Directly executes the command

        Args:
            stdout:
                stdout passthrough
            stderr:
                stderr passthrough

        Returns:
            None
        """
        logger.debug("executing command in %s", self.pwd)
        logger.debug(f'"{self._cmd}"')

        hostexec = "/bin/bash" if os.name != "nt" else None

        t0 = time.time()
        self._subprocess = subprocess.Popen(
            self._cmd,
            stdout=stdout,
            stderr=stderr,
            shell=True,
            text=True,
            executable=hostexec,
        )

        def capture_stream(stream, cache: list, print: bool) -> None:
            """
            Subprocess struggles with streaming output if more than one pipe is assigned

            For this, we need to use threads to monitor each pipe simultaneously

            Args:
                stream:
                    stdout or stderr streams
                cache:
                    list to fill
                print:
                    prints progress if True

            returns:
                None
            """
            # if carriage return, need an extra newline at the start of the next line
            extra_newline = False
            search = re.compile(r"^\s*([^\s]+)\s+(\d+%)\s+([\d.]+.+B/s)", re.MULTILINE)
            for line in iter(stream.readline, ""):
                pre = ""
                end = "\n"
                if search.match(line) is not None:
                    end = "\r"
                    extra_newline = True
                elif extra_newline:
                    pre = "\n"
                    extra_newline = False

                tmp = pre + line.rstrip("\n") + end
                if print:
                    verbose.print(tmp, end="", level=1)
                cache.append(tmp)

        if self.stream:
            # if we're streaming, set up the threads
            stdout_cache = []
            stdout_thread = threading.Thread(
                target=capture_stream,
                args=[self._subprocess.stdout, stdout_cache, True],
            )
            stderr_cache = []
            stderr_thread = threading.Thread(
                target=capture_stream,
                args=[self._subprocess.stderr, stderr_cache, False],
            )
            stdout_thread.start()
            stderr_thread.start()
            # wait for the command to complete
            while self._subprocess.poll() is None:
                pass
            # kill the threads
            stdout_thread.join()
            stderr_thread.join()
            # store output
            self._stdout = "".join(stdout_cache)
            self._stderr = "".join(stderr_cache)

        self._duration["exec"] = time.time() - t0
        self._pid = self._subprocess.pid
        if not self._async and not self.is_redirected:
            logger.debug("in-exec communication triggered")
            self.communicate(verbose=verbose)

    def _fexec(self, stdout, stderr, verbose) -> None:
        """
        Executes the command by first writing it to a file

        Args:
            stdout:
                stdout passthrough
            stderr:
                stderr passthrough

        Returns:
            None
        """
        file = self.tempfile
        verbose.print(f"Writing command to temporary file {file}", end="... ", level=3)
        with open(file, "w+") as o:
            o.write(self._cmd)
        verbose.print("done.", level=3)

        # noinspection PyTypedDict
        self._redirect["execfile"] = file

        t0 = time.time()
        self._subprocess = subprocess.Popen(
            f"bash {file}",
            stdout=stdout,
            stderr=stderr,
            shell=True,
            universal_newlines=True,
            executable="/bin/bash",
        )
        self._duration["exec"] = time.time() - t0
        self._pid = self._subprocess.pid

        if not self._async and not self.is_redirected:
            logger.debug("in-exec communication triggered")
            self.communicate(verbose=verbose)

    def communicate(
        self,
        use_cache: bool = True,
        ignore_errors: Union[bool, None] = None,
        verbose: Union[None, int, bool, Verbosity] = None,
    ) -> dict:
        """
        Communicates with the subprocess, returning the stdout and stderr in
        a dict

        Args:
            use_cache (bool):
                use cached value if it is available
            ignore_errors (bool):
                do not raise error regardless of base setting

        Returns (dict):
                {'stdout': stdout, 'stderr': stderr}
        """
        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose

        raise_errors = (
            not ignore_errors if ignore_errors is not None else self._raise_errors
        )

        if self._cached and use_cache:
            logger.info("using cached return values")
            return {
                "stdout": self._stdout,
                "stderr": self._stderr,
            }
        elif not self.is_redirected:
            logger.info("communicating with process %s", self.pid)
            std, err = self._communicate(verbose=verbose)
        else:
            logger.info("files are redirected, attempting to read")
            std, err = self._file_communicate()

        if self._stderr is not None and self._stderr.strip() != "":
            logger.warning(
                "stored stderr '%s' is not empty, not accepting new error '%s'",
                self._stderr,
                err,
            )
            err = self._stderr

        if self._stdout is not None and self._stdout.strip() != "":
            logger.warning(
                "stored stdout '%s' is not empty, not accepting new error '%s'",
                self._stdout,
                std,
            )
            std = self._stdout

        self._stdout = _clean_output(std)
        self._stderr = _clean_output(err)

        def format_output(string):
            if string is None:
                return

            if len(string.split("\n")) <= 1:
                return string

            return "\n".join([f"  {line}" for line in string.split("\n")])

        logger.info("stdout from exec: |\n%s", format_output(std))
        if err:
            logger.warning("stderr from exec: |\n%s", format_output(err))

        if std or err:  # skip if all None
            logger.debug("caching results")
            self._cached = True

        if self._redirect["execfile"] is not None:
            tf = self._redirect["execfile"]
            try:
                # noinspection PyTypeChecker
                os.remove(tf)
                logger.info("removed temp file %s", tf)
            except FileNotFoundError:
                logger.info("temp file %s not found)", tf)
                pass

        if raise_errors and err is not None and err != "":
            if detect_locale_error(err):
                logger.warning("locale error detected: %s", err)
            else:
                raise RuntimeError(f"received the following stderr: \n{err}")

        self._stdout = _clean_output(std)
        self._stderr = _clean_output(err)

        if (
            raise_errors
            and self._stderr is not None
            and self._stderr == ""
            and self.returncode != 0
        ):
            warnings.warn(
                f"stderr is empty, but return code != 0 ({self.returncode}). "
                f"This could indicate an error."
            )

        return {"stdout": self._stdout, "stderr": self._stderr}

    def _communicate(self, verbose: Union[None, int, bool, Verbosity]) -> Tuple[Union[str, None], Union[str, None]]:
        """
        Attempt to communicate with the process, handling timeout

        Issues a Popen.communicate() with a timeout
        If this fails, will wait for (timeout * number of tries) seconds and
        try again. This continues until max_timeouts has been reached

        Returns (str, str):
            stdout, stderr
        """
        timeout = self.timeout
        self._timeout_current_tries += 1
        dt = 0  # accumulate time on each retry, rather than the whole call
        try:
            t0 = time.time()

            if not timeout or timeout <= 0:
                stdout, stderr = self._subprocess.communicate()
            else:
                stdout, stderr = self._subprocess.communicate(timeout=timeout)
            dt += time.time() - t0
        except AttributeError as E:
            logger.info("attempted communicate on unexec CMD")
            logger.info(str(E))
            return None, None
        except subprocess.TimeoutExpired:
            verbose.print(
                f"({self._timeout_current_tries}/{self.max_timeouts}) "
                f"communication attempt failed after {timeout}s",
                end="... ",
                level=1,
            )

            if (
                isinstance(self.max_timeouts, int)
                and 0 < self.max_timeouts <= self._timeout_current_tries
            ):
                verbose.print("could not communicate, killing for safety", level=1)
                self.kill()
                raise RuntimeError("could not communicate with process")

            waittime = timeout * self._timeout_current_tries

            verbose.print(f"waiting {waittime}s and trying again", level=1)
            time.sleep(waittime)

            return self._communicate(verbose=verbose)

        self._duration["communicate"] = dt
        return stdout, stderr

    def _file_communicate(self) -> Tuple[Union[str, None], Union[str, None]]:
        """
        We are redirected to a file, attempt to read the output
        """
        self._subprocess.poll()
        returncode = self._subprocess.returncode
        count = 0
        while returncode is None:
            time.sleep(0.05)
            self._subprocess.poll()
            returncode = self._subprocess.returncode
            count += 1
            if count >= 10:
                raise RuntimeError("could not communicate with process")

        outfile = self._redirect["stdout"]
        errfile = self._redirect["stderr"]

        if outfile is not None:
            logger.debug("reading file %s", outfile)
            with open(outfile, "r") as o:
                std = o.read().strip()
        else:
            logger.debug("outfile is None")
            std = None

        if errfile is not None:
            logger.debug("reading file %s", errfile)
            with open(errfile, "r") as e:
                err = e.read().strip()
        else:
            logger.debug("errfile is None")
            err = None

        return std, err

    def kill(
        self, 
        pid: Union[int, None] = None, 
        verbose: Union[None, int, bool, Verbosity] = None
    ) -> None:
        """
        Kill the process associated with this command, if one exists

        Returns:
            None
        """

        if verbose is not None:
            verbose = Verbosity(verbose)
        else:
            verbose = self.verbose
        if not isinstance(verbose, Verbosity):
            raise RuntimeError(f"Malformed Verbosity: {verbose}")

        if pid is None:
            pid = self.pid

        if pid is None:
            return
        logger.info("received termination call for pid %s", pid)

        verbose.print(f"Terminating pid {pid}", end="... ", level=1)
        try:
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, os.WUNTRACED)
            verbose.print("Done.", level=1)
        except ProcessLookupError:
            verbose.print("Process not found.", level=1)
        except Exception as ex:
            verbose.print("Error.", level=1)
            raise ex
