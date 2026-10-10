
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def wait_for_high(signal, clk, limit=20):
    """Wait until a signal becomes high, with a cycle timeout."""
    for _ in range(limit):
        await Timer(1, unit="ns")
        if int(signal.value) == 1:
            return
        await RisingEdge(clk)
    raise AssertionError(f"Timeout waiting for {signal._name} to become high")


@cocotb.test()
async def single_word_copy_test(dut):
    source_address = 0x1000
    destination_address = 0x2000
    source_word = 0xDEADBEEF

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Initialize control and AXI slave inputs.
    dut.rst_n.value = 0
    dut.recovery_ready.value = 1
    dut.start.value = 0
    dut.src_addr.value = source_address
    dut.dst_addr.value = destination_address
    dut.length_bytes.value = 4

    dut.m_axi_arready.value = 1
    dut.m_axi_rdata.value = 0
    dut.m_axi_rresp.value = 0
    dut.m_axi_rlast.value = 1
    dut.m_axi_rvalid.value = 0

    dut.m_axi_awready.value = 1
    dut.m_axi_wready.value = 1

    dut.m_axi_bresp.value = 0
    dut.m_axi_bvalid.value = 0

    # Apply synchronous reset.
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # Start the transfer.
    await RisingEdge(dut.clk)
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for the read-address phase.
    await wait_for_high(dut.m_axi_arvalid, dut.clk)

    assert int(dut.m_axi_araddr.value) == source_address
    assert int(dut.m_axi_arlen.value) == 0
    assert int(dut.m_axi_arsize.value) == 2
    assert int(dut.m_axi_arburst.value) == 1

    # Allow the read-address handshake to complete.
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    # Return one successful read beat.
    dut.m_axi_rdata.value = source_word
    dut.m_axi_rresp.value = 0
    dut.m_axi_rlast.value = 1
    dut.m_axi_rvalid.value = 1

    await wait_for_high(dut.m_axi_rready, dut.clk)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.m_axi_rvalid.value = 0

    # Wait for the write-address phase.
    await wait_for_high(dut.m_axi_awvalid, dut.clk)

    assert int(dut.m_axi_awaddr.value) == destination_address
    assert int(dut.m_axi_awlen.value) == 0
    assert int(dut.m_axi_awsize.value) == 2
    assert int(dut.m_axi_awburst.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    # Check the write-data beat.
    await wait_for_high(dut.m_axi_wvalid, dut.clk)

    assert int(dut.m_axi_wdata.value) == source_word
    assert int(dut.m_axi_wstrb.value) == 0b1111
    assert int(dut.m_axi_wlast.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    # Return a successful write response.
    dut.m_axi_bresp.value = 0
    dut.m_axi_bvalid.value = 1

    await wait_for_high(dut.m_axi_bready, dut.clk)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.m_axi_bvalid.value = 0

    # Confirm completion.
    for _ in range(5):
        if int(dut.done.value) == 1:
            break
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
    else:
        raise AssertionError("DMA did not assert done")

    assert int(dut.error.value) == 0
    assert int(dut.busy.value) == 0

    dut._log.info(
        "PASS: copied 0x%08X from 0x%08X to 0x%08X",
        source_word,
        source_address,
        destination_address,
    )
