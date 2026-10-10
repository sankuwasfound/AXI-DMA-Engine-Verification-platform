"""Standalone diagnostic for stale AXI write responses after DMA reset."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel


CLOCK_NS = 10


async def setup(dut, memory):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.start.value = 0
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
async def diagnose_stale_write_response_after_reset(dut):
    memory = AxiMemoryModel(
        dut,
        initial_memory={
            0x1000: 0x11112222,
            0x3000: 0x33334444,
        },
        write_response_delay_cycles=1000,
    )
    await setup(dut, memory)

    # Complete the old transaction's address/data handshakes, but delay B.
    await submit(dut, 0x1000, 0x2000)
    await wait_for_signal(
        dut.m_axi_bready, 1, dut, "old WRITE_RESP state"
    )
    assert memory.write_response_active or memory.write_error_response_pending

    # Reset the DMA while the old write response is outstanding.
    await reset_dma(dut)

    # Suppress the scheduled B response and inject it at a controlled time.
    memory.write_error_response_pending = False
    memory.write_response_active = False
    memory.clear_write_response = False
    memory.write_response_delay_remaining = 0
    dut.m_axi_bvalid.value = 0
    dut.m_axi_bresp.value = 0

    # Start a fresh transaction and wait until its B response is expected.
    await submit(dut, 0x3000, 0x4000)
    await wait_for_signal(
        dut.m_axi_bready, 1, dut, "fresh WRITE_RESP state"
    )

    # Inject the old successful B response while the fresh write is waiting.
    await FallingEdge(dut.clk)
    await Timer(2, unit="ps")
    dut.m_axi_bresp.value = 0
    dut.m_axi_bvalid.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")

    accepted_as_fresh = int(dut.done.value) == 1
    dut.m_axi_bvalid.value = 0

    dut._log.warning(
        "M15 write diagnostic: stale B response accepted as fresh completion=%s",
        accepted_as_fresh,
    )

    # This diagnostic passes only when the suspected limitation is reproduced.
    assert accepted_as_fresh, (
        "Stale B response was not accepted as fresh completion"
    )

    dut._log.warning(
        "M15 limitation reproduced: stale B response completed the fresh "
        "transaction before its own B response was generated."
    )
