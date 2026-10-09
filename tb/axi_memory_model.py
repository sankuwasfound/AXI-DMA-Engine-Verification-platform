"""AXI memory model for the AXI DMA verification environment.

Supports INCR bursts, byte strobes, and configurable response errors.
This is a simulation model for the DMA's documented AXI subset, not
a complete AXI4-compliant slave.
"""

from cocotb.triggers import FallingEdge, RisingEdge, Timer


class AxiMemoryModel:
    def __init__(
        self,
        dut,
        initial_memory=None,
        read_resp=0,
        write_resp=0,
    ):
        self.dut = dut
        self.memory = dict(initial_memory or {})
        self.read_resp = read_resp
        self.write_resp = write_resp

        self.pending_read_beats = []
        self.read_active = False
        self.clear_read = False

        self.write_address = None
        self.write_beats_remaining = 0
        self.write_error_response_pending = False
        self.write_response_active = False
        self.clear_write_response = False

    def initialize(self):
        dut = self.dut

        dut.m_axi_arready.value = 1
        dut.m_axi_rdata.value = 0
        dut.m_axi_rresp.value = 0
        dut.m_axi_rlast.value = 0
        dut.m_axi_rvalid.value = 0

        dut.m_axi_awready.value = 1
        dut.m_axi_wready.value = 1

        dut.m_axi_bresp.value = 0
        dut.m_axi_bvalid.value = 0

    async def run(self):
        dut = self.dut
        bytes_per_beat = len(dut.m_axi_wstrb)

        while True:
            await FallingEdge(dut.clk)

            dut.m_axi_arready.value = 1
            dut.m_axi_awready.value = 1
            dut.m_axi_wready.value = 1

            if self.clear_read:
                dut.m_axi_rvalid.value = 0
                dut.m_axi_rlast.value = 0
                self.read_active = False
                self.clear_read = False

            if self.clear_write_response:
                dut.m_axi_bvalid.value = 0
                self.write_response_active = False
                self.clear_write_response = False

            # Present the next read beat, holding it until handshake.
            if self.pending_read_beats and not self.read_active:
                data, response, last = self.pending_read_beats.pop(0)
                dut.m_axi_rdata.value = data
                dut.m_axi_rresp.value = response
                dut.m_axi_rlast.value = last
                dut.m_axi_rvalid.value = 1
                self.read_active = True

            if (
                self.write_error_response_pending
                and not self.write_response_active
            ):
                dut.m_axi_bresp.value = self.write_resp
                dut.m_axi_bvalid.value = 1
                self.write_error_response_pending = False
                self.write_response_active = True

            await Timer(1, unit="ps")

            ar_handshake = (
                int(dut.m_axi_arvalid.value)
                and int(dut.m_axi_arready.value)
            )
            ar_address = int(dut.m_axi_araddr.value)
            ar_length = int(dut.m_axi_arlen.value)

            r_handshake = (
                int(dut.m_axi_rvalid.value)
                and int(dut.m_axi_rready.value)
            )

            aw_handshake = (
                int(dut.m_axi_awvalid.value)
                and int(dut.m_axi_awready.value)
            )
            aw_address = int(dut.m_axi_awaddr.value)
            aw_length = int(dut.m_axi_awlen.value)

            w_handshake = (
                int(dut.m_axi_wvalid.value)
                and int(dut.m_axi_wready.value)
            )
            w_data = int(dut.m_axi_wdata.value)
            w_strobe = int(dut.m_axi_wstrb.value)
            w_last = int(dut.m_axi_wlast.value)

            b_handshake = (
                int(dut.m_axi_bvalid.value)
                and int(dut.m_axi_bready.value)
            )

            await RisingEdge(dut.clk)

            if ar_handshake:
                if self.pending_read_beats or self.read_active:
                    raise AssertionError(
                        "New read address received while read burst active"
                    )

                self.pending_read_beats = [
                    (
                        self.memory.get(
                            ar_address + index * bytes_per_beat, 0
                        ),
                        self.read_resp,
                        int(index == ar_length),
                    )
                    for index in range(ar_length + 1)
                ]

            if r_handshake:
                self.clear_read = True

            if aw_handshake:
                if self.write_address is not None:
                    raise AssertionError(
                        "New write address received before previous burst ended"
                    )
                self.write_address = aw_address
                self.write_beats_remaining = aw_length + 1

            if w_handshake:
                if self.write_address is None:
                    raise AssertionError(
                        "Write data accepted before a write address"
                    )

                expected_last = self.write_beats_remaining == 1
                if bool(w_last) != expected_last:
                    raise AssertionError(
                        "WLAST did not match expected final write beat"
                    )

                old_value = self.memory.get(self.write_address, 0)
                new_value = old_value

                for lane in range(bytes_per_beat):
                    if (w_strobe >> lane) & 1:
                        mask = 0xFF << (8 * lane)
                        new_value = (
                            (new_value & ~mask) | (w_data & mask)
                        )

                self.memory[self.write_address] = new_value
                self.write_address += bytes_per_beat
                self.write_beats_remaining -= 1

                if self.write_beats_remaining == 0:
                    self.write_address = None
                    self.write_error_response_pending = True

            if b_handshake:
                self.clear_write_response = True
