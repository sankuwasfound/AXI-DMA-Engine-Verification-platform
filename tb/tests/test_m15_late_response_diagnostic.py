"""Standalone diagnostic for stale AXI read responses after DMA reset."""

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
    dut.src_addr.value = 0x1000
    dut.dst_addr.value = 0x2000
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
        if int(dut.m_axi_rready.value):
            return

    raise AssertionError("DMA did not enter READ_DATA")


@cocotb.test()
async def diagnose_stale_read_response_after_reset(dut):
    memory = AxiMemoryModel(
        dut,
        initial_memory={
            0x1000: 0xAAAAAAAA,
            0x3000: FRESH_DATA,
        },
        read_delay_cycles=1000,
    )
    await setup(dut, memory)

    # Accept an old read transaction, but delay its response.
    await submit(dut, 0x1000, 0x2000)
    await wait_for_read_data(dut)

    assert memory.pending_read_beats, "Expected an old read response pending"

    # Reset the DMA while the old transaction is outstanding.
    await reset_dma(dut)

    # Suppress the memory model's scheduled response. We will inject the
    # old response manually at a controlled point in the new transaction.
    memory.pending_read_beats.clear()
    memory.read_active = False
    memory.clear_read = False
    memory.read_delay_remaining = 0

    dut.m_axi_rvalid.value = 0
    dut.m_axi_rlast.value = 0

    # Start a fresh transaction and wait until it requests read data.
    await submit(dut, 0x3000, 0x4000)
    await wait_for_read_data(dut)

    # Inject the old successful one-beat response during the fresh transfer.
    await FallingEdge(dut.clk)
    await Timer(2, unit="ps")
    dut.m_axi_rdata.value = STALE_DATA
    dut.m_axi_rresp.value = 0
    dut.m_axi_rlast.value = 1
    dut.m_axi_rvalid.value = 1

    # Wait for the DMA to accept the response and leave READ_DATA.
    for _ in range(100):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(dut.m_axi_rready.value) == 0:
            break
    else:
        raise AssertionError("DMA did not leave READ_DATA after injected response")

    dut.m_axi_rvalid.value = 0

    # Wait for the resulting write transaction to complete.
    for _ in range(100):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")
        if int(dut.done.value):
            break
    else:
        raise AssertionError("DMA did not complete after injected response")

    observed = memory.memory.get(0x4000)

    dut._log.warning(
        "M15 diagnostic: destination=0x%08X, stale=0x%08X, fresh=0x%08X",
        observed if observed is not None else 0,
        STALE_DATA,
        FRESH_DATA,
    )

    # This diagnostic passes only when it reproduces the suspected issue.
    assert observed == STALE_DATA, (
        "Stale-response behavior was not reproduced: "
        f"destination contains {observed!r}"
    )

    dut._log.warning(
        "M15 limitation reproduced: the stale R response was consumed "
        "as data for the fresh transaction."
    )
