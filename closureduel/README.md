# ClosureDuel

**A pre-registered head-to-head on RTL timing closure: LLM agents against a
design-class-aware classical optimizer, on an open stack** (Yosys, OpenSTA,
OpenROAD, sky130hd).

Started as a benchmark. The prior-art check ([`PRIOR_ART.md`](PRIOR_ART.md))
found that CLOSER-Bench, PostEDA-Bench, PDAgent-Bench and SynAct already cover
most of that ground (verdict: partially covered), and that none of the
open-stack ones has an arm that uses no LLM at all. That arm, run properly,
is the contribution; the reasoning is in [`VISION.md`](VISION.md).

## Status

| Part | State |
|---|---|
| Spec, pre-registration, power analysis | done |
| Container (pinned image, toolchain stamped) | built and verified, [`docker/VERIFIED.md`](docker/VERIFIED.md) |
| Classical arms C0 to C5, 10 development designs | **run and scored** |
| Second equivalence checker (PDR) | amendment 2 controls failed; amendment 3 registered, not run |
| LLM agent arms | not built |
| 5 holdout designs | sealed; no arm has run on them |

## Classical results

From [`results/RESULTS_classical.md`](results/RESULTS_classical.md), which the
scorer generates from the raw rows. 820 evaluations and 400 equivalence
checks; every candidate byte-identical across two runs. No void condition
triggered. **7 of 11 registered predictions correct**; the 4 wrong ones are
listed there under their own heading.

| Arm | Designs closed, of 10 |
|---|---|
| C0 null | 0 |
| C1 `repair_design` (unplaced) | 3 |
| C2 buffer-only | 1 |
| C3 sizing-only | 5 |
| C4 classifier-routed | 5 |
| C5 random, median of 10 seeds | 5 (range 4 to 5) |

A candidate counts as closed only if WNS >= 0 **and** it is proven equivalent
to the baseline. That legality gate sets the ranking more than timing does:
of 189 lever candidates not proven, 175 contain `buffer`, and 126 of the 140
sizing-only candidates are proven. Ignoring legality, C1 reaches WNS >= 0 on
7 designs and C2 on 3. So C4's routing between buffering and sizing is not yet
testable: in the registered result it fell back to sizing everywhere except
one design.

One buffered case is diagnosed. On aes with `buffer`, the registered checker
proves 1,408 of 1,409 outputs, and PDR proves the remaining output (`o_done`)
in 29 s ([`results/diag_aes_buffer.json`](results/diag_aes_buffer.json)).
That points to checker limits rather than broken netlists, for that one case.

## Files

| File | What it holds |
|---|---|
| [`VISION.md`](VISION.md) | the question, the decision to pivot, the name history |
| [`PRIOR_ART.md`](PRIOR_ART.md) | the closest work and what each leaves open |
| [`SPEC.md`](SPEC.md) | arms, metric, design tiers, holdout, reproducibility, power |
| [`PREREGISTRATION.md`](PREREGISTRATION.md) | predictions and void conditions, committed before any arm code, and three dated amendments |
| [`results/POWER.md`](results/POWER.md) | trials an agent arm needs, as a function of its spread |
| `arms/` | the runner, scorer, equivalence-gate test and the two extra checkers |
| `docker/` | the image definition, toolchain stamp and smoke test |

## Reproduce

Needs Docker and a clone of `github.com/hkust-zhiyao/Dr_RTL` at commit
`8d86c0e`, placed beside this repository (or pointed to by `DR_RTL`).
From the repository root:

```bash
docker build -f closureduel/docker/Dockerfile -t closureduel:dev .
bash closureduel/arms/run.sh --jobs 8 --cec-jobs 6
python3 closureduel/arms/score.py
python3 closureduel/power/power.py
```

`run.sh` refuses to start with uncommitted harness changes or a Dr_RTL clone
off the pinned commit, and records the harness commit on every row. The run is
resumable.

## Designs and licence

The designs come from Dr. RTL (HKUST) and **are not included here**. That
repository carries no licence, so ClosureDuel is not released as a benchmark
until the design set has one (`SPEC.md`, "Release blocker"). This directory
holds only the harness, design names, hashes and measured numbers.
