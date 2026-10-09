
"""Reusable AXI memory model for the initial single-beat DMA prototype."""

from cocotb.triggers import FallingEdge, Timer, RisingEdge


class AxiMemoryModel:
    """Minimal AXI4 slave model for the DMA's current single-beat interface.

    Supports:
      - Read and write address handshakes
      - Read data responses
      - Write data storage
      - Write responses
      - Configurable RRESP and BRESP error injection

    This is intentionally not a full AXI4-compliant slave.
    """

    def __init__(self, dut, initial_memory=None,
                 read_resp=0, write_resp=0):
        self.dut = dut
        self.memory = dict(initial_memory or {})
        self.read_resp = read_resp
        self.write_resp = write_resp

        self.pending_read = None
        self.pending_write_response = False
        self.write_address = None

        self.read_active = False
        self.write_response_active = False
        self.clear_read = False
        self.clear_write_response = False

    def initialize(self):
        """Initialize signals driven by the AXI slave."""
        dut = self.dut

        dut.m_axi_arready.value = 1
        dut.m_axi_rdata.value = 0
        dut.m_axi_rresp.value = 0
        dut.m_axi_rlast.value = 1
        dut.m_axi_rvalid.value = 0

        dut.m_axi_awready.value = 1
        dut.m_axi_wready.value = 1

        dut.m_axi_bresp.value = 0
        dut.m_axi_bvalid.value = 0

    async def run(self):
        """Drive responses and process handshakes until the test ends."""
        dut = self.dut

        while True:
            await FallingEdge(dut.clk)

            # Keep the slave ready in this initial model.
            dut.m_axi_arready.value = 1
            dut.m_axi_awready.value = 1
            dut.m_axi_wready.value = 1

            # Clear responses accepted on the previous rising edge.
            if self.clear_read:
                dut.m_axi_rvalid.value = 0
                self.read_active = False
                self.clear_read = False

            if self.clear_write_response:
                dut.m_axi_bvalid.value = 0
                self.write_response_active = False
                self.clear_write_response = False

            # Present a pending read response.
            if self.pending_read is not None and not self.read_active:
                data, response = self.pending_read
                dut.m_axi_rdata.value = data
                dut.m_axi_rresp.value = response
                dut.m_axi_rlast.value = 1
                dut.m_axi_rvalid.value = 1

                self.pending_read = None
                self.read_active = True

            # Present a pending write response.
            if (
                self.pending_write_response
                and not self.write_response_active
            ):
                dut.m_axi_bresp.value = self.write_resp
                dut.m_axi_bvalid.value = 1

                self.pending_write_response = False
                self.write_response_active = True

            # Allow combinational outputs to settle before sampling.
            await Timer(1, unit="ps")

            # Sample handshakes that will occur at the next rising edge.
            ar_handshake = (
                int(dut.m_axi_arvalid.value)
                and int(dut.m_axi_arready.value)
            )
            ar_address = int(dut.m_axi_araddr.value)

            r_handshake = (
                int(dut.m_axi_rvalid.value)
                and int(dut.m_axi_rready.value)
            )

            aw_handshake = (
                int(dut.m_axi_awvalid.value)
                and int(dut.m_axi_awready.value)
            )
            aw_address = int(dut.m_axi_awaddr.value)

            w_handshake = (
                int(dut.m_axi_wvalid.value)
                and int(dut.m_axi_wready.value)
            )
            w_data = int(dut.m_axi_wdata.value)
            w_strobe = int(dut.m_axi_wstrb.value)

            b_handshake = (
                int(dut.m_axi_bvalid.value)
                and int(dut.m_axi_bready.value)
            )

            await RisingEdge(dut.clk)

            # Process the handshakes after the active clock edge.
            if ar_handshake:
                self.pending_read = (
                    self.memory.get(ar_address, 0),
                    self.read_resp,
                )

            if r_handshake:
                self.clear_read = True

            if aw_handshake:
                self.write_address = aw_address

            if w_handshake:
                if self.write_address is None:
                    raise AssertionError(
                        "Write data accepted before a write address"
                    )

                # Apply byte strobes to the destination word.
                old_value = self.memory.get(self.write_address, 0)
                new_value = old_value

                for lane in range(4):
                    if (w_strobe >> lane) & 1:
                        mask = 0xFF << (8 * lane)
                        new_value = (
                            (new_value & ~mask)
                            | (w_data & mask)
                        )

                self.memory[self.write_address] = new_value
                self.write_address = None
                self.pending_write_response = True

            if b_handshake:
                self.clear_write_response = True
