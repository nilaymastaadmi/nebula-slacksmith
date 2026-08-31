# P4 four-checker column, raw outcomes

    REGIME 1 (real firmware loop, 400 cycles, no shift instructions): MISSED
    REGIME 2 (random instructions, 20000): MISSED

    SRAI x2,x1,4 with x1=0xFFFFFFFF:
      gold retire_val = ffffffff
      gate retire_val = 0fffffff
      SIMULATION DIFFERS (bug manifests)

The directed probe is what makes the two MISSES interpretable: the defect is
fully visible to simulation, so both misses are stimulus weakness rather than
a phantom. EQY caught it in 46 seconds without needing to know which
instruction to aim at.
