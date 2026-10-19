#!/usr/bin/env python3
"""Render docs/waveform_stride4.png from the simulator's VCD files.

Shows the first stride-4 batch (addresses 0, 4, 8, 12 for lane 0..3) under the
linear and XOR bank mappings. Each row is one lane's req_valid: the request
stays high until that lane is granted, so the number of cycles the rows stay
high is the number of service cycles for the batch.

Run after scripts/run_all.sh (or run_all.ps1) has produced build/*.vcd.
Requires matplotlib.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CLK_PS = 10_000          # 10 ns clock, VCD timescale is 1 ps
STRIDE4_FIRST_BATCH = 40  # contiguous scenario runs 40 batches first


def read_vcd(path: Path, wanted: set[str]) -> dict[str, list[tuple[int, int]]]:
    """Return {signal: [(time_ps, value), ...]} for top-level testbench signals."""
    ids: dict[str, str] = {}
    scope_depth = 0
    changes: dict[str, list[tuple[int, int]]] = {}
    now = 0
    in_defs = True
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if in_defs:
            if line.startswith('$scope'):
                scope_depth += 1
            elif line.startswith('$upscope'):
                scope_depth -= 1
            elif line.startswith('$var') and scope_depth == 1:
                parts = line.split()
                name = parts[4]
                if name in wanted:
                    ids[parts[3]] = name
                    changes[name] = []
            elif line.startswith('$enddefinitions'):
                in_defs = False
            continue
        if not line or line.startswith('$'):
            continue
        if line[0] == '#':
            now = int(line[1:])
        elif line[0] in 'bB':
            val, ident = line[1:].split()
            if ident in ids and 'x' not in val.lower() and 'z' not in val.lower():
                changes[ids[ident]].append((now, int(val, 2)))
        elif line[0] in '01' and line[1:] in ids:
            changes[ids[line[1:]]].append((now, int(line[0])))
    return changes


def value_at(series: list[tuple[int, int]], t: int) -> int:
    val = 0
    for when, v in series:
        if when > t:
            break
        val = v
    return val


def batch_start(valid: list[tuple[int, int]]) -> int:
    """Time of the Nth rise of req_valid to 4'b1111 (start of stride-4 batch 0)."""
    rises, prev = [], 0
    for when, v in valid:
        if v == 0b1111 and prev != 0b1111:
            rises.append(when)
        prev = v
    return rises[STRIDE4_FIRST_BATCH]


def draw(ax, vcd: Path, title: str, note: str) -> None:
    sig = read_vcd(vcd, {'req_valid', 'clk'})
    t0 = batch_start(sig['req_valid']) - CLK_PS // 2
    cycles = 5
    ts = list(range(t0, t0 + cycles * CLK_PS + 1, 500))
    # Stop drawing lanes once this batch is fully served (the testbench starts
    # the next batch right after, which would only add visual noise).
    t_start = t0 + CLK_PS // 2
    t_end = next(t for t, v in sig['req_valid'] if t > t_start and v == 0)
    nan = float('nan')
    ink, muted = '#1f2937', '#9ca3af'
    # clock row on top, then one row per lane
    ax.step([(t - t0) / 1000 for t in ts], [value_at(sig['clk'], t) * 0.6 + 5 for t in ts],
            where='post', color=muted, lw=1.2)
    ax.text(-0.3, 5.3, 'clk', ha='right', va='center', fontsize=9, color=ink)
    for lane in range(4):
        y0 = 3 - lane
        ys = [((value_at(sig['req_valid'], t) >> lane) & 1) * 0.6 + y0
              if t <= t_end + CLK_PS // 2 else nan for t in ts]
        ax.step([(t - t0) / 1000 for t in ts], ys, where='post', color='#2563eb', lw=2)
        ax.text(-0.3, y0 + 0.3, f'lane {lane} req_valid', ha='right', va='center',
                fontsize=9, color=ink)
    ax.set_xlim(0, cycles * 10)
    ax.set_ylim(-0.3, 6)
    ax.set_yticks([])
    ax.set_xticks(range(0, cycles * 10 + 1, 10))
    ax.set_xticklabels([f'{c}' for c in range(cycles + 1)], fontsize=9, color=ink)
    ax.set_xlabel('clock cycles after batch offered', fontsize=9, color=ink)
    for x in range(0, cycles * 10 + 1, 10):
        ax.axvline(x, color='#e5e7eb', lw=0.8, zorder=0)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.set_title(title, loc='left', fontsize=11, fontweight='bold', color=ink)
    ax.text(cycles * 10, 4.3, note, ha='right', va='center', fontsize=10,
            fontweight='bold', color='#2563eb')


def main() -> None:
    build = ROOT / 'build'
    need = [build / 'b1_h0.vcd', build / 'b1_h1.vcd']
    missing = [p.name for p in need if not p.exists()]
    if missing:
        raise SystemExit(f'Missing {missing}. Run scripts/run_all.sh (or .ps1) first.')
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.2))
    draw(axes[0], need[0], 'Linear mapping: stride-4 batch (addresses 0, 4, 8, 12)',
         'all four hit bank 0: 4 service cycles')
    draw(axes[1], need[1], 'XOR mapping: same batch',
         'four different banks: 1 service cycle')
    fig.tight_layout(h_pad=2.0)
    out = ROOT / 'docs' / 'waveform_stride4.png'
    fig.savefig(out, dpi=150, facecolor='white')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
