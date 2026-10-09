
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel


@cocotb.test()
async def dma_copies_word_into_model_memory(dut):
    source_address = 0x1000
    destination_address = 0x2000
    source_word = 0xDEADBEEF

    # Reset and configure the DMA.
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.src_addr.value = source_address
    dut.dst_addr.value = destination_address
    dut.length_bytes.value = 4

    # Preload the source word into the model's memory.
    memory_model = AxiMemoryModel(
        dut,
        initial_memory={source_address: source_word},
    )
    memory_model.initialize()

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    cocotb.start_soon(memory_model.run())

    # Hold reset for two rising edges.
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Start on a falling edge to avoid racing the active clock edge.
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.start.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start.value = 0

    # Wait for the DMA's completion pulse.
    for _ in range(20):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if int(dut.done.value):
            break

        if int(dut.error.value):
            raise AssertionError("DMA asserted error during memory copy")
    else:
        raise AssertionError("Timed out waiting for DMA completion")

    # Verify actual destination memory contents.
    actual_word = memory_model.memory.get(destination_address)

    assert actual_word == source_word, (
        f"Destination mismatch: expected 0x{source_word:08X}, "
        f"got {actual_word!r}"
    )
    assert int(dut.error.value) == 0
    assert int(dut.busy.value) == 0

    dut._log.info(
        "PASS: memory[0x%08X] = 0x%08X",
        destination_address,
        actual_word,
    )
