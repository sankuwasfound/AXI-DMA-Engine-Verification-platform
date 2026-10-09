import pytest

from axi_memory_model import AxiMemoryModel


class DummyDut:
    """Minimal DUT placeholder for constructor-only unit tests."""


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"read_delay_cycles": -1}, "Response delays"),
        ({"write_response_delay_cycles": -1}, "Response delays"),
        ({"max_random_read_delay": -1}, "Random delay limits"),
        ({"max_random_write_response_delay": -1}, "Random delay limits"),
        ({"backpressure_probability": -0.1}, "Backpressure probability"),
        ({"backpressure_probability": 1.1}, "Backpressure probability"),
    ],
)
def test_invalid_configuration_is_rejected(kwargs, message):
    with pytest.raises(ValueError, match=message):
        AxiMemoryModel(DummyDut(), **kwargs)


def test_default_configuration_is_deterministic():
    first = AxiMemoryModel(DummyDut())
    second = AxiMemoryModel(DummyDut())

    assert first.random_seed == second.random_seed == 0
    assert first.backpressure_probability == 0.0
    assert first.read_delay_cycles == 0
    assert first.write_response_delay_cycles == 0


def test_randomized_ready_is_reproducible_with_same_seed():
    first = AxiMemoryModel(
        DummyDut(),
        backpressure_probability=0.5,
        random_seed=1234,
    )
    second = AxiMemoryModel(
        DummyDut(),
        backpressure_probability=0.5,
        random_seed=1234,
    )

    first_results = [first._randomized_ready() for _ in range(100)]
    second_results = [second._randomized_ready() for _ in range(100)]

    assert first_results == second_results
    assert set(first_results) <= {0, 1}


def test_randomized_ready_respects_probability_extremes():
    never_stall = AxiMemoryModel(
        DummyDut(),
        backpressure_probability=0.0,
        random_seed=7,
    )
    always_stall = AxiMemoryModel(
        DummyDut(),
        backpressure_probability=1.0,
        random_seed=7,
    )

    assert all(never_stall._randomized_ready() == 1 for _ in range(20))
    assert all(always_stall._randomized_ready() == 0 for _ in range(20))
