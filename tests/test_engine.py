"""Tests for the DataCal calculation core. Run: python -m unittest -v

Every numeric expectation here is hand-calculated in the comments so the
arithmetic can be audited independently of the code.
"""

import unittest

from datacal import (
    Campaign,
    Deployment,
    Instrument,
    Leg,
    calculate,
    campaign_from_dict,
    to_madmp,
)
from datacal import units


class TestUnits(unittest.TestCase):
    def test_human_bytes_decimal_si(self):
        self.assertEqual(units.human_bytes(864_000_000_000), "864.00 GB")
        self.assertEqual(units.human_bytes(1_500_000_000_000), "1.50 TB")
        self.assertEqual(units.human_bytes(0), "0.00 B")

    def test_bytes_to_mbps_uses_bits(self):
        # 1 MB in 1 second = 8 Mbit in 1 s = 8 Mbps (not 1).
        self.assertAlmostEqual(units.bytes_to_mbps(1_000_000, 1), 8.0)

    def test_bandwidth_window_must_be_positive(self):
        with self.assertRaises(ValueError):
            units.bytes_to_mbps(1000, 0)


class TestRawRate(unittest.TestCase):
    def test_sample_model_rate(self):
        # 4 ch * 100 Hz * 24 bit = 4*100*3 = 1200 B/s
        inst = Instrument(id="s", name="sensor", group="g", model="sample",
                          channels=4, sampling_hz=100, bit_depth=24)
        self.assertEqual(inst.raw_bytes_per_second(), 1200.0)

    def test_rate_model_rate(self):
        inst = Instrument(id="c", name="cam", group="g", model="rate",
                          data_rate_bytes_per_s=50_000_000)
        self.assertEqual(inst.raw_bytes_per_second(), 50_000_000.0)


class TestVolume(unittest.TestCase):
    def test_single_instrument_single_leg(self):
        # 1 MB/s * 10 days, duty 1.0, count 1, no compression/overhead
        # = 1_000_000 * 86_400 * 10 = 864_000_000_000 bytes = 864 GB
        camp = Campaign(
            title="t",
            legs=[Leg(id="L1", name="Leg 1", duration_days=10)],
            instruments=[Instrument(id="c", name="cam", group="optics",
                                    model="rate", data_rate_bytes_per_s=1_000_000)],
            deployments=[Deployment(instrument_id="c", leg_id="L1")],
        )
        r = calculate(camp)
        self.assertAlmostEqual(r.total_stored_bytes, 864_000_000_000)

    def test_duty_count_compression_overhead(self):
        # raw rate 1000 B/s; 1 day = 86400 s; duty 0.5; count 2
        # raw = 1000 * 86400 * 0.5 * 2 = 86_400_000
        # compression 2.0 -> /2 = 43_200_000 ; overhead 1.5 -> *1.5 = 64_800_000
        inst = Instrument(id="s", name="sensor", group="g", model="rate",
                          data_rate_bytes_per_s=1000, duty_cycle=0.5, count=2,
                          compression_ratio=2.0, overhead_factor=1.5)
        camp = Campaign(title="t",
                        legs=[Leg(id="L1", name="L1", duration_days=1)],
                        instruments=[inst],
                        deployments=[Deployment(instrument_id="s", leg_id="L1")])
        r = calculate(camp)
        self.assertAlmostEqual(r.total_stored_bytes, 64_800_000)

    def test_deployment_overrides_take_precedence(self):
        # instrument duty 1.0/count 1, but deployment overrides duty 0.25/count 4
        # raw = 1000 * 86400 * 0.25 * 4 = 86_400_000
        inst = Instrument(id="s", name="s", group="g", model="rate",
                          data_rate_bytes_per_s=1000, duty_cycle=1.0, count=1)
        camp = Campaign(title="t",
                        legs=[Leg(id="L1", name="L1", duration_days=1)],
                        instruments=[inst],
                        deployments=[Deployment(instrument_id="s", leg_id="L1",
                                                duty_cycle=0.25, count=4)])
        r = calculate(camp)
        self.assertAlmostEqual(r.total_stored_bytes, 86_400_000)

    def test_per_group_and_per_leg_aggregation(self):
        camp = Campaign(
            title="t",
            legs=[Leg(id="L1", name="L1", duration_days=1),
                  Leg(id="L2", name="L2", duration_days=1)],
            instruments=[
                Instrument(id="a", name="A", group="phys", model="rate",
                           data_rate_bytes_per_s=1000),
                Instrument(id="b", name="B", group="bio", model="rate",
                           data_rate_bytes_per_s=2000),
            ],
            deployments=[
                Deployment(instrument_id="a", leg_id="L1"),
                Deployment(instrument_id="a", leg_id="L2"),
                Deployment(instrument_id="b", leg_id="L1"),
            ],
        )
        r = calculate(camp)
        by_group = {b.key: b.stored_bytes for b in r.per_group}
        # a: 1000*86400*2 legs = 172_800_000 ; b: 2000*86400*1 = 172_800_000
        self.assertAlmostEqual(by_group["phys"], 172_800_000)
        self.assertAlmostEqual(by_group["bio"], 172_800_000)
        by_leg = {b.key: b.stored_bytes for b in r.per_leg}
        # L1: a(86_400_000) + b(172_800_000) = 259_200_000 ; L2: a only = 86_400_000
        self.assertAlmostEqual(by_leg["L1"], 259_200_000)
        self.assertAlmostEqual(by_leg["L2"], 86_400_000)

    def test_peak_bandwidth_is_busiest_leg(self):
        # transmit_fraction 1.0; L1 transmits 86_400_000 B over 86400 s
        # = 1000 B/s = 8000 bits/s = 0.008 Mbps
        inst = Instrument(id="a", name="A", group="g", model="rate",
                          data_rate_bytes_per_s=1000, transmit_fraction=1.0)
        camp = Campaign(title="t",
                        legs=[Leg(id="L1", name="L1", duration_days=1)],
                        instruments=[inst],
                        deployments=[Deployment(instrument_id="a", leg_id="L1")])
        r = calculate(camp)
        self.assertAlmostEqual(r.peak_transmit_mbps, 0.008, places=6)
        self.assertEqual(r.peak_transmit_leg_id, "L1")


class TestValidation(unittest.TestCase):
    def test_rate_model_requires_rate(self):
        with self.assertRaises(ValueError):
            Instrument(id="x", name="x", group="g", model="rate")

    def test_sample_model_requires_fields(self):
        with self.assertRaises(ValueError):
            Instrument(id="x", name="x", group="g", model="sample", channels=1)

    def test_bad_duty_cycle(self):
        with self.assertRaises(ValueError):
            Instrument(id="x", name="x", group="g", model="rate",
                       data_rate_bytes_per_s=1, duty_cycle=2.0)

    def test_compression_below_one_rejected(self):
        with self.assertRaises(ValueError):
            Instrument(id="x", name="x", group="g", model="rate",
                       data_rate_bytes_per_s=1, compression_ratio=0.5)

    def test_duplicate_leg_id_rejected(self):
        with self.assertRaises(ValueError):
            Campaign(title="t",
                     legs=[Leg(id="L1", name="a", duration_days=1),
                           Leg(id="L1", name="b", duration_days=1)])

    def test_deployment_unknown_instrument_rejected(self):
        with self.assertRaises(ValueError):
            Campaign(title="t",
                     legs=[Leg(id="L1", name="a", duration_days=1)],
                     instruments=[],
                     deployments=[Deployment(instrument_id="ghost", leg_id="L1")])

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            Leg(id="L1", name="a", duration_days=-1)


class TestIngestAndExport(unittest.TestCase):
    def test_campaign_from_dict_roundtrip(self):
        data = {
            "title": "JSON campaign",
            "legs": [{"id": "L1", "name": "Leg 1", "duration_days": 1}],
            "instruments": [{"id": "a", "name": "A", "group": "g",
                             "model": "rate", "data_rate_bytes_per_s": 1000}],
            "deployments": [{"instrument_id": "a", "leg_id": "L1"}],
        }
        camp = campaign_from_dict(data)
        r = calculate(camp)
        self.assertAlmostEqual(r.total_stored_bytes, 86_400_000)

    def test_madmp_has_dmp_root_and_byte_size(self):
        camp = Campaign(title="t",
                        legs=[Leg(id="L1", name="L1", duration_days=1)],
                        instruments=[Instrument(id="a", name="A", group="phys",
                                                model="rate", data_rate_bytes_per_s=1000)],
                        deployments=[Deployment(instrument_id="a", leg_id="L1")])
        madmp = to_madmp(calculate(camp))
        self.assertIn("dmp", madmp)
        self.assertEqual(len(madmp["dmp"]["dataset"]), 1)
        dist = madmp["dmp"]["dataset"][0]["distribution"][0]
        self.assertEqual(dist["byte_size"], 86_400_000)
        self.assertIsInstance(dist["byte_size"], int)

    def test_missing_key_gives_clear_error(self):
        with self.assertRaises(ValueError):
            campaign_from_dict({"title": "no legs"})


if __name__ == "__main__":
    unittest.main()
