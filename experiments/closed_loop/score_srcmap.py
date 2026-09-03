#!/usr/bin/env python3
"""Score PREREGISTRATION_srcmap.md (run 8, predictions 39 and 40).

    python3 score_srcmap.py run_v3_flat.jsonl run_v3_srcmap.jsonl
"""
import sys

from score_verdict import load, trajectory, final_slacks, iterations


def key(log):
    """The trajectory facts P39 compares: measurements, confirms, stop."""
    return ([r["slacks"] for r in log if r.get("step") == "measure"],
            [(r["iter"], r.get("component")) for r in log if r.get("step") == "confirm"],
            [r.get("reason") for r in log if r.get("step") == "stop"])


def main(base_path, treat_path):
    base, treat = load(base_path), load(treat_path)
    print(f"run 8 {treat_path}")
    for it, s, txt in trajectory(treat):
        print(f"  it{it} {s:9s} {txt}")

    ok = lambda b: "CORRECT" if b else "WRONG"
    p39 = key(base) == key(treat) and iterations(base) == iterations(treat)
    print(f"\nP39 run 8 reproduces run 6's trajectory: {ok(p39)}")
    if not p39:
        print(f"    run 6: {key(base)}")
        print(f"    run 8: {key(treat)}")

    cls_b = {(r["iter"], r["clock"]): r for r in base if r.get("step") == "classify"}
    cls_t = {(r["iter"], r["clock"]): r for r in treat if r.get("step") == "classify"}
    named, differs = [], []
    for k, r in sorted(cls_t.items()):
        mods_t = [c.get("module") for c in r.get("top_cells", [])]
        mods_b = [c.get("module") for c in cls_b.get(k, {}).get("top_cells", [])]
        print(f"  it{k[0]} {k[1]}: run 8 {mods_t}   run 6 {mods_b}")
        named += [m for m in mods_t if m and m != "bench_top"]
        if mods_t != mods_b:
            differs.append(k)
    print(f"P40 at least one real module named, and attribution differs from "
          f"run 6: {ok(named and differs)} (named {sorted(set(named))}, "
          f"records that changed {differs})")
    print(f"\nfinal state run 6 {final_slacks(base)}  run 8 {final_slacks(treat)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
