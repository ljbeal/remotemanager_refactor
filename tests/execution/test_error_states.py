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

        with pytest.raises(SubmissionError):
            ps.run_direct(a=1)

    def test_broken_submitter(self):
        url = URL(submitter="foo")
        ps = self.create_process(run, url=url)

        with pytest.raises(SubmissionError, match=r".*Is the submitter 'foo' correct?"):
            ps.run_direct(a=1)

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

    def test_broken_repo(self):
        ps = self.create_process(run)

        ps.prepare(a=1)
        ps.transfer()

        with open(ps.files.repo.remote, "w") as o:
            o.write("")

        with pytest.raises(SubmissionError, match=r".*Hash mismatch.*"):
            ps.run()

    def test_broken_jobscript(self):
        ps = self.create_process(run)

        ps.prepare(a=1)
        ps.prepare(a=2)
        ps.transfer()

        with open(ps.runners[0].files.jobscript.remote, "w") as o:
            o.write("")

        self.run_ps()
        assert isinstance(ps.results[0], RunnerFailedError)
        assert "Hash mismatch" in str(ps.results[0])

        # if only one file is broken, it should not spoil other runs
        assert ps.results[1] == 2
