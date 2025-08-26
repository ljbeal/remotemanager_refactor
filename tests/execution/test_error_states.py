import pytest
from remoref.engine.exceptions import RunnerFailedError, SubmissionError
from remoref.utils.basetestclass import BaseTestClass
from remotemanager import URL


def run(a: int) -> int:
    return a


class TestMalformedCommands(BaseTestClass):
    def test_broken_shell(self):
        url = URL(shell="foo")
        ps = self.create_process(run, url=url)

        with pytest.raises(RuntimeError):
            ps.run_direct(a=1)

    def test_broken_submitter(self):
        url = URL(submitter="foo")
        ps = self.create_process(run, url=url)

        ps.run_direct(a=1)

        assert isinstance(ps.results[0], RunnerFailedError)
        assert ps.stderr is not None
        assert "foo: command not found" in ps.stderr

    def test_broken_python(self):
        url = URL(python="foo")
        ps = self.create_process(run, url=url)

        ps.run_direct(a=1)

        assert isinstance(ps.results[0], RunnerFailedError)
        
        assert "foo: command not found" in str(ps.results[0])


class TestMalformedFiles(BaseTestClass):
    def test_broken_master(self):
        ps = self.create_process(run)

        ps.prepare(a=1)
        ps.transfer()

        with open(ps.files.master.remote, "w") as o:
            o.write("")

        with pytest.raises(SubmissionError):
            ps.run()
