#!/usr/bin/env python3
"""
render_report.py -- render REPORT.md to a paginated A4 HTML, so the page count
against the organizer's 10 to 12 page limit is MEASURED rather than estimated.

Estimating from word count was wrong by a wide margin here. At 6,244 words a
words-per-page estimate calibrated on an earlier revision predicted 12.4 to
14.6 pages; the measured figure at that revision was 10.39. The report is
table-heavy, and tables carry far more content per vertical inch than prose,
so any words-per-page rule overstates it.

**Re-measure after every edit; do not quote a number from this docstring.**
The 10.39 above is a historical measurement of a 6,244-word revision and was
read as current by an external reviewer on 2026-09-11, who then reported the
repository as contradicting itself. Measured 2026-09-11 at 8,073 source words:
**12.36 pages, over the 12-page cap.** A figure baked into a comment ages into
a false claim, which is the same failure mode as the hard-coded paths this
project already fixed once.

Usage:
    pip install markdown
    python3 tools/render_report.py            # writes REPORT.html next to REPORT.md
    python3 tools/render_report.py --open     # also prints the measuring snippet

To get the page count, open the HTML in a browser and run in the console:

    var s = document.getElementById('sheet');
    s.getBoundingClientRect().height / 987

987 px is the A4 text-block height at 96 dpi with 18 mm margins
(1123 px page - 2 x 68 px). The divisor changes if you change the margins.

To produce the PDF: open the HTML and print to PDF with **A4, 18 mm margins,
background graphics on, scale 100%**. Those are the settings the 10.39 figure
was measured at. Larger type or 1 inch margins push it to roughly 12.6 pages,
so if the submission portal insists on a specific typography, re-measure
before assuming it still fits.
"""
import argparse, io, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "REPORT.md")
OUT = os.path.join(HERE, "REPORT.html")

CSS = """
  @page { size: A4; margin: 18mm; }
  html { background:#888; }
  body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
         line-height: 1.38; margin:0; }
  #sheet { width: 658px; margin: 0 auto; background:#fff; padding: 0; }
  h1 { font-size: 19pt; margin: 0 0 2px 0; }
  h2 { font-size: 13pt; margin: 15px 0 5px 0; border-bottom:1px solid #bbb; }
  h3 { font-size: 11.3pt; margin: 11px 0 4px 0; }
  p  { margin: 6px 0; text-align: justify; }
  table { border-collapse: collapse; font-size: 8.8pt; margin: 7px 0; width:100%; }
  th, td { border: 1px solid #999; padding: 2px 5px; text-align: left; }
  th { background:#eee; }
  pre { background:#f4f4f4; font-size:8pt; padding:5px; overflow-x:auto;
        line-height:1.2; }
  code { font-family: Consolas, monospace; font-size: 9pt; }
  li { margin: 2px 0; }
  hr { border:0; border-top:1px solid #ccc; margin:10px 0; }
  @media print { html { background:#fff; } #sheet { width:auto; } }
"""

MEASURE_JS = """
window.__pageinfo = function () {
  var h = document.getElementById('sheet').getBoundingClientRect().height;
  var pageH = 987;   // A4 text block at 96dpi with 18mm margins
  return { contentPx: Math.round(h), pageHeightPx: pageH,
           pages: +(h / pageH).toFixed(2) };
};
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    try:
        import markdown
    except ImportError:
        sys.exit("need the markdown package: pip install markdown")

    text = io.open(a.src, encoding="utf-8").read()
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists"])

    html = ("<!doctype html><html><head><meta charset=\"utf-8\">\n<style>"
            + CSS + "</style></head><body><div id=\"sheet\">\n"
            + body + "\n</div>\n<script>" + MEASURE_JS + "</script></body></html>")
    io.open(a.out, "w", encoding="utf-8").write(html)

    words = len(text.split())
    print(f"wrote {a.out} ({os.path.getsize(a.out)} bytes) from {words} words")
    print("open it and run this in the console for the page count:")
    print("    document.getElementById('sheet').getBoundingClientRect()"
          ".height / 987")


if __name__ == "__main__":
    main()
