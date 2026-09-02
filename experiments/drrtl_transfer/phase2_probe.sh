set -u
# Phase 2 groundwork: for each FANOUT_DOMINATED design, which net does the
# worst path's top cell drive, how many loads, and which RTL signal is it?
# Dr. RTL skill #7 says "duplicate the register driving it"; this finds it.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
W=$HOME/drrtl_run
DR=/mnt/c/Users/toshn/Projects/Dr_RTL/rtl_dataset
python3 - "$W" "$DR" <<'PY'
import json, re, sys
sys.path.insert(0, "tools")
from classify_path import parse_netlist, resolve_fanout
W, DR = sys.argv[1], sys.argv[2]
designs = {"aes":("key_expansion_128aes","sv"), "arm_cpu2":("risclite_mx","v"),
           "communication":("sync_serial_communication_tx_rx","v"),
           "cpu_fsm":("mini_cpu","v"), "datapath":("datapath","v")}
for d, (top, ext) in designs.items():
    c = json.load(open(f"experiments/drrtl_transfer/results/{d}/classify.json"))
    mods = parse_netlist(f"{W}/{d}/A.v")
    print(f"=== {d} ({top})  share={c['fanout_delay_share']}  path={c['path_delay_ns']} ns / {c['cells_on_path']} cells")
    for t in c["top_cells"][:2]:
        inst, mod = t["inst"], t["module"]
        leaf = inst.split("/")[-1]
        net = mods.get(mod, {}).get("drv", {}).get(leaf) if mod in mods else None
        fo, _ = resolve_fanout(mods, top, inst)
        print(f"  {t['incr_ns']:>7} ns {t['cell']:<28} fanout={fo}  inst={inst}  net={net}")
        # is the net an RTL-named signal (not a Yosys temp)?
        if net and not net.startswith("_"):
            base = re.sub(r"\[.*\]$", "", net).split(".")[-1]
            rtl = open(f"{DR}/{d}.v0.{ext}", encoding="utf-8", errors="replace").read()
            hits = [l.strip() for l in rtl.splitlines() if re.search(rf"\b{re.escape(base)}\b", l)]
            decl = [h for h in hits if re.match(r"^(reg|wire|output|input)\b", h)]
            print(f"      RTL signal '{base}': {len(hits)} refs; decl: {decl[:2]}")
        else:
            print(f"      net is a synthesis temporary; trace its driver's D-input cone in RTL by hand")
PY
