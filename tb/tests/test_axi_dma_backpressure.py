"""Deterministic AXI backpressure and signal-stability test."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

from axi_memory_model import AxiMemoryModel
from functional_coverage import hit


@cocotb.test()
async def holds_address_and_write_data_during_stalls(dut):
    beats = 4
    bytes_per_beat = len(dut.m_axi_wstrb)
    src_addr = 0x1000
    dst_addr = 0x2000

    source = {
        src_addr + i * bytes_per_beat: 0xA5000000 + i
        for i in range(beats)
    }

    memory = AxiMemoryModel(dut, initial_memory=source)
    memory.initialize()

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.rst_n.value = 0
    dut.start.value = 0
    dut.src_addr.value = src_addr
    dut.dst_addr.value = dst_addr
    dut.length_bytes.value = beats * bytes_per_beat

    for _ in range(3):
        await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    cocotb.start_soon(memory.run())

    for _ in range(2):
        await RisingEdge(dut.clk)

    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Each channel is held not-ready until VALID appears.
    # Once VALID appears, stall it for three sampled cycles.
    stall_cycles = {"ar": 0, "aw": 0, "w": 0}
    stall_done = {"ar": False, "aw": False, "w": False}
    saw_stall = {"ar": False, "aw": False, "w": False}

    signals = {
        "ar": (
            "m_axi_arvalid", "m_axi_arready",
            ("m_axi_araddr", "m_axi_arlen",
             "m_axi_arsize", "m_axi_arburst"),
        ),
        "aw": (
            "m_axi_awvalid", "m_axi_awready",
            ("m_axi_awaddr", "m_axi_awlen",
             "m_axi_awsize", "m_axi_awburst"),
        ),
        "w": (
            "m_axi_wvalid", "m_axi_wready",
            ("m_axi_wdata", "m_axi_wstrb", "m_axi_wlast"),
        ),
    }

    previous = None
    completed = False

    for _ in range(300):
        await FallingEdge(dut.clk)

        for channel, (valid_name, ready_name, _) in signals.items():
            valid_now = int(getattr(dut, valid_name).value)

            if not stall_done[channel]:
                getattr(dut, ready_name).value = 0

                if valid_now:
                    stall_cycles[channel] += 1
                    saw_stall[channel] = True

                    if stall_cycles[channel] >= 3:
                        stall_done[channel] = True
            else:
                getattr(dut, ready_name).value = 1

        await Timer(1, unit="ps")

        current = {}

        for channel, (valid_name, ready_name, payload_names) in signals.items():
            valid = int(getattr(dut, valid_name).value)
            ready = int(getattr(dut, ready_name).value)
            payload = tuple(
                int(getattr(dut, name).value)
                for name in payload_names
            )
            current[channel] = (valid, *payload)

            if previous is not None:
                prev_valid, *prev_payload = previous[channel]
                prev_ready = previous[channel + "_ready"]

                if prev_valid and not prev_ready:
                    assert valid, (
                        f"{channel.upper()}VALID dropped during a stall"
                    )
                    assert payload == tuple(prev_payload), (
                        f"{channel.upper()} payload changed during a stall"
                    )

            current[channel + "_ready"] = ready

        previous = current

        await RisingEdge(dut.clk)
        await Timer(1, unit="ps")

        if int(dut.error.value):
            raise AssertionError("DMA reported an unexpected error")

        if int(dut.done.value):
            completed = True
            break

    assert completed, "DMA did not complete under backpressure"

    for channel in ("ar", "aw", "w"):
        assert saw_stall[channel], (
            f"Test did not stall the {channel.upper()} channel"
        )
        assert stall_done[channel], (
            f"{channel.upper()} channel did not complete its forced stall"
        )

    for i, expected in enumerate(source.values()):
        address = dst_addr + i * bytes_per_beat
        actual = memory.memory.get(address)
        assert actual == expected, (
            f"Destination mismatch at 0x{address:08X}: "
            f"expected 0x{expected:08X}, got {actual!r}"
        )

    # Record coverage only after every assertion passes.
    hit("backpressure.ar")
    hit("backpressure.aw")
    hit("backpressure.w")

    dut._log.info(
        "PASS: 4-beat transfer completed; AR, AW and W stalls verified"
    )
