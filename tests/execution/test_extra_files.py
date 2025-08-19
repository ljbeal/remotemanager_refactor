import pytest
from remoref.utils.basetestclass import BaseTestClass


def read(ifile: str) -> str:
    with open(ifile, 'r') as f:
        data = f.read()
    return data


def copy(ifile: str, ofile: str) -> None:
    with open(ifile, 'r') as f:
        data = f.read()
    
    with open(ofile, 'w+') as f:
        f.write(data)


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

    def test_copy(self, nRunners: int):        
        ps = self.create_process(copy)

        for i in range(nRunners):
            with open(f"test_in_{i}.txt", "w+") as o:
                o.write("foo")
            
            ps.prepare(
                ifile=f"test_in_{i}.txt", 
                ofile=f"test_out_{i}.txt", 
                extra_files_send=[f"test_in_{i}.txt"], 
                extra_files_recv= [f"test_out_{i}.txt"],
            )

        ps.run()
        ps.wait(0.1, 2)
        ps.fetch_results()

        # search locally for the file content
        for runner in ps.runners:
            assert runner.files.extra_recv[0].content == "foo"
