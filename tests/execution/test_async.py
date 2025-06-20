import time
import pytest
from alchemy_test.utils.basetestclass import BaseTestClass


def basic(a: int, t: float) -> int:
    import time

    time.sleep(t)

    return a


class TestAsync(BaseTestClass):

    sleeptime = 0.5
    nRunners = 10

    @pytest.mark.parametrize("setpoint", ["init", "append", "run"])
    def test_async(self, setpoint: str):
        if setpoint == "init":
            ps = self.create_process(basic, asynchronous=True)
        else:
            ps = self.create_process(basic)

        if setpoint == "append":
            for i in range(self.nRunners):
                ps.prepare(a=i, t=self.sleeptime, asynchronous=True)
        else:
            for i in range(self.nRunners):
                ps.prepare(a=i, t=self.sleeptime)
        
        t0 = time.perf_counter()        
        if setpoint == "run":
            self.run_ps(asynchronous=True)
        else:
            self.run_ps()

        dt = time.perf_counter() - t0

        # async run should take approximately sleeptime, since they should run in parallel
        # in practice, that's not the case when running in the CI, but we can add some flexibility
        # to the time constraint.
        flex_time = self.sleeptime + 3
        assert dt < flex_time

        # just to make sure the test remains valid if we update it blindly
        assert flex_time < self.sleeptime * self.nRunners

    def test_comparison(self):
        ps = self.create_process(basic)

        for i in range(self.nRunners):
            ps.prepare(a=i, t=self.sleeptime)
    
        t0 = time.perf_counter()     
        self.run_ps(asynchronous=True)

        dt_async = time.perf_counter() - t0
        
        # now perform the run again, sequentially
        t0 = time.perf_counter()    
        self.run_ps(force=True, asynchronous=False)

        dt_seq = time.perf_counter() - t0
        
        assert dt_seq >= self.sleeptime * self.nRunners

        # theoretically the async run should not take much more than sleeptime,
        # but in reality this is not the case when run on the CI/actions
        # Just make sure that we're less than half the sequential run
        assert dt_async < dt_seq / 2
