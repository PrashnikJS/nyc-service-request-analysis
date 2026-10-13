import unittest
import pandas as pd
from analysis import prepare, group_summary

class ServiceTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame([
            ['1', '2025-11-01', '2025-11-01 12:00', 'Noise', 'QUEENS'],
            ['2', '2025-11-01', None, 'Noise', 'QUEENS'],
            ['3', '2025-11-01', '2025-12-02', 'Noise', 'QUEENS'],
            ['4', '2025-11-01', '2025-10-31', 'Noise', 'QUEENS']],
            columns=['unique_key', 'created_date', 'closed_date', 'complaint_type', 'borough'])
    def test_open_and_later_closed_cases_stay_in_denominator(self):
        df, _ = prepare(self.fixture())
        summary = group_summary(df, ['complaint_type']).iloc[0]
        self.assertEqual(summary.requests, 4)
        self.assertEqual(summary.closed_by_cutoff, 1)
        self.assertEqual(summary.within_48h_pct_all_requests, 25)
    def test_negative_closure_is_audited_and_not_fast(self):
        df, audit = prepare(self.fixture())
        self.assertEqual(audit['negative_closure_intervals'], 1)
        self.assertTrue(pd.isna(df.loc[3, 'closure_hours']))
    def test_duplicate_ids_are_rejected(self):
        raw = self.fixture(); raw.loc[1, 'unique_key'] = '1'
        with self.assertRaises(ValueError): prepare(raw)
    def test_invalid_created_date_is_quarantined(self):
        raw = self.fixture(); raw.loc[0, 'created_date'] = 'invalid'
        df, audit = prepare(raw)
        self.assertEqual(audit['invalid_created_rows'], 1)
        self.assertEqual(len(df), 3)
