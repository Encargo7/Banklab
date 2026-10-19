`timescale 1ns/1ps
// BankLab: GPU-inspired four-bank scratchpad with four independent request lanes.
// This is educational RTL: not an NVIDIA GPU memory controller.
// Addresses are WORD indices 0..63 (not byte addresses).
// Exactly one request can be accepted by each bank in one clock cycle.
// For every accepted request, the response is registered on the SAME rising
// edge and observed immediately AFTER that edge (one registered stage).
// Responses are always consumed; there is no response backpressure.
// BANKED=0: reference single-issue memory engine (max 1 request/cycle).
// BANKED=1: parallel per-bank arbitration (max 4 requests/cycle).
// HASHED=0: bank=address[1:0]
// HASHED=1: bank=address[1:0] XOR address[3:2]
// Keep HASHED fixed while accessing a populated memory: changing it would
// remap physical addresses and invalidate stored data.
module banked_scratchpad #(
    parameter integer BANKED = 1,
    parameter integer HASHED = 0
)(
    input  wire         clk,
    input  wire         rst,
    input  wire [3:0]   req_valid,
    output reg  [3:0]   req_ready,
    input  wire [23:0]  req_addr,   // lane i: [i*6 +: 6]
    input  wire [3:0]   req_write,
    input  wire [127:0] req_wdata,  // lane i: [i*32 +: 32]
    output reg  [3:0]   rsp_valid,
    output reg  [127:0] rsp_rdata   // lane i: [i*32 +: 32]
);
    // Four banks, each with 16 x 32-bit words = 256 bytes total.
    reg [31:0] memory [0:3][0:15];
    reg [1:0] rr_ptr [0:3];
    reg [1:0] rr_serial;

    function [1:0] bank_of;
        input [5:0] addr;
        begin
            if (HASHED != 0)
                bank_of = addr[1:0] ^ addr[3:2];
            else
                bank_of = addr[1:0];
        end
    endfunction

    // -1 means no grant for that physical bank this cycle.
    integer selected [0:3];
    integer b, k, lane, chosen_bank;
    reg have_serial_winner;

    always @* begin
        req_ready = 4'b0000;
        have_serial_winner = 1'b0;
        chosen_bank = 0;
        for (b = 0; b < 4; b = b + 1)
            selected[b] = -1;

        if (BANKED != 0) begin
            // Each bank independently scans the four lanes in rotating order.
            for (b = 0; b < 4; b = b + 1) begin
                for (k = 0; k < 4; k = k + 1) begin
                    lane = (rr_ptr[b] + k) % 4;
                    if ((selected[b] == -1) && req_valid[lane] &&
                        (bank_of(req_addr[lane*6 +: 6]) == b)) begin
                        selected[b] = lane;
                        req_ready[lane] = 1'b1;
                    end
                end
            end
        end else begin
            // Baseline: only one request globally per clock cycle.
            for (k = 0; k < 4; k = k + 1) begin
                lane = (rr_serial + k) % 4;
                if (!have_serial_winner && req_valid[lane]) begin
                    chosen_bank = bank_of(req_addr[lane*6 +: 6]);
                    selected[chosen_bank] = lane;
                    req_ready[lane] = 1'b1;
                    have_serial_winner = 1'b1;
                end
            end
        end
    end

    integer x, y, bank_idx, row_idx, win_lane;
    always @(posedge clk) begin
        if (rst) begin
            rr_serial <= 2'd0;
            rsp_valid <= 4'b0000;
            rsp_rdata <= 128'b0;
            for (x = 0; x < 4; x = x + 1) begin
                rr_ptr[x] <= 2'd0;
                for (y = 0; y < 16; y = y + 1)
                    memory[x][y] <= 32'b0;
            end
        end else begin
            rsp_valid <= req_valid & req_ready;
            rsp_rdata <= 128'b0;
            for (bank_idx = 0; bank_idx < 4; bank_idx = bank_idx + 1) begin
                if (selected[bank_idx] >= 0) begin
                    win_lane = selected[bank_idx];
                    row_idx = req_addr[win_lane*6 + 2 +: 4];
                    if (req_write[win_lane]) begin
                        memory[bank_idx][row_idx] <= req_wdata[win_lane*32 +: 32];
                    end else begin
                        rsp_rdata[win_lane*32 +: 32] <= memory[bank_idx][row_idx];
                    end
                    rr_ptr[bank_idx] <= (win_lane + 1) % 4;
                    if (BANKED == 0)
                        rr_serial <= (win_lane + 1) % 4;
                end
            end
        end
    end
endmodule
