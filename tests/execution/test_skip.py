import os
import time
from alchemy_test.utils.basetestclass import BaseTestClass


def basic(a: int) -> int:
    return a


class TestSkip(BaseTestClass):
    def test_skip(self):
        ps = self.create_process(basic)
        
        ps.prepare(a=1)

        assert ps.run()
        ps.wait(0.1, 2)

        result_mtime = os.path.getmtime(ps.runners[0].files.result.remote)

        time.sleep(1)

        assert not ps.run()

        assert os.path.getmtime(ps.runners[0].files.result.remote) == result_mtime

    def test_force(self):
        ps = self.create_process(basic)
        
        ps.prepare(a=1)

        assert ps.run()
        ps.wait(0.1, 2)

        result_mtime = os.path.getmtime(ps.runners[0].files.result.remote)

        time.sleep(1)

        assert ps.run(force=True)

        assert os.path.getmtime(ps.runners[0].files.result.remote) > result_mtime
