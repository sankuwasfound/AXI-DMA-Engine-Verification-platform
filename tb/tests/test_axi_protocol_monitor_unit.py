import pytest

from axi_protocol_monitor import AxiProtocolMonitor


CHANNEL_PAYLOADS = {
    "AR": (0x1000, 3, 2, 1),
    "R": (0xDEADBEEF, 0, 1),
    "AW": (0x2000, 7, 2, 1),
    "W": (0xCAFEBABE, 0xF, 1),
    "B": (0,),
}


def make_monitor():
    # Sampling logic can be tested without a live simulator DUT.
    monitor = AxiProtocolMonitor.__new__(AxiProtocolMonitor)
    monitor.stalled = {
        name: None for name in AxiProtocolMonitor.CHANNELS
    }
    monitor.stall_checks = {
        name: 0 for name in AxiProtocolMonitor.CHANNELS
    }
    return monitor


@pytest.mark.parametrize("channel", CHANNEL_PAYLOADS)
def test_stable_payload_during_stall_passes(channel):
    monitor = make_monitor()
    payload = CHANNEL_PAYLOADS[channel]

    monitor._check_sample(channel, 1, 0, payload)
    monitor._check_sample(channel, 1, 0, payload)
    monitor._check_sample(channel, 1, 1, payload)

    assert monitor.stall_checks[channel] == 2
    assert monitor.stalled[channel] is None


@pytest.mark.parametrize("channel", CHANNEL_PAYLOADS)
def test_valid_dropping_during_stall_is_detected(channel):
    monitor = make_monitor()
    payload = CHANNEL_PAYLOADS[channel]

    monitor._check_sample(channel, 1, 0, payload)

    with pytest.raises(
        AssertionError, match=f"AXI {channel}: VALID dropped while stalled"
    ):
        monitor._check_sample(channel, 0, 0, payload)


@pytest.mark.parametrize("channel", CHANNEL_PAYLOADS)
def test_payload_changing_during_stall_is_detected(channel):
    monitor = make_monitor()
    payload = CHANNEL_PAYLOADS[channel]
    changed_payload = (payload[0] ^ 1,) + payload[1:]

    monitor._check_sample(channel, 1, 0, payload)

    with pytest.raises(
        AssertionError, match=f"AXI {channel}: payload changed while stalled"
    ):
        monitor._check_sample(channel, 1, 0, changed_payload)


@pytest.mark.parametrize("channel", CHANNEL_PAYLOADS)
def test_new_transfer_can_start_after_handshake(channel):
    monitor = make_monitor()
    payload = CHANNEL_PAYLOADS[channel]
    next_payload = (payload[0] + 4,) + payload[1:]

    # First transfer stalls, then completes with a handshake.
    monitor._check_sample(channel, 1, 0, payload)
    monitor._check_sample(channel, 1, 1, payload)

    # A new transfer may now present a different payload.
    monitor._check_sample(channel, 1, 0, next_payload)

    assert monitor.stalled[channel] == next_payload


@pytest.mark.parametrize("channel", CHANNEL_PAYLOADS)
def test_reset_clears_stalled_channel_history(channel):
    monitor = make_monitor()
    payload = CHANNEL_PAYLOADS[channel]
    next_payload = (payload[0] + 4,) + payload[1:]

    # A transaction begins but is stalled.
    monitor._check_sample(channel, 1, 0, payload)
    assert monitor.stalled[channel] == payload

    # Exercise the same reset-history logic used by run().
    monitor._clear_stalled_history()

    # After reset, a fresh transaction may use a different payload.
    monitor._check_sample(channel, 1, 0, next_payload)

    assert monitor.stalled[channel] == next_payload
    assert monitor.stall_checks[channel] == 0
