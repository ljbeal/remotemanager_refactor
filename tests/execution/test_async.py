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
    nRunners = 5

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

        if asynchronous:
            assert dt < self.sleeptime + 1
        else:
            assert dt >= self.sleeptime * self.nRunners
