#!/usr/bin/env python3
"""Re-score phase 1 and phase 3 statistics on the corrected verdicts
(PREREGISTRATION.md amendment 4). Reads the committed result tables; nothing
is re-measured. Prints the original grouping and the corrected grouping side
by side, then scores predictions 15 to 18.

    python3 experiments/drrtl_transfer/rescore_corrected.py
"""
import csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))


def tsv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def med(xs):
    return round(statistics.median(xs), 3) if xs else None


def group(rows, verdict_of, gain_key, slack_key):
    out = {}
    for v in ("FANOUT_DOMINATED", "MIXED", "DEPTH_DOMINATED"):
        sel = [r for r in rows if verdict_of(r) == v]
        gains = [fnum(r[gain_key]) for r in sel if fnum(r[gain_key]) is not None]
        closes = sum(1 for r in sel if fnum(r[slack_key]) is not None and fnum(r[slack_key]) >= 0)
        worse = sum(1 for g in gains if g < 0)
        out[v] = (len(sel), med(gains), closes, worse)
    return out


def show(title, old, new):
    print(f"\n{title}")
    print(f"  {'verdict':<18} {'n':>3} {'median gain':>12} {'closes':>7} {'worse':>6}   |  {'n':>3} {'median gain':>12} {'closes':>7} {'worse':>6}")
    print(f"  {'':<18} {'original grouping':^32}   |  {'corrected grouping':^32}")
    for v in ("FANOUT_DOMINATED", "MIXED", "DEPTH_DOMINATED"):
        o, n = old[v], new[v]
        print(f"  {v:<18} {o[0]:>3} {str(o[1]):>12} {o[2]:>7} {o[3]:>6}   |  {n[0]:>3} {str(n[1]):>12} {n[2]:>7} {n[3]:>6}")


def main():
    corrected = {r["design"]: r for r in tsv(os.path.join(HERE, "results_reclassified", "summary.tsv"))}
    p1 = [r for r in tsv(os.path.join(HERE, "results", "summary.tsv")) if r["design"] in corrected]
    p3 = [r for r in tsv(os.path.join(HERE, "phase3", "results", "summary.tsv")) if r["design"] in corrected]

    changed = [(d, r["old_verdict"], r["new_verdict"], r["old_share"], r["new_share"])
               for d, r in corrected.items() if r["old_verdict"] != r["new_verdict"]]
    moved_share = [(d, r["old_share"], r["new_share"]) for d, r in corrected.items()
                   if r["old_share"] != r["new_share"]]
    print(f"designs re-classified: {len(corrected)}")
    print(f"verdicts changed: {len(changed)} {changed}")
    print(f"shares moved: {len(moved_share)} {moved_share}")

    old_v = lambda r: r["verdict"]
    new_v = lambda r: corrected[r["design"]]["new_verdict"]

    show("Phase 1: combined lever (buffer+size), gain = delta_B, closes = slack_B >= 0",
         group(p1, old_v, "delta_B", "slack_B"), group(p1, new_v, "delta_B", "slack_B"))
    show("Phase 3: buffer-only, gain = gain_buf, closes = slack_buf >= 0",
         group(p3, old_v, "gain_buf", "slack_buf"), group(p3, new_v, "gain_buf", "slack_buf"))
    show("Phase 3: sizing-only, gain = gain_size, closes = slack_size >= 0",
         group(p3, old_v, "gain_size", "slack_size"), group(p3, new_v, "gain_size", "slack_size"))

    # Predictions 15 to 18.
    order = {"DEPTH_DOMINATED": 0, "MIXED": 1, "FANOUT_DOMINATED": 2}
    toward_depth = [d for d, r in corrected.items() if order[r["new_verdict"]] < order[r["old_verdict"]]]
    print(f"\nP15 no verdict moves toward DEPTH: {'CORRECT' if not toward_depth else 'WRONG'} ({toward_depth})")
    tv = corrected.get("tv80", {})
    print(f"P16 tv80 changes from DEPTH_DOMINATED: "
          f"{'CORRECT' if tv.get('new_verdict') not in (None, 'DEPTH_DOMINATED') else 'WRONG'} "
          f"({tv.get('old_verdict')} -> {tv.get('new_verdict')}, share {tv.get('old_share')} -> {tv.get('new_share')})")
    depth_changed = [d for d, r in corrected.items()
                     if r["old_verdict"] == "DEPTH_DOMINATED" and r["new_verdict"] != "DEPTH_DOMINATED"]
    print(f"P17 at least 2 of 8 DEPTH verdicts change: "
          f"{'CORRECT' if len(depth_changed) >= 2 else 'WRONG'} ({len(depth_changed)}: {depth_changed})")
    depth_new = [r for r in p3 if new_v(r) == "DEPTH_DOMINATED"]
    gains = [fnum(r["gain_buf"]) for r in depth_new if fnum(r["gain_buf"]) is not None]
    m = med(gains)
    print(f"P18 buffer-only median gain on corrected DEPTH set at or below 0: "
          f"{'CORRECT' if m is not None and m <= 0 else 'WRONG'} (n={len(gains)}, median {m}, "
          f"worse on {sum(1 for g in gains if g < 0)} of {len(gains)})")


if __name__ == "__main__":
    main()
