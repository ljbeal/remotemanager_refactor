import os
import pytest
from remoref.engine.runnerstates import RunnerState
from remoref.utils.basetestclass import BaseTestClass


def f(x):
    # test_call_stack.py
    return x


class TestCallStack(BaseTestClass):

    nRunners = 5

    def setup_step(self, nStage, nTransfer, nRun):
        print(f"Testing with {nStage} stage calls")
        print(f"Testing with {nTransfer} transfer calls")
        print(f"Testing with {nRun} run calls")

        ps = self.create_process(f)

        print("appending")
        for i in range(self.nRunners):
            ps.prepare(x=i)

    def check_stage(self, nStage):
        for runner in self.ps.runners:
            if nStage > 0:
                assert runner.files.jobscript.exists_local
                assert runner.state == RunnerState.STAGED
            else:
                assert not runner.files.jobscript.exists_local
                assert runner.state == RunnerState.CREATED

    def check_transfer(self, nTransfer):
        for runner in self.ps.runners:
            if nTransfer > 0:
                assert os.path.exists(runner.files.jobscript.remote)
                assert runner.state == RunnerState.TRANSFERRED
            else:
                assert not os.path.exists(runner.files.jobscript.remote)

    def check_run(self, nRun, expected: list):
        for runner in self.ps.runners:
            if nRun > 0:
                assert runner.state == RunnerState.RUNNING

        self.ps.wait(0.1, 2)
        self.ps.fetch_results()

        for runner in self.ps.runners:
            if nRun > 0:
                assert runner.state == RunnerState.COMPLETED

        assert self.ps.results == expected

    @pytest.mark.parametrize("nStage", [0, 1, 2])  # number of times to call stage
    @pytest.mark.parametrize("nTransfer", [0, 1, 2])  # number of times to call transfer
    @pytest.mark.parametrize("nRun", [0, 1, 2])  # number of times to call run
    def test_instances(self, nStage, nTransfer, nRun):
        self.setup_step(nStage, nTransfer, nRun)

        ### Staging ###
        print("### Staging ###")
        for i in range(nStage):
            self.ps.stage()
        self.check_stage(nStage)

        ### Transfer ###
        print("### Transfer ###")
        for i in range(nTransfer):
            self.ps.transfer()
    
        self.check_transfer(nTransfer)

        ### Run ###
        print("### Run ###")

        if nRun > 0:
            expected = [i for i in range(self.nRunners)]
        else:
            expected = [None] * self.nRunners

        for i in range(nRun):
            self.ps.run()

        self.check_run(nRun=nRun, expected=expected)
