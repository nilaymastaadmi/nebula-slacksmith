You are proposing ONE typed RTL transform to reduce the critical path delay of a
module in a synthesized design. Your proposal will be checked by a formal
equivalence gate that you cannot influence, and then re-measured by static
timing analysis. A transform that is wrong will be refuted with a
counterexample. A transform that is correct but does not improve timing will be
reverted.

## The state right now

Iteration 2 of the closed loop.

Worst path group: **clk_e**, slack **-24.079 ns**.

Slack history so far, by iteration: it1 -25.957, it2 -24.079

The classifier routed this path to the RTL lever with verdict **FANOUT_DOMINATED**,
fanout delay share 0.9895, path delay 29.172 ns across
6 cells. Its evidence:

| instance | cell | incr ns | fanout | module |
|---|---|---|---|---|
| `u_aes_e/u_core/keymem/_07877_` | `sky130_fd_sc_hd__nor4_1` | 21.585 | 293 | aes_key_mem |
| `u_aes_e/u_core/keymem/_10899_` | `sky130_fd_sc_hd__and2_0` | 6.333 | 256 | aes_key_mem |
| `u_aes_e/u_core/keymem/_14194_` | `sky130_fd_sc_hd__dfrtp_1` | 0.947 | 54 | aes_key_mem |

Binding module: **aes_key_mem**

## The critical path report

```

Startpoint: u_aes_e/u_core/keymem/_14194_
            (rising edge-triggered flip-flop clocked by clk_e)
Endpoint: u_aes_e/u_core/keymem/_14582_
          (rising edge-triggered flip-flop clocked by clk_e)
Path Group: clk_e
Path Type: max

Fanout    Delay     Time   Description
-----------------------------------------------------------------
          0.000    0.000   clock clk_e (rise edge)
          0.000    0.000   clock network delay (ideal)
          0.000    0.000 ^ u_aes_e/u_core/keymem/_14194_/CLK (sky130_fd_sc_hd__dfrtp_1)
    54    0.947    0.947 v u_aes_e/u_core/keymem/_14194_/Q (sky130_fd_sc_hd__dfrtp_1)
   293   21.585   22.532 ^ u_aes_e/u_core/keymem/_07877_/Y (sky130_fd_sc_hd__nor4_1)
   256    6.333   28.865 ^ u_aes_e/u_core/keymem/_10899_/X (sky130_fd_sc_hd__and2_0)
     1    0.307   29.172 v u_aes_e/u_core/keymem/_11153_/Y (sky130_fd_sc_hd__a21oi_1)
          0.000   29.172 v u_aes_e/u_core/keymem/_14582_/D (sky130_fd_sc_hd__dfrtp_1)
                  29.172   data arrival time

          5.500    5.500   clock clk_e (rise edge)
          0.000    5.500   clock network delay (ideal)
          0.000    5.500   clock reconvergence pessimism
                   5.500 ^ u_aes_e/u_core/keymem/_14582_/CLK (sky130_fd_sc_hd__dfrtp_1)
         -0.407    5.093   library setup time
                   5.093   data required time
-----------------------------------------------------------------
                   5.093   data required time
                 -29.172   data arrival time
-----------------------------------------------------------------
                 -24.079   slack (VIOLATED)



```

## The current source of aes_key_mem

This is the CURRENT source. It may already contain a transform accepted in an
earlier iteration of this run.

```verilog
//======================================================================
//
// aes_key_mem.v
// -------------
// The AES key memory including round key generator.
//
//
// Author: Joachim Strombergson
// Copyright (c) 2013 Secworks Sweden AB
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or
// without modification, are permitted provided that the following
// conditions are met:
//
// 1. Redistributions of source code must retain the above copyright
//    notice, this list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright
//    notice, this list of conditions and the following disclaimer in
//    the documentation and/or other materials provided with the
//    distribution.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
// FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
// COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
// INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
// BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
// STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
// ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
//======================================================================

`default_nettype none

module aes_key_mem(
                   input wire            clk,
                   input wire            reset_n,

                   input wire [255 : 0]  key,
                   input wire            keylen,
                   input wire            init,

                   input wire    [3 : 0] round,
                   output wire [127 : 0] round_key,
                   output wire           ready,


                   output wire [31 : 0]  sboxw,
                   input wire  [31 : 0]  new_sboxw
                  );


  //----------------------------------------------------------------
  // Parameters.
  //----------------------------------------------------------------
  localparam AES_128_BIT_KEY = 1'h0;
  localparam AES_256_BIT_KEY = 1'h1;

  localparam AES_128_NUM_ROUNDS = 10;
  localparam AES_256_NUM_ROUNDS = 14;

  localparam CTRL_IDLE     = 3'h0;
  localparam CTRL_INIT     = 3'h1;
  localparam CTRL_GENERATE = 3'h2;
  localparam CTRL_DONE     = 3'h3;


  //----------------------------------------------------------------
  // Registers.
  //----------------------------------------------------------------
  reg [127 : 0] key_mem [0 : 14];
  reg [127 : 0] key_mem_new;
  reg           key_mem_we;

  reg [127 : 0] prev_key0_reg;
  reg [127 : 0] prev_key0_new;
  reg           prev_key0_we;

  reg [127 : 0] prev_key1_reg;
  reg [127 : 0] prev_key1_new;
  reg           prev_key1_we;

  reg [3 : 0] round_ctr_reg;
  reg [3 : 0] round_ctr_new;
  reg         round_ctr_rst;
  reg         round_ctr_inc;
  reg         round_ctr_we;

  reg [2 : 0] key_mem_ctrl_reg;
  reg [2 : 0] key_mem_ctrl_new;
  reg         key_mem_ctrl_we;

  reg         ready_reg;
  reg         ready_new;
  reg         ready_we;

  reg [7 : 0] rcon_reg;
  reg [7 : 0] rcon_new;
  reg         rcon_we;
  reg         rcon_set;
  reg         rcon_next;


  //----------------------------------------------------------------
  // Wires.
  //----------------------------------------------------------------
  reg [31 : 0]  tmp_sboxw;
  reg           round_key_update;
  reg [127 : 0] tmp_round_key;


  //----------------------------------------------------------------
  // Concurrent assignments for ports.
  //----------------------------------------------------------------
  assign round_key = tmp_round_key;
  assign ready     = ready_reg;
  assign sboxw     = tmp_sboxw;


  //----------------------------------------------------------------
  // reg_update
  //
  // Update functionality for all registers in the core.
  // All registers are positive edge triggered with asynchronous
  // active low reset. All registers have write enable.
  //----------------------------------------------------------------
  always @ (posedge clk or negedge reset_n)
    begin: reg_update
      integer i;

      if (!reset_n)
        begin
          for (i = 0 ; i <= AES_256_NUM_ROUNDS ; i = i + 1)
            key_mem [i] <= 128'h0;

          ready_reg        <= 1'b1;
          rcon_reg         <= 8'h0;
          round_ctr_reg    <= 4'h0;
          prev_key0_reg    <= 128'h0;
          prev_key1_reg    <= 128'h0;
          key_mem_ctrl_reg <= CTRL_IDLE;
        end
      else
        begin
          if (ready_we)
            ready_reg <= ready_new;

          if (rcon_we)
            rcon_reg <= rcon_new;

          if (round_ctr_we)
            round_ctr_reg <= round_ctr_new;

          // ---- online transform O1 -------------------------------
          // Was:  if (key_mem_we) key_mem[round_ctr_reg] <= key_mem_new;
          // The implicit array-write decode synthesizes to a shared
          // multi-level term driving 300 loads, worth 21.029 ns of a
          // 30.602 ns path. Fifteen independent per-entry enables give
          // each entry its own 4-bit compare, so no single decode net
          // is shared across entries. Same flops, same values, k = 0.
          for (i = 0 ; i <= 14 ; i = i + 1)
            if (key_mem_we && (round_ctr_reg == i[3 : 0]))
              key_mem[i] <= key_mem_new;
          // --------------------------------------------------------

          if (prev_key0_we)
            prev_key0_reg <= prev_key0_new;

          if (prev_key1_we)
            prev_key1_reg <= prev_key1_new;

          if (key_mem_ctrl_we)
            key_mem_ctrl_reg <= key_mem_ctrl_new;
        end
    end // reg_update


  //----------------------------------------------------------------
  // key_mem_read
  //
  // Combinational read port for the key memory.
  //----------------------------------------------------------------
  always @*
    begin : key_mem_read
      tmp_round_key = key_mem[round];
    end // key_mem_read


  //----------------------------------------------------------------
  // round_key_gen
  //
  // The round key generator logic for AES-128 and AES-256.
  //----------------------------------------------------------------
  always @*
    begin: round_key_gen
      reg [31 : 0] w0, w1, w2, w3, w4, w5, w6, w7;
      reg [31 : 0] k0, k1, k2, k3;
      reg [31 : 0] rconw, rotstw, tw, trw;

      // Default assignments.
      key_mem_new   = 128'h0;
      key_mem_we    = 1'b0;
      prev_key0_new = 128'h0;
      prev_key0_we  = 1'b0;
      prev_key1_new = 128'h0;
      prev_key1_we  = 1'b0;

      k0 = 32'h0;
      k1 = 32'h0;
      k2 = 32'h0;
      k3 = 32'h0;

      rcon_set   = 1'b1;
      rcon_next  = 1'b0;

      // Extract words and calculate intermediate values.
      // Perform rotation of sbox word etc.
      w0 = prev_key0_reg[127 : 096];
      w1 = prev_key0_reg[095 : 064];
      w2 = prev_key0_reg[063 : 032];
      w3 = prev_key0_reg[031 : 000];

      w4 = prev_key1_reg[127 : 096];
      w5 = prev_key1_reg[095 : 064];
      w6 = prev_key1_reg[063 : 032];
      w7 = prev_key1_reg[031 : 000];

      rconw = {rcon_reg, 24'h0};
      tmp_sboxw = w7;
      rotstw = {new_sboxw[23 : 00], new_sboxw[31 : 24]};
      trw = rotstw ^ rconw;
      tw = new_sboxw;

      // Generate the specific round keys.
      if (round_key_update)
        begin
          rcon_set   = 1'b0;
          key_mem_we = 1'b1;
          case (keylen)
            AES_128_BIT_KEY:
              begin
                if (round_ctr_reg == 0)
                  begin
                    key_mem_new   = key[255 : 128];
                    prev_key1_new = key[255 : 128];
                    prev_key1_we  = 1'b1;
                    rcon_next     = 1'b1;
                  end
                else
                  begin
                    k0 = w4 ^ trw;
                    k1 = w5 ^ w4 ^ trw;
                    k2 = w6 ^ w5 ^ w4 ^ trw;
                    k3 = w7 ^ w6 ^ w5 ^ w4 ^ trw;

                    key_mem_new   = {k0, k1, k2, k3};
                    prev_key1_new = {k0, k1, k2, k3};
                    prev_key1_we  = 1'b1;
                    rcon_next     = 1'b1;
                  end
              end

            AES_256_BIT_KEY:
              begin
                if (round_ctr_reg == 0)
                  begin
                    key_mem_new   = key[255 : 128];
                    prev_key0_new = key[255 : 128];
                    prev_key0_we  = 1'b1;
                  end
                else if (round_ctr_reg == 1)
                  begin
                    key_mem_new   = key[127 : 0];
                    prev_key1_new = key[127 : 0];
                    prev_key1_we  = 1'b1;
                    rcon_next     = 1'b1;
                  end
                else
                  begin
                    if (round_ctr_reg[0] == 0)
                      begin
                        k0 = w0 ^ trw;
                        k1 = w1 ^ w0 ^ trw;
                        k2 = w2 ^ w1 ^ w0 ^ trw;
                        k3 = w3 ^ w2 ^ w1 ^ w0 ^ trw;
                      end
                    else
                      begin
                        k0 = w0 ^ tw;
                        k1 = w1 ^ w0 ^ tw;
                        k2 = w2 ^ w1 ^ w0 ^ tw;
                        k3 = w3 ^ w2 ^ w1 ^ w0 ^ tw;
                        rcon_next = 1'b1;
                      end

                    // Store the generated round keys.
                    key_mem_new   = {k0, k1, k2, k3};
                    prev_key1_new = {k0, k1, k2, k3};
                    prev_key1_we  = 1'b1;
                    prev_key0_new = prev_key1_reg;
                    prev_key0_we  = 1'b1;
                  end
              end

            default:
              begin
              end
          endcase // case (keylen)
        end
    end // round_key_gen


  //----------------------------------------------------------------
  // rcon_logic
  //
  // Caclulates the rcon value for the different key expansion
  // iterations.
  //----------------------------------------------------------------
  always @*
    begin : rcon_logic
      reg [7 : 0] tmp_rcon;
      rcon_new = 8'h00;
      rcon_we  = 1'b0;

      tmp_rcon = {rcon_reg[6 : 0], 1'b0} ^ (8'h1b & {8{rcon_reg[7]}});

      if (rcon_set)
        begin
          rcon_new = 8'h8d;
          rcon_we  = 1'b1;
        end

      if (rcon_next)
        begin
          rcon_new = tmp_rcon[7 : 0];
          rcon_we  = 1'b1;
        end
    end


  //----------------------------------------------------------------
  // round_ctr
  //
  // The round counter logic with increase and reset.
  //----------------------------------------------------------------
  always @*
    begin : round_ctr
      round_ctr_new = 4'h0;
      round_ctr_we  = 1'b0;

      if (round_ctr_rst)
        begin
          round_ctr_new = 4'h0;
          round_ctr_we  = 1'b1;
        end

      else if (round_ctr_inc)
        begin
          round_ctr_new = round_ctr_reg + 1'b1;
          round_ctr_we  = 1'b1;
        end
    end


  //----------------------------------------------------------------
  // key_mem_ctrl
  //
  //
  // The FSM that controls the round key generation.
  //----------------------------------------------------------------
  always @*
    begin: key_mem_ctrl
      reg [3 : 0] num_rounds;

      // Default assignments.
      ready_new        = 1'b0;
      ready_we         = 1'b0;
      round_key_update = 1'b0;
      round_ctr_rst    = 1'b0;
      round_ctr_inc    = 1'b0;
      key_mem_ctrl_new = CTRL_IDLE;
      key_mem_ctrl_we  = 1'b0;

      if (keylen == AES_128_BIT_KEY)
        num_rounds = AES_128_NUM_ROUNDS;
      else
        num_rounds = AES_256_NUM_ROUNDS;

      case(key_mem_ctrl_reg)
        CTRL_IDLE:
          begin
            if (init)
              begin
                ready_new        = 1'b0;
                ready_we         = 1'b1;
                key_mem_ctrl_new = CTRL_INIT;
                key_mem_ctrl_we  = 1'b1;
              end
          end

        CTRL_INIT:
          begin
            round_ctr_rst    = 1'b1;
            key_mem_ctrl_new = CTRL_GENERATE;
            key_mem_ctrl_we  = 1'b1;
          end

        CTRL_GENERATE:
          begin
            round_ctr_inc    = 1'b1;
            round_key_update = 1'b1;
            if (round_ctr_reg == num_rounds)
              begin
                key_mem_ctrl_new = CTRL_DONE;
                key_mem_ctrl_we  = 1'b1;
              end
          end

        CTRL_DONE:
          begin
            ready_new        = 1'b1;
            ready_we         = 1'b1;
            key_mem_ctrl_new = CTRL_IDLE;
            key_mem_ctrl_we  = 1'b1;
          end

        default:
          begin
          end
      endcase // case (key_mem_ctrl_reg)

    end // key_mem_ctrl
endmodule // aes_key_mem

//======================================================================
// EOF aes_key_mem.v
//======================================================================

```

## What you must return

A single JSON object, and nothing else. No prose before or after it.

```json
{
  "id": "O2",
  "def_id": "<short_snake_case_name_for_the_transform_class>",
  "target_module": "aes_key_mem",
  "target_file": "rtl/aes_key_mem.v",
  "latency_delta_k": 0,
  "obligation_branch": "<one of the four below>",
  "rationale": "<why this shortens the critical path, in two or three sentences>",
  "variant_source": "<the COMPLETE rewritten source of the module>"
}
```

### The four proof-obligation branches

Declare the one your transform actually needs. The declaration selects the
proof, so declaring the wrong branch means being checked against the wrong
question.

| `latency_delta_k` | `obligation_branch` | when |
|---|---|---|
| 0 | `1 (combinational equivalence, EQY)` | state-preserving: same flops, same cycle behaviour |
| >0 | `2 (k-padded miter)` | you added k pipeline stages and the interface is rigid |
| >0 | `3 (stream equivalence)` | you added stages and the interface is elastic (valid/ready) |
| 0 | `4 (mapped-state equivalence)` | you re-encoded state, e.g. binary to one-hot |

### Rules that will be checked mechanically

- `variant_source` must be the complete module, parseable by Yosys, and must
  synthesize with **zero inferred latches**.
- The module name, its port list and port widths must be unchanged.
- Do not change any interface timing unless you declare `latency_delta_k > 0`
  and the matching branch.
- Do not add `set_multicycle_path`, `set_false_path` or any other constraint.
  The SDC is fingerprinted and constraint changes are rejected before timing is
  believed.
- Prefer a transform that shortens the **specific** path in the report above.
  A correct transform that does not touch the binding path will be reverted.

Return the JSON object only.