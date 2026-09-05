# Reproducibility: the claim we had not checked

**Date:** 2026-09-05. **Commit under test:** `ab453d5`.

`REPORT.md` §10 said "cold-clone reproduction was verified per directory."
It had not been. Nothing in this repository had ever been cloned and run
anywhere other than the author's working directory, and it could not have been:
every script opened with

    cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark

A project whose argument is that measured claims must be checkable had shipped
an unchecked claim about its own checkability. This directory is what happens
when you actually run it.

## What was broken, and only a clone would have shown it

1. **30 shell scripts and 7 Python entry points hard-coded tool paths.** The
   repo ran at one path on one machine.
2. **Two artifacts the demo depends on were not in the repo.** The flat arm E
   netlist lived in `~/flatexp/E/mapped.v`. The SDC-integrity result is
   specifically a claim about a *byte-identical* netlist, and nobody could
   check that against a file they did not have.
3. **`core.autocrlf=true` with no `.gitattributes`.** Any clone on a Windows
   machine would have checked out every `.sh` with CRLF endings, and bash
   would have failed on the shebang. The author never saw it because his
   working tree was written directly, never checked out.

## The test

Clone the committed repo to a **different directory name**, at a **different
depth**, on a **different filesystem** (ext4 rather than the `/mnt/c`
DrvFs mount), and run everything from there.

    git clone <repo> ~/repro/some-other-name
    cd ~/repro/some-other-name
    bash tools/preflight.sh
    bash tools/demo_check.sh

Confirmed genuine rather than accidentally reading the original: during the
run, yosys was observed reading
`/home/toshn/repro/some-other-name/rtl/aes/aes_core.v` and writing to
`$SLACKSMITH_WORK`, not to the source tree.

## Result

    preflight: all present. run: bash tools/demo_check.sh
    preflight exit: 0

    === demo check: 12 pass, 0 fail ===
    DEMO EXIT: 0

**12 of 12 assertions pass from the clone**, including the live closed loop
(beat 2, full synthesis and STA of the 55K-cell benchmark), the SDC-integrity
result now reading the committed fixture rather than a home directory
(`clk_e` −0.319 to +4.860, 26,958 cells, gain 5.179), and beat 4's check that
the pre-registration commit precedes the proposals commit, which needs the
git history a zip download would not carry.

## Liberty substitution, measured

`SETUP.md` tells you to point `LIBERTY` at the ORFS-shipped
`sky130_fd_sc_hd__tt_025C_1v80.lib`. That instruction is worth nothing if the
substitute produces different numbers, so `tools/liberty_equivalence.sh` runs
both files against the same frozen netlist and SDC.

The two differ by 9 bytes across two hunks: `default_fanout_load : 1.0;`
against `1.0000000000;`, and `default_operating_conditions : "tt_025C_1v80";`
declared at line 37 in one and line 173,158 in the other.

| liberty | clk_a | clk_b | clk_e |
|---|---|---|---|
| `~/sta_work/sky130hd_tt.lib` (used for the committed results) | 11.157918 | 5.665101 | -0.318779 |
| ORFS `sky130_fd_sc_hd__tt_025C_1v80.lib` | 11.157918 | 5.665101 | -0.318779 |

Identical to six decimal places. The substitution is safe, and now that is a
measurement.

## What this does NOT establish

**One machine, one operating system, one toolchain install.** This proves the
repo is path-independent, not that it is portable. Nobody has run it on a
different Linux distribution, a different Yosys build, or macOS. The Yosys here
is a dirty git build (`0.67+94`, sha1 `7defa5186-dirty`), so an exact-version
match from a release tarball is not achievable and version sensitivity is
untested.

**The archival experiments still do not run from a clone.** The scripts under
`experiments/openroad_repair/`, `openroad_flat/`, `openroad_cts/`,
`max_fanout/`, `buffering_control/`, `drrtl_transfer/` and `llm_proposer_v3/`
no longer hard-code the repo path, but they read intermediate netlists from
`$HOME/flatexp/`, `$HOME/or_repair/` and `$HOME/bufexp/`, which are earlier
stages' outputs and hundreds of megabytes. Their **results** are committed;
their **runs** would need the chain re-run from the start. `SETUP.md` says
which is which, because a reviewer should know that up front rather than
discover it.

**Two clones, twice.** Run once on `ab453d5` and again on `9d1e780`, both
12 of 12 (`results/clean_clone_2026-09-05.log` and `..._rerun.log`). That is
still two observations, not a CI job. It will rot the next time someone adds a
script with a path in it, and nothing here prevents that.

**One failure worth recording, and it was the harness rather than the repo.**
The first attempt at the second run died with a syntax error at line 10,
because `clone_and_check.sh` was edited while bash was part-way through
reading it, and bash parses scripts incrementally rather than up front. The
script was valid before and after. A run that fails for a reason that has
nothing to do with what it is testing still gets written down, because the
alternative is a directory of results that only ever went well.
