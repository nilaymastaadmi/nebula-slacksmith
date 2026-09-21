#!/usr/bin/env bash
# Build-time toolchain record (SPEC.md 2.4 rule 1 and 2). Runs during
# `docker build`; a non-zero exit fails the build, which is the point.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$(dirname "${BASH_SOURCE[0]}")/toolpaths.sh"

echo "closure-bench toolchain, stamped $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "base image: openroad/orfs:26Q3-600-g3a964e13f"
echo "base digest: sha256:7fbb16f7aaf3caa170ea308c1bd833defc7fdf1f5316303dce6a0e6eeb6deee9"
echo
echo "yosys:    $YOSYS"
echo "          $("$YOSYS" -V 2>&1 | head -1)"
echo "openroad: $OPENROAD"
echo "          $("$OPENROAD" -version 2>&1 | head -1)"
echo "sta:      $STA ($STA_KIND)"
echo "python3:  $PYTHON  $("$PYTHON" --version 2>&1)"
echo
echo "liberty:  $LIBERTY"
echo "          sha256 $(sha256sum "$LIBERTY" | cut -d' ' -f1)"
echo "          bytes  $(stat -c %s "$LIBERTY")"
if [ -n "$TECH_LEF" ]; then
  echo "tech lef: $TECH_LEF  sha256 $(sha256sum "$TECH_LEF" | cut -d' ' -f1)"
  echo "cell lef: $SC_LEF  sha256 $(sha256sum "$SC_LEF" | cut -d' ' -f1)"
fi

# The dont_use exclusion must be non-empty. Same test as run_classify.sh:
# at least 2 words, i.e. at least one "-dont_use <cell>" pair. A silently
# empty list once put a 12.8 ns lpflow artifact into eight commits.
words=$("$PYTHON" -c "import sys; sys.path.insert(0,'$HERE/../../tools'); import remeasure; print(len(remeasure.dont_use_flags('$LIBERTY').split()))")
echo "dont_use: $words words, $((words / 2)) cells excluded"
[ "$words" -ge 2 ] || { echo "TOOLCHAIN BROKEN: dont_use returned $words words, expected >= 2" >&2; exit 3; }
