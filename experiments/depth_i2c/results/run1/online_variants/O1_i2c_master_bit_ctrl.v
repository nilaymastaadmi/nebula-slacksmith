module i2c_master_bit_ctrl(
	clk, rst, nReset, 
	clk_cnt, ena, cmd, cmd_ack, busy, al, din, dout,
	scl_i, scl_o, scl_oen, sda_i, sda_o, sda_oen
	);

	//
	// inputs & outputs
	//
	input clk;
	input rst;
	input nReset;
	input ena;            // core enable signal

	input [15:0] clk_cnt; // clock prescale value

	input  [3:0] cmd;
	output       cmd_ack; // command complete acknowledge
	reg cmd_ack;
	output       busy;    // i2c bus busy
	reg busy;
	output       al;      // i2c bus arbitration lost
	reg al;

	input  din;
	output dout;
	reg dout;

	// I2C lines
	input  scl_i;         // i2c clock line input
	output scl_o;         // i2c clock line output
	output scl_oen;       // i2c clock line output enable (active low)
	reg scl_oen;
	input  sda_i;         // i2c data line input
	output sda_o;         // i2c data line output
	output sda_oen;       // i2c data line output enable (active low)
	reg sda_oen;


	//
	// variable declarations
	//

	reg sSCL, sSDA;             // synchronized SCL and SDA inputs
	reg dscl_oen;               // delayed scl_oen
	reg sda_chk;                // check SDA output (Multi-master arbitration)
	reg clk_en;                 // clock generation signals
	wire slave_wait;
//	reg [15:0] cnt = clk_cnt;   // clock divider counter (simulation)
	reg [15:0] cnt;             // clock divider counter (synthesis)

	// state machine variable
	reg [16:0] c_state; 

	//
	// module body
	//

	// whenever the slave is not ready it can delay the cycle by pulling SCL low
	// delay scl_oen
	always @(posedge clk)
	  dscl_oen <= #1 scl_oen;

	assign slave_wait = dscl_oen && !sSCL;


	// generate clk enable signal
	always @(posedge clk or negedge nReset)
	  if(~nReset)
	    begin
	        cnt    <= #1 16'h0;
	        clk_en <= #1 1'b1;
	    end
	  else if (rst)
	    begin
	        cnt    <= #1 16'h0;
	        clk_en <= #1 1'b1;
	    end
	  else if ( ~|cnt || ~ena)
	    if (~slave_wait)
	      begin
	          cnt    <= #1 clk_cnt;
	          clk_en <= #1 1'b1;
	      end
	    else
	      begin
	          cnt    <= #1 cnt;
	          clk_en <= #1 1'b0;
	      end
	  else
	    begin
                cnt    <= #1 cnt - 16'h1;
	        clk_en <= #1 1'b0;
	    end


	// generate bus status controller
	reg dSCL, dSDA;
	reg sta_condition;
	reg sto_condition;

	// synchronize SCL and SDA inputs
	// reduce metastability risc
	always @(posedge clk or negedge nReset)
	  if (~nReset)
	    begin
	        sSCL <= #1 1'b1;
	        sSDA <= #1 1'b1;

	        dSCL <= #1 1'b1;
	        dSDA <= #1 1'b1;
	    end
	  else if (rst)
	    begin
	        sSCL <= #1 1'b1;
	        sSDA <= #1 1'b1;

	        dSCL <= #1 1'b1;
	        dSDA <= #1 1'b1;
	    end
	  else
	    begin
	        sSCL <= #1 scl_i;
	        sSDA <= #1 sda_i;

	        dSCL <= #1 sSCL;
	        dSDA <= #1 sSDA;
	    end

	// detect start condition => detect falling edge on SDA while SCL is high
	// detect stop condition => detect rising edge on SDA while SCL is high
	always @(posedge clk or negedge nReset)
	  if (~nReset)
	    begin
	        sta_condition <= #1 1'b0;
	        sto_condition <= #1 1'b0;
	    end
	  else if (rst)
	    begin
	        sta_condition <= #1 1'b0;
	        sto_condition <= #1 1'b0;
	    end
	  else
	    begin
	        sta_condition <= #1 ~sSDA &  dSDA & sSCL;
	        sto_condition <= #1  sSDA & ~dSDA & sSCL;
	    end

	// generate i2c bus busy signal
	always @(posedge clk or negedge nReset)
	  if(!nReset)
	    busy <= #1 1'b0;
	  else if (rst)
	    busy <= #1 1'b0;
	  else
	    busy <= #1 (sta_condition | busy) & ~sto_condition;

	// generate arbitration lost signal
	// aribitration lost when:
	// 1) master drives SDA high, but the i2c bus is low
	// 2) stop detected while not requested
	reg cmd_stop;
	always @(posedge clk or negedge nReset)
	  if (~nReset)
	    cmd_stop <= #1 1'b0;
	  else if (rst)
	    cmd_stop <= #1 1'b0;
	  else if (clk_en)
	    cmd_stop <= #1 cmd == `I2C_CMD_STOP;

	always @(posedge clk or negedge nReset)
	  if (~nReset)
	    al <= #1 1'b0;
	  else if (rst)
	    al <= #1 1'b0;
	  else
	    al <= #1 (sda_chk & ~sSDA & sda_oen) | (|c_state & sto_condition & ~cmd_stop);


	// generate dout signal (store SDA on rising edge of SCL)
	always @(posedge clk)
	  if(sSCL & ~dSCL)
	    dout <= #1 sSDA;

	// generate statemachine

	// nxt_state decoder
	parameter [16:0] idle    = 17'b0_0000_0000_0000_0000;
	parameter [16:0] start_a = 17'b0_0000_0000_0000_0001;
	parameter [16:0] start_b = 17'b0_0000_0000_0000_0010;
	parameter [16:0] start_c = 17'b0_0000_0000_0000_0100;
	parameter [16:0] start_d = 17'b0_0000_0000_0000_1000;
	parameter [16:0] start_e = 17'b0_0000_0000_0001_0000;
	parameter [16:0] stop_a  = 17'b0_0000_0000_0010_0000;
	parameter [16:0] stop_b  = 17'b0_0000_0000_0100_0000;
	parameter [16:0] stop_c  = 17'b0_0000_0000_1000_0000;
	parameter [16:0] stop_d  = 17'b0_0000_0001_0000_0000;
	parameter [16:0] rd_a    = 17'b0_0000_0010_0000_0000;
	parameter [16:0] rd_b    = 17'b0_0000_0100_0000_0000;
	parameter [16:0] rd_c    = 17'b0_0000_1000_0000_0000;
	parameter [16:0] rd_d    = 17'b0_0001_0000_0000_0000;
	parameter [16:0] wr_a    = 17'b0_0010_0000_0000_0000;
	parameter [16:0] wr_b    = 17'b0_0100_0000_0000_0000;
	parameter [16:0] wr_c    = 17'b0_1000_0000_0000_0000;
	parameter [16:0] wr_d    = 17'b1_0000_0000_0000_0000;

	// c_state bit map (one-hot; idle is the all-zero value):
	// 0 start_a 1 start_b 2 start_c 3 start_d 4 start_e
	// 5 stop_a  6 stop_b  7 stop_c  8 stop_d
	// 9 rd_a   10 rd_b   11 rd_c   12 rd_d
	// 13 wr_a  14 wr_b   15 wr_c   16 wr_d
	//
	// Reachable-state decode: this FSM is a shared idle dispatch feeding
	// four independent one-bit shift chains that always return to idle.
	// c_state is one-hot-or-idle for every state reached from reset (idle
	// sets at most one bit; every non-idle state has exactly one successor
	// bit below), so each next-state bit and each output reduces to reading
	// a handful of individual bits instead of a 17-way exact-match decode.
	wire idle_st = ~(|c_state);

	wire [16:0] nstate;
	assign nstate[0]  = idle_st & (cmd == `I2C_CMD_START); // -> start_a
	assign nstate[1]  = c_state[0];                        // start_a -> start_b
	assign nstate[2]  = c_state[1];                        // start_b -> start_c
	assign nstate[3]  = c_state[2];                        // start_c -> start_d
	assign nstate[4]  = c_state[3];                        // start_d -> start_e
	assign nstate[5]  = idle_st & (cmd == `I2C_CMD_STOP);  // -> stop_a
	assign nstate[6]  = c_state[5];                        // stop_a -> stop_b
	assign nstate[7]  = c_state[6];                        // stop_b -> stop_c
	assign nstate[8]  = c_state[7];                        // stop_c -> stop_d
	assign nstate[9]  = idle_st & (cmd == `I2C_CMD_READ);  // -> rd_a
	assign nstate[10] = c_state[9];                        // rd_a -> rd_b
	assign nstate[11] = c_state[10];                       // rd_b -> rd_c
	assign nstate[12] = c_state[11];                       // rd_c -> rd_d
	assign nstate[13] = idle_st & (cmd == `I2C_CMD_WRITE); // -> wr_a
	assign nstate[14] = c_state[13];                       // wr_a -> wr_b
	assign nstate[15] = c_state[14];                       // wr_b -> wr_c
	assign nstate[16] = c_state[15];                       // wr_c -> wr_d
	// (start_e, stop_d, rd_d, wr_d have no successor bit below: with only
	// that bit set, every nstate[] term above is 0, so next c_state is
	// idle, matching each chain's terminal branch in the original case.)

	// scl_oen: 1 in start_b/c/d, stop_b/c/d, rd_b/c, wr_b/c; 0 in start_e,
	// stop_a, rd_a/d, wr_a/d; held in idle and start_a (only these two hold
	// scl_oen in the original case).
	wire scl_grp1 = c_state[1] | c_state[2]  | c_state[3]  |
	                c_state[6] | c_state[7]  | c_state[8]  |
	                c_state[10]| c_state[11] |
	                c_state[14]| c_state[15];
	wire hold_scl = idle_st | c_state[0];

	// sda_oen: 1 in start_a/b, stop_d, rd_a/b/c/d; 0 in start_c/d/e,
	// stop_a/b/c; din in wr_a/b/c/d; held only in idle.
	wire sda_grp1 = c_state[0] | c_state[1] | c_state[8]  |
	                c_state[9] | c_state[10]| c_state[11] | c_state[12];
	wire wr_grp   = c_state[13]| c_state[14]| c_state[15] | c_state[16];
	wire hold_sda = idle_st;

	// cmd_ack pulses only on the last state of each of the four chains.
	wire ack_grp = c_state[4] | c_state[8] | c_state[12] | c_state[16];

	// sda_chk is set only in wr_b/wr_c, 0 everywhere else including idle.
	wire chk_grp = c_state[14] | c_state[15];

	always @(posedge clk or negedge nReset)
	  if (!nReset)
	    begin
	        c_state <= #1 idle;
	        cmd_ack <= #1 1'b0;
	        scl_oen <= #1 1'b1;
	        sda_oen <= #1 1'b1;
	        sda_chk <= #1 1'b0;
	    end
	  else if (rst | al)
	    begin
	        c_state <= #1 idle;
	        cmd_ack <= #1 1'b0;
	        scl_oen <= #1 1'b1;
	        sda_oen <= #1 1'b1;
	        sda_chk <= #1 1'b0;
	    end
	  else
	    begin
	        cmd_ack   <= #1 1'b0; // default no command acknowledge + assert cmd_ack only 1clk cycle

	        if (clk_en)
	          begin
	              c_state <= #1 nstate;
	              cmd_ack <= #1 ack_grp;
	              scl_oen <= #1 hold_scl ? scl_oen : scl_grp1;
	              sda_oen <= #1 hold_sda ? sda_oen : (wr_grp ? din : sda_grp1);
	              sda_chk <= #1 chk_grp;
	          end
	    end


	// assign scl and sda output (always gnd)
	assign scl_o = 1'b0;
	assign sda_o = 1'b0;

endmodule