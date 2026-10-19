#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v iverilog >/dev/null 2>&1 || ! command -v vvp >/dev/null 2>&1; then
  echo 'ERROR: Icarus Verilog (iverilog, vvp) not found on PATH. See "How to run" in README.md.' >&2
  exit 1
fi
mkdir -p build results
python3 -m unittest discover -s model -p 'test_*.py' -v
python3 model/run_benchmarks.py
for banked in 0 1; do
  for hashed in 0 1; do
    name="b${banked}_h${hashed}"
    echo "=== RTL test: ${name} ==="
    iverilog -g2012 -s tb_scratchpad \
      -Ptb_scratchpad.BANKED="$banked" -Ptb_scratchpad.HASHED="$hashed" \
      -o "build/${name}.vvp" rtl/banked_scratchpad.sv tb/tb_scratchpad.sv
    vvp "build/${name}.vvp" "+CSV=results/rtl_${name}.csv" "+VCD=build/${name}.vcd"
  done
done
python3 model/verify_rtl.py
echo 'ALL CHECKS PASSED — refer to model/RTL comparison and VCD files.'
