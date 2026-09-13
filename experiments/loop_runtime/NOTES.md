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

## What the report may say

The loop's cost on this machine is **about two minutes, 84 to 153 s across five
runs (median 113 s)**, dominated by synthesis on one core. One wall clock is not
quoted as the cost.
