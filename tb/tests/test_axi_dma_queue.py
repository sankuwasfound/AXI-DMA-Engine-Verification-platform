"""Descriptor FIFO tests for the AXI DMA M4 milestone."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel
from functional_coverage import hit


CLOCK_NS = 10
QUEUE_DEPTH = 4
BYTES_PER_BEAT = 4


async def setup_dma(dut, memory):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.recovery_ready.value = 1
    dut.start.value = 0
    dut.src_addr.value = 0x1000
    dut.dst_addr.value = 0x2000
    dut.length_bytes.value = BYTES_PER_BEAT

    memory.initialize()
    cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start())
    cocotb.start_soon(memory.run())

    for _ in range(3):
        await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def submit(dut, src, dst, length=BYTES_PER_BEAT):
    """Present one descriptor for one rising clock edge."""
    await FallingEdge(dut.clk)
    dut.src_addr.value = src
    dut.dst_addr.value = dst
    dut.length_bytes.value = length
    dut.start.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start.value = 0


async def wait_for_completions(dut, count, limit=500):
    """Wait for the requested number of successful DMA completions."""
    completed = 0

    for _ in range(limit):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if int(dut.error.value):
            raise AssertionError("DMA reported an error during queued transfers")

        if int(dut.done.value):
            completed += 1
            if completed == count:
                return

    raise AssertionError(
        f"Timed out: observed {completed}/{count} completions"
    )


@cocotb.test()
async def queued_descriptors_execute_in_fifo_order(dut):
    """Queued descriptors must execute without losing or reordering requests."""
    source_words = {
        0x1000: 0x11112222,
        0x1100: 0x33334444,
        0x1200: 0x55556666,
        0x1300: 0x77778888,
    }
    memory = AxiMemoryModel(
        dut,
        initial_memory=source_words,
        read_delay_cycles=12,
    )
    await setup_dma(dut, memory)

    # Start the first transfer; it should become active immediately.
    await submit(dut, 0x1000, 0x2000)

    # Submit three more descriptors while the first transfer is in progress.
    await submit(dut, 0x1100, 0x2100)
    await submit(dut, 0x1200, 0x2200)
    await submit(dut, 0x1300, 0x2300)

    assert int(dut.queue_level.value) == 3, (
        "Expected three waiting descriptors after four submissions"
    )

    await wait_for_completions(dut, 4)

    expected_destinations = {
        0x2000: 0x11112222,
        0x2100: 0x33334444,
        0x2200: 0x55556666,
        0x2300: 0x77778888,
    }

    for address, expected in expected_destinations.items():
        actual = memory.memory.get(address)
        assert actual == expected, (
            f"Destination 0x{address:08X}: "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    assert int(dut.queue_empty.value) == 1
    assert int(dut.queue_level.value) == 0

    hit("queue.fifo_order")


@cocotb.test()
async def full_queue_rejects_extra_descriptor(dut):
    """A full FIFO must reject a new request without corrupting queued work."""
    source_words = {
        0x1000: 0xA0000001,
        0x1100: 0xA0000002,
        0x1200: 0xA0000003,
        0x1300: 0xA0000004,
        0x1400: 0xA0000005,
        0x1500: 0xA0000006,
    }
    memory = AxiMemoryModel(
        dut,
        initial_memory=source_words,
        read_delay_cycles=30,
    )
    await setup_dma(dut, memory)

    # One active descriptor plus four waiting descriptors fills the FIFO.
    await submit(dut, 0x1000, 0x2000)
    await submit(dut, 0x1100, 0x2100)
    await submit(dut, 0x1200, 0x2200)
    await submit(dut, 0x1300, 0x2300)
    await submit(dut, 0x1400, 0x2400)

    assert int(dut.queue_full.value) == 1, "FIFO did not report full"
    assert int(dut.queue_level.value) == QUEUE_DEPTH, (
        "Expected four waiting descriptors in the FIFO"
    )

    # A further request must not replace any of the four queued entries.
    await submit(dut, 0x1500, 0x2500)

    assert int(dut.queue_level.value) == QUEUE_DEPTH, (
        "Queue level changed after a request was submitted while full"
    )

    await wait_for_completions(dut, 5)

    for index in range(5):
        src = 0x1000 + index * 0x100
        dst = 0x2000 + index * 0x100
        expected = source_words[src]
        actual = memory.memory.get(dst)

        assert actual == expected, (
            f"Transfer {index}: destination 0x{dst:08X}, "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    assert 0x2500 not in memory.memory, (
        "The extra descriptor was executed despite the full queue"
    )

    hit("queue.full_rejection")
