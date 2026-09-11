#!/usr/bin/env python3
"""Check that every distinctive number in REPORT.md appears somewhere in the
evidence, and flag the ones that do not.

Why this exists. On 2026-09-11 an external reviewer found three numbers where
REPORT.md and SUBMISSION_PACK.md disagreed. Compressing the report the same day
surfaced two more that disagreed with their own experiment notes: §7.5 said "6
of 16 findings are noise" when that directory's own NOTES had already corrected
it to 8, and it described a limitation that the same NOTES recorded as fixed.

Every one of those was a number that was true when written and went stale. The
project's whole argument is that claims must be checkable, so the claims in its
own report should be mechanically checkable against the files that carry their
evidence.

What this does NOT do: it cannot tell you a number is *correct*, only that the
number appears somewhere in the repository outside the report. A number that
appears nowhere else is either freshly computed, wrong, or stale, and all three
are worth a human look. Treat the output as a worklist, not a verdict.

Usage:
    python3 tools/check_report_numbers.py                 # report + pack
    python3 tools/check_report_numbers.py --file REPORT.md
"""
import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Numbers too common to be evidence of anything. Years, small counts, section
# numbers, and the page-cap figures the report quotes from the problem
# statement itself.
BORING = {
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
    "13", "14", "15", "16", "20", "24", "25", "30", "32", "50", "64", "100",
    "128", "256", "2024", "2025", "2026",
}

# Where evidence is allowed to live. The report and the pack are the CLAIMS;
# they cannot corroborate each other, which is exactly the failure mode the
# reviewer found.
EVIDENCE_DIRS = ["experiments", "tools", "rtl", "sdc", "docs", "demo"]


def numbers_in(path):
    """Distinctive numbers in a markdown file, with the line each came from."""
    out = {}
    with io.open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            # Skip fenced code and the render-settings footer.
            if line.startswith("    ") or line.startswith("```"):
                continue
            for m in re.finditer(r"(?<![\w.])(\d[\d,]*\.\d+|\d[\d,]{2,})(?![\w])", line):
                raw = m.group(1)
                bare = raw.replace(",", "")
                if bare in BORING or raw in BORING:
                    continue
                # A bare integer under 1000 is rarely distinctive.
                if "." not in bare and len(bare) < 4:
                    continue
                out.setdefault(raw, []).append((lineno, line.strip()))
    return out


def supported(raw):
    """True if this number appears anywhere in the evidence directories.

    Both spellings are tried, because the report writes 55,413 and a log
    writes 55413.
    """
    bare = raw.replace(",", "")
    for form in {raw, bare}:
        for d in EVIDENCE_DIRS:
            p = os.path.join(HERE, d)
            if not os.path.isdir(p):
                continue
            r = subprocess.run(
                ["git", "grep", "-l", "-F", "--", form, "--", d],
                cwd=HERE, capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", dest="files", default=None,
                    help="markdown file to check; repeatable")
    a = ap.parse_args()
    files = a.files or ["REPORT.md", "SUBMISSION_PACK.md"]

    total = unsupported = 0
    for f in files:
        path = os.path.join(HERE, f)
        if not os.path.isfile(path):
            print("skip (missing): %s" % f)
            continue
        nums = numbers_in(path)
        bad = []
        for raw, sites in sorted(nums.items()):
            total += 1
            if not supported(raw):
                bad.append((raw, sites))
        print("\n=== %s: %d distinctive numbers, %d unsupported ==="
              % (f, len(nums), len(bad)))
        for raw, sites in bad:
            unsupported += 1
            lineno, text = sites[0]
            snippet = text if len(text) <= 110 else text[:107] + "..."
            print("  %-12s line %-5d %s" % (raw, lineno, snippet))

    print("\n%d numbers checked, %d appear nowhere in the evidence."
          % (total, unsupported))
    print("An unsupported number is not proof of an error. It is a number no "
          "file in this repository corroborates, which is the state every "
          "stale claim passes through.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
