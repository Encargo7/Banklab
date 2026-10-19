import unittest
from bank_model import Request, ScratchpadModel, bank_of, build_batch, run_experiments


class ControllerModelTests(unittest.TestCase):
    def test_bank_mapping_is_bijective_over_64_addresses(self):
        for hashed in (False, True):
            locations = [(bank_of(addr, hashed), addr >> 2) for addr in range(64)]
            self.assertEqual(len(set(locations)), 64)

    def test_no_conflict_parallel_single_cycle(self):
        requests = [Request(i, False, 0) for i in range(4)]
        self.assertEqual(ScratchpadModel(True, False).run_batch(requests)[0], 1)

    def test_same_bank_four_cycles_without_hash(self):
        requests = [Request(4 * i, False, 0) for i in range(4)]
        self.assertEqual(ScratchpadModel(True, False).run_batch(requests)[0], 4)
        self.assertEqual(ScratchpadModel(True, True).run_batch(requests)[0], 1)

    def test_stride_eight_halves_conflict_with_hash(self):
        requests = [Request(8 * i, False, 0) for i in range(4)]
        self.assertEqual(ScratchpadModel(True, False).run_batch(requests)[0], 4)
        self.assertEqual(ScratchpadModel(True, True).run_batch(requests)[0], 2)

    def test_same_address_must_serialize_no_broadcast(self):
        requests = [Request(7, False, 0) for _ in range(4)]
        for hashed in (False, True):
            self.assertEqual(ScratchpadModel(True, hashed).run_batch(requests)[0], 4)

    def test_read_write_and_lane_order_preserved(self):
        model = ScratchpadModel(True, False)
        req = [Request(0, True, 99), Request(1, True, 41),
               Request(2, False, 0), Request(3, False, 0)]
        _, replies = model.run_batch(req)
        self.assertEqual(replies, {0: 0, 1: 0, 2: 0, 3: 0})
        _, replies = model.run_batch([Request(i, False, 0) for i in range(4)])
        self.assertEqual(replies, {0: 99, 1: 41, 2: 0, 3: 0})

    def test_all_scenarios_complete_every_configuration(self):
        for banked in (False, True):
            for hashed in (False, True):
                records = run_experiments(banked, hashed)
                self.assertEqual(len(records), 176)
                self.assertTrue(all(1 <= r['cycles'] <= 4 for r in records))
                if not banked:
                    self.assertTrue(all(r['cycles'] == 4 for r in records))

    def test_round_robin_serves_every_lane_equally(self):
        model = ScratchpadModel(True, False)
        for batch in range(200):
            model.run_batch(build_batch(1, batch))
        self.assertEqual(model.served_count, [200, 200, 200, 200])


if __name__ == '__main__':
    unittest.main()
