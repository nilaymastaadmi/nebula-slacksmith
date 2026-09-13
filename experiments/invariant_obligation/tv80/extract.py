#!/usr/bin/env python3
"""Pull one module out of a whole-file source and rename it.

The loop's variant files are the entire tv80.v with tv80_mcode edited, so a
child-level miter needs just that module, twice, under two names. Extraction
is by the module's own `module ... endmodule` span, and the output is checked
to contain exactly one module of the requested name.

    python3 extract.py SRC MODULE NEWNAME OUT
"""
import io
import re
import sys


def span(text, name):
    m = re.search(r"^\s*module\s+%s\b" % re.escape(name), text, re.M)
    if not m:
        raise SystemExit("no module %s" % name)
    e = re.search(r"^\s*endmodule\b.*$", text[m.start():], re.M)
    if not e:
        raise SystemExit("no endmodule after %s" % name)
    return text[m.start():m.start() + e.end()]


def main():
    src, module, new, out = sys.argv[1:5]
    text = io.open(src, encoding="utf-8", errors="replace").read()
    body = span(text, module)
    body = re.sub(r"^(\s*module\s+)%s\b" % re.escape(module), r"\g<1>" + new, body, count=1, flags=re.M)
    # tv80 uses `TV80DELAY in nonblocking assignments; define it empty here so
    # the extracted module elaborates on its own.
    body = "`ifndef TV80DELAY\n`define TV80DELAY\n`endif\n" + body + "\n"
    if len(re.findall(r"^\s*module\s", body, re.M)) != 1:
        raise SystemExit("extraction did not yield exactly one module")
    io.open(out, "w", encoding="utf-8", newline="\n").write(body)
    print("%s: %s -> %s, %d lines" % (out, module, new, body.count("\n")))


if __name__ == "__main__":
    main()
