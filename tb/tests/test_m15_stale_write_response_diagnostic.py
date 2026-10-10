"""Verify AXI write-response recovery after a DMA-only reset.

The test models the external fabric guarantee that old responses are
impossible before recovery_ready is asserted.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel

CLOCK_NS = 10


async def setup(dut, memory):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.recovery_ready.value = 1
    dut.src_addr.value = 0x1000
    dut.dst_addr.value = 0x2000
    dut.length_bytes.value = 4

    memory.initialize()
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
    dut.m_axi_arready.value = 1
    dut.m_axi_awready.value = 1
    dut.m_axi_wready.value = 1
    cocotb.start_soon(memory.run())


async def submit(dut, src, dst):
    await FallingEdge(dut.clk)
    dut.src_addr.value = src
    dut.dst_addr.value = dst
    dut.length_bytes.value = 4
    dut.start.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start.value = 0


async def reset_dma(dut):
    await FallingEdge(dut.clk)
    dut.start.value = 0
    dut.recovery_ready.value = 0
    dut.rst_n.value = 0

    for _ in range(2):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

    assert int(dut.busy.value) == 0
    assert int(dut.queue_level.value) == 0

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def wait_for_signal(signal, expected, dut, description, limit=100):
    for _ in range(limit):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(signal.value) == expected:
            return

    raise AssertionError(f"Timed out waiting for {description}")


@cocotb.test()
async def verify_stale_write_response_recovery(dut):
    fresh_data = 0x33334444

    memory = AxiMemoryModel(
        dut,
        initial_memory={
            0x1000: 0x11112222,
            0x3000: fresh_data,
        },
        write_response_delay_cycles=1000,
    )
    await setup(dut, memory)

    # Reach the old transaction's write-response state.
    await submit(dut, 0x1000, 0x2000)
    await wait_for_signal(
        dut.m_axi_bready, 1, dut, "old WRITE_RESP state"
    )
    assert (
        memory.write_response_active
        or memory.write_error_response_pending
    )

    # Reset the DMA while its old B response is outstanding.
    await reset_dma(dut)

    # Model the external fabric guaranteeing that the old response
    # has been drained/cancelled and can no longer arrive.
    memory.write_error_response_pending = False
    memory.write_response_active = False
    memory.clear_write_response = False
    memory.write_response_delay_remaining = 0
    dut.m_axi_bvalid.value = 0
    dut.m_axi_bresp.value = 0

    # Inject a stale B response while recovery is disabled.
    await FallingEdge(dut.clk)
    dut.m_axi_bresp.value = 0
    dut.m_axi_bvalid.value = 1

    for _ in range(3):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        assert int(dut.m_axi_bready.value) == 0, (
            "DMA accepted B response while recovery_ready was low"
        )
        assert int(dut.done.value) == 0, (
            "Stale B response caused false completion"
        )
        assert int(dut.busy.value) == 0, (
            "DMA unexpectedly became busy during recovery hold"
        )

    # Remove the stale response before enabling recovery.
    await FallingEdge(dut.clk)
    dut.m_axi_bvalid.value = 0
    dut.recovery_ready.value = 1
    memory.write_response_delay_cycles = 0

    # A fresh transfer must complete normally.
    await submit(dut, 0x3000, 0x4000)
    await wait_for_signal(dut.done, 1, dut, "fresh transfer completion")

    assert memory.memory[0x4000] == fresh_data, (
        f"Fresh destination data mismatch: "
        f"got 0x{memory.memory[0x4000]:08X}, "
        f"expected 0x{fresh_data:08X}"
    )
    assert int(dut.error.value) == 0, "Fresh transfer reported an error"

    dut._log.info(
        "M15 write recovery passed: stale B response blocked; "
        "fresh transfer copied 0x%08X",
        fresh_data,
    )
