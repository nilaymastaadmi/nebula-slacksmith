#!/usr/bin/env python3
"""Derive every registered-prediction tally from the PREREGISTRATION files.

Why this exists. Review 3 (2026-09-12) found that REPORT.md and
SUBMISSION_PACK.md both said "4 of 13" registered predictions missed on
2026-09-11, while `experiments/missing_classes/PREREGISTRATION.md` numbers its
predictions past R30 and scores more than four of them wrong. The figure was
correct when written at 15:22 and eighteen more predictions were registered in
the same file afterwards. Three different transfer-study figures appear across
the report, the pack and that study's own notes, and none of them appears under
`experiments/`.

`tools/check_report_numbers.py` passes all of them, because it asks whether the
digits occur anywhere in the repository, not whether the tally is current. A
number that was true yesterday is present today. That is the exact failure this
project exists to argue against, committed in the project's own report.

So the tallies are no longer written by hand. This reads the registration files
and prints the counts; the report quotes what it prints.

    python3 tools/tally_predictions.py            # summary
    python3 tools/tally_predictions.py --detail   # every id and its verdict

A prediction is registered where its id OPENS a line in a declaration form
(`**R64.**`, `| R92 |`, `## R12`, `- (H1)`), and scored where such a line, or
an id opening a sentence, is followed by a verdict keyword before the next id
and within the same sentence. Any other mention is a reference. Later lines
win, because a prediction scored in an amendment supersedes the same id in the
original table. Registered ids never scored are reported as UNSCORED rather
than silently dropped. `--self-test` runs the real lines that broke earlier
versions; run it after any change to the matching rules.

Until 2026-09-13 every mention counted. Review 5 found R92 scored WRONG from a
prose sentence and cross-references counted as registrations; diffing the fix
found R21, R22 and R58 misread and U7, U10 and U11 never scored. The tally
went from 38 of 102 decided across 153 to 35 of 105 across 127, and from 34
unscored to 10, most of the difference being references to other directories'
predictions.
"""
import argparse
import io
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Prediction ids used across this project's registrations: R (general), C (cli
# backend), U (unforced), L (G7 in the loop), H (hypotheses).
ID = re.compile(r"\b([RCULH])(\d{1,2})\b")

# Verdict vocabulary, longest first so "CONFIRMED in direction" is not read as
# a plain CONFIRMED by a shorter pattern. The direction-qualified form is its
# own class: it is neither a clean hit nor a miss, and collapsing it into
# either is how a scorecard starts drifting.
VERDICTS = [
    ("PARTIAL", re.compile(r"CONFIRMED\s+in\s+direction", re.I)),
    ("VOID", re.compile(r"\bVOID\b", re.I)),
    ("WRONG", re.compile(r"\b(WRONG|MISS(?:ED)?|NOT\s+ANSWERED)\b", re.I)),
    ("CONFIRMED", re.compile(r"\bCONFIRMED\b", re.I)),
]

SKIP_LINE = re.compile(r"^\s*(#|>)")

# The id group that opens a line, after list numbering and markdown
# punctuation: one id, or several joined by "," "and" "&" "/". "R64 to R69" is
# a range reference and yields only R64.
_ONE = r"\**`?[RCULH]\d{1,2}\b`?\**"
LEAD = re.compile(r"^\s*(?:\d+\.\s+)?[#>\-\*\|\s(]*(?P<ids>" + _ONE
                  + r"(?:\s*(?:,|and|&|/)\s*" + _ONE + r")*)")
ID_ONLY = re.compile(r"[RCULH]\d{1,2}\b")
# The three characters before a mention, plus a space: does the mention open a
# sentence? ". R22", "; R57", "**R98".
SENTENCE_ID = re.compile(r".*(?:[.;]\s|\*\*|[.;]\*\*)\s?$")


def score_file(path):
    """Return OrderedDict id -> (verdict, line number, line text)."""
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return score_lines(fh)


def score_lines(lines):
    """Score an iterable of lines; see score_file."""
    out = OrderedDict()
    seen = OrderedDict()
    for n, line in enumerate(lines, 1):
        # Only an id that OPENS the line declares or scores a prediction:
        # "**R64.** ...", "| R92 | ... |", "## R12, ...", "**R28 and R29 are
        # VOID**". An id anywhere else is a reference. Until review 5
        # (2026-09-13) every mention counted, so "not vacuous (R92). A variant
        # with one assignment wrong" scored R92 WRONG against its own
        # scorecard, and "R1 to R63 are in the earlier registrations"
        # registered R1 and R63 in a directory that never declared them.
        #
        # Each group's verdict is read only from the text between it and the
        # next id on the line, so "R21 CONFIRMED. R22 CONFIRMED. The void
        # condition does NOT fire." scores two CONFIRMED rather than two VOID,
        # and "R58, R59 WRONG; R57 VOID." scores R58 WRONG. A later id that
        # opens a sentence (after ". ", "; " or "**") is its own group.
        m = LEAD.match(line)
        if not m:
            continue
        mentions = [(x.start(), x.end()) for x in ID.finditer(line)]
        groups = [(ID_ONLY.findall(m.group("ids")), m.end("ids"))]
        for s, e in mentions:
            if s >= m.end("ids") and SENTENCE_ID.match(line[max(0, s - 3):s] + " "):
                groups.append(([line[s:e]], e))
        skip = SKIP_LINE.match(line)
        decorated = bool(re.search(r"[*|#-]", line[:m.start("ids") + 1]))
        for ids, end in groups:
            nxt = next((s for s, _e in mentions if s >= end), len(line))
            segment = line[end:nxt]
            # ...and only to the end of the sentence holding its first verdict
            # word, so prose after a score ("The void condition does NOT
            # fire.") cannot override it.
            first = min((x.start() for _nm, pat in VERDICTS
                         for x in [pat.search(segment)] if x), default=None)
            if first is not None:
                stop = re.search(r"[.;](?:\*\*)?\s", segment[first:])
                if stop:
                    segment = segment[:first + stop.start()]
            verdict = None
            if not skip:
                for name, pat in VERDICTS:
                    if pat.search(segment):
                        verdict = name
                        break
            if verdict is None and ids is not groups[0][0]:
                continue  # a sentence-opening mention with no verdict is a reference
            if verdict is None and not decorated:
                # A bare id opening a line with no verdict is a wrapped
                # reference: depth_i2c's registration line 71 is "R38 there
                # (column C).", the tail of a sentence about composed_rtl.
                continue
            for i in ids:
                seen.setdefault(i, n)
                if verdict is not None:
                    out[i] = (verdict, n, line.strip()[:100])
    for i, n in seen.items():
        out.setdefault(i, ("UNSCORED", n, ""))
    return out


# Regression fixtures, from review 5 (2026-09-13). Each is a real line from
# this repository and the verdicts it must produce, and nothing else. The
# first two are the defects that review found: a prose sentence scored as a
# verdict, and a cross-reference counted as a registration.
SELF_TEST = [
    # experiments/invariant_obligation/NOTES.md line 39: prose, not a score.
    ("5. **The assumption is not vacuous (R92).** A variant with one assignment wrong",
     {}),
    # experiments/closure_cost/PREREGISTRATION.md line 4: references only.
    ("Predictions **R64 to R69 and R83**; R1 to R63 are in the earlier registrations, "
     "and R70 to R82 are reserved by `PROMPT_FINAL_2026-09-12.md` for the blocks that follow this one.",
     {}),
    # the scorecard row for R92; R91 is mentioned in the verdict cell, not scored.
    ("| R92 | a broken child is still REFUTED under the same invariant | **CONFIRMED**, so R91 stands |",
     {"R92": "CONFIRMED"}),
    ("**R93. WRONG.** The proven transform is 0.421 ns worse.", {"R93": "WRONG"}),
    ("**R28 and R29 are VOID** under the amendment.", {"R28": "VOID", "R29": "VOID"}),
    ("| **R64** | A4 adds less than half the area | CONFIRMED |", {"R64": "CONFIRMED"}),
    # Found by diffing the stricter parser against the old one, same day.
    # experiments/missing_classes/NOTES.md: both were read as VOID.
    ("**R21 CONFIRMED. R22 CONFIRMED. The void condition does NOT fire.**",
     {"R21": "CONFIRMED", "R22": "CONFIRMED"}),
    # experiments/depth_i2c/NOTES.md: R58 was read as VOID.
    ("R58, R59 WRONG; R57 VOID. Counts by `tools/tally_predictions.py`.",
     {"R58": "WRONG", "R59": "WRONG", "R57": "VOID"}),
    # experiments/unforced/NOTES.md: only U6 was scored.
    ("| U6, U7, U10, U11 | the fixes change no `bench_top` result | **CONFIRMED**, `classify_regression.py` |",
     {"U6": "CONFIRMED", "U7": "CONFIRMED", "U10": "CONFIRMED", "U11": "CONFIRMED"}),
    # experiments/depth_i2c/PREREGISTRATION.md line 71: a wrapped reference.
    ("R38 there (column C).", {}),
    # experiments/depth_i2c/PREREGISTRATION.md line 33: unforced/'s U1, in parentheses.
    ("(U1) that the router selects RTL on it with no override. Chosen because it is", {}),
    # experiments/llm_proposer_aes/PREREGISTRATION.md: a declared hypothesis, unscored.
    ("- (H1) A non-RTL buffering pass should beat every RTL transform in this", {"H1": None}),
    # a mixed cell keeps the miss: vocabulary priority inside one segment.
    ("| R2 | it rejects the project's own one-hot for the same reason | CONFIRMED on mechanism, **MISS on count** |",
     {"R2": "WRONG"}),
]


def self_test():
    bad = 0
    for line, want in SELF_TEST:
        scored = score_lines([line + "\n"])
        got = {i: v for i, (v, _n, _t) in scored.items() if v != "UNSCORED"}
        registered = set(scored)
        # a None verdict means "registered, not scored on this line"
        ok = (got == {k: v for k, v in want.items() if v is not None}
              and registered == set(want))
        bad += 0 if ok else 1
        print("%s  %s\n      want %s\n      got  verdicts %s, registered %s"
              % ("PASS" if ok else "FAIL", line[:80], want, got, sorted(registered)))
    print("self-test: %d of %d fixtures pass" % (len(SELF_TEST) - bad, len(SELF_TEST)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    # Registrations declare the predictions; several experiments score them in
    # NOTES.md instead (g7_in_loop's L1 to L4, for one). Reading only the
    # registration reports those as unscored, which is the opposite error to
    # the one this tool exists to fix.
    files = []
    for root, _dirs, names in os.walk(os.path.join(HERE, "experiments")):
        for nm in names:
            if nm.endswith(".md") and (nm.startswith("PREREGISTRATION")
                                       or nm == "NOTES.md"):
                files.append(os.path.join(root, nm))
    files.sort()

    totals = {"CONFIRMED": 0, "WRONG": 0, "VOID": 0, "PARTIAL": 0, "UNSCORED": 0}
    # One prediction may be declared in PREREGISTRATION.md and scored in
    # NOTES.md; merge by directory so it counts once, with the scored verdict
    # winning over the unscored declaration.
    by_dir = OrderedDict()
    for f in files:
        d = os.path.dirname(f)
        merged = by_dir.setdefault(d, OrderedDict())
        for i, (verdict, n, txt) in score_file(f).items():
            if i not in merged or merged[i][0] == "UNSCORED":
                merged[i] = (verdict, n, txt)
    print("| experiment | registered | confirmed | wrong | void | partial | unscored |")
    print("|---|---|---|---|---|---|---|")
    for f, res in by_dir.items():
        if not res:
            continue
        c = {k: 0 for k in totals}
        for verdict, _n, _t in res.values():
            c[verdict] += 1
            totals[verdict] += 1
        rel = os.path.relpath(f, HERE).replace(os.sep, "/") + "/"
        print("| `%s` | %d | %d | %d | %d | %d | %d |"
              % (rel, len(res), c["CONFIRMED"], c["WRONG"], c["VOID"],
                 c["PARTIAL"], c["UNSCORED"]))
        if a.detail:
            for i, (verdict, n, txt) in res.items():
                print("|   %-4s | | | | | | %s (line %d) %s |" % (i, verdict, n, txt))

    reg = sum(totals.values())
    decided = totals["CONFIRMED"] + totals["WRONG"] + totals["PARTIAL"]
    print("| **total** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** |"
          % (reg, totals["CONFIRMED"], totals["WRONG"], totals["VOID"],
             totals["PARTIAL"], totals["UNSCORED"]))
    print()
    print("%d predictions registered across %d files in %d directories."
          % (reg, len(files), len(by_dir)))
    print("%d decided, of which **%d missed** (%.0f%%); %d void, %d unscored."
          % (decided, totals["WRONG"],
             100.0 * totals["WRONG"] / decided if decided else 0.0,
             totals["VOID"], totals["UNSCORED"]))
    print()
    print("Quote these numbers. Do not write a tally by hand: the previous "
          "hand-written figure was correct when written and stale six hours "
          "later, and tools/check_report_numbers.py cannot see the difference "
          "because it checks presence, not currency.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
