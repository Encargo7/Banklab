`timescale 1ns/1ps
module tb_scratchpad;
    parameter integer BANKED = 1;
    parameter integer HASHED = 0;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst = 1'b1;
    reg [3:0] req_valid = 0;
    wire [3:0] req_ready;
    reg [23:0] req_addr = 0;
    reg [3:0] req_write = 0;
    reg [127:0] req_wdata = 0;
    wire [3:0] rsp_valid;
    wire [127:0] rsp_rdata;

    banked_scratchpad #(.BANKED(BANKED), .HASHED(HASHED)) dut (
        .clk(clk), .rst(rst), .req_valid(req_valid), .req_ready(req_ready),
        .req_addr(req_addr), .req_write(req_write), .req_wdata(req_wdata),
        .rsp_valid(rsp_valid), .rsp_rdata(rsp_rdata)
    );

    reg [31:0] golden_mem [0:63];
    integer csv_fd, lane, scenario, batch, batches, ncycles;
    integer total_cycles [0:4];
    integer total_requests = 0;
    reg [1023:0] csv_file;
    reg [1023:0] vcd_file;

    function integer make_address;
        input integer sc;
        input integer bat;
        input integer ln;
        begin
            case (sc)
                0: make_address = ((bat * 4) + ln) % 64; // contiguous
                1: make_address = (bat + ln * 4) % 64;   // stride-4
                2: make_address = (bat + ln * 8) % 64;   // stride-8
                3: make_address = (bat*19 + ln*(7 + bat%5)) % 64; // mixed
                4: make_address = (bat * 4 + ln) % 64;   // readback sweep
                default: make_address = 0;
            endcase
        end
    endfunction

    // One batch = four requests offered at once; each lane retains its
    // address, operation, and data until req_ready grants that lane.
    task automatic run_batch;
        input integer sc;
        input integer bat;
        reg [3:0] accepted;
        reg [3:0] expected_valid;
        reg [127:0] expected_data;
        integer ln, addr, cycle;
        begin
            @(negedge clk);
            req_valid = 4'b1111;
            for (ln = 0; ln < 4; ln = ln + 1) begin
                req_addr[ln*6 +: 6] = make_address(sc, bat, ln);
                req_write[ln] = (sc == 4) ? 1'b0 : (((bat+ln*3+sc) % 4) == 0);
                req_wdata[ln*32 +: 32] = 32'hAB000000 + sc*100000 + bat*100 + ln;
            end
            begin : completed_batch
                for (cycle = 1; cycle <= 8; cycle = cycle + 1) begin
                    @(posedge clk);
                    accepted = req_valid & req_ready;
                    expected_valid = accepted;
                    expected_data = 128'b0;
                    if (accepted == 0)
                        $fatal(1, "No progress: sc=%0d batch=%0d", sc, bat);
                    for (ln = 0; ln < 4; ln = ln + 1) begin
                        if (accepted[ln]) begin
                            addr = req_addr[ln*6 +: 6];
                            if (req_write[ln])
                                golden_mem[addr] = req_wdata[ln*32 +: 32];
                            else
                                expected_data[ln*32 +: 32] = golden_mem[addr];
                            total_requests = total_requests + 1;
                        end
                    end
                    #1; // Observe values after nonblocking assignments.
                    if (rsp_valid !== expected_valid)
                        $fatal(1, "Response-valid mismatch: got %b expected %b", rsp_valid, expected_valid);
                    for (ln = 0; ln < 4; ln = ln + 1) begin
                        if (expected_valid[ln] &&
                            (rsp_rdata[ln*32 +: 32] !== expected_data[ln*32 +: 32]))
                            $fatal(1, "Data mismatch at sc=%0d batch=%0d lane=%0d: got %h expected %h",
                                sc, bat, ln, rsp_rdata[ln*32 +: 32], expected_data[ln*32 +: 32]);
                    end
                    @(negedge clk);
                    req_valid = req_valid & ~accepted;
                    if (req_valid == 4'b0000) begin
                        total_cycles[sc] = total_cycles[sc] + cycle;
                        if (csv_fd != 0)
                            $fdisplay(csv_fd, "%0d,%0d,%0d,%0d,%0d", BANKED, HASHED, sc, bat, cycle);
                        disable completed_batch;
                    end
                end
                $fatal(1, "Batch exceeded 8 cycles: sc=%0d batch=%0d", sc, bat);
            end
        end
    endtask

    initial begin
        csv_fd = 0;
        for (lane = 0; lane < 64; lane = lane + 1)
            golden_mem[lane] = 32'b0;
        for (lane = 0; lane < 5; lane = lane + 1)
            total_cycles[lane] = 0;
        if ($value$plusargs("CSV=%s", csv_file)) begin
            csv_fd = $fopen(csv_file, "w");
            if (csv_fd == 0)
                $fatal(1, "Unable to open CSV: %s", csv_file);
            $fdisplay(csv_fd, "banked,hashed,scenario,batch,cycles");
        end
        if ($value$plusargs("VCD=%s", vcd_file)) begin
            $dumpfile(vcd_file);
            $dumpvars(0, tb_scratchpad);
        end
        repeat (3) @(negedge clk);
        rst = 1'b0;
        for (scenario = 0; scenario < 4; scenario = scenario + 1) begin
            for (batch = 0; batch < 40; batch = batch + 1)
                run_batch(scenario, batch);
            $display("CASE banked=%0d hashed=%0d scenario=%0d batches=40 service_cycles=%0d",
                BANKED, HASHED, scenario, total_cycles[scenario]);
        end
        // Read back every logical word, independently of the bank mapping.
        for (batch = 0; batch < 16; batch = batch + 1)
            run_batch(4, batch);
        $display("PASS banked=%0d hashed=%0d requests=%0d readback_cycles=%0d",
            BANKED, HASHED, total_requests, total_cycles[4]);
        if (csv_fd != 0) $fclose(csv_fd);
        $finish;
    end
    initial begin
        #100000;
        $fatal(1, "Global simulation timeout");
    end
endmodule
