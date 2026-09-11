#!/usr/bin/env python3
"""Required period and F_max per clock, read from full OpenSTA path reports.

required period = capture clock period - slack, with the capture clock taken
from the report's own "clock <name> (rise edge)" line in the required-time
block rather than assumed to be the path group's name. On this benchmark the
clk_a group's binding path is captured by clk_a_div2 at 31.0 ns, so deriving
F_max from the group name and its create_clock period gives a wrong and
flattering answer.
"""
import re, sys

def blocks(text):
    cur, name = [], None
    for line in text.splitlines():
        m = re.match(r"---CLOCK:(\w+)---", line)
        if m:
            if name:
                yield name, "\n".join(cur)
            name, cur = m.group(1), []
        elif name is not None:
            cur.append(line)
    if name:
        yield name, "\n".join(cur)

def one(body):
    # the required-time half starts at the second "clock <x> (rise edge)"
    edges = re.findall(r"^\s*([\d.]+)\s+[\d.]+\s+clock (\w+) \(rise edge\)", body, re.M)
    slack = re.search(r"^\s*(-?[\d.]+)\s+slack", body, re.M)
    if len(edges) < 2 or not slack:
        return None
    period, cap = float(edges[1][0]), edges[1][1]
    s = float(slack.group(1))
    req = period - s
    return cap, period, s, req, (1000.0 / req if req > 0 else float("inf"))

if __name__ == "__main__":
    text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    print("| path group | capture clock | period ns | slack ns | required period ns | F_max MHz |")
    print("|---|---|---|---|---|---|")
    for name, body in blocks(text):
        r = one(body)
        if r:
            cap, per, s, req, f = r
            print("| %s | %s | %.3f | %+.3f | **%.3f** | **%.2f** |" % (name, cap, per, s, req, f))
        else:
            print("| %s | (no path reported) | | | | |" % name)
