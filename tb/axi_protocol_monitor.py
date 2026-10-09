"""Reusable AXI protocol monitor for VALID/READY stall stability."""

from cocotb.triggers import FallingEdge, Timer


class AxiProtocolMonitor:
    """Check that AXI channel VALID and payload remain stable during stalls."""

    CHANNELS = {
        "AR": (
            "m_axi_arvalid",
            "m_axi_arready",
            ("m_axi_araddr", "m_axi_arlen", "m_axi_arsize", "m_axi_arburst"),
        ),
        "R": (
            "m_axi_rvalid",
            "m_axi_rready",
            ("m_axi_rdata", "m_axi_rresp", "m_axi_rlast"),
        ),
        "AW": (
            "m_axi_awvalid",
            "m_axi_awready",
            ("m_axi_awaddr", "m_axi_awlen", "m_axi_awsize", "m_axi_awburst"),
        ),
        "W": (
            "m_axi_wvalid",
            "m_axi_wready",
            ("m_axi_wdata", "m_axi_wstrb", "m_axi_wlast"),
        ),
        "B": (
            "m_axi_bvalid",
            "m_axi_bready",
            ("m_axi_bresp",),
        ),
    }

    def __init__(self, dut):
        self.dut = dut
        self.active = True
        self.stalled = {name: None for name in self.CHANNELS}
        self.stall_checks = {name: 0 for name in self.CHANNELS}

    def stop(self):
        self.active = False

    @staticmethod
    def _value(signal):
        return int(signal.value)

    async def run(self):
        dut = self.dut

        while self.active:
            await FallingEdge(dut.clk)
            await Timer(1, unit="ps")

            if not self.active:
                break

            # A reset cancels any previously observed stall.
            if self._value(dut.rst_n) == 0:
                for name in self.CHANNELS:
                    self.stalled[name] = None
                continue

            for name, (valid_name, ready_name, payload_names) in (
                self.CHANNELS.items()
            ):
                valid = self._value(getattr(dut, valid_name))
                ready = self._value(getattr(dut, ready_name))
                payload = tuple(
                    self._value(getattr(dut, signal_name))
                    for signal_name in payload_names
                )

                previous = self.stalled[name]

                if previous is not None:
                    assert valid == 1, (
                        f"AXI {name}: VALID dropped while stalled"
                    )
                    assert payload == previous, (
                        f"AXI {name}: payload changed while stalled; "
                        f"previous={previous}, current={payload}"
                    )
                    self.stall_checks[name] += 1

                # Save this cycle if the transfer is currently stalled.
                self.stalled[name] = (
                    payload if valid == 1 and ready == 0 else None
                )

    def report(self):
        return {
            name: self.stall_checks[name]
            for name in self.CHANNELS
        }
