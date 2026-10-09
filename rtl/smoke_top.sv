module smoke_top (
    input  logic       clk,
    input  logic       rst_n,
    output logic [3:0] count
);

    always_ff @(posedge clk) begin
        if (!rst_n)
            count <= 4'd0;
        else
            count <= count + 1'b1;
    end

endmodule
