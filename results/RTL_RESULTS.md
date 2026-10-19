# RTL simulation results

Measured by simulating `rtl/banked_scratchpad.sv` with `tb/tb_scratchpad.sv`.

- **Simulator:** Icarus Verilog 12.0 (stable), Linux
- **Run:** `bash scripts/run_all.sh` on 2026-10-17
- **Outcome:** all four compile-time configurations passed the self-checking
  testbench (704 requests each), and every per-batch cycle count matched the
  independent Python model (176 batches x 4 configurations = 704 comparisons).

## Service cycles per batch (average over 40 batches)

Measured from the RTL simulation. Smaller is better.

| Access pattern | Serial baseline | 4-bank linear | 4-bank XOR |
|:--|--:|--:|--:|
| contiguous | 4.00 | 1.00 | 1.00 |
| stride4 | 4.00 | 4.00 | 1.00 |
| stride8 | 4.00 | 4.00 | 2.00 |
| mixed | 4.00 | 1.80 | 1.95 |

These match the Python model's predictions exactly (see `MODEL_RESULTS.md`).

## Run log (excerpt)

```text
Ran 8 tests in 0.030s
OK
CASE banked=0 hashed=0 scenario=0 batches=40 service_cycles=160
CASE banked=0 hashed=0 scenario=1 batches=40 service_cycles=160
CASE banked=0 hashed=0 scenario=2 batches=40 service_cycles=160
CASE banked=0 hashed=0 scenario=3 batches=40 service_cycles=160
PASS banked=0 hashed=0 requests=704 readback_cycles=64
CASE banked=0 hashed=1 scenario=0 batches=40 service_cycles=160
CASE banked=0 hashed=1 scenario=1 batches=40 service_cycles=160
CASE banked=0 hashed=1 scenario=2 batches=40 service_cycles=160
CASE banked=0 hashed=1 scenario=3 batches=40 service_cycles=160
PASS banked=0 hashed=1 requests=704 readback_cycles=64
CASE banked=1 hashed=0 scenario=0 batches=40 service_cycles=40
CASE banked=1 hashed=0 scenario=1 batches=40 service_cycles=160
CASE banked=1 hashed=0 scenario=2 batches=40 service_cycles=160
CASE banked=1 hashed=0 scenario=3 batches=40 service_cycles=72
PASS banked=1 hashed=0 requests=704 readback_cycles=16
CASE banked=1 hashed=1 scenario=0 batches=40 service_cycles=40
CASE banked=1 hashed=1 scenario=1 batches=40 service_cycles=40
CASE banked=1 hashed=1 scenario=2 batches=40 service_cycles=80
CASE banked=1 hashed=1 scenario=3 batches=40 service_cycles=78
PASS banked=1 hashed=1 requests=704 readback_cycles=16
PASS: RTL CSV matches reference: rtl_b0_h0.csv (176 batches)
PASS: RTL CSV matches reference: rtl_b0_h1.csv (176 batches)
PASS: RTL CSV matches reference: rtl_b1_h0.csv (176 batches)
PASS: RTL CSV matches reference: rtl_b1_h1.csv (176 batches)
PASS: verified 704 model/RTL batch-cycle comparisons
ALL CHECKS PASSED — refer to model/RTL comparison and VCD files.
```

## What this does and does not show

- Shows: functional correctness of reads/writes under all four configurations on
  the directed and mixed stimuli, and that the RTL's arbitration timing matches
  the reference model cycle for cycle.
- Does not show: formal proof of correctness, synthesis results, area, timing
  (frequency), power, FPGA behavior, or behavior of a real GPU.
