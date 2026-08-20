// Single source of truth for the fsm_reencode state-mapping bijection.
// Included verbatim by both domain_b_onehot.v (where it produces the
// externally-observable status bits) and miter_mapped.sv (where it is
// the formal obligation's state-mapping invariant). One function, two
// consumers, no possibility of the two drifting apart.
function [3:0] decode_state;
    input [9:0] oh;
    begin
        decode_state = 4'd0;  // default / S_IDLE
        if (oh[1]) decode_state = 4'd1;  // S_FETCH
        if (oh[2]) decode_state = 4'd2;  // S_WAIT
        if (oh[3]) decode_state = 4'd3;  // S_DECODE
        if (oh[4]) decode_state = 4'd4;  // S_EXEC1
        if (oh[5]) decode_state = 4'd5;  // S_EXEC2
        if (oh[6]) decode_state = 4'd6;  // S_ACCUM
        if (oh[7]) decode_state = 4'd7;  // S_EMIT
        if (oh[8]) decode_state = 4'd8;  // S_HOLD
        if (oh[9]) decode_state = 4'd9;  // S_ERR
    end
endfunction
