# Single source of truth for every path SlackSmith's entry points need.
# Source it, do not execute it:   . "$(dirname "$0")/env.sh"
#
# Why this file exists: until 2026-09-05 every script here began with
#   cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
# which meant the repo ran on exactly one machine, at exactly one path. The
# numbers in REPORT.md were reproducible in principle and unreproducible in
# practice. Every value below is overridable by an environment variable of the
# same name; the defaults are this author's install locations, which is fine
# as a default and was never fine as a hard-coded constant.
#
# See SETUP.md for where each dependency comes from and which versions were
# used for the committed results.

# Repo root, derived from this file's own location. Works from any cwd, any
# clone path, and through a symlink.
SLACKSMITH_ENV_SELF="${BASH_SOURCE[0]:-$0}"
REPO="${REPO:-$(cd "$(dirname "$SLACKSMITH_ENV_SELF")/.." && pwd)}"
export REPO

# OSS CAD Suite: yosys, yosys-abc, eqy, sby, iverilog, vvp.
export OSS_CAD_BIN="${OSS_CAD_BIN:-$HOME/tools/oss-cad-suite/bin}"

# OpenSTA, built from source. Not part of OSS CAD Suite.
export STA_BIN="${STA_BIN:-$HOME/tools/OpenSTA/build/sta}"

# OpenROAD, for the physical levers (repair_design) and G6.
export OPENROAD_BIN="${OPENROAD_BIN:-$HOME/or_env/bin/openroad}"

# SKY130 HD typical-corner liberty. SETUP.md names a public source.
export LIBERTY="${LIBERTY:-$HOME/sta_work/sky130hd_tt.lib}"

# OpenROAD-flow-scripts platform dir, for LEF/tech files.
export ORFS_PLATFORM="${ORFS_PLATFORM:-$HOME/orfs/flow/platforms/sky130hd}"

# Scratch. Everything a run generates goes under here, so a stranger's home
# directory does not collect twelve stray .txt files.
export SLACKSMITH_WORK="${SLACKSMITH_WORK:-$HOME/slacksmith_work}"

export PATH="$OSS_CAD_BIN:$PATH"
cd "$REPO" || { echo "env.sh: cannot cd to REPO=$REPO" >&2; exit 1; }
