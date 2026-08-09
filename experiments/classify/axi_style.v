// AXI-style prefixed handshake naming: the handshake words are embedded in a
// channel prefix rather than standing alone. Tests substring matching.
module axi_style #(
    parameter W = 8
) (
    input  wire            aclk,
    input  wire            aresetn,
    input  wire            s_axis_tvalid,
    output wire            s_axis_tready,
    input  wire [W-1:0]    s_axis_tdata_a,
    input  wire [W-1:0]    s_axis_tdata_b,
    output reg             m_axis_tvalid,
    input  wire            m_axis_tready,
    output reg  [2*W-1:0]  m_axis_tdata
);
    assign s_axis_tready = !m_axis_tvalid || m_axis_tready;

    always @(posedge aclk) begin
        if (!aresetn) begin
            m_axis_tvalid <= 1'b0;
            m_axis_tdata  <= {(2*W){1'b0}};
        end else if (s_axis_tvalid && s_axis_tready) begin
            m_axis_tvalid <= 1'b1;
            m_axis_tdata  <= s_axis_tdata_a * s_axis_tdata_b;
        end else if (m_axis_tready) begin
            m_axis_tvalid <= 1'b0;
        end
    end
endmodule
