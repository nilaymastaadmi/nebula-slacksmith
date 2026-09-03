#!/usr/bin/env python3
"""Score PREREGISTRATION_flat.md (runs 6 and 7, predictions 29 to 33).

    python3 score_flat.py run_v3_flat.jsonl run_v3_flatpi.jsonl
"""
import sys

from score_verdict import load, trajectory, final_slacks, iterations


def measures(log):
    return {r["iter"]: r["slacks"] for r in log if r.get("step") == "measure"}


def classifies(log):
    return {(r["iter"], r["clock"]): r for r in log if r.get("step") == "classify"}


def main(p6, p7):
    r6, r7 = load(p6), load(p7)
    for name, log in (("run 6", r6), ("run 7", r7)):
        print(f"{name}: {log[0].get('flatten')=} {log[0].get('buffer_pi')=}")
        for it, s, txt in trajectory(log):
            print(f"  it{it} {s:9s} {txt}")
    m, c = measures(r6), classifies(r6)
    ok = lambda b: "CORRECT" if b else "WRONG"
    p29 = m.get(1) == {"clk_a": 9.279, "clk_b": -4.065, "clk_e": -15.762} and \
        c.get((1, "clk_e"), {}).get("verdict") == "FANOUT_DOMINATED" and \
        abs(c.get((1, "clk_e"), {}).get("fanout_delay_share", 0) - 0.9547) < 1e-4
    print(f"\nP29 it1 = arm C, clk_e FANOUT 0.9547: {ok(p29)} ({m.get(1)}, {c.get((1,'clk_e'),{}).get('verdict')} {c.get((1,'clk_e'),{}).get('fanout_delay_share')})")
    conf = [(r["iter"], r.get("component")) for r in r6 if r.get("step") == "confirm"]
    p30 = m.get(2) == {"clk_a": 10.362, "clk_b": 5.665, "clk_e": -0.613} and (2, "buffer") in conf and \
        c.get((2, "clk_e"), {}).get("verdict") == "MIXED" and abs(c.get((2, "clk_e"), {}).get("fanout_delay_share", 0) - 0.3221) < 1e-4
    print(f"P30 it2 = arm D, buffer confirmed, clk_e MIXED 0.3221: {ok(p30)} ({m.get(2)}, confirms {conf})")
    p31 = m.get(3) == {"clk_a": 11.158, "clk_b": 5.665, "clk_e": -0.319} and (3, "size") in conf
    print(f"P31 it3 = arm E, sizing CONFIRMED: {ok(p31)} ({m.get(3)})")
    stops = [r for r in r6 if r.get("step") == "stop"]
    gates = [r for r in r6 if r.get("step") == "gate"]
    p32 = bool(stops) and stops[-1]["reason"] == "physical_exhausted" and iterations(r6) == 3 and not gates \
        and final_slacks(r6) == {"clk_a": 11.158, "clk_b": 5.665, "clk_e": -0.319}
    print(f"P32 stop physical_exhausted at it3, no gate, final +11.158/+5.665/-0.319: {ok(p32)} "
          f"(stop {stops[-1]['reason'] if stops else None}, iterations {iterations(r6)}, gates {len(gates)}, final {final_slacks(r6)})")
    f6, f7 = final_slacks(r6), final_slacks(r7)
    print(f"P33 run 7 clk_e above run 6's {f6.get('clk_e')}: {ok(f7.get('clk_e', -99) > f6.get('clk_e', 0))} (run 7 {f7})")
    same = [r["slacks"] for r in r6 if r.get("step") == "measure"] == [r["slacks"] for r in r7 if r.get("step") == "measure"]
    print(f"run 7 measurements identical to run 6: {same}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
