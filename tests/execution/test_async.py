import time
import pytest
from alchemy_test.utils.basetestclass import BaseTestClass


def basic(a: int, t: float) -> int:
    import time

    time.sleep(t)

    return a


@pytest.mark.parametrize("setpoint", ["init", "append", "run"])
@pytest.mark.parametrize("asynchronous", [True, False])
class TestAsync(BaseTestClass):

    sleeptime = 0.5
    nRunners = 10

    def test_async(self, setpoint: str, asynchronous: bool):
        if setpoint == "init":
            ps = self.create_process(basic, asynchronous=asynchronous)
        else:
            ps = self.create_process(basic)

        if setpoint == "append":
            for i in range(self.nRunners):
                ps.prepare(a=i, t=self.sleeptime, asynchronous=asynchronous)
        else:
            for i in range(self.nRunners):
                ps.prepare(a=i, t=self.sleeptime)
        
        t0 = time.perf_counter()        
        if setpoint == "run":
            self.run_ps(asynchronous=asynchronous)
        else:
            self.run_ps()

        dt = time.perf_counter() - t0

        # async run should take approximately sleeptime, since they should run in parallel
        # in practice, that's not the case when running in the CI, but we can add some flexibility
        # to the time constraint.
        if asynchronous:
            flex_time = self.sleeptime + 2
            assert dt < flex_time
            # just to make sure the test remains valid if we update it blindly
            assert flex_time < self.sleeptime * self.nRunners
        else:
            assert dt >= self.sleeptime * self.nRunners
