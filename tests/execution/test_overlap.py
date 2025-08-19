import json
import os
import time

import pytest
from remoref.utils.basetestclass import BaseTestClass


def basic(a: int) -> int:
    import time

    time.sleep(a)

    return a


@pytest.mark.parametrize("t", [3])
class TestOverlap(BaseTestClass):
    def test_resub_during(self, t: int):
        ps = self.create_process(basic)

        ps.prepare(a=t)

        t0 = time.perf_counter()
        ps.run()
        time.sleep(t/2)

        ps.run()
        ps.wait(0.1, t + 1)
        ps.fetch_results()

        dt = time.perf_counter() - t0
        assert dt > t


class TestOutdatedResult(BaseTestClass):
    def test_outdated_result(self):
        ps = self.create_process(basic)

        os.mkdir(ps.local_dir)
        os.mkdir(ps.remote_dir)

        ps.prepare(a=3)

        with open(ps.runners[0].files.result.local, 'w') as f:
            json.dump("foo", f)
        with open(ps.runners[0].files.result.remote, 'w') as f:
            json.dump("foo", f)
        
        assert not ps.all_finished
        
        t0 = time.perf_counter()
        ps.run()
        ps.wait(0.1, 4)
        ps.fetch_results()

        dt = time.perf_counter() - t0
        assert dt > 3
        assert ps.results == [3]
        
