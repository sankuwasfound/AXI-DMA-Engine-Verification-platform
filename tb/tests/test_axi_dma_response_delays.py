"""Tests for delayed AXI read and write responses."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel


async def start_transfer(dut, memory, src_addr, dst_addr, length_bytes):
    memory.initialize()

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.rst_n.value = 0
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
    await Timer(1, unit="ps")
    dut.start.value = 0


@cocotb.test()
async def waits_for_delayed_read_response(dut):
    beats = 4
    bytes_per_beat = len(dut.m_axi_wstrb)
    src_addr = 0x1000
    dst_addr = 0x2000
    delay_cycles = 6

    source = {
        src_addr + i * bytes_per_beat: 0xB6000000 + i
        for i in range(beats)
    }

    memory = AxiMemoryModel(
        dut,
        initial_memory=source,
        read_delay_cycles=delay_cycles,
    )

    await start_transfer(
        dut, memory, src_addr, dst_addr, beats * bytes_per_beat
    )

    waiting_cycles = 0
    saw_read_response = False

    for _ in range(200):
        await FallingEdge(dut.clk)
        await Timer(2, unit="ps")

        if int(dut.m_axi_rvalid.value):
            saw_read_response = True
            break

        waiting_cycles += 1
        assert int(dut.done.value) == 0, (
            "DMA asserted done before receiving read data"
        )
        assert int(dut.busy.value) == 1, (
            "DMA stopped being busy while waiting for read data"
        )

        await RisingEdge(dut.clk)

    assert saw_read_response, "Read response did not arrive"
    assert waiting_cycles >= delay_cycles, (
        f"Read response was not delayed enough: {waiting_cycles} cycles"
    )

    completed = False

    for _ in range(200):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        assert int(dut.error.value) == 0, (
            "DMA reported an unexpected error"
        )

        if int(dut.done.value):
            completed = True
            break

    assert completed, "DMA did not complete after the read response"

    for i, expected in enumerate(source.values()):
        address = dst_addr + i * bytes_per_beat
        actual = memory.memory.get(address)
        assert actual == expected, (
            f"Destination mismatch at 0x{address:08X}: "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    dut._log.info(
        f"PASS: DMA waited {waiting_cycles} cycles for delayed read data"
    )


@cocotb.test()
async def waits_for_delayed_write_response(dut):
    beats = 4
    bytes_per_beat = len(dut.m_axi_wstrb)
    src_addr = 0x3000
    dst_addr = 0x4000
    delay_cycles = 6

    source = {
        src_addr + i * bytes_per_beat: 0xC7000000 + i
        for i in range(beats)
    }

    memory = AxiMemoryModel(
        dut,
        initial_memory=source,
        write_response_delay_cycles=delay_cycles,
    )

    await start_transfer(
        dut, memory, src_addr, dst_addr, beats * bytes_per_beat
    )

    final_write_seen = False
    waiting_cycles = 0
    saw_write_response = False
    completed = False

    for _ in range(300):
        await FallingEdge(dut.clk)
        await Timer(2, unit="ps")

        final_write_handshake = (
            int(dut.m_axi_wvalid.value)
            and int(dut.m_axi_wready.value)
            and int(dut.m_axi_wlast.value)
        )

        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if final_write_handshake:
            final_write_seen = True

        if final_write_seen and not int(dut.m_axi_bvalid.value):
            waiting_cycles += 1
            assert int(dut.done.value) == 0, (
                "DMA asserted done before receiving the write response"
            )

        if int(dut.m_axi_bvalid.value):
            saw_write_response = True

        if int(dut.error.value):
            raise AssertionError("DMA reported an unexpected error")

        if int(dut.done.value):
            completed = True
            break

        if saw_write_response:
            # The response has arrived; continue until the DMA completes.
            continue

    assert final_write_seen, "Final write-data beat was never accepted"
    assert saw_write_response, "Write response did not arrive"
    assert waiting_cycles >= delay_cycles, (
        f"Write response was not delayed enough: {waiting_cycles} cycles"
    )
    assert completed, "DMA did not complete after the write response"

    for i, expected in enumerate(source.values()):
        address = dst_addr + i * bytes_per_beat
        actual = memory.memory.get(address)
        assert actual == expected, (
            f"Destination mismatch at 0x{address:08X}: "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    dut._log.info(
        f"PASS: DMA waited {waiting_cycles} cycles for delayed write response"
    )
