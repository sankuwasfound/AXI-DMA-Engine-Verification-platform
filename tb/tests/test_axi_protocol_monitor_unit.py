import pytest

from axi_protocol_monitor import AxiProtocolMonitor


def make_monitor():
    # The sample-checking method does not need a live DUT.
    monitor = AxiProtocolMonitor.__new__(AxiProtocolMonitor)
    monitor.stalled = {
        name: None for name in AxiProtocolMonitor.CHANNELS
    }
    monitor.stall_checks = {
        name: 0 for name in AxiProtocolMonitor.CHANNELS
    }
    return monitor


def test_stable_payload_during_stall_passes():
    monitor = make_monitor()

    monitor._check_sample("AR", 1, 0, (0x1000, 3, 2, 1))
    monitor._check_sample("AR", 1, 0, (0x1000, 3, 2, 1))
    monitor._check_sample("AR", 1, 1, (0x1000, 3, 2, 1))

    assert monitor.stall_checks["AR"] == 2
    assert monitor.stalled["AR"] is None


def test_valid_dropping_during_stall_is_detected():
    monitor = make_monitor()

    monitor._check_sample("W", 1, 0, (0xDEADBEEF, 0xF, 1))

    with pytest.raises(AssertionError, match="VALID dropped while stalled"):
        monitor._check_sample("W", 0, 0, (0xDEADBEEF, 0xF, 1))


def test_payload_changing_during_stall_is_detected():
    monitor = make_monitor()

    monitor._check_sample("AW", 1, 0, (0x2000, 7, 2, 1))

    with pytest.raises(AssertionError, match="payload changed while stalled"):
        monitor._check_sample("AW", 1, 0, (0x3000, 7, 2, 1))
