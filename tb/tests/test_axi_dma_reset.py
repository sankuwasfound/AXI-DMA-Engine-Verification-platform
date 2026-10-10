"""Reset recovery and transaction-abort tests for the AXI DMA."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel


CLOCK_NS = 10
BYTES_PER_BEAT = 4
QUEUE_DEPTH = 4


async def setup_dma(dut, memory):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.recovery_ready.value = 1
    dut.start.value = 0
    dut.src_addr.value = 0x1000
    dut.dst_addr.value = 0x2000
    dut.length_bytes.value = BYTES_PER_BEAT

    memory.initialize()

    # Prevent stale handshakes from a previous test before reset
    # has been sampled by the DUT.
    dut.m_axi_arready.value = 0
    dut.m_axi_awready.value = 0
    dut.m_axi_wready.value = 0
    dut.m_axi_rvalid.value = 0
    dut.m_axi_bvalid.value = 0

    cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start())

    for _ in range(3):
        await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

    # Start the slave model only after the DUT is safely reset.
    dut.m_axi_arready.value = 1
    dut.m_axi_awready.value = 1
    dut.m_axi_wready.value = 1
    cocotb.start_soon(memory.run())


async def submit(dut, src, dst, length):
    """Submit one descriptor at a rising clock edge."""
    await FallingEdge(dut.clk)
    dut.src_addr.value = src
    dut.dst_addr.value = dst
    dut.length_bytes.value = length
    dut.start.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start.value = 0


async def assert_reset_state(dut):
    """Apply synchronous active-low reset and check cleared status."""
    await FallingEdge(dut.clk)
    dut.start.value = 0
    dut.recovery_ready.value = 0
    dut.rst_n.value = 0

    for _ in range(2):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

    assert int(dut.busy.value) == 0, "busy did not clear on reset"
    assert int(dut.done.value) == 0, "done did not clear on reset"
    assert int(dut.error.value) == 0, "error did not clear on reset"
    assert int(dut.queue_level.value) == 0, "queue was not cleared on reset"
    assert int(dut.queue_empty.value) == 1, "queue_empty not asserted"
    assert int(dut.queue_full.value) == 0, "queue_full remained asserted"

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def wait_for_done(dut, limit=300):
    """Wait for a successful completion and reject unexpected errors."""
    for _ in range(limit):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        assert int(dut.error.value) == 0, "DMA reported an unexpected error"

        if int(dut.done.value):
            return

    raise AssertionError("DMA did not complete within the cycle limit")


@cocotb.test()
async def reset_aborts_delayed_read_and_recovers(dut):
    """Reset during READ_DATA must discard the active descriptor."""
    source = {
        0x1000: 0xA1000001,
        0x1004: 0xA1000002,
        0x1008: 0xA1000003,
        0x100C: 0xA1000004,
        0x3000: 0xB2000001,
    }

    memory = AxiMemoryModel(
        dut,
        initial_memory=source,
        read_delay_cycles=40,
    )
    await setup_dma(dut, memory)

    await submit(dut, 0x1000, 0x2000, 16)

    # Wait until the read address is accepted and the DMA waits for data.
    for _ in range(30):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(dut.m_axi_rready.value):
            break
    else:
        raise AssertionError("DMA never entered the read-data phase")

    assert int(dut.busy.value) == 1, "DMA should be busy before reset"

    await assert_reset_state(dut)

    # The memory model may still hold a pre-reset response. Clear its
    # response bookkeeping as part of resetting the simulated slave.
    memory.pending_read_beats.clear()
    memory.read_active = False
    memory.clear_read = False
    memory.read_delay_remaining = 0
    dut.m_axi_rvalid.value = 0
    dut.m_axi_rlast.value = 0
    dut.recovery_ready.value = 1

    # The aborted descriptor must not write to its destination.
    for _ in range(5):
        await RisingEdge(dut.clk)
    assert 0x2000 not in memory.memory, (
        "Aborted read unexpectedly produced a destination write"
    )

    await submit(dut, 0x3000, 0x4000, 4)
    await wait_for_done(dut)

    assert memory.memory.get(0x4000) == source[0x3000], (
        "Fresh transfer failed after resetting an active read"
    )
    assert 0x2000 not in memory.memory, (
        "Aborted descriptor executed after recovery"
    )


@cocotb.test()
async def reset_aborts_write_burst_and_recovers(dut):
    """Reset during WRITE_DATA must stop further DMA write beats."""
    source = {
        0x1000 + index * BYTES_PER_BEAT: 0xC3000000 + index
        for index in range(8)
    }
    source[0x3000] = 0xD4000001

    memory = AxiMemoryModel(
        dut,
        initial_memory=source,
        write_response_delay_cycles=20,
    )
    await setup_dma(dut, memory)

    await submit(dut, 0x1000, 0x2000, 8 * BYTES_PER_BEAT)

    # Wait until the write-data channel becomes active.
    for _ in range(100):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(dut.m_axi_wvalid.value):
            break
    else:
        raise AssertionError("DMA never entered the write-data phase")

    # Hold the slave's WREADY low so the burst cannot advance while
    # we establish a stable mid-write reset point.
    dut.m_axi_wready.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")

    assert int(dut.busy.value) == 1, "DMA should be busy during write"
    assert int(dut.m_axi_wvalid.value) == 1, (
        "Expected write-data valid before reset"
    )

    await assert_reset_state(dut)

    # Restore the memory model's default ready behavior.
    dut.m_axi_wready.value = 1
    dut.m_axi_awready.value = 1
    dut.m_axi_bvalid.value = 0

    # Discard slave-side state belonging to the aborted burst.
    memory.write_address = None
    memory.write_beats_remaining = 0
    memory.write_response_active = False
    memory.write_error_response_pending = False
    memory.clear_write_response = False
    memory.write_response_delay_remaining = 0
    dut.recovery_ready.value = 1

    # The reset descriptor must not resume writing after reset.
    for _ in range(8):
        await RisingEdge(dut.clk)
    assert int(dut.busy.value) == 0, "DMA restarted an aborted transfer"
    assert int(dut.done.value) == 0, "Aborted transfer reported done"

    await submit(dut, 0x3000, 0x4000, 4)
    await wait_for_done(dut)

    assert memory.memory.get(0x4000) == source[0x3000], (
        "Fresh transfer failed after resetting during a write"
    )


@cocotb.test()
async def reset_clears_queued_descriptors(dut):
    """Reset must discard queued descriptors and permit fresh work."""
    source = {
        0x1000: 0xE5000001,
        0x1100: 0xE5000002,
        0x1200: 0xE5000003,
        0x3000: 0xF6000001,
    }

    memory = AxiMemoryModel(
        dut,
        initial_memory=source,
        read_delay_cycles=40,
    )
    await setup_dma(dut, memory)

    # Start one active descriptor and queue three additional descriptors.
    await submit(dut, 0x1000, 0x2000, 4)
    await submit(dut, 0x1100, 0x2100, 4)
    await submit(dut, 0x1200, 0x2200, 4)
    await submit(dut, 0x1000, 0x2300, 4)

    assert int(dut.queue_level.value) == 3, (
        "Expected three queued descriptors before reset"
    )

    await assert_reset_state(dut)

    # Reset the simulated read slave too, preventing stale responses
    # from the pre-reset transaction from affecting the recovery test.
    memory.pending_read_beats.clear()
    memory.read_active = False
    memory.clear_read = False
    memory.read_delay_remaining = 0
    dut.m_axi_rvalid.value = 0
    dut.m_axi_rlast.value = 0
    dut.recovery_ready.value = 1

    for _ in range(8):
        await RisingEdge(dut.clk)

    assert int(dut.busy.value) == 0, "Old work restarted after reset"
    assert int(dut.queue_level.value) == 0, "Queue refilled after reset"
    assert 0x2100 not in memory.memory, "Queued descriptor 1 was executed"
    assert 0x2200 not in memory.memory, "Queued descriptor 2 was executed"
    assert 0x2300 not in memory.memory, "Queued descriptor 3 was executed"

    await submit(dut, 0x3000, 0x4000, 4)
    await wait_for_done(dut)

    assert memory.memory.get(0x4000) == source[0x3000], (
        "Fresh transfer failed after clearing the queue"
    )
    assert int(dut.queue_empty.value) == 1, (
        "Queue should be empty after recovery transfer"
    )
