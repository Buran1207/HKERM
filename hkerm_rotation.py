"""HKERM V1.1: causal, transparent RRG-style sector coordinates and flexible lookbacks.

These are NOT the proprietary JdK / StockCharts RRG indicators. All values use
only observations available on or before their corresponding trading dates.
Original sector daily returns use a fixed stock universe and unadjusted prices.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FIXED_HORIZONS = (1, 5, 20, 60)
FAST_EMA = 14
SLOW_EMA = 36
MOMENTUM_LAG = 5
MAX_DAILY_RAW_JUMP = 0.35


def resolve_asof(requested_date, calendar) -> pd.Timestamp:
    """Calendar-day selection resolves to the most recent actual trading day <= requested."""
    dates = pd.DatetimeIndex(pd.to_datetime(calendar)).sort_values().unique()
    if dates.empty:
        raise ValueError('No trading dates in data.')
    requested = pd.Timestamp(requested_date).normalize()
    matches = dates[dates <= requested]
    if len(matches) == 0:
        raise ValueError('Requested date precedes the available history.')
    return pd.Timestamp(matches[-1])


def rrg_coordinates(sector_daily: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    """Historical RS coordinates consistent with the USERM logarithmic EMA method.

    RS(t) is the chained sector daily *research-return proxy* divided by the
    benchmark HSCI close index. The chain is reset after missing sector sessions.
    X = 100 * exp(EMA14(log(RS)) - EMA36(log(RS)))
    Y = 100 * X(t) / X(t-5)
    At least 36 observations + 5 lags are required for a plotted pair.
    """
    b = benchmark[['date', 'close']].copy()
    b['date'] = pd.to_datetime(b['date'])
    b = b.sort_values('date').drop_duplicates('date')
    b['hsciret_calc'] = b['close'].pct_change(fill_method=None)
    calendar = b[['date', 'hsciret_calc']].copy()
    sectors = sector_daily[['date', 'sector_id', 'ret_1']].copy()
    sectors['date'] = pd.to_datetime(sectors['date'])
    sectors = sectors.drop_duplicates(['sector_id','date'])
    result = []
    for sid, sector_part in sectors.groupby('sector_id', sort=False):
        g = calendar.merge(sector_part[['date', 'ret_1']], on='date', how='left')
        g = g.sort_values('date').reset_index(drop=True)
        # The earliest day has no prior close *inside the published dataset*.
        # It is a baseline, not an invented earlier return.
        valid = g['ret_1'].notna() & (g['ret_1'] > -1) & (g['hsciret_calc'].fillna(0) > -1)
        valid.iloc[0] = True
        g['x'] = np.nan
        g['y'] = np.nan
        # Segment whenever the input is unavailable; do not bridge missing sessions.
        segment = (~valid).cumsum()
        for _, part in g[valid].groupby(segment[valid], sort=False):
            if len(part) < SLOW_EMA + MOMENTUM_LAG:
                continue
            daily_sector = part['ret_1'].astype(float).copy()
            daily_bench = part['hsciret_calc'].astype(float).copy()
            if part.index[0] == 0:
                daily_sector.iloc[0] = 0.0
                daily_bench.iloc[0] = 0.0
            # The ratio's arbitrary first level cancels out in the EMA difference.
            log_rs = (np.log1p(daily_sector) - np.log1p(daily_bench)).cumsum()
            fast = log_rs.ewm(span=FAST_EMA, adjust=False, min_periods=FAST_EMA).mean()
            slow = log_rs.ewm(span=SLOW_EMA, adjust=False, min_periods=SLOW_EMA).mean()
            x = 100.0 * np.exp(fast - slow)
            y = 100.0 * x / x.shift(MOMENTUM_LAG)
            g.loc[part.index, 'x'] = x.to_numpy()
            g.loc[part.index, 'y'] = y.to_numpy()
        g['sector_id'] = sid
        result.append(g[['date', 'sector_id', 'x', 'y']])
    if not result:
        return pd.DataFrame(columns=['date','sector_id','x','y'])
    return pd.concat(result, ignore_index=True).sort_values(['date','sector_id'])


def rrg_state(x, y):
    if not np.isfinite(x) or not np.isfinite(y):
        return '历史不足'
    if x >= 100 and y >= 100:
        return '领先强化'
    if x >= 100 and y < 100:
        return '领先减弱'
    if x < 100 and y >= 100:
        return '落后改善'
    return '落后持续'


def stock_period_returns(stock_prices: pd.DataFrame, benchmark: pd.DataFrame,
                         asof, horizon: int) -> pd.DataFrame:
    """Return all codes' X-day raw-price change from the same observed start/end.

    For the four existing standardized horizons use the original precomputed
    fields, which can contain historical pre-bundle lookback information.
    """
    day = pd.Timestamp(asof)
    h = int(horizon)
    current = stock_prices.loc[stock_prices.date == day, ['code','close']].copy()
    if h in FIXED_HORIZONS:
        raw = stock_prices.loc[stock_prices.date == day, ['code', f'ret_{h}']].copy()
        return raw.rename(columns={f'ret_{h}': 'ret_custom'})
    cal = pd.DatetimeIndex(benchmark.date).sort_values().unique()
    loc = cal.get_indexer([day])[0]
    if loc < h:
        current['ret_custom'] = np.nan
        return current[['code','ret_custom']]
    start = pd.Timestamp(cal[loc-h])
    left = stock_prices.loc[stock_prices.date == start, ['code','close']].rename(columns={'close':'start_close'})
    out = current.merge(left,on='code',how='left')
    out['ret_custom'] = np.where((out.close > 0) & (out.start_close > 0),
                                 out.close / out.start_close - 1.0, np.nan)
    return out[['code','ret_custom']]


def sector_horizon_snapshot(sector_daily: pd.DataFrame, stock_prices: pd.DataFrame,
                            stock_master: pd.DataFrame, benchmark: pd.DataFrame,
                            asof, horizon: int) -> tuple[pd.DataFrame, float]:
    """X-day, start-cap-weighted sector returns for any 1..60 session horizon.

    The original 1/5/20/60 snapshots are kept unchanged (including earlier
    pre-bundle history). Other horizons are calculated from the bundled raw closes.
    No future data, forward-filling, or extrapolation is used.
    """
    day = pd.Timestamp(asof)
    h = int(horizon)
    if not 1 <= h <= 60:
        raise ValueError('Observation horizon must be 1..60 trading sessions.')
    cols = ['sector_id','sector',f'n_{h}',f'ret_{h}',f'excess_{h}',
            f'equal_{h}',f'breadth_{h}',f'concentration_{h}']
    existing = sector_daily.loc[sector_daily.date == day].copy()
    b = benchmark.sort_values('date').drop_duplicates('date').reset_index(drop=True)
    if h in FIXED_HORIZONS:
        r = b.loc[b.date == day, f'hsciret_{h}']
        return existing[cols].copy(), (float(r.iloc[0]) if len(r) else np.nan)

    blank = existing[['sector_id','sector']].copy()
    for name in [f'n_{h}',f'ret_{h}',f'excess_{h}',f'equal_{h}',f'breadth_{h}',f'concentration_{h}']:
        blank[name] = np.nan
    locs = b.index[b.date == day].tolist()
    if not locs or locs[0] < h:
        return blank[cols], np.nan
    start_date = pd.Timestamp(b.loc[locs[0]-h, 'date'])
    bm_close = float(b.loc[locs[0], 'close'])
    bm_start = float(b.loc[locs[0]-h, 'close'])
    bm = bm_close / bm_start - 1.0 if bm_close>0 and bm_start>0 else np.nan
    start = stock_prices.loc[stock_prices.date == start_date, ['code','close','cap']].rename(
        columns={'close':'start_close','cap':'start_cap'})
    end = stock_prices.loc[stock_prices.date == day, ['code','close']].rename(columns={'close':'end_close'})
    members = start.merge(end,on='code',how='inner').merge(stock_master[['code','sector_id']],on='code',how='inner')
    members = members[(members.start_close > 0) & (members.end_close > 0) &
                      (members.start_cap > 0)].copy()
    members['raw_return'] = members.end_close / members.start_close - 1.0

    # Reject securities with >35% single-day unadjusted price discontinuities
    # anywhere inside the lookback window, similar to source-data filtering.
    window = stock_prices.loc[(stock_prices.date >= start_date) &
                              (stock_prices.date <= day), ['date','code','close']].copy()
    window = window.sort_values(['code','date'])
    window['daily_change'] = window.groupby('code')['close'].pct_change(fill_method=None)
    bad = window.loc[window.daily_change.abs() > MAX_DAILY_RAW_JUMP, 'code'].unique()
    if len(bad):
        members = members[~members.code.isin(bad)].copy()
    if members.empty:
        return blank[cols], bm

    members['weighted_return'] = members.raw_return * members.start_cap
    members['positive'] = (members.raw_return>0).astype(float)
    agg = members.groupby('sector_id',sort=False).agg(
        count=('code','count'), cap_sum=('start_cap','sum'),
        weighted_sum=('weighted_return','sum'), mean_return=('raw_return','mean'),
        breadth=('positive','mean'), max_cap=('start_cap','max'))
    agg['ret'] = agg.weighted_sum/agg.cap_sum
    agg['excess'] = agg.ret-bm
    agg['concentration'] = agg.max_cap/agg.cap_sum
    agg = agg.rename(columns={
        'count':f'n_{h}','ret':f'ret_{h}','excess':f'excess_{h}',
        'mean_return':f'equal_{h}','breadth':f'breadth_{h}',
        'concentration':f'concentration_{h}'})
    output = blank[['sector_id','sector']].merge(
        agg[[f'n_{h}',f'ret_{h}',f'excess_{h}',f'equal_{h}',f'breadth_{h}',f'concentration_{h}']],
        left_on='sector_id',right_index=True,how='left')
    return output[cols], bm


def sector_horizon_history(stock_prices: pd.DataFrame, stock_master: pd.DataFrame,
                           benchmark: pd.DataFrame, sector_id: str, asof,
                           horizon: int) -> pd.DataFrame:
    """One sector's historical X-day excess series for a nonstandard lookback.

    Vectorized reconstruction using exact observed trading-session endpoints and
    start-of-window cap weights. Returns NaN where no complete window exists.
    """
    h = int(horizon)
    b = benchmark.loc[benchmark.date <= pd.Timestamp(asof), ['date','close']].sort_values('date').copy()
    if b.empty:
        return pd.DataFrame(columns=['date','excess'])
    b['bench_return'] = b.close / b.close.shift(h) - 1.0
    b.loc[(b.close <= 0) | (b.close.shift(h) <= 0), 'bench_return'] = np.nan
    if len(b) <= h:
        return b[['date']].assign(excess=np.nan)

    tickers = set(stock_master.loc[stock_master.sector_id == sector_id, 'code'])
    p = stock_prices.loc[(stock_prices.code.isin(tickers)) &
                         (stock_prices.date <= pd.Timestamp(asof)), ['date','code','close','cap']].copy()
    if p.empty:
        return b[['date']].assign(excess=np.nan)
    p = p.sort_values(['code','date'])
    p['daily_jump'] = p.groupby('code')['close'].pct_change(fill_method=None).abs() > MAX_DAILY_RAW_JUMP
    p['bad_cumulative'] = p.groupby('code')['daily_jump'].cumsum()
    next_dates = dict(zip(b.date.iloc[:-h], b.date.iloc[h:]))
    begins = p.loc[p.date.isin(next_dates), ['date','code','close','cap','bad_cumulative']].copy()
    begins['end_date'] = begins.date.map(next_dates)
    begins = begins.rename(columns={'close':'start_close','cap':'start_cap','bad_cumulative':'bad_start'})
    ends = p[['date','code','close','bad_cumulative']].rename(columns={
        'date':'end_date','close':'end_close','bad_cumulative':'bad_end'})
    rows = begins.merge(ends,on=['code','end_date'],how='inner')
    rows = rows[(rows.start_close>0)&(rows.end_close>0)&(rows.start_cap>0)&
                (rows.bad_end == rows.bad_start)].copy()
    if rows.empty:
        return b[['date']].assign(excess=np.nan)
    rows['weighted_return'] = (rows.end_close/rows.start_close-1.0)*rows.start_cap
    grouped = rows.groupby('end_date').agg(num=('weighted_return','sum'),denom=('start_cap','sum'))
    grouped['sector_return'] = grouped.num/grouped.denom
    result = b[['date','bench_return']].merge(grouped[['sector_return']],
                                              left_on='date',right_index=True,how='left')
    result['excess'] = result.sector_return-result.bench_return
    return result[['date','excess']]
