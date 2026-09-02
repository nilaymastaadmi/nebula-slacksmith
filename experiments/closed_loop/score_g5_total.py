#!/usr/bin/env python3
"""Score PREREGISTRATION_g5_total.md (predictions 6 to 9).

    python3 score_g5_total.py run_v3_verdict.jsonl run_v3_g5total.jsonl

The first log is the verdict-policy run with the per-group bar (the baseline
named in the registration); the second is the same policy with --g5 total.
"""
import json
import sys

from score_verdict import load, trajectory, final_slacks, iterations

CLOCKS = ("clk_a", "clk_b", "clk_e")


def total(sl):
    return round(sum(min(v, 0.0) for v in sl.values() if v is not None), 3)


def main(base_path, treat_path):
    base, treat = load(base_path), load(treat_path)
    print(f"baseline  {base_path} (verdict policy, --g5 target)")
    for it, s, txt in trajectory(base):
        print(f"  it{it} {s:9s} {txt}")
    print(f"\ntreatment {treat_path} (verdict policy, --g5 total)")
    for it, s, txt in trajectory(treat):
        print(f"  it{it} {s:9s} {txt}")
    for r in treat:
        if r.get("step") == "g5_total":
            print(f"  it{r['iter']} g5_total  {r['total_before']} -> {r['total_after']} "
                  f"{'improved' if r['improved'] else 'NOT improved'}")

    reverts = [r for r in treat if r.get("step") == "revert"]
    stops = [r for r in treat if r.get("step") in ("stop", "done")]
    fb, ft = final_slacks(base), final_slacks(treat)

    # P6: the sizing step is reverted.
    p6 = any(r.get("lever") == "physical" and r.get("component") == "size" for r in reverts)
    print(f"\nP6 sizing step reverted: {'CORRECT' if p6 else 'WRONG'} "
          f"({[(r.get('component') or r.get('proposal'), r['before'], r['after']) for r in reverts]})")

    # P7: stops with no_proposal_on_path, worst group clk_e.
    last_stop = stops[-1] if stops else {}
    last_cls = [r for r in treat if r.get("step") == "classify"]
    p7 = (last_stop.get("reason") == "no_proposal_on_path"
          and bool(last_cls) and last_cls[-1].get("clock") == "clk_e"
          and last_cls[-1].get("verdict") == "DEPTH_DOMINATED")
    print(f"P7 stops no_proposal_on_path on clk_e DEPTH: {'CORRECT' if p7 else 'WRONG'} "
          f"(stop={last_stop.get('reason')}, last classify="
          f"{(last_cls[-1].get('clock'), last_cls[-1].get('verdict')) if last_cls else None}, "
          f"binding_modules={last_stop.get('binding_modules')})")

    # P8: final state clk_a +1.75, clk_b +5.556, clk_e -1.444, <= 4 iterations.
    want = {"clk_a": 1.75, "clk_b": 5.556, "clk_e": -1.444}
    p8 = all(abs(ft.get(c, 99) - want[c]) < 1e-9 for c in CLOCKS) and iterations(treat) <= 4
    print(f"P8 final {want} in <= 4 iterations: {'CORRECT' if p8 else 'WRONG'} "
          f"(final {ft}, iterations {iterations(treat)})")

    # P9: final total -1.444 vs baseline -2.322.
    tb, tt = total(fb), total(ft)
    p9 = tt == -1.444 and tb == -2.322
    print(f"P9 final total {tt} vs baseline {tb}: {'CORRECT' if p9 else 'WRONG'}")
    print(f"\ngroups violating at the end: baseline {sum(1 for c in CLOCKS if fb.get(c, 0) < 0)}, "
          f"treatment {sum(1 for c in CLOCKS if ft.get(c, 0) < 0)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
