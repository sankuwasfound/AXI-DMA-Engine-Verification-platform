module axi_dma #(
    parameter int ADDR_WIDTH = 32,
    parameter int DATA_WIDTH = 32,
    parameter int MAX_BURST_LEN = 16
) (
    input  logic                   clk,
    input  logic                   rst_n,

    // Control interface
    input  logic                   start,
    input  logic [ADDR_WIDTH-1:0]  src_addr,
    input  logic [ADDR_WIDTH-1:0]  dst_addr,
    input  logic [31:0]            length_bytes,
    output logic                   busy,
    output logic                   done,
    output logic                   error,

    // AXI read address channel
    output logic [ADDR_WIDTH-1:0]  m_axi_araddr,
    output logic [7:0]             m_axi_arlen,
    output logic [2:0]             m_axi_arsize,
    output logic [1:0]             m_axi_arburst,
    output logic                   m_axi_arvalid,
    input  logic                   m_axi_arready,

    // AXI read data channel
    input  logic [DATA_WIDTH-1:0]  m_axi_rdata,
    input  logic [1:0]             m_axi_rresp,
    input  logic                   m_axi_rlast,
    input  logic                   m_axi_rvalid,
    output logic                   m_axi_rready,

    // AXI write address channel
    output logic [ADDR_WIDTH-1:0]  m_axi_awaddr,
    output logic [7:0]             m_axi_awlen,
    output logic [2:0]             m_axi_awsize,
    output logic [1:0]             m_axi_awburst,
    output logic                   m_axi_awvalid,
    input  logic                   m_axi_awready,

    // AXI write data channel
    output logic [DATA_WIDTH-1:0]  m_axi_wdata,
    output logic [DATA_WIDTH/8-1:0] m_axi_wstrb,
    output logic                   m_axi_wlast,
    output logic                   m_axi_wvalid,
    input  logic                   m_axi_wready,

    // AXI write response channel
    input  logic [1:0]             m_axi_bresp,
    input  logic                   m_axi_bvalid,
    output logic                   m_axi_bready
);

    localparam int BYTES_PER_BEAT = DATA_WIDTH / 8;
    localparam int BYTE_ADDR_BITS = $clog2(BYTES_PER_BEAT);

    typedef enum logic [2:0] {
        IDLE,
        READ_ADDR,
        READ_DATA,
        WRITE_ADDR,
        WRITE_DATA,
        WRITE_RESP
    } state_t;

    state_t state;

    logic [ADDR_WIDTH-1:0] src_addr_reg;
    logic [ADDR_WIDTH-1:0] dst_addr_reg;

    // Buffer the complete read burst before starting the write burst.
    logic [DATA_WIDTH-1:0] data_buffer [0:MAX_BURST_LEN-1];

    // Counts are zero-based beat indices while processing data.
    logic [31:0] beats_total;
    logic [31:0] read_count;
    logic [31:0] write_count;

    always_comb begin
        m_axi_araddr  = src_addr_reg;
        m_axi_arlen   = 8'(beats_total - 1);
        m_axi_arsize  = 3'(BYTE_ADDR_BITS);
        m_axi_arburst = 2'b01;  // INCR
        m_axi_arvalid = 1'b0;

        m_axi_rready  = 1'b0;

        m_axi_awaddr  = dst_addr_reg;
        m_axi_awlen   = 8'(beats_total - 1);
        m_axi_awsize  = 3'(BYTE_ADDR_BITS);
        m_axi_awburst = 2'b01;  // INCR
        m_axi_awvalid = 1'b0;

        m_axi_wdata   = '0;
        m_axi_wstrb   = '1;
        m_axi_wlast   = 1'b0;
        m_axi_wvalid  = 1'b0;

        m_axi_bready  = 1'b0;

        case (state)
            READ_ADDR: begin
                m_axi_arvalid = 1'b1;
            end

            READ_DATA: begin
                m_axi_rready = 1'b1;
            end

            WRITE_ADDR: begin
                m_axi_awvalid = 1'b1;
            end

            WRITE_DATA: begin
                m_axi_wvalid = 1'b1;
                m_axi_wdata  = data_buffer[write_count];
                m_axi_wlast  = (write_count == beats_total - 1);
            end

            WRITE_RESP: begin
                m_axi_bready = 1'b1;
            end

            default: begin
                // Inactive defaults.
            end
        endcase
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state        <= IDLE;
            src_addr_reg <= '0;
            dst_addr_reg <= '0;
            beats_total  <= 0;
            read_count   <= 0;
            write_count  <= 0;
            busy         <= 1'b0;
            done         <= 1'b0;
            error        <= 1'b0;
        end else begin
            // Status outputs are one-cycle pulses.
            done  <= 1'b0;
            error <= 1'b0;

            case (state)
                IDLE: begin
                    busy <= 1'b0;

                    if (start) begin
                        // Validate the transfer before issuing AXI traffic.
                        if ((DATA_WIDTH < 8) ||
                            ((DATA_WIDTH % 8) != 0) ||
                            (BYTES_PER_BEAT == 0) ||
                            (MAX_BURST_LEN < 1) ||
                            (length_bytes == 0) ||
                            ((length_bytes % BYTES_PER_BEAT) != 0) ||
                            ((length_bytes / BYTES_PER_BEAT) > MAX_BURST_LEN) ||
                            (src_addr[BYTE_ADDR_BITS-1:0] != '0) ||
                            (dst_addr[BYTE_ADDR_BITS-1:0] != '0) ||
                            (({20'b0, src_addr[11:0]} + {1'b0, length_bytes}) > 33'd4096) ||
                            (({20'b0, dst_addr[11:0]} + {1'b0, length_bytes}) > 33'd4096)) begin
                            error <= 1'b1;
                        end else begin
                            src_addr_reg <= src_addr;
                            dst_addr_reg <= dst_addr;
                            beats_total  <= length_bytes / BYTES_PER_BEAT;
                            read_count   <= 0;
                            write_count  <= 0;
                            busy         <= 1'b1;
                            state        <= READ_ADDR;
                        end
                    end
                end

                READ_ADDR: begin
                    if (m_axi_arvalid && m_axi_arready) begin
                        read_count <= 0;
                        state      <= READ_DATA;
                    end
                end

                READ_DATA: begin
                    if (m_axi_rvalid && m_axi_rready) begin
                        // RLAST must be asserted on exactly the final beat.
                        if ((m_axi_rresp != 2'b00) ||
                            (m_axi_rlast != (read_count == beats_total - 1))) begin
                            busy  <= 1'b0;
                            error <= 1'b1;
                            state <= IDLE;
                        end else begin
                            data_buffer[read_count] <= m_axi_rdata;

                            if (read_count == beats_total - 1) begin
                                write_count <= 0;
                                state       <= WRITE_ADDR;
                            end else begin
                                read_count <= read_count + 1;
                            end
                        end
                    end
                end

                WRITE_ADDR: begin
                    if (m_axi_awvalid && m_axi_awready) begin
                        write_count <= 0;
                        state       <= WRITE_DATA;
                    end
                end

                WRITE_DATA: begin
                    if (m_axi_wvalid && m_axi_wready) begin
                        if (write_count == beats_total - 1) begin
                            state <= WRITE_RESP;
                        end else begin
                            write_count <= write_count + 1;
                        end
                    end
                end

                WRITE_RESP: begin
                    if (m_axi_bvalid && m_axi_bready) begin
                        busy <= 1'b0;

                        if (m_axi_bresp != 2'b00) begin
                            error <= 1'b1;
                        end else begin
                            done <= 1'b1;
                        end

                        state <= IDLE;
                    end
                end

                default: begin
                    state <= IDLE;
                    busy  <= 1'b0;
                    error <= 1'b1;
                end
            endcase
        end
    end

endmodule
