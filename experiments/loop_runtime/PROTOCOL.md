# Loop runtime, measured under stated conditions

Written and committed before the first run.

## Why

`REPORT.md` §1.1 and §7.3 quote **46.7 s** as the closed loop's end-to-end cost
on SDC v2. That is one wall clock, `run_v2.jsonl`, 2026-09-03. The same command
has since measured 93.88 s and 367.8 s (`demo/PHASE1_CUT.md`, finding 1),
832.8 s (`demo/takes/beat2_timing.txt`) and 74.98 s (review 5, inside
`tools/demo_check.sh`), all on 2026-09-13 on the same machine. A single wall
clock on a shared machine is an observation about that machine at that moment,
not a cost of the loop.

## Protocol

- **Command:** `DEMO.md` beat 2, exactly as `tools/demo_check.sh` runs it: SDC v2,
  `--engine sta`, clocks `clk_a`, `clk_b`, `clk_e`. A fresh work directory per
  run, because `PHASE1_CUT.md` finding 3 found `~/demo_run` accumulating across
  runs.
- **N = 5**, sequential. No warm-up run is discarded. Every run is reported. No
  run is repeated or dropped for any reason; a run that does not close is
  reported as a failure with its time.
- **Recorded per run:** start time (UTC), wall seconds, user and system CPU
  seconds of the process and its children (`/usr/bin/time`), the WSL one-minute
  load average before and after, `nproc`, the top processes by CPU at the start,
  and whether the output contains `ALL REPORTED GROUPS MEET`.
- **Reported:** median and range of wall seconds, and median and range of CPU
  seconds (user plus system). CPU seconds depend less on what else the machine
  is doing, so they are the better estimate of what the loop itself costs.
- **Not controlled:** Windows-side processes and any other session's work. The
  load average is recorded so a slow run can be attributed, not so it can be
  excluded.

## Files

- `run.sh`, the harness.
- `results/runs.tsv`, one row per run; `results/summary.txt`, generated from it.
- `results/run<N>.log`, each run's full output; `results/ps_before_run<N>.txt`.
