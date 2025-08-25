import pytest
from remoref.engine.runnerstates import State

# Define a list of tuples where each tuple contains (first, second) states to compare
comparison_tests = [
    (State("CREATED"), State("STAGED")),
    (State("STAGED"), State("TRANSFERRED")),
    (State("TRANSFERRED"), State("RUNNING")),
    (State("RUNNING"), State("COMPLETED")),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests)
def test_state_comparison(first_state, second_state):
    assert first_state < second_state

# Define a list of states to test for equality and greater/less than comparisons
states = [State("CREATED"), State("STAGED"), State("TRANSFERRED"), State("RUNNING"), State("COMPLETED"), State("FAILED")]

@pytest.mark.parametrize("state", states)
def test_state_equality(state):
    assert state == state

comparison_tests_gt = [
    (State("CREATED"), State("STAGED")),
    (State("STAGED"), State("TRANSFERRED")),
    (State("TRANSFERRED"), State("RUNNING")),
    (State("RUNNING"), State("COMPLETED")),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_gt)
def test_state_greater_than(first_state, second_state):
    assert first_state < second_state

comparison_tests_ge = [
    (State("CREATED"), State("STAGED")),
    (State("STAGED"), State("TRANSFERRED")),
    (State("TRANSFERRED"), State("RUNNING")),
    (State("RUNNING"), State("COMPLETED")),
    (State("CREATED"), State("CREATED")),
    (State("STAGED"), State("STAGED")),
    (State("TRANSFERRED"), State("TRANSFERRED")),
    (State("RUNNING"), State("RUNNING")),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_ge)
def test_state_greater_equal(first_state, second_state):
    assert first_state <= second_state

comparison_tests_lt = [
    (State("CREATED"), State("STAGED")),
    (State("STAGED"), State("TRANSFERRED")),
    (State("TRANSFERRED"), State("RUNNING")),
    (State("RUNNING"), State("COMPLETED")),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_lt)
def test_state_less_than(first_state, second_state):
    assert first_state < second_state

comparison_tests_le = [
    (State("CREATED"), State("STAGED")),
    (State("STAGED"), State("TRANSFERRED")),
    (State("TRANSFERRED"), State("RUNNING")),
    (State("RUNNING"), State("COMPLETED")),
    (State("CREATED"), State("CREATED")),
    (State("STAGED"), State("STAGED")),
    (State("TRANSFERRED"), State("TRANSFERRED")),
    (State("RUNNING"), State("RUNNING")),
]
@pytest.mark.parametrize("first_state, second_state", comparison_tests_le)
def test_state_less_equal(first_state, second_state):
    assert first_state <= second_state
