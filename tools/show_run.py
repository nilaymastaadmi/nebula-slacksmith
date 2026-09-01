#!/usr/bin/env python3
"""Pretty-print a slacksmith.py decision log.

Usage: python3 tools/show_run.py <workdir>/decisions.jsonl
"""
import json, sys

for line in open(sys.argv[1], encoding="utf-8"):
    d = json.loads(line)
    it, step = d.get("iter", "?"), d.get("step")
    if step == "measure":
        s = "  ".join(f"{k}={v}" for k, v in d["slacks"].items())
        print(f"it{it}  MEASURE   {s}   physical={d['physical_applied']} "
              f"rtl={d.get('rtl_applied')}")
    elif step == "classify":
        print(f"it{it}  CLASSIFY  {d['clock']}: {d['verdict']} "
              f"(fanout share {d['fanout_delay_share']}, "
              f"{d['path_delay_ns']} ns over {d['cells_on_path']} cells) "
              f"-> {d['lever']}")
        for c in (d.get("top_cells") or [])[:2]:
            print(f"              {c['incr_ns']:>8} ns  {c['cell']:<28} "
                  f"fanout={c['fanout']}  {c['inst']}")
    elif step == "apply":
        print(f"it{it}  APPLY     {d['lever']}: "
              f"{d.get('how') or d.get('proposal')}")
    elif step == "gate":
        print(f"it{it}  GATE      {d['proposal']} ({d.get('def_id')}) "
              f"k={d.get('declared_k')} G3={d.get('G3')} G4={d.get('G4')}")
    elif step == "confirm":
        print(f"it{it}  CONFIRM   {d['proposal']}: {d['clock']} "
              f"{d['before']} -> {d['after']} ({d['gain']:+})")
    elif step == "revert":
        print(f"it{it}  REVERT    {d['proposal']}: {d['clock']} "
              f"{d['before']} -> {d['after']}, {d['reason']}")
    elif step == "stop":
        print(f"it{it}  STOP      {d['reason']}")
    else:
        print(f"it{it}  {step}  {d}")
