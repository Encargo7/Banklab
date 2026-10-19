#!/usr/bin/env python3
"""Compare actual Icarus RTL CSV traces, per batch, with Python reference."""
import csv
from pathlib import Path
from bank_model import run_experiments

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'


def verify() -> None:
    cases = 0
    for banked in (0,1):
        for hashed in (0,1):
            path = RESULTS / f'rtl_b{banked}_h{hashed}.csv'
            if not path.exists():
                raise SystemExit(f'Missing RTL result {path.name}. Run scripts/run_all.sh or .ps1 first.')
            with path.open(newline='', encoding='utf8') as f:
                actual = list(csv.DictReader(f))
            expected = run_experiments(bool(banked), bool(hashed))
            if len(actual) != len(expected):
                raise AssertionError(f'{path.name}: got {len(actual)} batches, expected {len(expected)}')
            for row, ref in zip(actual, expected):
                for key in ('banked', 'hashed', 'scenario', 'batch', 'cycles'):
                    if int(row[key]) != ref[key]:
                        raise AssertionError(f'{path.name}: batch mismatch at {key}: RTL={row} model={ref}')
                cases += 1
            print(f'PASS: RTL CSV matches reference: {path.name} ({len(actual)} batches)')
    print(f'PASS: verified {cases} model/RTL batch-cycle comparisons')


if __name__ == '__main__':
    verify()
