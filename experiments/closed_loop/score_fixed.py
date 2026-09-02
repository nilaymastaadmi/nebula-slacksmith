#!/usr/bin/env python3
"""Score PREREGISTRATION_classifier_fixed.md (predictions 10 to 14).

    python3 score_fixed.py run_v3_g5total.jsonl run_v3_fixed.jsonl
"""
import sys

from score_verdict import load, trajectory, final_slacks, iterations


def main(base_path, treat_path):
    base, treat = load(base_path), load(treat_path)
    print(f"treatment {treat_path} (corrected classifier, verdict policy, --g5 total)")
    for it, s, txt in trajectory(treat):
        print(f"  it{it} {s:9s} {txt}")

    cls = [r for r in treat if r.get("step") == "classify"]
    it2 = [r for r in cls if r["iter"] == 2 and r["clock"] == "clk_e"]
    p10 = bool(it2) and it2[0]["verdict"] == "MIXED" and abs(it2[0]["fanout_delay_share"] - 0.286) < 0.001
    print(f"\nP10 it2 clk_e MIXED at 0.286: {'CORRECT' if p10 else 'WRONG'} "
          f"({(it2[0]['verdict'], it2[0]['fanout_delay_share']) if it2 else None})")
    stops = [r for r in treat if r.get("step") == "stop"]
    p11 = bool(stops) and stops[-1].get("reason") == "physical_exhausted"
    print(f"P11 stops physical_exhausted: {'CORRECT' if p11 else 'WRONG'} ({stops[-1].get('reason') if stops else None})")
    gates = [r for r in treat if r.get("step") == "gate"]
    print(f"P12 RTL lever never fires: {'CORRECT' if not gates else 'WRONG'} ({len(gates)} gate records)")
    ft, fb = final_slacks(treat), final_slacks(base)
    p13 = ft == fb and iterations(treat) == 4
    print(f"P13 final identical to run 4 in 4 iterations: {'CORRECT' if p13 else 'WRONG'} "
          f"(final {ft}, run 4 {fb}, iterations {iterations(treat)})")
    it1 = [r for r in cls if r["iter"] == 1]
    p14 = bool(it1) and it1[0]["verdict"] == "FANOUT_DOMINATED" and abs(it1[0]["fanout_delay_share"] - 0.9139) < 1e-4
    print(f"P14 it1 clk_e FANOUT_DOMINATED at 0.9139: {'CORRECT' if p14 else 'WRONG'} "
          f"({(it1[0]['verdict'], it1[0]['fanout_delay_share']) if it1 else None})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
