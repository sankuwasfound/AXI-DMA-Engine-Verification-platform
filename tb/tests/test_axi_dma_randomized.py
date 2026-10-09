"""M5: seeded randomized descriptor and data-integrity stress test."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel
from axi_protocol_monitor import AxiProtocolMonitor
from functional_coverage import hit, hit_transfer_length, write_report


CLOCK_NS = 10
BYTES_PER_WORD = 4
MAX_WORDS = 16
BATCH_SIZE = 5
NUM_DESCRIPTORS = 20
RANDOM_SEED = 0x5A17


async def setup_dma(dut, memory):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.start.value = 0
    dut.src_addr.value = 0x1000
    dut.dst_addr.value = 0x8000
    dut.length_bytes.value = BYTES_PER_WORD

    memory.initialize()
    cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start())
    cocotb.start_soon(memory.run())

    for _ in range(3):
        await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def submit(dut, src, dst, length_bytes):
    await FallingEdge(dut.clk)
    dut.src_addr.value = src
    dut.dst_addr.value = dst
    dut.length_bytes.value = length_bytes
    dut.start.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start.value = 0


async def wait_for_completions(dut, count, limit=10000):
    completed = 0

    for _ in range(limit):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if int(dut.error.value):
            raise AssertionError("DMA asserted error during randomized test")

        if int(dut.done.value):
            completed += 1
            if completed == count:
                return

    raise AssertionError(
        f"Timed out waiting for completions: {completed}/{count}"
    )


@cocotb.test()
async def randomized_descriptors_preserve_data(dut):
    rng = random.Random(RANDOM_SEED)

    descriptors = []
    initial_memory = {}
    expected_memory = {}

    for index in range(NUM_DESCRIPTORS):
        src = 0x1000 + index * 0x100
        dst = 0x8000 + index * 0x100
        words = rng.randint(1, MAX_WORDS)

        descriptor = {
            "src": src,
            "dst": dst,
            "words": words,
        }
        descriptors.append(descriptor)

        for word_index in range(words):
            address = src + word_index * BYTES_PER_WORD
            value = rng.getrandbits(32)
            initial_memory[address] = value
            expected_memory[dst + word_index * BYTES_PER_WORD] = value

    memory = AxiMemoryModel(
        dut,
        initial_memory=initial_memory,
        read_delay_cycles=2,
        write_response_delay_cycles=1,
        backpressure_probability=0.25,
        max_random_read_delay=8,
        max_random_write_response_delay=6,
        random_seed=RANDOM_SEED,
    )
    await setup_dma(dut, memory)
    monitor = AxiProtocolMonitor(dut)
    monitor_task = cocotb.start_soon(monitor.run())

    dut._log.info(
        "M5 randomized test: seed=%d descriptors=%d",
        RANDOM_SEED,
        NUM_DESCRIPTORS,
    )

    for batch_start in range(0, NUM_DESCRIPTORS, BATCH_SIZE):
        batch = descriptors[batch_start:batch_start + BATCH_SIZE]

        for descriptor in batch:
            await submit(
                dut,
                descriptor["src"],
                descriptor["dst"],
                descriptor["words"] * BYTES_PER_WORD,
            )

        # First descriptor is active; remaining four should be queued.
        assert int(dut.queue_level.value) == len(batch) - 1, (
            f"Unexpected queue level in batch starting at {batch_start}: "
            f"{int(dut.queue_level.value)}"
        )

        await wait_for_completions(dut, len(batch))

    for address, expected in expected_memory.items():
        actual = memory.memory.get(address)
        assert actual == expected, (
            f"Seed={RANDOM_SEED}: data mismatch at 0x{address:08X}; "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    assert int(dut.queue_empty.value) == 1
    assert int(dut.queue_level.value) == 0

    dut._log.info(
        "PASS: seed=%d; checked %d randomized descriptors",
        RANDOM_SEED,
        NUM_DESCRIPTORS,
    )

    monitor.stop()
    await monitor_task
    dut._log.info("AXI protocol stall checks: %s", monitor.report())

    # Record coverage only after the complete stress test and monitor pass.
    for descriptor in descriptors:
        hit_transfer_length(descriptor["words"])

    hit("randomized.seeded_stress")

    # This is the final test module in the Makefile regression.
    write_report()
