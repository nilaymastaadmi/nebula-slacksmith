#!/usr/bin/env python3
"""Build the do-nothing control for i2c: the same RTL with two independent
always blocks in i2c_master_bit_ctrl exchanged in source order.

Reordering module items is a semantic no-op in Verilog, so the control is
equivalent by construction. It is not a no-op for the mapper: Yosys names and
orders cells by source position, and ABC's mapping is sensitive to that order,
which is exactly the perturbation this control exists to measure. It is the
i2c analogue of A5 (experiments/llm_proposer_aes/), the reset-unroll edit that
touched nothing on the read path and still moved clk_b by 0.436 ns.

The control is rebuilt by this script and checked against the committed copy,
so the committed control cannot drift from its definition.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "rtl", "i2c.v")).read()

busy = """\t// generate i2c bus busy signal
\talways @(posedge clk or negedge nReset)
\t  if(!nReset)
\t    busy <= #1 1'b0;
\t  else if (rst)
\t    busy <= #1 1'b0;
\t  else
\t    busy <= #1 (sta_condition | busy) & ~sto_condition;

"""
anchor = """\t// generate arbitration lost signal
"""
assert src.count(busy) == 1, "busy block not found exactly once"
assert src.count(anchor) == 1, "anchor not found exactly once"
# Move the busy block to AFTER the cmd_stop block that follows the anchor.
cmd_stop_end = """\t  else if (clk_en)
\t    cmd_stop <= #1 cmd == `I2C_CMD_STOP;

"""
assert src.count(cmd_stop_end) == 1, "cmd_stop block end not found exactly once"
out = src.replace(busy, "", 1)
out = out.replace(cmd_stop_end, cmd_stop_end + busy, 1)
assert out != src and len(out) == len(src), "control must be a pure reordering"

target = os.path.join(HERE, "rtl_control", "i2c.v")
if os.path.exists(target) and "--write" not in sys.argv:
    cur = open(target).read()
    print("CONTROL OK" if cur == out else "CONTROL MISMATCH: committed control is not the defined reordering")
    sys.exit(0 if cur == out else 4)
open(target, "w").write(out)
print("wrote", target)
