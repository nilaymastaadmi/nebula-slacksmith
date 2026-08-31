# rv32i_core calibrated WNS: re-derived, resolved, and made precise

Run 2026-08-31 (audit finding F3 follow-up). OpenSTA (this project's build),
sky130hd_tt, preserved netlist and SDC from the 2026-08-14 session.

## History, stated plainly

The 2026-08-14 result note reported "WNS -8.527 ns" for rv32i_core at a 10 ns
target, and that number became the justification anecdote for the frozen-SDC
discipline (cited in sdc/bench_top.sdc). The 2026-08-31 audit reran the
preserved SDC + netlist and got `report_wns` = -32.30, could not explain the
gap, and ruled the number VOID pending re-derivation
(~/jarvis-vault/Decisions/2026-08-31-nebula-rv32i-wns-void.md).

## Resolution: every original number reproduces exactly; the label was imprecise

Full log: logs/rv32i_rederive_2026-08-31.log. Same netlist, same SDC:

| Path group | Startpoint -> Endpoint | Arrival | Slack |
|---|---|---|---|
| input -> output (worst DATA path) | imem_data[24] -> retire_val[20] | 16.527 | **-8.527** |
| reg -> reg | internal | 10.821 | **-1.114** |
| **recovery check (the missing group)** | rst_n -> _11385_ recovery | 31.028 | **-32.296** |

The -8.527 and -1.114 reproduce to the digit. The tool-level `report_wns` of
-32.30 comes from a fourth path group the original write-up did not account
for: core.sdc gives rst_n an input delay and a buf_1 driving cell and no
false-path, so OpenSTA times RECOVERY checks on the async reset against all
1,024 flops, and one weakly-driven reset tree with that fanout produces a
-32.3 artifact. That is an SDC modeling decision about the reset, not a
datapath timing fact.

So: "-8.527" was never fabricated and is not VOID. It is the worst data-path
slack. Calling it "WNS" without qualification was the error, because the
tool's WNS additionally sees the reset recovery group. The 2026-08-14 note's
qualitative claim survives fully and is actually sharpened: leaving
imem_data/dmem_rdata unconstrained would have hidden 7.4 ns (41% of the true
data period), and separately, how you constrain an async RESET decides
whether a recovery artifact dominates the tool's headline number. Both are
arguments for the same discipline: the number is a property of the SDC as
much as the circuit.

## Supersession

This resolves and supersedes the VOID ruling per that decision file's own
reopen condition ("reopens the moment a saved recipe reproduces a number").
Superseding decision file:
~/jarvis-vault/Decisions/2026-08-31-nebula-rv32i-wns-resolved.md.

## Reproduce

The core RTL lives in the external rv32-dsp-soc repo; the mapped netlist and
liberty live on the build machine (~/sta_work/). With those two files beside
this directory's core.sdc and rederive.tcl:

    sta -no_init -no_splash -exit rederive.tcl
