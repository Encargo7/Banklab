"""Executable reference model for the four-bank educational scratchpad.

No GPU hardware, CUDA installation, or third-party Python package is needed.
Addresses are indices 0..63 of 32-bit words (not byte addresses).
"""
from __future__ import annotations
from dataclasses import dataclass

SCENARIO_NAMES = ('contiguous', 'stride4', 'stride8', 'mixed', 'readback')


def make_address(scenario: int, batch: int, lane: int) -> int:
    if scenario == 0:
        return (batch * 4 + lane) % 64
    if scenario == 1:
        return (batch + lane * 4) % 64
    if scenario == 2:
        return (batch + lane * 8) % 64
    if scenario == 3:
        return (batch * 19 + lane * (7 + batch % 5)) % 64
    if scenario == 4:
        return (batch * 4 + lane) % 64
    raise ValueError(f'Unknown scenario: {scenario}')


def bank_of(addr: int, hashed: bool) -> int:
    if not 0 <= addr < 64:
        raise ValueError(f'word address out of range: {addr}')
    return (addr & 3) ^ ((addr >> 2) & 3) if hashed else addr & 3


@dataclass(frozen=True)
class Request:
    addr: int
    write: bool
    data: int


def build_batch(scenario: int, batch: int) -> list[Request]:
    return [
        Request(
            addr=make_address(scenario, batch, lane),
            write=False if scenario == 4 else (batch + 3 * lane + scenario) % 4 == 0,
            data=0xAB000000 + scenario * 100000 + batch * 100 + lane,
        )
        for lane in range(4)
    ]


class ScratchpadModel:
    """Architectural request service + functional memory golden model.

    Four request lanes. A granted lane is serviced exactly once. One bank can
    serve one lane each cycle; the serial variant serves one lane globally.
    Each memory location is associated with a logical address; hashing changes
    its physical bank, not its logical contents.
    """

    def __init__(self, banked: bool, hashed: bool) -> None:
        self.banked = banked
        self.hashed = hashed
        self.memory = [0] * 64
        self.rr_ptr = [0] * 4
        self.rr_serial = 0
        self.served_count = [0] * 4

    def run_batch(self, requests: list[Request]) -> tuple[int, dict[int, int]]:
        if len(requests) != 4:
            raise ValueError('Exactly four lane requests are required')
        pending = set(range(4))
        responses: dict[int, int] = {}
        cycles = 0
        while pending:
            cycles += 1
            if cycles > 8:
                raise AssertionError('Unbounded/failing progress')
            winners: dict[int, int] = {}
            if self.banked:
                for bank in range(4):
                    for offset in range(4):
                        lane = (self.rr_ptr[bank] + offset) % 4
                        if lane in pending and bank_of(requests[lane].addr, self.hashed) == bank:
                            winners[bank] = lane
                            break
            else:
                for offset in range(4):
                    lane = (self.rr_serial + offset) % 4
                    if lane in pending:
                        winners[bank_of(requests[lane].addr, self.hashed)] = lane
                        break
            if not winners:
                raise AssertionError('No progress despite pending requests')
            for bank, lane in winners.items():
                request = requests[lane]
                if request.write:
                    self.memory[request.addr] = request.data & 0xFFFFFFFF
                    responses[lane] = 0  # write acknowledge
                else:
                    responses[lane] = self.memory[request.addr]
                self.served_count[lane] += 1
                self.rr_ptr[bank] = (lane + 1) % 4
                if not self.banked:
                    self.rr_serial = (lane + 1) % 4
                pending.remove(lane)
        return cycles, responses


def run_experiments(banked: bool, hashed: bool) -> list[dict[str, int | str]]:
    dut = ScratchpadModel(banked, hashed)
    records = []
    for scenario in range(5):
        batches = 16 if scenario == 4 else 40
        for batch in range(batches):
            cycles, responses = dut.run_batch(build_batch(scenario, batch))
            assert len(responses) == 4
            records.append({
                'banked': int(banked), 'hashed': int(hashed),
                'scenario': scenario, 'scenario_name': SCENARIO_NAMES[scenario],
                'batch': batch, 'cycles': cycles,
            })
    assert sum(dut.served_count) == 4 * (4 * 40 + 16)
    return records
