module axi_dma #(
    parameter int ADDR_WIDTH = 32,
    parameter int DATA_WIDTH = 32,
    parameter int MAX_BURST_LEN = 16,
    parameter int QUEUE_DEPTH = 4
) (
    input  logic                   clk,
    input  logic                   rst_n,

    // Transfer submission interface
    input  logic                   start,
    input  logic [ADDR_WIDTH-1:0]  src_addr,
    input  logic [ADDR_WIDTH-1:0]  dst_addr,
    input  logic [31:0]            length_bytes,
    output logic                   busy,
    output logic                   done,
    output logic                   error,

    // Descriptor queue status
    output logic                   queue_full,
    output logic                   queue_empty,
    output logic [$clog2(QUEUE_DEPTH+1)-1:0] queue_level,

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
    localparam int PTR_WIDTH =
        (QUEUE_DEPTH > 1) ? $clog2(QUEUE_DEPTH) : 1;
    localparam int COUNT_WIDTH = $clog2(QUEUE_DEPTH + 1);

    typedef enum logic [2:0] {
        IDLE,
        READ_ADDR,
        READ_DATA,
        WRITE_ADDR,
        WRITE_DATA,
        WRITE_RESP
    } state_t;

    state_t state;

    // Active descriptor registers.
    logic [ADDR_WIDTH-1:0] src_addr_reg;
    logic [ADDR_WIDTH-1:0] dst_addr_reg;

    // Waiting descriptor FIFO. The active descriptor is not stored here.
    logic [ADDR_WIDTH-1:0] queue_src [0:QUEUE_DEPTH-1];
    logic [ADDR_WIDTH-1:0] queue_dst [0:QUEUE_DEPTH-1];
    logic [31:0] queue_len [0:QUEUE_DEPTH-1];

    logic [PTR_WIDTH-1:0] queue_wr_ptr;
    logic [PTR_WIDTH-1:0] queue_rd_ptr;
    logic [COUNT_WIDTH-1:0] queue_count;

    logic enqueue_descriptor;
    logic dequeue_descriptor;

    logic [ADDR_WIDTH-1:0] candidate_src;
    logic [ADDR_WIDTH-1:0] candidate_dst;
    logic [31:0] candidate_len;
    logic candidate_valid;

    // Buffer the complete read burst before starting the write burst.
    logic [DATA_WIDTH-1:0] data_buffer [0:MAX_BURST_LEN-1];

    logic [31:0] beats_total;
    logic [31:0] read_count;
    logic [31:0] write_count;

    // Queue status describes waiting descriptors only.
    always_comb begin
        queue_level = queue_count;
        queue_empty = (queue_count == 0);
        queue_full  = (queue_count == COUNT_WIDTH'(QUEUE_DEPTH));
    end

    // When idle, queued work has priority over a newly submitted request.
    // If no descriptor is waiting, start launches directly as before.
    always_comb begin
        candidate_src = src_addr;
        candidate_dst = dst_addr;
        candidate_len = length_bytes;

        if (queue_count != 0) begin
            candidate_src = queue_src[queue_rd_ptr];
            candidate_dst = queue_dst[queue_rd_ptr];
            candidate_len = queue_len[queue_rd_ptr];
        end

        candidate_valid =
            (DATA_WIDTH >= 8) &&
            ((DATA_WIDTH % 8) == 0) &&
            (BYTES_PER_BEAT != 0) &&
            (MAX_BURST_LEN >= 1) &&
            (candidate_len != 0) &&
            ((candidate_len % BYTES_PER_BEAT) == 0) &&
            ((candidate_len / BYTES_PER_BEAT) <= MAX_BURST_LEN) &&
            (candidate_src[BYTE_ADDR_BITS-1:0] == '0) &&
            (candidate_dst[BYTE_ADDR_BITS-1:0] == '0) &&
            (({20'b0, candidate_src[11:0]} +
              {1'b0, candidate_len}) <= 33'd4096) &&
            (({20'b0, candidate_dst[11:0]} +
              {1'b0, candidate_len}) <= 33'd4096);
    end

    // A request starts directly only when idle and the FIFO is empty.
    // Otherwise it is accepted into the FIFO if a slot is available.
    always_comb begin
        enqueue_descriptor = 1'b0;
        dequeue_descriptor = 1'b0;

        if (start && !((state == IDLE) && (queue_count == 0))) begin
            if (queue_count < COUNT_WIDTH'(QUEUE_DEPTH))
                enqueue_descriptor = 1'b1;
        end

        if ((state == IDLE) && (queue_count != 0))
            dequeue_descriptor = 1'b1;
    end

    always_comb begin
        m_axi_araddr  = src_addr_reg;
        m_axi_arlen   = 8'(beats_total - 1);
        m_axi_arsize  = 3'(BYTE_ADDR_BITS);
        m_axi_arburst = 2'b01;
        m_axi_arvalid = 1'b0;

        m_axi_rready  = 1'b0;

        m_axi_awaddr  = dst_addr_reg;
        m_axi_awlen   = 8'(beats_total - 1);
        m_axi_awsize  = 3'(BYTE_ADDR_BITS);
        m_axi_awburst = 2'b01;
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
            end
        endcase
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            queue_wr_ptr <= '0;
            queue_rd_ptr <= '0;
            queue_count  <= '0;

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
            done  <= 1'b0;
            error <= 1'b0;

            // FIFO write and read pointers.
            if (enqueue_descriptor) begin
                queue_src[queue_wr_ptr] <= src_addr;
                queue_dst[queue_wr_ptr] <= dst_addr;
                queue_len[queue_wr_ptr] <= length_bytes;

                if (queue_wr_ptr == PTR_WIDTH'(QUEUE_DEPTH - 1))
                    queue_wr_ptr <= '0;
                else
                    queue_wr_ptr <= queue_wr_ptr + 1'b1;
            end

            if (dequeue_descriptor) begin
                if (queue_rd_ptr == PTR_WIDTH'(QUEUE_DEPTH - 1))
                    queue_rd_ptr <= '0;
                else
                    queue_rd_ptr <= queue_rd_ptr + 1'b1;
            end

            case ({enqueue_descriptor, dequeue_descriptor})
                2'b10: queue_count <= queue_count + 1'b1;
                2'b01: queue_count <= queue_count - 1'b1;
                default: queue_count <= queue_count;
            endcase

            case (state)
                IDLE: begin
                    busy <= 1'b0;

                    if ((queue_count != 0) || start) begin
                        if (candidate_valid) begin
                            src_addr_reg <= candidate_src;
                            dst_addr_reg <= candidate_dst;
                            beats_total  <=
                                candidate_len / BYTES_PER_BEAT;
                            read_count  <= 0;
                            write_count <= 0;
                            busy        <= 1'b1;
                            state       <= READ_ADDR;
                        end else begin
                            error <= 1'b1;
                            state <= IDLE;
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
                        if ((m_axi_rresp != 2'b00) ||
                            (m_axi_rlast !=
                             (read_count == beats_total - 1))) begin
                            busy  <= 1'b0;
                            error <= 1'b1;
                            state <= IDLE;
                        end else begin
                            data_buffer[read_count] <= m_axi_rdata;

                            if (read_count == beats_total - 1) begin
                                write_count <= 0;
                                state       <= WRITE_ADDR;
                            end else begin
                                read_count <= read_count + 1'b1;
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
                        if (write_count == beats_total - 1)
                            state <= WRITE_RESP;
                        else
                            write_count <= write_count + 1'b1;
                    end
                end

                WRITE_RESP: begin
                    if (m_axi_bvalid && m_axi_bready) begin
                        busy <= 1'b0;

                        if (m_axi_bresp != 2'b00)
                            error <= 1'b1;
                        else
                            done <= 1'b1;

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


`ifndef SYNTHESIS
    // M14 simulation-time invariants
    always_ff @(posedge clk) begin
        if (rst_n) begin
            assert (state <= WRITE_RESP)
                else $error("M14: illegal FSM state");

            assert (queue_count <= COUNT_WIDTH'(QUEUE_DEPTH))
                else $error("M14: queue occupancy exceeds QUEUE_DEPTH");

            if (state == READ_ADDR || state == READ_DATA ||
                state == WRITE_ADDR || state == WRITE_DATA ||
                state == WRITE_RESP) begin
                assert (beats_total >= 1 &&
                        beats_total <= MAX_BURST_LEN)
                    else $error("M14: active burst length out of range");
            end

            if (state == READ_DATA) begin
                assert (read_count < beats_total)
                    else $error("M14: read counter out of range");
            end

            if (state == WRITE_DATA) begin
                assert (write_count < beats_total)
                    else $error("M14: write counter out of range");
            end
        end
    end
`endif

endmodule
