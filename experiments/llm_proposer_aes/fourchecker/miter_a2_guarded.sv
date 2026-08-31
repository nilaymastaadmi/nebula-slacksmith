// Is A2's refutation confined to the unreachable round=15 read?
//
// key_mem is declared [0:14] and `round` is 4 bits, so round=15 is an
// out-of-range read. Gold reads one 15-entry 128-bit array; A2 reads four
// 15-entry 32-bit arrays. Simulation reports both as x and calls them equal
// (x === x). A SAT-based equivalence check does not: an out-of-range read is
// an unconstrained value, and gold's is not forced to agree with A2's.
//
// The AES key-expansion controller counts round_ctr_reg 0..14 and never
// issues round=15. So the engineering question is whether A2 is equivalent
// ON REACHABLE INPUTS. This miter asserts exactly that by assuming the
// constraint, and is the control for the claim.
//
// If this PROVES, the refutation is a specification gap in the obligation,
// not a defect in the transform, and the gate needs reachability constraints.
// If it FAILS, A2 is genuinely broken and the round=15 story is wrong.
module miter_a2_guarded (
    input wire clk,
    input wire reset_n,
    input wire [255:0] key,
    input wire keylen,
    input wire init,
    input wire [3:0] round,
    input wire [31:0] new_sboxw
);
    wire [127:0] g_round_key, t_round_key;
    wire         g_ready, t_ready;
    wire [31:0]  g_sboxw, t_sboxw;

    aes_key_mem_gold u_g (
        .clk(clk), .reset_n(reset_n), .key(key), .keylen(keylen),
        .init(init), .round(round), .new_sboxw(new_sboxw),
        .round_key(g_round_key), .ready(g_ready), .sboxw(g_sboxw)
    );
    aes_key_mem_gate u_t (
        .clk(clk), .reset_n(reset_n), .key(key), .keylen(keylen),
        .init(init), .round(round), .new_sboxw(new_sboxw),
        .round_key(t_round_key), .ready(t_ready), .sboxw(t_sboxw)
    );

`ifdef FORMAL
    initial assume (!reset_n);
    always @(posedge clk) begin
        // the reachability constraint, and the only thing that differs from
        // the unguarded obligation EQY ran
        assume (round <= 4'd14);
        if (reset_n) begin
            eq_round_key: assert (g_round_key == t_round_key);
            eq_ready:     assert (g_ready     == t_ready);
            eq_sboxw:     assert (g_sboxw     == t_sboxw);
        end
    end
`endif
endmodule
