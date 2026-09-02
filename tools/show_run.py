#!/usr/bin/env python3
"""Pretty-print a slacksmith.py decision log.

Usage: python3 tools/show_run.py <workdir>/decisions.jsonl

Reads logs from before and after 2026-09-03: older logs carry
`physical_applied`, newer ones carry `physical` {buffer, size}, the lever
policy, the G5 mode and the total violation.
"""
import json, sys


def physical(d):
    if "physical" in d:
        p = d["physical"]
        on = [k for k in ("buffer", "size") if p.get(k)]
        return "+".join(on) if on else "none"
    return str(d.get("physical_applied"))


for line in open(sys.argv[1], encoding="utf-8"):
    d = json.loads(line)
    it, step = d.get("iter", "?"), d.get("step")
    if step == "measure":
        s = "  ".join(f"{k}={v}" for k, v in d["slacks"].items())
        extra = ""
        if "total_violation" in d:
            extra = f"  total={d['total_violation']}"
        print(f"it{it}  MEASURE   {s}   physical={physical(d)}{extra} "
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
        what = d.get("component") or d.get("proposal") or d.get("how")
        prov = " (provisional)" if d.get("provisional") or d.get("status") == "provisional" else ""
        print(f"it{it}  APPLY     {d['lever']}: {what}{prov}")
    elif step == "gate":
        print(f"it{it}  GATE      {d['proposal']} ({d.get('def_id')}) "
              f"k={d.get('declared_k')} G3={d.get('G3')} G4={d.get('G4')}")
    elif step == "g5_total":
        print(f"it{it}  G5 TOTAL  {d['total_before']} -> {d['total_after']} "
              f"({'improved' if d['improved'] else 'not improved'})")
    elif step == "confirm":
        what = d.get("component") or d.get("proposal")
        print(f"it{it}  CONFIRM   {what}: {d['clock']} "
              f"{d['before']} -> {d['after']} ({d['gain']:+})")
    elif step == "revert":
        what = d.get("component") or d.get("proposal")
        print(f"it{it}  REVERT    {what}: {d['clock']} "
              f"{d['before']} -> {d['after']}, {d['reason']}")
    elif step == "stop":
        print(f"it{it}  STOP      {d['reason']}")
    else:
        print(f"it{it}  {step}  {d}")
