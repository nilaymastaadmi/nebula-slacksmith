// ---------------------------------------------------------------------------
// aes_load - self-driving AES-128 workload block, one per hosting domain.
//
// Exists for benchmark growth (organizer spec: "~50K standard cells"; the
// original skeleton was 3,584, measured 2026-08-31). This is not padding
// with dead logic: aes_core is a real, third-party, verification-grade
// AES implementation (secworks/aes, BSD-2-Clause, vendored under rtl/aes/
// with its LICENSE), driven with live data derived from the hosting
// domain's own state and folded back into the hosting domain's outputs, so
// synthesis cannot prune it and timing paths through it terminate
// observably, the same rule the original skeleton's README set for every
// block.
//
// Driver protocol (from aes_core's own interface contract): pulse init to
// expand the key, wait for ready, then pulse next per block; result_valid
// flags each completed encryption. This driver free-runs: init once after
// reset, then re-next whenever the core reports ready, feeding a rolling
// block register that absorbs seed_in every cycle, so the core is
// continuously active and its result stream continuously changes.
//
// fold_out is a 32-bit XOR reduction of the last result, for the hosting
// domain to mix into its own visible outputs.
// ---------------------------------------------------------------------------
module aes_load (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [127:0] key_in,     // low 128 bits used, keylen=0 (AES-128)
    input  wire [31:0]  seed_in,    // live data from the hosting domain
    output wire [31:0]  fold_out
);

    wire        ready;
    wire [127:0] result;
    wire        result_valid;

    reg         init_r;
    reg         inited_r;
    reg         next_r;
    reg [127:0] block_r;
    reg [127:0] last_result_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            init_r        <= 1'b0;
            inited_r      <= 1'b0;
            next_r        <= 1'b0;
            block_r       <= 128'd0;
            last_result_r <= 128'd0;
        end else begin
            // one init pulse, once, after reset
            init_r   <= ~inited_r;
            inited_r <= 1'b1;

            // rolling block: rotate and absorb the live seed
            block_r <= {block_r[95:0], block_r[127:96] ^ seed_in};

            // request a new encryption whenever the core is idle-ready
            next_r <= inited_r & ready & ~next_r;

            if (result_valid)
                last_result_r <= result;
        end
    end

    aes_core u_core (
        .clk          (clk),
        .reset_n      (rst_n),
        .encdec       (1'b1),          // encrypt
        .init         (init_r),
        .next         (next_r),
        .ready        (ready),
        .key          ({128'd0, key_in}),
        .keylen       (1'b0),          // AES-128
        .block        (block_r),
        .result       (result),
        .result_valid (result_valid)
    );

    assign fold_out = last_result_r[127:96] ^ last_result_r[95:64]
                    ^ last_result_r[63:32]  ^ last_result_r[31:0];

endmodule
