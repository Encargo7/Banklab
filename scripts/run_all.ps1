$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
New-Item -ItemType Directory -Force -Path build, results | Out-Null
if (-not (Get-Command iverilog -ErrorAction SilentlyContinue)) { throw 'Icarus Verilog (iverilog) not found on PATH. See "How to run" in README.md.' }
if (-not (Get-Command vvp -ErrorAction SilentlyContinue)) { throw 'vvp not found on PATH. See "How to run" in README.md.' }
python -m unittest discover -s model -p 'test_*.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed' }
python model/run_benchmarks.py
if ($LASTEXITCODE -ne 0) { throw 'Python benchmark failed' }
foreach ($banked in 0,1) {
  foreach ($hashed in 0,1) {
    $name = "b${banked}_h${hashed}"
    Write-Host "=== RTL test: $name ==="
    & iverilog -g2012 -s tb_scratchpad "-Ptb_scratchpad.BANKED=$banked" "-Ptb_scratchpad.HASHED=$hashed" -o "build/$name.vvp" rtl/banked_scratchpad.sv tb/tb_scratchpad.sv
    if ($LASTEXITCODE -ne 0) { throw "Icarus compile failed: $name" }
    & vvp "build/$name.vvp" "+CSV=results/rtl_$name.csv" "+VCD=build/$name.vcd"
    if ($LASTEXITCODE -ne 0) { throw "RTL simulation failed: $name" }
  }
}
python model/verify_rtl.py
if ($LASTEXITCODE -ne 0) { throw 'RTL comparison failed' }
Write-Host 'ALL CHECKS PASSED' -ForegroundColor Green
