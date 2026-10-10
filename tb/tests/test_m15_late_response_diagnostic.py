"""Standalone recovery test for AXI read responses after DMA reset."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel


CLOCK_NS = 10
STALE_DATA = 0xDEADCAFE
FRESH_DATA = 0x12345678


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


async def wait_for_read_data(dut):
    for _ in range(30):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(dut.m_axi_rready.value) == 1:
            return

    raise AssertionError("DMA did not enter READ_DATA")


async def wait_for_done(dut, limit=100):
    for _ in range(limit):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(dut.done.value) == 1:
            return

    raise AssertionError("Fresh transfer did not complete")


@cocotb.test()
async def recover_from_stale_read_response_after_reset(dut):
    memory = AxiMemoryModel(
        dut,
        initial_memory={
            0x1000: 0xAAAAAAAA,
            0x3000: FRESH_DATA,
        },
        read_delay_cycles=1000,
    )
    await setup(dut, memory)

    # Launch an old transfer and wait until its read response is outstanding.
    await submit(dut, 0x1000, 0x2000)
    await wait_for_read_data(dut)
    assert memory.pending_read_beats, "Expected an old read response pending"

    # Reset the DMA and keep the response channel disabled.
    await reset_dma(dut)

    # Model the external fabric's guarantee that old responses are now
    # impossible: discard its pending transaction and clear driven signals.
    memory.pending_read_beats.clear()
    memory.read_active = False
    memory.clear_read = False
    memory.read_delay_remaining = 0

    dut.m_axi_rvalid.value = 0
    dut.m_axi_rlast.value = 0

    # Inject a stale response while recovery_ready is low. It must not be
    # accepted, and it must not trigger a write or completion.
    await FallingEdge(dut.clk)
    dut.m_axi_rdata.value = STALE_DATA
    dut.m_axi_rresp.value = 0
    dut.m_axi_rlast.value = 1
    dut.m_axi_rvalid.value = 1

    for _ in range(3):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        assert int(dut.m_axi_rready.value) == 0, (
            "RREADY asserted while recovery_ready was low"
        )
        assert int(dut.done.value) == 0, (
            "Stale read response caused a completion"
        )
        assert int(dut.busy.value) == 0, (
            "DMA unexpectedly started while recovery was blocked"
        )

    dut.m_axi_rvalid.value = 0
    dut.m_axi_rlast.value = 0

    # With the external stale-response guarantee satisfied, permit recovery.
    memory.read_delay_cycles = 0
    memory.read_delay_remaining = 0
    dut.recovery_ready.value = 1

    await submit(dut, 0x3000, 0x4000)
    await wait_for_done(dut)

    observed = memory.memory.get(0x4000)
    assert observed == FRESH_DATA, (
        f"Fresh transfer copied {observed!r}, expected 0x{FRESH_DATA:08X}"
    )
    assert int(dut.error.value) == 0, "Fresh transfer reported an error"

    dut._log.info(
        "M15 read recovery passed: stale response blocked; "
        "fresh transfer copied 0x%08X",
        observed,
    )
