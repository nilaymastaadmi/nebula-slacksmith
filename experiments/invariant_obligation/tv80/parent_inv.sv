// R90: the parent's reachable-state invariant, proven on tv80_core at Mode = 1.
//
// tv80_core drives tv80_mcode's MCycle input directly from its `mcycle`
// register (`.MCycle (mcycle)` in the i_mcode instantiation), so an invariant
// proven on that register holds at the child's input by construction. That is
// the assume-guarantee split: guarantee it here, assume it in child_miter.sv.
//
// Two properties, one task each:
//   EXCL    !(mcycle[5] && mcycle[6])   exactly what the transform needs (R90)
//   ONEHOT  $onehot(mcycle)             stronger; used only if EXCL is not
//                                       k-inductive, and disclosed as a
//                                       strengthening if it is used
//
// Start from reset. number_to_bitvec() returns 7'bx for an argument of 0, and
// the flow maps undefined values to free choices (setundef -anyseq), so the
// proof does not quietly assume x is 0.
module mcycle_inv_chk (
    input wire       clk,
    input wire       reset_n,
    input wire [6:0] mcycle
);
`ifdef FORMAL
    reg started = 1'b0;
    always @(posedge clk) started <= 1'b1;
    always @(*) if (!started) assume (!reset_n);

    always @(posedge clk) if (started && reset_n) begin
`ifdef ONEHOT
        onehot: assert ($onehot(mcycle));
`else
        excl: assert (!(mcycle[5] && mcycle[6]));
`endif
    end
`endif
endmodule

bind tv80_core mcycle_inv_chk u_mcycle_inv (
    .clk(clk), .reset_n(reset_n), .mcycle(mcycle)
);
