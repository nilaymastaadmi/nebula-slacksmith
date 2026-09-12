#!/usr/bin/env python3
"""Print REPORT.html to PDF with headless Chrome and count the real pages.

Why this exists. Until 2026-09-12 the page count in this project was measured
by dividing the rendered sheet's continuous pixel height by one page's text
height. That number is not a page count. It assumes content flows across page
boundaries without penalty, and it does not: a table or a heading that will not
fit is pushed whole to the next page, so a document measuring 11.85 "pages"
continuous printed as **13**. An external reviewer found that by printing it,
which is the only way to find it.

The lesson is the project's own: a proxy that has never been checked against
the thing it proxies is a guess with a decimal point.

    python3 tools/page_count.py            # render and count
    python3 tools/page_count.py --keep     # also leave the PDF for inspection

Requires Chrome or Edge. The path is probed, and the script says which binary
it used, because "13 pages" from an unnamed renderer is the same kind of
unchecked number this file exists to replace.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(HERE, "REPORT.html")

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]


def find_browser():
    for c in CANDIDATES:
        if os.path.isfile(c):
            return c
        w = shutil.which(c)
        if w:
            return w
    return None


def pdf_pages(path):
    """Count pages without a PDF library: /Type /Page objects, minus /Pages."""
    with open(path, "rb") as fh:
        blob = fh.read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", blob))
    if n:
        return n
    m = re.findall(rb"/Count\s+(\d+)", blob)
    return max(int(x) for x in m) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--html", default=HTML)
    a = ap.parse_args()

    if not os.path.isfile(a.html):
        print("no %s; run tools/render_report.py first" % a.html)
        return 2
    br = find_browser()
    if br is None:
        print("no Chrome or Edge found; cannot measure a real page count.")
        print("Do NOT fall back to dividing pixel height: that is the estimate")
        print("this tool exists to replace, and it was wrong by one page.")
        return 3

    out = os.path.join(tempfile.gettempdir(), "slacksmith_report.pdf")
    if os.path.exists(out):
        os.remove(out)
    url = "file:///" + os.path.abspath(a.html).replace("\\", "/")
    cmd = [br, "--headless", "--disable-gpu", "--no-pdf-header-footer",
           "--print-to-pdf=" + out, url]
    subprocess.run(cmd, capture_output=True, timeout=180)
    if not os.path.exists(out):
        print("browser produced no PDF; command was:\n  %s" % " ".join(cmd))
        return 4

    n = pdf_pages(out)
    print("renderer : %s" % br)
    print("source   : %s" % a.html)
    print("pages    : %d" % n)
    print("cap      : 10 to 12")
    print("verdict  : %s" % ("INSIDE" if 10 <= n <= 12 else "OUTSIDE"))
    if not a.keep:
        os.remove(out)
    else:
        print("pdf      : %s" % out)
    return 0 if 10 <= n <= 12 else 1


if __name__ == "__main__":
    sys.exit(main())
