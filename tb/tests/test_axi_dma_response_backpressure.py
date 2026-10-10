"""Controlled AXI R/B response-stall checks using the recovery gate.

This tests response VALID/payload stability while the DMA's READY outputs
are gated low by recovery_ready. It does not test independent, ordinary
AXI backpressure because this RTL ties RREADY/BREADY to that gate.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel


async def falling_sample(dut):
    await FallingEdge(dut.clk)
    await Timer(1, unit="ps")


async def rising_settle(dut):
    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")


@cocotb.test()
async def holds_read_data_and_write_response_during_stalls(dut):
    src_addr = 0x1000
    dst_addr = 0x2000
    expected = 0xA5C37E19

    memory = AxiMemoryModel(
        dut,
        initial_memory={src_addr: expected},
        read_delay_cycles=2,
        write_response_delay_cycles=2,
    )

    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.recovery_ready.value = 1
    dut.start.value = 0
    dut.src_addr.value = src_addr
    dut.dst_addr.value = dst_addr
    dut.length_bytes.value = 4

    # Initialize slave inputs only. RREADY and BREADY are DUT outputs.
    memory.initialize()
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    for _ in range(3):
        await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    cocotb.start_soon(memory.run())

    await FallingEdge(dut.clk)
    dut.start.value = 1
    await rising_settle(dut)
    dut.start.value = 0

    # Wait for the read address handshake, then hold RREADY low.
    ar_seen = False
    for _ in range(100):
        await falling_sample(dut)
        if int(dut.m_axi_arvalid.value) and int(dut.m_axi_arready.value):
            await rising_settle(dut)
            dut.recovery_ready.value = 0
            ar_seen = True
            break

    assert ar_seen, "Read address handshake was not observed"

    # Check RVALID and its payload remain stable while RREADY is low.
    r_payload = None
    r_stall_cycles = 0

    for _ in range(100):
        await falling_sample(dut)

        rvalid = int(dut.m_axi_rvalid.value)
        rready = int(dut.m_axi_rready.value)

        if rvalid and not rready:
            payload = (
                int(dut.m_axi_rdata.value),
                int(dut.m_axi_rresp.value),
                int(dut.m_axi_rlast.value),
            )

            if r_payload is None:
                r_payload = payload

            assert payload == r_payload, "R payload changed while stalled"
            r_stall_cycles += 1

            if r_stall_cycles >= 3:
                await rising_settle(dut)
                dut.recovery_ready.value = 1
                break

    assert r_stall_cycles >= 3, "Did not observe a 3-cycle R-channel stall"

    # Wait for the R response handshake after releasing the gate.
    r_handshake_seen = False

    for _ in range(100):
        await falling_sample(dut)

        if int(dut.m_axi_rvalid.value) and int(dut.m_axi_rready.value):
            await rising_settle(dut)
            r_handshake_seen = True
            break

    assert r_handshake_seen, "R response did not handshake after releasing gate"

    # Wait for the final W beat, then gate BREADY before BVALID arrives.
    final_w_seen = False

    for _ in range(150):
        await falling_sample(dut)

        if (
            int(dut.m_axi_wvalid.value)
            and int(dut.m_axi_wready.value)
            and int(dut.m_axi_wlast.value)
        ):
            await rising_settle(dut)
            dut.recovery_ready.value = 0
            final_w_seen = True
            break

    assert final_w_seen, "Final write-data handshake was not observed"

    # Check BVALID and BRESP remain stable while BREADY is low.
    b_payload = None
    b_stall_cycles = 0

    for _ in range(100):
        await falling_sample(dut)

        bvalid = int(dut.m_axi_bvalid.value)
        bready = int(dut.m_axi_bready.value)

        if bvalid and not bready:
            payload = (int(dut.m_axi_bresp.value),)

            if b_payload is None:
                b_payload = payload

            assert payload == b_payload, "B response payload changed while stalled"
            b_stall_cycles += 1

            if b_stall_cycles >= 3:
                await rising_settle(dut)
                dut.recovery_ready.value = 1
                break

    assert b_stall_cycles >= 3, "Did not observe a 3-cycle B-channel stall"

    # Wait for completion after releasing the B-channel stall.
    completed = False

    for _ in range(150):
        await falling_sample(dut)

        if int(dut.error.value):
            raise AssertionError("DMA reported an unexpected error")

        if int(dut.done.value):
            completed = True
            break

    assert completed, "DMA did not complete after releasing the B-channel stall"

    assert memory.memory.get(dst_addr) == expected, (
        f"Destination mismatch: expected 0x{expected:08X}, "
        f"got {memory.memory.get(dst_addr)!r}"
    )

    dut._log.info(
        "PASS: response payloads stayed stable during %d R-stall cycles "
        "and %d B-stall cycles",
        r_stall_cycles,
        b_stall_cycles,
    )
