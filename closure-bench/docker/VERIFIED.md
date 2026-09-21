# Container verification record

Phase 3 step 1: "verify by running one design end to end inside the container
before writing anything else." Run 2026-09-21 on Docker 29.8.1 in WSL Ubuntu
24.04, image `closure-bench:dev` built from
`openroad/orfs:26Q3-600-g3a964e13f@sha256:7fbb16f7...deee9`.

## Result

| | Committed row | Host rerun | Container |
|---|---|---|---|
| design | ticket_machine | ticket_machine | ticket_machine |
| mapped cells | 18 | 18 | 18 |
| required ns | 0.791 | 0.791 | 0.791 |
| period ns | 0.712 | 0.712 | 0.712 |
| slack ns | -0.080 | -0.080 | -0.080 |
| Yosys | 0.67+94 `7defa5186-dirty` | same | 0.68 `38e001a6f` |
| OpenSTA | standalone | standalone | embedded in OpenROAD |

Identical on every measured field across three toolchain configurations.

## Controls, each run through the real invocation path

| Check | Expected | Got |
|---|---|---|
| holdout design `arm_cpu2` | refused, exit 4 | exit 4 |
| no designs mounted | fail loudly, exit 3, no number | exit 3 |
| same design twice | byte-identical output | identical, 308 bytes |
| exact `RUN` line under `/bin/sh`, broken liberty | build step fails | exit 3 |
| the old `\| tee` line, same breakage | (the bug) | exit 0 - reproduced |
| bad tech LEF | halt, exit 3, no label | `STA_READ_FAIL`, exit 3 |
| `STA_ERROR` branch vs the literal `ORD-2010` text | `STA_ERROR` | `STA_ERROR` |

## The liberty files differ as bytes and not as timing data

Host `sky130hd_tt.lib` (sha256 `70a45bf9...`, 12,800,126 bytes) against the
image's `sky130_fd_sc_hd__tt_025C_1v80.lib` (sha256 `ec0e1067...`,
12,800,135 bytes): 428 cells each, 173,160 lines each, **6 differing lines**.
`default_fanout_load` is written `1.0` in one and `1.0000000000` in the other,
and `default_operating_conditions` sits at a different position in the library
group. No timing table differs. Host numbers are comparable to container
numbers on the liberty axis.

## Two defects the first build hid, both fixed

1. **`| tee` under `/bin/sh` masked a failing stamp.** `/bin/sh` has no
   `pipefail`, so the pipeline reported `tee`'s status. The first build passed
   and baked a **0-byte** `TOOLCHAIN.txt`. Now redirect-then-`cat`.
2. **`X=$(_find_tool x)` under `set -e` aborted silently on a miss.** The
   function returned the loop's last status (1), so the stamp died at the
   `sta` lookup before its fallback or its fatal message could run - which is
   why the build log showed no output at all rather than an error. Now returns 0.

A third defect surfaced on the first container run: the OpenROAD fallback was
documented as accepting "the same Tcl" as standalone OpenSTA, which was never
tested, and it does not (`ORD-2010 no technology has been read` until LEFs are
loaded). The script labelled that tool error `NO_PATH` on a design whose
register path had just been measured. Fixed twice over: LEFs are loaded on the
OpenROAD path, and any unrecognised tool error or unexplained missing slack now
halts with exit 3 instead of producing a label.

## Limits of this verification

- **One design, and the smallest one** (18 cells, 6 flops). Identical numbers
  here do not show the two toolchains agree on the other nine development
  designs. That is the next check, and it may not come back identical.
- **`repair_design` was not exercised.** OpenROAD 2022 vs 2026 matters for the
  classical baseline, and nothing here touches it.
- **OpenROAD prints its version as "unknown".** The image digest is the only
  pin for it; `TOOLCHAIN.txt` cannot carry a version string.
- Determinism is shown for the null flow on one design across two runs, not
  for any agent and not across machines.
