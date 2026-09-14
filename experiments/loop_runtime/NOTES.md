# Loop runtime: results

Protocol committed first (`0850521`). Five sequential runs of `DEMO.md` beat 2,
2026-09-13, 14:52 to 15:02 UTC, fresh work directory each, none dropped.

| run | wall s | CPU s (user+sys) | load1 before | closes |
|---|---|---|---|---|
| 1 | 118.89 | 118.65 | 0.83 | yes |
| 2 | 112.70 | 112.79 | 0.98 | yes |
| 3 | 152.67 | 152.06 | 1.00 | yes |
| 4 | 108.76 | 109.01 | 1.00 | yes |
| 5 | 83.92 | 84.14 | 1.04 | yes |

`results/summary.txt`: **5 of 5 closed; wall median 112.7 s, range 83.9 to
152.7 s; CPU median 112.8 s, range 84.1 to 152.1 s.** `nproc` 16.

## What this shows

- **The loop is single-threaded and CPU-bound.** CPU seconds equal wall seconds
  in every run to within 0.3 s, and the load average sits at about 1.0 on 16
  cores, which is the loop itself.
- **The spread is not other WSL processes.** With nothing else running in WSL,
  CPU seconds still vary 1.8x across five identical runs. The protocol expected
  CPU seconds to be steadier than wall seconds; **that expectation was wrong**:
  they vary together. What does vary is not measured here: Windows-side
  contention for the VM's cores, and CPU frequency or thermal state.
- **46.7 s is below this whole range** and is not explained by this
  measurement. It is `run_v2.jsonl`, committed 2026-09-01 in `4d5eaa8`, and
  `tools/slacksmith.py`, `classify_path.py` and `remeasure.py` have 29 commits
  since, so the two timings are not of the same program. That is a candidate
  explanation, not a finding.

## Outside the protocol

The same command, timed on this machine on other occasions. None is part of
the registered five, and none was controlled for load.

| wall s | when | source |
|---|---|---|
| 46.7 | committed 2026-09-01 | `experiments/closed_loop/run_v2.jsonl`, a program 29 commits older |
| 93.88, 367.8 | 2026-09-13 | `demo/PHASE1_CUT.md` finding 1 |
| 832.8 | 2026-09-13 | `demo/takes/beat2_timing.txt` |
| 74.98 | 2026-09-13 | review 5, inside `demo_check`, `REVIEW_RESULT_2026-09-13_r5.md` |
| 60.94 | 2026-09-13 | review 6, inside `demo_check`, `REVIEW_RESULT_2026-09-13_r6.md` |

Three of these (46.7, 74.98 and 60.94 s) are below the protocol's 83.9 s, so **83.9 to 152.7 s is the
spread of one ten-minute window, not the bounds of what the loop takes.** The
report quotes the median and gives 47 to 833 s as the out-of-protocol spread.

## What the report may say

The loop's cost on this machine is **a median of 112.7 s on one core** across the
five protocol runs, dominated by synthesis. The protocol's 83.9 to 152.7 s and the
out-of-protocol 47 to 833 s are both stated as spreads; neither is quoted as the
cost, and no single wall clock is.
