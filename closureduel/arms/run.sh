#!/usr/bin/env bash
# Launch the classical arms inside closureduel:dev. Run from the repo root on
# the host (WSL). The image supplies the toolchain; the harness code is the
# repo at HEAD, mounted read-only, and HEAD is recorded on every row.
#
#   bash closureduel/arms/run.sh [--designs ticket_machine ...] [--jobs 6]
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
DR=${DR_RTL:-$(dirname "$REPO")/Dr_RTL}   # the design clone, default beside this repo
WORK=${CLOSUREDUEL_WORK:-$HOME/closureduel_work}
RES="$REPO/closureduel/results"
IMG=${IMG:-closureduel:dev}
mkdir -p "$WORK" "$RES"

# The harness must be committed, or HEAD on every row would be a lie.
if [ -n "$(git -C "$REPO" status --porcelain -- closureduel/arms closureduel/tools tools/classify_path.py tools/remeasure.py)" ]; then
  echo "REFUSED: uncommitted changes in the harness; commit first so HARNESS_COMMIT is true" >&2
  exit 5
fi
# Design pin (SPEC.md 2.4 item 3).
[ "$(git -C "$DR" rev-parse HEAD)" = 8d86c0e3d0a6260a3b20caa98412e81f496ad19a ] || {
  echo "REFUSED: Dr_RTL is not at the pinned commit 8d86c0e" >&2; exit 5; }

COMMIT=$(git -C "$REPO" rev-parse HEAD)
IMAGE_ID=$(docker image inspect --format '{{.Id}}' "$IMG")

docker run --rm \
  -v "$REPO:/repo:ro" -v "$DR:/designs:ro" -v "$WORK:/work" -v "$RES:/results" \
  -e HARNESS_COMMIT="$COMMIT" -e IMAGE_ID="$IMAGE_ID" \
  --entrypoint bash "$IMG" -c '. /repo/closureduel/docker/toolpaths.sh && python3 /repo/closureduel/arms/run_arms.py "$@"' _ "$@"
