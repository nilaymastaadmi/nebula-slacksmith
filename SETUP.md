# Setup, and what is actually reproducible

Written 2026-09-05, after discovering that every script in this repo began with
`cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark`. The numbers in
`REPORT.md` were reproducible in principle and runnable on exactly one machine.
This file, `tools/env.sh` and `tools/preflight.sh` fix that, and this section
is honest about the parts they do not fix.

## Quick start

```
git clone <repo> && cd slacksmith-benchmark
bash tools/preflight.sh      # names every missing dependency and where to get it
bash tools/demo_check.sh     # runs all 8 demo beats, 12 assertions, ~2 min
```

Clone it, do not download a zip. Beat 4 checks that the pre-registration commit
precedes the proposals commit, which needs git history.

## Dependencies

Every path below is an environment variable with a default. Override the
variable, do not edit a script.

| variable | default | what it is |
|---|---|---|
| `OSS_CAD_BIN` | `~/tools/oss-cad-suite/bin` | yosys, yosys-abc, eqy, sby, iverilog, vvp |
| `STA_BIN` | `~/tools/OpenSTA/build/sta` | OpenSTA, built from source |
| `LIBERTY` | `~/sta_work/sky130hd_tt.lib` | SKY130 HD typical corner |
| `OPENROAD_BIN` | `~/or_env/bin/openroad` | OpenROAD, only for the physical levers and G6 |
| `ORFS_PLATFORM` | `~/orfs/flow/platforms/sky130hd` | OpenROAD-flow-scripts platform files |
| `SLACKSMITH_WORK` | `~/slacksmith_work` | all scratch output |
| `REPO` | derived from `tools/env.sh` | repo root; you should never need to set this |

`demo_check.sh` needs the first three. OpenROAD is optional for it.

### Versions used for the committed results

Measured on this machine 2026-09-05, not copied from documentation:

- Yosys 0.67+94 (git sha1 7defa5186-dirty, Clang 18.1.8)
- Icarus Verilog 14.0 (devel) (s20260301-322-ga4989d023-dirty)
- Python 3.12.3
- eqy, sby, yosys-abc: the builds shipped in the same OSS CAD Suite bundle
- OpenSTA and OpenROAD: built from source, versions not stamped in the binaries

Yosys is a dirty git build, so an exact-version match is not achievable from a
release tarball. Nothing here depends on a version-specific behaviour we know
of, but that is an expectation, not a measurement.

### The liberty file

`LIBERTY` is `sky130_fd_sc_hd__tt_025C_1v80.lib`, 428 cells, 12,800,126 bytes.

It is **not committed**: 12.8 MB, 2.2 MB compressed, against a 6.6 MB repo.
The copy used here came from an OpenLane/SkyWater distribution and differs from
the one OpenROAD-flow-scripts ships at
`$ORFS_PLATFORM/lib/sky130_fd_sc_hd__tt_025C_1v80.lib` by **9 bytes across two
hunks**: `default_fanout_load : 1.0;` against `1.0000000000;`, and
`default_operating_conditions : "tt_025C_1v80";` declared at line 37 in one and
line 173,158 in the other. Same library name, same 428 cells, no difference in
the cell list.

**Use the ORFS copy if you have it, and that is measured rather than assumed.**
`tools/liberty_equivalence.sh` runs both against the same frozen netlist and
SDC: `clk_a 11.157918`, `clk_b 5.665101`, `clk_e -0.318779`, identical to six
decimal places on both. Output in `experiments/reproducibility/NOTES.md`.

## What is reproducible from a clean clone, and what is not

**Reproducible now:** everything `tools/demo_check.sh` runs. That is the closed
loop on v2 (live compute), the three replayed v3 logs, the registration
ordering, the verdict regression, the SDC-integrity result, the SlackBench
exam, and the classifier regression. 12 assertions.

The SDC-integrity netlist (flat arm E, 26,958 cells) is now committed at
`experiments/sdc_integrity/flat_E_mapped.v.gz`, 387 KB, sha256 `80686092…`.
It was previously only in the author's home directory, which meant the single
most quotable claim in the project ("byte-identical netlist") could not be
checked by anyone else.

**Not reproducible from a clean clone:** the archival experiment scripts under
`experiments/*/run.sh` for `openroad_repair`, `openroad_flat`, `openroad_cts`,
`max_fanout`, `buffering_control`, `drrtl_transfer` and `llm_proposer_v3`.
They no longer hard-code the repo path, but they read intermediate netlists
from `$HOME/flatexp/`, `$HOME/or_repair/`, `$HOME/bufexp/` and
`$HOME/drrtl_run/`, which are the outputs of earlier stages in the same chain
and are hundreds of megabytes in total. Running the chain from the start
regenerates them. Their **results are committed** under each experiment's
`results/` and `NOTES.md`, so the record is checkable even where the run is
expensive to repeat.

This is stated rather than hidden. A reader should know which claims they can
re-derive in two minutes and which would cost them an afternoon of synthesis.

## Logs keep their absolute paths

Files under `*/results/` and `*/logs/` still contain
`/mnt/c/Users/toshn/...`. That is deliberate: they are records of runs that
actually happened at that path. Rewriting them would be falsifying evidence to
make a directory listing look tidier.
