from alchemy_test.engine.runnerstates import RunnerState
from alchemy_test.utils.basetestclass import BaseTestClass


def basic(a: int, fail: bool = False) -> int:
    if fail:
        raise ValueError("This is a failure")
    return a


class TestBasic(BaseTestClass):
    def test_run(self):
        ps = self.create_process(basic)
        
        ps.prepare(a=1)
        assert ps.runners[0].state == RunnerState.CREATED

        ps.stage()
        assert ps.runners[0].state == RunnerState.STAGED

        ps.transfer()
        assert ps.runners[0].state == RunnerState.TRANSFERRED

        ps.run()
        assert ps.runners[0].state == RunnerState.RUNNING

        ps.wait(0.1, 2)
        assert ps.runners[0].state == RunnerState.COMPLETED
    
    def test_fail(self):
        ps = self.create_process(basic)

        ps.prepare(a=1, fail=True)

        try:
            self.run_ps()
        except RuntimeError:
            pass

        assert ps.runners[0].state == RunnerState.FAILED
