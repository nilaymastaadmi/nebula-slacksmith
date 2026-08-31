# Third-party RTL: secworks/aes

The 6 Verilog files in this directory (aes_core.v, aes_encipher_block.v,
aes_decipher_block.v, aes_key_mem.v, aes_sbox.v, aes_inv_sbox.v) are vendored
unmodified from https://github.com/secworks/aes (Joachim Strombergson,
Assured AB), BSD-2-Clause, license text in LICENSE in this directory and in
each file's own header. Vendored 2026-08-31 for benchmark growth (organizer
requirement "~50K standard cells"); see the v2 note in rtl/bench_top.v.

Everything else in rtl/ is this project's own work. rv32i_core.v is the
team's own core, copied from the same author's rv32-dsp-soc repository where
it is verified against a golden C++ ISS over a 400-seed differential
regression.
