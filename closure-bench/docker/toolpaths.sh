# Discover the toolchain inside the image. Source it, do not execute it.
#
# The ORFS image's install layout was not inspected before this was written,
# so nothing here is a hardcoded guess: each tool is found by `command -v`
# first, then by a bounded search of the roots ORFS images use, and a miss is
# fatal. Every path found is exported and later recorded in TOOLCHAIN.txt.

_find_tool () {  # $1 binary name; prints the first hit or nothing
  local hit
  hit=$(command -v "$1" 2>/dev/null) && { echo "$hit"; return; }
  for root in /OpenROAD-flow-scripts/tools/install /OpenROAD-flow-scripts /opt /usr/local; do
    [ -d "$root" ] || continue
    hit=$(find "$root" -maxdepth 6 -type f -name "$1" -perm -u+x 2>/dev/null | head -1)
    [ -n "$hit" ] && { echo "$hit"; return; }
  done
}

_fatal () { echo "TOOLCHAIN BROKEN: $*" >&2; exit 3; }

YOSYS=$(_find_tool yosys);        [ -n "$YOSYS" ]    || _fatal "yosys not found"
OPENROAD=$(_find_tool openroad);  [ -n "$OPENROAD" ] || _fatal "openroad not found"
PYTHON=$(_find_tool python3);     [ -n "$PYTHON" ]   || _fatal "python3 not found"

# OpenSTA: a standalone `sta` if the image ships one, otherwise OpenROAD, which
# embeds OpenSTA and accepts the same Tcl and the same -no_init -no_splash
# -exit flags. Which one ran is recorded, because the two are separate builds.
STA=$(_find_tool sta)
if [ -n "$STA" ]; then STA_KIND=standalone; else STA=$OPENROAD; STA_KIND=openroad-embedded; fi

# Liberty: sky130hd typical corner, the same corner the committed transfer
# study used. Exactly one match is required; zero or several is ambiguous and
# fatal, because a silently wrong corner shifts every slack in the table.
LIBERTY=${LIBERTY:-}
if [ -z "$LIBERTY" ]; then
  mapfile -t _libs < <(find / -xdev -type f -name 'sky130_fd_sc_hd__tt_025C_1v80.lib' 2>/dev/null)
  [ "${#_libs[@]}" -ge 1 ] || _fatal "sky130hd tt_025C_1v80 liberty not found"
  # Several copies of one file are fine; several DIFFERENT files are not.
  _uniq=$(for l in "${_libs[@]}"; do sha256sum "$l" | cut -d' ' -f1; done | sort -u | wc -l)
  [ "$_uniq" -eq 1 ] || _fatal "${#_libs[@]} tt liberty files with $_uniq different contents: ${_libs[*]}"
  LIBERTY=${_libs[0]}
fi
[ -s "$LIBERTY" ] || _fatal "liberty is empty or unreadable: $LIBERTY"

export YOSYS OPENROAD PYTHON STA STA_KIND LIBERTY
