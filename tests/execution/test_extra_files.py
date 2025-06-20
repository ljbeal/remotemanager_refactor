import pytest
from alchemy_test.utils.basetestclass import BaseTestClass


def read(ifile: str) -> str:
    with open(ifile, 'r') as f:
        data = f.read()
    return data


@pytest.mark.parametrize("nRunners", [1, 5])
class TestSend(BaseTestClass):
    def test_send(self, nRunners: int):
        ps = self.create_process(read)

        for i in range(nRunners):
            
            with open(f"test_send_in_{i}.txt", "w+") as o:
                o.write("foo")
            
            ps.prepare(ifile=f"test_send_in_{i}.txt", extra_files_send=[f"test_send_in_{i}.txt"])

        ps.run()
        ps.wait(0.1, 2)
        ps.fetch_results()

        assert ps.results == ["foo"] * nRunners
