import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel
from functional_coverage import hit


CLOCK_PERIOD_NS = 10
SOURCE = 0x1000
DESTINATION = 0x2000
SOURCE_WORD = 0xDEADBEEF


async def prepare_dut(dut, memory_model=None):
    """Reset the DMA and start the clock and optional AXI memory model."""
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.recovery_ready.value = 1
    dut.start.value = 0
    dut.src_addr.value = SOURCE
    dut.dst_addr.value = DESTINATION
    dut.length_bytes.value = 4

    if memory_model is None:
        memory_model = AxiMemoryModel(dut)

    memory_model.initialize()

    cocotb.start_soon(
        Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start()
    )
    cocotb.start_soon(memory_model.run())

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")

    return memory_model


async def launch_transfer(dut, source=SOURCE, destination=DESTINATION,
                          length=4):
    """Launch one request on a falling clock edge."""
    await FallingEdge(dut.clk)
    dut.src_addr.value = source
    dut.dst_addr.value = destination
    dut.length_bytes.value = length
    dut.start.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start.value = 0


async def wait_for_error_or_done(dut, limit=30):
    """Wait until the DMA reports either success or an error."""
    for _ in range(limit):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if int(dut.error.value):
            return "error"

        if int(dut.done.value):
            return "done"

    raise AssertionError(
        f"DMA produced neither done nor error within {limit} cycles"
    )


@cocotb.test()
async def rejects_zero_length_transfer(dut):
    """A zero-byte request must fail without issuing AXI traffic."""
    await prepare_dut(dut)
    await launch_transfer(dut, length=0)

    assert int(dut.error.value) == 1, "Zero length was not rejected"
    assert int(dut.done.value) == 0, "Invalid request reported done"
    assert int(dut.busy.value) == 0, "DMA busy after invalid request"
    assert int(dut.m_axi_arvalid.value) == 0, "Unexpected AXI read request"
    assert int(dut.m_axi_awvalid.value) == 0, "Unexpected AXI write request"

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    assert int(dut.error.value) == 0, "Error should be a one-cycle pulse"

    hit("error.zero_length")


@cocotb.test()
async def rejects_unaligned_source_address(dut):
    """An unaligned source address must fail before issuing AXI traffic."""
    await prepare_dut(dut)
    await launch_transfer(dut, source=SOURCE + 1)

    assert int(dut.error.value) == 1, "Unaligned source was not rejected"
    assert int(dut.done.value) == 0, "Invalid request reported done"
    assert int(dut.busy.value) == 0, "DMA busy after invalid request"
    assert int(dut.m_axi_arvalid.value) == 0, "Unexpected AXI read request"
    assert int(dut.m_axi_awvalid.value) == 0, "Unexpected AXI write request"

    hit("error.unaligned_source")


@cocotb.test()
async def reports_axi_read_error(dut):
    """An AXI SLVERR on the read response must abort the transfer."""
    memory_model = AxiMemoryModel(
        dut,
        initial_memory={SOURCE: SOURCE_WORD},
        read_resp=2,
    )
    await prepare_dut(dut, memory_model)
    await launch_transfer(dut)

    result = await wait_for_error_or_done(dut)

    assert result == "error", "Read error did not produce DMA error"
    assert int(dut.done.value) == 0, "DMA reported done after read error"
    assert int(dut.busy.value) == 0, "DMA remained busy after read error"
    assert DESTINATION not in memory_model.memory, (
        "DMA unexpectedly wrote destination after read error"
    )

    hit("error.axi_read_slverr")


@cocotb.test()
async def reports_axi_write_error(dut):
    """An AXI SLVERR on the write response must not report success."""
    memory_model = AxiMemoryModel(
        dut,
        initial_memory={SOURCE: SOURCE_WORD},
        write_resp=2,
    )
    await prepare_dut(dut, memory_model)
    await launch_transfer(dut)

    result = await wait_for_error_or_done(dut)

    assert result == "error", "Write error did not produce DMA error"
    assert int(dut.done.value) == 0, "DMA reported done after write error"
    assert int(dut.busy.value) == 0, "DMA remained busy after write error"

    # A write response error does not guarantee that the slave left memory
    # unchanged. The important check here is that the DMA reports failure.
    hit("error.axi_write_slverr")
