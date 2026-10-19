#!/usr/bin/env python3
"""Create model-generated CSV, PNG comparison and Markdown results.

Values are from an executable Python architectural MODEL, not measured GPU
performance or verified RTL unless separately checked via verify_rtl.py.
"""
from __future__ import annotations
import csv
from pathlib import Path
from collections import defaultdict
from bank_model import run_experiments, SCENARIO_NAMES

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'


def write_outputs() -> None:
    RESULTS.mkdir(exist_ok=True)
    all_rows = []
    for banked in (False, True):
        for hashed in (False, True):
            all_rows.extend(run_experiments(banked, hashed))
    path = RESULTS / 'model_batch_cycles.csv'
    with path.open('w', newline='', encoding='utf8') as f:
        out = csv.DictWriter(f, fieldnames=['banked', 'hashed', 'scenario', 'scenario_name', 'batch', 'cycles'])
        out.writeheader()
        out.writerows(all_rows)

    grouped: dict[tuple[int,int,int],list[int]] = defaultdict(list)
    for row in all_rows:
        grouped[(row['banked'],row['hashed'],row['scenario'])].append(row['cycles'])

    variants = ((0,0,'Serial baseline'),(1,0,'4-bank: linear'),(1,1,'4-bank: XOR'))
    summary = []
    for sc in range(4):
        d = {'pattern': SCENARIO_NAMES[sc]}
        for b,h,label in variants:
            cycles = grouped[(b,h,sc)]
            d[label] = sum(cycles) / len(cycles)
        summary.append(d)

    with (RESULTS / 'model_summary.csv').open('w', newline='', encoding='utf8') as f:
        writer = csv.DictWriter(f, fieldnames=['pattern'] + [x[2] for x in variants])
        writer.writeheader()
        writer.writerows(summary)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        x = np.arange(4)
        width = 0.25
        fig, ax = plt.subplots(figsize=(10, 5))
        for i, (_,_,name) in enumerate(variants):
            bars = ax.bar(x+(i-1)*width, [r[name] for r in summary], width, label=name)
            ax.bar_label(bars, fmt='%.2f', padding=3, fontsize=8)
        ax.set_xticks(x, ['Contiguous', 'Stride 4', 'Stride 8', 'Mixed'])
        ax.set_ylim(0, 4.8)
        ax.set_ylabel('Service cycles per four-request batch (lower is better)')
        ax.set_title('BankLab: model-predicted memory service cycles')
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=.2)
        fig.tight_layout()
        fig.savefig(RESULTS / 'model_comparison.png', dpi=170)
        plt.close(fig)
    except ImportError:
        print('Optional matplotlib/numpy missing: skipped model_comparison.png')

    lines = [
        '# Performance results — executable Python model',
        '',
        '> These are deterministic model-predicted service cycles, **not** measured GPU',
        '> performance. The RTL simulation reproduces them exactly (see RTL_RESULTS.md);',
        '> to re-check, run `scripts/run_all.sh` (or `run_all.ps1`) with Icarus Verilog.',
        '',
        'Each experiment contains 40 groups of four simultaneously offered requests.',
        'The model excludes test-driver idle cycles between groups. Smaller is better.',
        '',
        '| Access pattern | Serial baseline | 4-bank linear | 4-bank XOR |',
        '|:--|--:|--:|--:|'
    ]
    for r in summary:
        lines.append('| ' + r['pattern'] + ' | ' + ' | '.join(f'{r[label]:.2f}' for _,_,label in variants) + ' |')
    lines += ['',
        '## Interpretation',
        '',
        '- Different banks can be served in parallel, while competing requests to one bank serialize.',
        '- XOR address mapping distributes stride-4 word accesses in this 4-bank model.',
        '- The benefit depends on the access pattern: this does **not** universally improve throughput.',
        '- This hardware supports distinct accesses, not same-word read broadcast/multicast.',
        '- Address mapping is a hardware configuration parameter, **not** a runtime switch:',
        '  changing mapping after writing memory would require moving stored contents.',
        '',
        '![Model comparison](model_comparison.png)',
        '',
    ]
    (RESULTS / 'MODEL_RESULTS.md').write_text('\n'.join(lines), encoding='utf8')
    print('Wrote model_batch_cycles.csv, model_summary.csv, MODEL_RESULTS.md, and (if available) model_comparison.png')
    for row in summary:
        print(row)


if __name__ == '__main__':
    write_outputs()
