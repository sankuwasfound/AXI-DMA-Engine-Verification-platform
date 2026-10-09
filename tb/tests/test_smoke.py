import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer


@cocotb.test()
async def counter_smoke_test(dut):
    """Verify reset and sequential operation through Verilator."""

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await Timer(1, unit="ns")

    assert int(dut.count.value) == 0, "Reset did not clear counter"

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 3)
    await Timer(1, unit="ns")

    assert int(dut.count.value) == 3, (
        f"Expected count=3, got {int(dut.count.value)}"
    )

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 1)
    await Timer(1, unit="ns")

    assert int(dut.count.value) == 0, "Counter failed to reset"

    dut._log.info("PASS: reset, clock and counter behavior verified")
