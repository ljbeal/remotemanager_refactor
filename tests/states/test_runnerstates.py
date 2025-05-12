import pytest
from alchemy_test.engine.runnerstates import RunnerState

# Define a list of tuples where each tuple contains (first, second) states to compare
comparison_tests = [
    (RunnerState.CREATED, RunnerState.STAGED),
    (RunnerState.STAGED, RunnerState.TRANSFERRED),
    (RunnerState.TRANSFERRED, RunnerState.RUNNING),
    (RunnerState.RUNNING, RunnerState.COMPLETED),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests)
def test_state_comparison(first_state, second_state):
    assert first_state < second_state

# Define a list of states to test for equality and greater/less than comparisons
states = [RunnerState.CREATED, RunnerState.STAGED, RunnerState.TRANSFERRED, RunnerState.RUNNING, RunnerState.COMPLETED, RunnerState.FAILED]

@pytest.mark.parametrize("state", states)
def test_state_equality(state):
    assert state == state

comparison_tests_gt = [
    (RunnerState.CREATED, RunnerState.STAGED),
    (RunnerState.STAGED, RunnerState.TRANSFERRED),
    (RunnerState.TRANSFERRED, RunnerState.RUNNING),
    (RunnerState.RUNNING, RunnerState.COMPLETED),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_gt)
def test_state_greater_than(first_state, second_state):
    assert first_state < second_state

comparison_tests_ge = [
    (RunnerState.CREATED, RunnerState.STAGED),
    (RunnerState.STAGED, RunnerState.TRANSFERRED),
    (RunnerState.TRANSFERRED, RunnerState.RUNNING),
    (RunnerState.RUNNING, RunnerState.COMPLETED),
    (RunnerState.CREATED, RunnerState.CREATED),
    (RunnerState.STAGED, RunnerState.STAGED),
    (RunnerState.TRANSFERRED, RunnerState.TRANSFERRED),
    (RunnerState.RUNNING, RunnerState.RUNNING),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_ge)
def test_state_greater_equal(first_state, second_state):
    assert first_state <= second_state

comparison_tests_lt = [
    (RunnerState.CREATED, RunnerState.STAGED),
    (RunnerState.STAGED, RunnerState.TRANSFERRED),
    (RunnerState.TRANSFERRED, RunnerState.RUNNING),
    (RunnerState.RUNNING, RunnerState.COMPLETED),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_lt)
def test_state_less_than(first_state, second_state):
    assert first_state < second_state

comparison_tests_le = [
    (RunnerState.CREATED, RunnerState.STAGED),
    (RunnerState.STAGED, RunnerState.TRANSFERRED),
    (RunnerState.TRANSFERRED, RunnerState.RUNNING),
    (RunnerState.RUNNING, RunnerState.COMPLETED),
    (RunnerState.CREATED, RunnerState.CREATED),
    (RunnerState.STAGED, RunnerState.STAGED),
    (RunnerState.TRANSFERRED, RunnerState.TRANSFERRED),
    (RunnerState.RUNNING, RunnerState.RUNNING),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_le)
def test_state_less_equal(first_state, second_state):
    assert first_state <= second_state
