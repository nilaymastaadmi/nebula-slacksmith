#!/usr/bin/env python3
"""Score PREREGISTRATION_verdict_lever.md against two decisions.jsonl logs.

    python3 score_verdict.py run_v3_final.jsonl run_v3_verdict.jsonl

Prints both trajectories side by side, then the five registered predictions
with their outcome read straight from the treatment log. No thresholds are
tuned here; the numbers quoted in the registration are repeated verbatim.
"""
import json
import sys

CLOCKS = ("clk_a", "clk_b", "clk_e")


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def trajectory(log):
    rows = []
    for r in log:
        it = r.get("iter")
        s = r.get("step")
        if s == "measure":
            sl = r["slacks"]
            rows.append((it, "measure", "  ".join(f"{c}={sl.get(c)}" for c in CLOCKS)))
        elif s == "classify":
            rows.append((it, "classify", f"{r.get('clock')} {r.get('verdict')} "
                                        f"share={r.get('fanout_delay_share')} -> {r.get('lever')}"))
        elif s == "apply":
            what = r.get("component") or r.get("proposal") or r.get("lever")
            rows.append((it, "apply", f"{r.get('lever')} {what}"
                                     + (" (provisional)" if r.get("provisional") else "")))
        elif s in ("confirm", "revert"):
            what = r.get("component") or r.get("proposal")
            rows.append((it, s, f"{what} {r.get('clock')} {r.get('before')} -> {r.get('after')}"))
        elif s == "stop":
            rows.append((it, "stop", r.get("reason")))
        elif s == "done":
            rows.append((it, "done", r.get("reason") or json.dumps(r.get("slacks"))))
        elif s == "gate":
            rows.append((it, "gate", f"{r.get('proposal')} G3={r.get('G3')} G4={r.get('G4')}"))
    return rows


def final_slacks(log):
    m = [r for r in log if r.get("step") == "measure"]
    return m[-1]["slacks"] if m else {}


def iterations(log):
    return max((r.get("iter") or 0) for r in log)


def main(base_path, treat_path):
    base, treat = load(base_path), load(treat_path)
    print(f"baseline  {base_path}")
    for it, s, txt in trajectory(base):
        print(f"  it{it} {s:9s} {txt}")
    print(f"\ntreatment {treat_path}")
    for it, s, txt in trajectory(treat):
        print(f"  it{it} {s:9s} {txt}")

    fb, ft = final_slacks(base), final_slacks(treat)
    print("\nfinal slack   " + "  ".join(f"{c}: blunt {fb.get(c)} / verdict {ft.get(c)}" for c in CLOCKS))

    applies = [r for r in treat if r.get("step") == "apply" and r.get("lever") == "physical"]
    reverts = [r for r in treat if r.get("step") == "revert" and r.get("lever") == "physical"]
    classify = {(r["iter"], r["clock"]): r for r in treat if r.get("step") == "classify"}

    # P1 as written: clk_b at or above 0 after the first buffer-only step,
    # whichever group that step targeted (amendment 1: the step targets clk_e).
    after_buf = None
    for r in applies:
        if r.get("component") == "buffer":
            nxt = [m for m in treat if m.get("step") == "measure" and m["iter"] > r["iter"]]
            if nxt:
                after_buf = (r.get("clock"), nxt[0]["slacks"])
            break
    p1 = after_buf is not None and after_buf[1].get("clk_b", -1) >= 0
    print(f"\nP1 clk_b closes with buffer-only alone: "
          f"{'CORRECT' if p1 else 'WRONG'} (first buffer-only step targeted "
          f"{after_buf[0] if after_buf else None}; slacks after = {after_buf[1] if after_buf else None})")
    if after_buf:
        e = after_buf[1].get("clk_e")
        print(f"   unregistered: clk_e after buffer-only = {e} "
              f"({'closed' if e is not None and e >= 0 else 'not closed'}; blunt run ended at -0.606)")

    # P2: clk_a after its first physical step is better than -1.716.
    clk_a_first = None
    for r in applies:
        if r.get("clock") == "clk_a":
            nxt = [m for m in treat if m.get("step") == "measure" and m["iter"] > r["iter"]]
            if nxt:
                clk_a_first = (r.get("component"), nxt[0]["slacks"].get("clk_a"))
            break
    p2 = clk_a_first is not None and clk_a_first[1] > -1.716
    print(f"P2 clk_a after first physical step better than -1.716: "
          f"{'CORRECT' if p2 else 'WRONG'} (step={clk_a_first})")

    # P3: at least one physical step reverted.
    print(f"P3 at least one physical step reverted: "
          f"{'CORRECT' if reverts else 'WRONG'} ({len(reverts)} reverted: "
          f"{[(r['component'], r['clock'], r['before'], r['after']) for r in reverts]})")

    # P4: no more iterations than the blunt run.
    ib, itr = iterations(base), iterations(treat)
    print(f"P4 iterations <= blunt: {'CORRECT' if itr <= ib else 'WRONG'} "
          f"(blunt {ib}, verdict {itr})")

    # P5: never buffer-only on a DEPTH group.
    bad = [r for r in applies if r.get("component") == "buffer"
           and classify.get((r["iter"], r["clock"]), {}).get("verdict") == "DEPTH_DOMINATED"]
    print(f"P5 never buffer-only on DEPTH_DOMINATED: "
          f"{'CORRECT' if not bad else 'WRONG'} ({len(bad)} violations)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
