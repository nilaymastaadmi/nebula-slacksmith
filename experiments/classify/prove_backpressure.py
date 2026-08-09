#!/usr/bin/env python3
"""
Third pass: PROVE the interface class instead of inferring it.

classify.py establishes that a candidate back-pressure input reaches sequential
state. That is necessary but not sufficient -- an input named `busy` that feeds a
status counter also reaches state without being able to stall anything.

The property that actually defines an elastic interface is output stability
under back-pressure:

    if the output is valid and the consumer is not ready,
    then next cycle the output data and valid must be unchanged.

A module that satisfies it can be stalled, so a fixed cycle offset between it and
a re-pipelined version does not exist, and the k-padded miter is unsound.
A module that violates it drops or overwrites data when stalled -- it is not
honouring the handshake, and is rigid whatever its ports are called.

This generates that assertion as a wrapper and discharges it with yosys-smtbmc,
so the classifier's verdict becomes a proof obligation like everything else in
this project.

Usage:  prove_backpressure.py <top> <file.v> <valid_port> <ready_port> <data_port>
"""

import subprocess
import sys
import tempfile
import os

WRAPPER = """
module bp_check (
    input wire clk,
    input wire rst,
    input wire free_in_valid,
    input wire [7:0] free_a,
    input wire [7:0] free_b,
    input wire [15:0] free_c,
    input wire free_out_ready
);
    wire dut_valid;
    wire [15:0] dut_data;

    {top} u_dut (
        .{clk_port}(clk),
        .{rst_port}({rst_expr}),
        .{in_valid_port}(free_in_valid),
{data_in_conns}
        .{valid}(dut_valid),
        .{ready}(free_out_ready),
        .{data}(dut_data)
    );

    reg        p_valid, p_ready, p_rst;
    reg [15:0] p_data;
    always @(posedge clk) begin
        p_valid <= dut_valid;
        p_ready <= free_out_ready;
        p_data  <= dut_data;
        p_rst   <= rst;
    end

    reg started = 1'b0;
    always @(posedge clk) if (!rst) started <= 1'b1;

`ifdef FORMAL
    initial assume (rst);

    // Output stability under back-pressure.
    always @(posedge clk) begin
        if (started && !rst && !p_rst && p_valid && !p_ready) begin
            assert (dut_valid == p_valid);
            assert (dut_data  == p_data);
        end
    end
`endif
endmodule
"""


def build_wrapper(top, valid, ready, data, clk_port, rst_port, rst_expr,
                  in_valid_port, data_in_ports):
    conns = "".join(
        f"        .{p}(free_{n}),\n"
        for p, n in zip(data_in_ports, ("a", "b", "c"))
    )
    return WRAPPER.format(
        top=top, valid=valid, ready=ready, data=data,
        clk_port=clk_port, rst_port=rst_port, rst_expr=rst_expr,
        in_valid_port=in_valid_port, data_in_conns=conns,
    )


def prove(top, src, valid, ready, data, clk_port, rst_port, rst_expr,
          in_valid_port, data_in_ports, depth=16):
    wrap = build_wrapper(top, valid, ready, data, clk_port, rst_port,
                         rst_expr, in_valid_port, data_in_ports)
    d = tempfile.mkdtemp()
    wf = os.path.join(d, "bp_check.sv")
    smt = os.path.join(d, "bp.smt2")
    open(wf, "w").write(wrap)

    y = subprocess.run(
        ["yosys", "-q", "-p",
         f"read_verilog -sv {src}; read_verilog -formal -sv {wf}; "
         f"prep -top bp_check -flatten; write_smt2 -wires {smt}"],
        capture_output=True, text=True)
    if y.returncode != 0:
        return "ELAB_FAIL", y.stderr[-500:]

    r = subprocess.run(
        ["yosys-smtbmc", "-s", "z3", "-t", str(depth), smt],
        capture_output=True, text=True)
    out = r.stdout + r.stderr
    if "Status: PASSED" in out:
        return "PASSED", ""
    if "Status: FAILED" in out:
        return "FAILED", ""
    return "UNRESOLVED", out[-300:]


if __name__ == "__main__":
    if len(sys.argv) < 6:
        sys.exit(__doc__)
    top, src, valid, ready, data = sys.argv[1:6]
    clk_port      = sys.argv[6] if len(sys.argv) > 6 else "clk"
    rst_port      = sys.argv[7] if len(sys.argv) > 7 else "rst"
    rst_expr      = sys.argv[8] if len(sys.argv) > 8 else "rst"
    in_valid_port = sys.argv[9] if len(sys.argv) > 9 else "in_valid"
    din           = sys.argv[10].split(",") if len(sys.argv) > 10 else ["a", "b", "c"]

    verdict, detail = prove(top, src, valid, ready, data, clk_port, rst_port,
                            rst_expr, in_valid_port, din)
    print(f"{top:<18} output-stability-under-backpressure: {verdict}")
    if detail:
        print(detail)
    sys.exit(0 if verdict == "PASSED" else 1)
