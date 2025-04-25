from alchemy_test.utils.basetestclass import BaseTestClass


def basic(a: int) -> int:
    return a


class TestIsFinished(BaseTestClass):
    def test_norun(self):
        ps = self.create_process(basic)
        assert not ps.is_finished
