module axi_response_harness (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        start_r,
    input  logic        rready,
    output logic        rvalid,
    output logic [31:0] rdata,
    output logic [1:0]  rresp,
    output logic        rlast,

    input  logic        start_b,
    input  logic        bready,
    output logic        bvalid,
    output logic [1:0]  bresp
);

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            rvalid <= 1'b0;
            rdata  <= '0;
            rresp  <= 2'b00;
            rlast  <= 1'b0;
            bvalid <= 1'b0;
            bresp  <= 2'b00;
        end else begin
            // Hold the read response until VALID and READY handshake.
            if (rvalid && rready) begin
                rvalid <= 1'b0;
            end else if (start_r && !rvalid) begin
                rvalid <= 1'b1;
                rdata  <= 32'hA5C37E19;
                rresp  <= 2'b00;
                rlast  <= 1'b1;
            end

            // Hold the write response until VALID and READY handshake.
            if (bvalid && bready) begin
                bvalid <= 1'b0;
            end else if (start_b && !bvalid) begin
                bvalid <= 1'b1;
                bresp  <= 2'b00;
            end
        end
    end

endmodule
