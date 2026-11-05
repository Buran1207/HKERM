"""Unit checks for HKERM's no-lookahead RRG and flexible horizon calculations."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hkerm_rotation import (resolve_asof, rrg_coordinates, rrg_state,
                            sector_horizon_snapshot, stock_period_returns, sector_horizon_history)


class RotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = ROOT / 'data'
        cls.sectors=pd.read_csv(d/'sector_daily.csv.gz',parse_dates=['date'],dtype={'sector_id':str})
        cls.prices=pd.read_csv(d/'stock_daily.csv.gz',parse_dates=['date'],dtype={'code':str})
        cls.master=pd.read_csv(d/'stock_master.csv',dtype={'code':str,'sector_id':str})
        cls.bench=pd.read_csv(d/'benchmark.csv',parse_dates=['date'])
        cls.calendar=pd.DatetimeIndex(cls.bench.date)

    def test_calendar_includes_first_original_date(self):
        self.assertEqual(str(self.calendar.min().date()),'2026-06-25')
        self.assertEqual(str(self.calendar.max().date()),'2026-11-02')
        self.assertEqual(resolve_asof('2026-06-25',self.calendar),pd.Timestamp('2026-06-25'))
        self.assertEqual(resolve_asof('2026-07-04',self.calendar),pd.Timestamp('2026-07-03'))
        self.assertEqual(resolve_asof('2026-11-01',self.calendar),pd.Timestamp('2026-10-30'))

    def test_rrg_uses_hsci_benchmark_no_future_leak(self):
        a=rrg_coordinates(self.sectors,self.bench)
        day=pd.Timestamp('2026-10-09')
        a_cut=a.loc[a.date==day].sort_values('sector_id').reset_index(drop=True)
        cutoff=rrg_coordinates(self.sectors.loc[self.sectors.date<=day],self.bench.loc[self.bench.date<=day])
        b_cut=cutoff.loc[cutoff.date==day].sort_values('sector_id').reset_index(drop=True)
        pd.testing.assert_frame_equal(a_cut,b_cut)
        self.assertTrue(a.loc[a.date==pd.Timestamp('2026-06-25'),'x'].isna().all())
        last=a.loc[a.date==self.calendar.max()]
        self.assertGreater(last.x.notna().sum(),60)
        self.assertTrue((last.x.dropna()>0).all())
        self.assertTrue((last.y.dropna()>0).all())

    def test_quadrants_are_100_centered(self):
        self.assertEqual(rrg_state(100.2,100.5),'领先强化')
        self.assertEqual(rrg_state(101,99.9),'领先减弱')
        self.assertEqual(rrg_state(99,101),'落后改善')
        self.assertEqual(rrg_state(99,99),'落后持续')
        self.assertEqual(rrg_state(np.nan,100),'历史不足')

    def test_original_horizons_keep_bundled_snapshots(self):
        date=self.calendar.max()
        src=self.sectors[self.sectors.date==date].set_index('sector_id')
        for h in (1,5,20,60):
            got,bm=sector_horizon_snapshot(self.sectors,self.prices,self.master,self.bench,date,h)
            got=got.set_index('sector_id')
            self.assertTrue(np.allclose(got[f'ret_{h}'],src.loc[got.index,f'ret_{h}'],equal_nan=True))
            self.assertAlmostEqual(bm,float(self.bench.loc[self.bench.date==date,f'hsciret_{h}'].iloc[0]))

    def test_arbitrary_horizon_is_not_rounded_to_fixed_options(self):
        asof=self.calendar.max()
        for h in (2,7,11,28,59):
            got,bm=sector_horizon_snapshot(self.sectors,self.prices,self.master,self.bench,asof,h)
            self.assertFalse(got.empty)
            self.assertGreater(got[f'ret_{h}'].notna().sum(),60)
            before=self.bench.loc[self.bench.date==self.calendar[-(h+1)],'close'].iloc[0]
            after=self.bench.loc[self.bench.date==asof,'close'].iloc[0]
            self.assertAlmostEqual(bm,float(after/before-1))
            stock=stock_period_returns(self.prices,self.bench,asof,h)
            self.assertGreater(stock.ret_custom.notna().sum(),400)
            self.assertLess(abs(float(stock.ret_custom.dropna().mean())),1)

    def test_historical_curve_matches_selected_horizon_snapshot(self):
        date=self.calendar.max()
        for h in (2,7,17,59):
            snapshot,_=sector_horizon_snapshot(self.sectors,self.prices,self.master,self.bench,date,h)
            for sid in ['S01-01','S03-02','S08-03']:
                curve=sector_horizon_history(self.prices,self.master,self.bench,sid,date,h)
                target=float(snapshot.loc[snapshot.sector_id==sid,f'excess_{h}'].iloc[0])
                calculated=float(curve.loc[curve.date==date,'excess'].iloc[0])
                self.assertAlmostEqual(target,calculated,places=10)

    def test_missing_early_custom_history_not_fabricated(self):
        asof=self.calendar.min()
        snap,bm=sector_horizon_snapshot(self.sectors,self.prices,self.master,self.bench,asof,7)
        self.assertTrue(snap['ret_7'].isna().all())
        self.assertTrue(np.isnan(bm))
        returns=stock_period_returns(self.prices,self.bench,asof,7)
        self.assertTrue(returns.ret_custom.isna().all())
        snap1,bm1=sector_horizon_snapshot(self.sectors,self.prices,self.master,self.bench,asof,1)
        self.assertTrue(snap1['ret_1'].notna().any())
        self.assertTrue(np.isfinite(bm1))


if __name__=='__main__':
    unittest.main()
