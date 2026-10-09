"""Standalone AXI response-channel backpressure tests."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer


@cocotb.test()
async def holds_r_and_b_responses_until_handshake(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.start_r.value = 0
    dut.rready.value = 0
    dut.start_b.value = 0
    dut.bready.value = 0

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    for _ in range(3):
        await RisingEdge(dut.clk)

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.start_r.value = 1
    dut.start_b.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")
    dut.start_r.value = 0
    dut.start_b.value = 0

    await Timer(1, unit="ns")
    assert int(dut.rvalid.value) == 1, "RVALID was not asserted"
    assert int(dut.bvalid.value) == 1, "BVALID was not asserted"

    expected_r = (
        int(dut.rdata.value),
        int(dut.rresp.value),
        int(dut.rlast.value),
    )
    expected_b = int(dut.bresp.value)

    assert expected_r == (0xA5C37E19, 0, 1)
    assert expected_b == 0

    # Keep READY low and check three complete clock cycles of stability.
    for cycle in range(3):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        assert int(dut.rvalid.value) == 1, (
            f"RVALID dropped during stall cycle {cycle + 1}"
        )
        assert (
            int(dut.rdata.value),
            int(dut.rresp.value),
            int(dut.rlast.value),
        ) == expected_r, f"R payload changed during stall cycle {cycle + 1}"

        assert int(dut.bvalid.value) == 1, (
            f"BVALID dropped during stall cycle {cycle + 1}"
        )
        assert int(dut.bresp.value) == expected_b, (
            f"BRESP changed during stall cycle {cycle + 1}"
        )

    # Release both channels; each response must handshake and clear VALID.
    await FallingEdge(dut.clk)
    dut.rready.value = 1
    dut.bready.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ps")

    assert int(dut.rvalid.value) == 0, "RVALID did not clear after handshake"
    assert int(dut.bvalid.value) == 0, "BVALID did not clear after handshake"

    dut._log.info(
        "PASS: R and B responses stayed stable for three stalled cycles "
        "and cleared after handshake"
    )
