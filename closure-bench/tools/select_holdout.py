#!/usr/bin/env python3
"""Regenerate the sealed holdout from SPEC.md's published rule.

The point of this file is that the holdout is a mechanical consequence of a
salt fixed before the selection existed, not a choice. Anyone can re-run it
and get the same five designs, or find out that they cannot.

Usage:
    python3 select_holdout.py --dataset ~/Projects/Dr_RTL/rtl_dataset
    python3 select_holdout.py --dataset <dir> --verify   # exit 1 on any drift
"""
import argparse
import hashlib
import os
import sys

# Fixed by SPEC.md 2.3. c2f4186 is the commit that added VISION.md and
# PRIOR_ART.md; it existed before this selection did, so it could not have
# been chosen to produce a favourable split.
SALT = "c2f4186"

TIERS = {
    "FANOUT": ["cpu_fsm", "datapath", "aes", "communication", "arm_cpu2"],
    "MIXED": ["router", "tv80", "arm_cpu1"],
    "DEPTH": ["vending_machine", "ticket_machine", "DSP", "simple_spi",
              "controller", "cpu_pipe", "i2c"],
}
TAKE = {"FANOUT": 2, "MIXED": 1, "DEPTH": 2}

# Sealed 2026-09-21. Any mismatch means the dataset moved under us.
SEALED = {
    "arm_cpu2":   "9089774688d22ad7d371324ebe1595963e1ba85b7ac1c76b1b68acac550fd061",
    "datapath":   "7647ab3f5bd554c5f0c6060712a63ed59a6a83805cfbd5b76bdd3f9d8ed35594",
    "arm_cpu1":   "bb2020ea808fcf7125064fddfaf5214b858cebcfafca59cd5962af8a391dddcf",
    "simple_spi": "5d31bfd3742a88c95177281b525ebd5f2f03b3d727814e1bc5d2bde590035d2c",
    "controller": "5f46393afd33b60b6e2ad31e0d012e9a9792972aab1258ce9b52f430d3b1e106",
}


def rank(design):
    return hashlib.sha256(f"{SALT}:{design}".encode()).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def index_dataset(dataset):
    """Map design name -> filename. Guarded: an empty index over a directory
    that exists is a broken instrument, not a finding (SPEC.md 2.4 rule 8)."""
    if not os.path.isdir(dataset):
        sys.exit(f"BROKEN: dataset directory does not exist: {dataset}")
    entries = os.listdir(dataset)
    if not entries:
        sys.exit(f"BROKEN: dataset directory is empty: {dataset}")
    files = {f.split(".v0.")[0]: f for f in entries if ".v0." in f}
    if not files:
        sys.exit(
            f"BROKEN: {len(entries)} entries in {dataset} but none matched the "
            "'*.v0.*' pattern. This is an instrument failure, not an empty "
            "dataset - check the naming convention before trusting any run."
        )
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--verify", action="store_true",
                    help="exit 1 if the regenerated seal differs from SPEC.md")
    args = ap.parse_args()

    files = index_dataset(os.path.expanduser(args.dataset))

    expected = sum(len(v) for v in TIERS.values())
    missing = [d for ms in TIERS.values() for d in ms if d not in files]
    if missing:
        sys.exit(f"BROKEN: {len(missing)} of {expected} tiered designs absent "
                 f"from the dataset: {', '.join(missing)}")

    holdout, dev = [], []
    for tier, members in TIERS.items():
        ranked = sorted(members, key=rank)
        for i, design in enumerate(ranked):
            (holdout if i < TAKE[tier] else dev).append((tier, design))

    drift = []
    print(f"salt={SALT}  stratified {TAKE}\n")
    print("SEALED HOLDOUT")
    for tier, design in holdout:
        path = os.path.join(os.path.expanduser(args.dataset), files[design])
        got = sha256_file(path)
        want = SEALED.get(design)
        status = "OK" if got == want else ("DRIFT" if want else "UNSEALED")
        if status != "OK":
            drift.append((design, want, got))
        print(f"  {tier:7s} {design:16s} {files[design]:24s} {status:9s} {got}")

    print("\nDEVELOPMENT SET")
    for tier, design in dev:
        print(f"  {tier:7s} {design}")

    if len(holdout) != sum(TAKE.values()):
        sys.exit(f"\nBROKEN: selected {len(holdout)}, expected "
                 f"{sum(TAKE.values())}")

    if drift:
        print("\nSEAL BROKEN - the dataset changed after sealing:")
        for design, want, got in drift:
            print(f"  {design}: sealed {want}\n  {' ' * len(design)}  now    {got}")
        sys.exit(1)

    print(f"\nSeal intact: {len(holdout)} held out, {len(dev)} development.")
    if args.verify:
        print("VERIFY PASS")


if __name__ == "__main__":
    main()
