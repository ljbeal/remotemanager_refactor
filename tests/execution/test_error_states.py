import pytest
from remoref.engine.exceptions import RunnerFailedError
from remoref.utils.basetestclass import BaseTestClass
from remotemanager import URL


def run(a: int) -> int:
    return a


class TestErrorStates(BaseTestClass):
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
