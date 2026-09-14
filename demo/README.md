# The interactive demo

Organizer deliverable 7. `explorer.html` is a single self-contained page: no
server, no network, no dependencies. Open it in a browser.

    python3 demo/build.py     # regenerate from the logs
    # then open demo/explorer.html

**It is generated, not written.** `build.py` reads
`experiments/closed_loop/*.jsonl`, `experiments/llm_proposer/proposals/*.json`
and `experiments/slackbench/results/raw.tsv` at build time, so the page cannot
drift from the runs it claims to show. Change a log, rebuild, the page changes.

## What is on it

| tab | what a judge can do |
|---|---|
| **The loop** | Pick one of five committed runs and read down it. Every iteration shows the slack per clock and the delta, then the classifier's verdict **with the evidence table it decided on**: instance path, cell, incremental delay, fanout. A routing decision you disagree with can be argued with. |
| **The gate** | Six LLM-proposed transforms, frozen in git before any check ran. Declared type, selected obligation, G1 to G4. The two refuted ones expand to the solver's counterexample, including P4's `a=ae19f605, shamt=7`, gold `ff5c33ec` against gate `015c33ec`. |
| **The exam** | SlackBench as a confusion matrix. `CANNOT` is coloured as its own answer rather than as a failure, circular cells are marked excluded, and **our own two checkers are labelled as ours** so the two cells where we are wrong are not hidden in the middle of the table. |
| **The cheat** | The one result no equivalence checker can catch: `clk_e` from −0.319 to +4.860, worth +5.179 ns, on a byte-identical 26,958-cell netlist. |

## What it is not

**It replays committed logs. It does not run the flow.** Clicking a run does
not synthesize anything; the numbers were produced by
`tools/slacksmith.py` when that run happened and are read back here. The live
compute is beat 2 of `DEMO.md`, which takes a median **112.7 s** on one core (five protocol runs, 83.9 to 152.7 s; 47 to 833 s outside the protocol; `experiments/loop_runtime/`) and is real.

The default run selected on load is v2, the one that goes well. The other four
include the run that reverts three formally proven transforms and the run kept
deliberately because its defects are reported in section 9.
