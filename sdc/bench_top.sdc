###############################################################################
# bench_top.sdc -- frozen timing constraints for the 5-domain benchmark SoC.
#
# Written and verified against OpenSTA (yosys-abc mapped netlist, sky130hd_tt).
# This file is frozen per the SlackSmith project discipline: the optimization
# agent never edits constraints, and timing exceptions (multicycle paths in
# particular) are never used to manufacture slack. The only exception here is
# the standard, textbook-correct treatment of true asynchronous domains and
# async reset ports, both justified explicitly below.
###############################################################################

# -----------------------------------------------------------------------
# 1. Primary clocks -- five independent domains, no phase relationship.
#    Periods are illustrative (non-harmonic on purpose, so no accidental
#    common period lets a lazy check skip real CDC treatment). Real F_max
#    targets come from post-synthesis analysis, not an assumed period.
# -----------------------------------------------------------------------
create_clock -name clk_a -period 8.0  [get_ports clk_a]
create_clock -name clk_b -period 11.0 [get_ports clk_b]
create_clock -name clk_c -period 6.0  [get_ports clk_c]
create_clock -name clk_d -period 13.0 [get_ports clk_d]
create_clock -name clk_e -period 9.0  [get_ports clk_e]

# -----------------------------------------------------------------------
# 2. Generated clocks -- one per domain, produced by clkdiv.v.
#
#    -edges {e1 e2 e3} gives three MASTER-clock edge numbers (1=first rise,
#    2=first fall, 3=second rise, ... alternating) that define one full
#    period of the generated clock: e1=its rise, e2=its fall, e3=its next
#    rise. Derived by hand-tracing clkdiv.v's counter logic against the
#    master's edge sequence, then cross-checked against a real simulation
#    of the RTL (Icarus Verilog) that measured every high/low segment over
#    a 2000ns run -- both agree to the last digit.
#
#    DIV=2 (clk_a, clk_e): single posedge-clocked toggle flop. Toggles at
#    every source rising edge -> edges {1 3 5}. Standard divide-by-2 idiom.
#
#    DIV=4 (clk_c): posedge-clocked toggle flop, toggles every 2nd rising
#    edge -> edges {3 7 11}. Exact 50% duty (a toggle flop is always 50%).
#
#    DIV=3 (clk_b) and DIV=5 (clk_d): the odd cases. clkdiv.v builds these
#    from TWO independent phase counters -- one clocked on posedge, one on
#    negedge -- ANDed together (clk_out = clk_p & clk_n). The AND rises at
#    whichever phase's rising edge arrives LAST (always clk_n, since it is
#    clocked half a source period after clk_p) and falls at whichever
#    phase's falling edge arrives FIRST (always clk_p). Working through
#    the master-edge arithmetic for general odd DIV gives:
#        rise      @ master edge  2*DIV
#        fall      @ master edge  2*(DIV + (DIV+1)/2) - 1
#        next rise @ master edge  4*DIV
#    which for DIV=3 -> {6 9 12} and DIV=5 -> {10 15 20}. Both give exact
#    50% duty: the half-source-period lag cancels to exactly half after
#    the AND, which is the whole point of the both-edges construction.
#
#    ASSUMPTION, disclosed rather than hidden: this derivation assumes
#    clk_in's first post-reset transition sampled by the posedge-clocked
#    counter is a RISING edge (i.e. reset releases while clk_in is low).
#    The RTL's own README already flags that the alternative phase (reset
#    releasing while clk_in is high) shifts clk_out's phase by half a
#    source period -- the PERIOD and DUTY CYCLE are unaffected either way,
#    only which specific master edge is "the" first one. STA is a
#    steady-state method; it cannot and does not reason about reset
#    transients, so this is the standard, expected way to handle it -- the
#    same idealization every real SDC flow makes for every generated clock.
# -----------------------------------------------------------------------
create_generated_clock -name clk_a_div2 -source [get_ports clk_a] \
    -edges {1 3 5} [get_nets clk_a_div2]

create_generated_clock -name clk_b_div3 -source [get_ports clk_b] \
    -edges {6 9 12} [get_nets clk_b_div3]

create_generated_clock -name clk_c_div4 -source [get_ports clk_c] \
    -edges {3 7 11} [get_nets clk_c_div4]

create_generated_clock -name clk_d_div5 -source [get_ports clk_d] \
    -edges {10 15 20} [get_nets clk_d_div5]

create_generated_clock -name clk_e_div2 -source [get_ports clk_e] \
    -edges {1 3 5} [get_nets clk_e_div2]

# -----------------------------------------------------------------------
# 3. Asynchronous domain groups.
#
#    Each primary clock and ITS OWN generated clock are related (the
#    generated-clock relationship already tells OpenSTA how to time paths
#    between them). The five DOMAINS are not related to each other at
#    all, by construction -- no shared reference, no fixed phase.
#
#    This single statement is also what correctly exempts every CDC
#    synchronizer path in the design (the sync2ff first-flop-to-second-
#    flop path inside every async_fifo pointer sync, and inside the two
#    standalone single-bit sync2ff instances in domain_c/domain_e) from
#    ordinary setup/hold analysis. That is the textbook-correct treatment
#    for a synchronizer -- those paths are meant to tolerate metastability,
#    not meet a same-domain timing check -- and it requires no additional
#    false_path or multicycle_path statements beyond this one line. No
#    multicycle_path is used anywhere in this file: a multicycle path is
#    an SDC statement that can manufacture slack without changing the
#    design, and this project treats that as out of bounds (see the
#    project abstract).
# -----------------------------------------------------------------------
set_clock_groups -name async_domains -asynchronous \
    -group {clk_a clk_a_div2} \
    -group {clk_b clk_b_div3} \
    -group {clk_c clk_c_div4} \
    -group {clk_d clk_d_div5} \
    -group {clk_e clk_e_div2}

# -----------------------------------------------------------------------
# 4. Asynchronous reset ports -- excluded from setup/hold analysis.
#
#    Every flop's reset is asynchronous by design (the RTL's own stated
#    rule: "every flop explicitly reset, async active-low"). Standard
#    practice is to exclude the reset net itself from ordinary data-path
#    timing, since it is not a synchronous data signal. This file does
#    NOT attempt recovery/removal analysis (the check that verifies an
#    async reset's de-assertion is safely synchronized) -- that is a
#    separate, more specialized analysis this benchmark does not yet
#    perform. Flagged here rather than left silent.
# -----------------------------------------------------------------------
set_false_path -from [get_ports {rst_a_n rst_b_n rst_c_n rst_d_n rst_e_n}]

# -----------------------------------------------------------------------
# 5. I/O timing -- every port constrained against the clock that actually
#    samples or drives it, confirmed by reading the RTL directly rather
#    than assumed. mac_result_a in particular is on clk_a_div2 (the
#    GENERATED clock), not clk_a -- domain_a accumulates on the divided
#    clock even though its front end samples on the primary. Getting
#    this wrong is exactly the class of mistake that hid 41% of the real
#    data-path critical path on rv32i_core: worst DATA-path slack -8.527
#    (imem_data->retire_val) vs -1.114 reg-to-reg with I/O unconstrained.
#    Re-derived and made precise 2026-08-31 with a saved recipe (see
#    experiments/rv32i_wns/): tool-level report_wns on those same inputs is
#    -32.30, dominated by a reset RECOVERY artifact because that SDC times
#    rst_n without a false-path -- a second, independent lesson in the same
#    direction, and the reason section 4 above false-paths the resets here.
#
#    Input/output delays are set to roughly 30% of the relevant domain's
#    period, a standard default in the absence of a real board-level
#    timing spec. set_load gives every output a nominal fanout load so
#    output-side delay is meaningful rather than defaulting to zero
#    capacitance.
# -----------------------------------------------------------------------

# domain A inputs -- sampled on clk_a (primary)
set_input_delay -clock clk_a -max 2.4 [get_ports {data_in_a valid_in_a}]
set_input_delay -clock clk_a -min 0.4 [get_ports {data_in_a valid_in_a}]

# domain E inputs -- sampled on clk_e (primary)
set_input_delay -clock clk_e -max 2.7 [get_ports {cfg_addr_e cfg_wdata_e cfg_we_e}]
set_input_delay -clock clk_e -min 0.5 [get_ports {cfg_addr_e cfg_wdata_e cfg_we_e}]

# mac_result_a -- driven on clk_a_div2 (GENERATED clock, not clk_a)
set_output_delay -clock clk_a_div2 -max 2.4 [get_ports mac_result_a]
set_output_delay -clock clk_a_div2 -min 0.4 [get_ports mac_result_a]
set_load 0.05 [get_ports mac_result_a]

# status_b -- driven on clk_b (primary)
set_output_delay -clock clk_b -max 3.3 [get_ports status_b]
set_output_delay -clock clk_b -min 0.5 [get_ports status_b]
set_load 0.05 [get_ports status_b]

# uart_tx_c -- driven on clk_c (primary)
set_output_delay -clock clk_c -max 1.8 [get_ports uart_tx_c]
set_output_delay -clock clk_c -min 0.3 [get_ports uart_tx_c]
set_load 0.05 [get_ports uart_tx_c]

# timer_pulse_d -- driven on clk_d (primary)
set_output_delay -clock clk_d -max 3.9 [get_ports timer_pulse_d]
set_output_delay -clock clk_d -min 0.6 [get_ports timer_pulse_d]
set_load 0.05 [get_ports timer_pulse_d]

# cfg_status_e -- driven on clk_e (primary)
set_output_delay -clock clk_e -max 2.7 [get_ports cfg_status_e]
set_output_delay -clock clk_e -min 0.5 [get_ports cfg_status_e]
set_load 0.05 [get_ports cfg_status_e]
