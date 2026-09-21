# closure-bench toolchain image. Phase 3, step 1.
#
# Build from the REPO ROOT, because the harness imports tools/remeasure.py:
#     docker build -f closure-bench/docker/Dockerfile -t closure-bench:dev .
#
# Run the one-design smoke test. Designs are mounted, never baked in:
#     docker run --rm -v "$HOME/Projects/Dr_RTL:/designs:ro" closure-bench:dev ticket_machine
#
# Pinned by tag AND digest. The tag names the OpenROAD-flow-scripts commit
# (3a964e1, ORFS master on 2026-09-19); the digest makes the pin immutable
# even if someone moves the tag. This one image supplies OpenROAD, OpenSTA,
# Yosys and the sky130hd platform, so there is one pin to audit, not three.
FROM openroad/orfs:26Q3-600-g3a964e13f@sha256:7fbb16f7aaf3caa170ea308c1bd833defc7fdf1f5316303dce6a0e6eeb6deee9

# DESIGNS ARE NOT COPIED INTO THIS IMAGE, deliberately.
# github.com/hkust-zhiyao/Dr_RTL has no LICENSE file and GitHub reports no
# licence, and 19 of its 20 design files carry no licence text (simple_spi
# alone keeps an OpenCores header). Unlicensed code is all-rights-reserved by
# default, so a published image containing it would be redistributing it.
# Designs are mounted read-only at /designs from a clone pinned at commit
# 8d86c0e3d0a6260a3b20caa98412e81f496ad19a (the commit the holdout was sealed
# against). See SPEC.md 2.3 and the data card.

WORKDIR /opt/closure-bench
COPY tools/remeasure.py tools/remeasure.py
COPY closure-bench/ closure-bench/

# Record the exact toolchain at build time, and FAIL THE BUILD if any tool or
# the liberty is missing. A container that builds but cannot find yosys would
# otherwise surface as every design reporting SYNTH_FAIL, which reads as a
# result rather than as a broken image.
RUN bash closure-bench/docker/stamp.sh | tee /opt/closure-bench/TOOLCHAIN.txt

ENTRYPOINT ["bash", "/opt/closure-bench/closure-bench/docker/smoke.sh"]
