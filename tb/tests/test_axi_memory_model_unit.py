
import pytest

from axi_memory_model import AxiMemoryModel


class DummyDut:
    """Minimal DUT placeholder for unit tests."""


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


@pytest.mark.parametrize(
    ("old_value", "write_data", "write_strobe", "expected"),
    [
        (0x11223344, 0xAABBCCDD, 0b1111, 0xAABBCCDD),
        (0x11223344, 0xAABBCCDD, 0b0001, 0x112233DD),
        (0x11223344, 0xAABBCCDD, 0b1010, 0xAA22CC44),
        (0x11223344, 0xAABBCCDD, 0b0000, 0x11223344),
    ],
)
def test_write_strobes_update_only_enabled_byte_lanes(
    old_value, write_data, write_strobe, expected
):
    actual = AxiMemoryModel._apply_write_strobes(
        old_value=old_value,
        write_data=write_data,
        write_strobe=write_strobe,
        bytes_per_beat=4,
    )

    assert actual == expected


def test_write_response_delay_configuration_is_preserved():
    model = AxiMemoryModel(
        DummyDut(),
        write_response_delay_cycles=3,
        max_random_write_response_delay=4,
        random_seed=123,
    )

    assert model.write_response_delay_cycles == 3
    assert model.max_random_write_response_delay == 4
    assert model.write_response_delay_remaining == 0


def test_write_response_delay_helper_applies_fixed_and_random_delay():
    model = AxiMemoryModel(
        DummyDut(),
        write_response_delay_cycles=3,
        max_random_write_response_delay=5,
        random_seed=123,
    )

    for _ in range(100):
        model._schedule_write_response_delay()
        assert 3 <= model.write_response_delay_remaining <= 8


def test_write_response_delay_helper_is_reproducible():
    first = AxiMemoryModel(
        DummyDut(),
        write_response_delay_cycles=2,
        max_random_write_response_delay=5,
        random_seed=123,
    )
    second = AxiMemoryModel(
        DummyDut(),
        write_response_delay_cycles=2,
        max_random_write_response_delay=5,
        random_seed=123,
    )

    first_delays = []
    second_delays = []

    for _ in range(20):
        first._schedule_write_response_delay()
        second._schedule_write_response_delay()

        first_delays.append(first.write_response_delay_remaining)
        second_delays.append(second.write_response_delay_remaining)

    assert first_delays == second_delays
    assert all(2 <= delay <= 7 for delay in first_delays)
