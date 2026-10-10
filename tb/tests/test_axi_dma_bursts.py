"""Burst-transfer tests for the AXI DMA."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from axi_memory_model import AxiMemoryModel
from functional_coverage import hit_transfer_length


async def run_burst_test(dut, beats):
    bytes_per_beat = len(dut.m_axi_wstrb)
    src_addr = 0x1000
    dst_addr = 0x2000
    length_bytes = beats * bytes_per_beat

    rng = random.Random(0xD00 + beats)
    source_words = {
        src_addr + i * bytes_per_beat: rng.getrandbits(
            len(dut.m_axi_wdata)
        )
        for i in range(beats)
    }

    memory = AxiMemoryModel(dut, initial_memory=source_words)
    memory.initialize()

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.rst_n.value = 0
    dut.recovery_ready.value = 1
    dut.start.value = 0
    dut.src_addr.value = src_addr
    dut.dst_addr.value = dst_addr
    dut.length_bytes.value = length_bytes

    for _ in range(3):
        await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    cocotb.start_soon(memory.run())

    for _ in range(2):
        await RisingEdge(dut.clk)

    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    completed = False
    failed = False

    for _ in range(200 + beats * 20):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if int(dut.done.value):
            completed = True
            break

        if int(dut.error.value):
            failed = True
            break

    assert not failed, f"{beats}-beat burst unexpectedly reported error"
    assert completed, f"{beats}-beat burst timed out"

    for i, expected in enumerate(source_words.values()):
        address = dst_addr + i * bytes_per_beat
        actual = memory.memory.get(address)
        assert actual == expected, (
            f"Beat {i}: memory[0x{address:08X}] "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    assert int(dut.busy.value) == 0, "DMA should be idle after completion"

    # Record coverage only after the transfer and data checks pass.
    hit_transfer_length(beats)

    dut._log.info(
        "PASS: %d-beat burst (%d bytes) copied correctly",
        beats,
        length_bytes,
    )


@cocotb.test()
async def copies_two_beat_burst(dut):
    await run_burst_test(dut, 2)


@cocotb.test()
async def copies_four_beat_burst(dut):
    await run_burst_test(dut, 4)


@cocotb.test()
async def copies_maximum_sixteen_beat_burst(dut):
    await run_burst_test(dut, 16)
