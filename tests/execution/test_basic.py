from alchemy_test.utils.basetestclass import BaseTestClass


def basic(a: int) -> int:
    return a


class TestBasic(BaseTestClass):
    def test_direct(self):        
        ps = self.create_process(basic)
        
        assert ps(1) == 1
        assert ps(4) == 4

    def test_multi(self):
        ps = self.create_process(basic)

        for i in range(10):
            ps.prepare(a=i)
        
        ps.run()

        ps.wait(0.1, 2)
        ps.fetch_results()
        assert ps.results == [i for i in range(10)]
