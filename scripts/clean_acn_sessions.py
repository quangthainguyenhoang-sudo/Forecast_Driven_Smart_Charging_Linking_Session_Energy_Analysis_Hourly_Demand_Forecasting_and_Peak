"""Rebuild the cleaned ACN-Data session table (v3, 60,105 sessions) from the original export.

IMPORTANT: these rules were INFERRED by comparing acn_data_full_original.xlsx (66,745 sessions)
with acn_data(cleaned).xlsx (60,105 sessions). They reproduce the cleaned file exactly (same
sessions, same 21 columns, see --verify), but they are not the group's original cleaning code.

Usage:
    python clean_acn_sessions.py ORIGINAL.xlsx OUTPUT.xlsx [--verify CLEANED.xlsx]

Rules (in this order; the counts after each step are printed):
  1. kWhDelivered must satisfy 0.5 < kWh < 40.
  2. Parking time (disconnect - connection) must be between 5 minutes and 48 hours.
  3. A missing doneChargingTime is imputed as connection + kWh / RATE_KW, RATE_KW = 3.1504235 kW
     (the constant observed in the cleaned file; roughly total kWh / total charging hours of the
     sessions that have a doneChargingTime, but the exact way it was computed is unknown).
  4. Charging time (done - connection) must be between 5 minutes and 24 hours.
  5. Sessions whose done time is later than the disconnect time by more than 61 seconds are removed;
     for the others the done time is cut to the disconnect time.
  6. Sessions connected from 2020-04-01 to 2021-01-31 (local date) are removed (period of the pandemic closure; the reason is not documented in the project;
     the original has 3,157 sessions in it, none is kept in the cleaned file).
Timestamps: the cleaned file stores them as naive times of a FIXED UTC-7 clock (no daylight saving
switch). In winter (UTC-8) they are one hour later than the wall clock of the original strings.
Derived columns: hour, day_of_week (Mon=0), month, month_sin/cos, is_weekend, seasonal
(Oct-Dec=0, Jan-Mar=1, Apr-Jun=2, Jul-Sep=3), hour_sin/cos, day_of_year, week_of_year (ISO),
is_holiday (US federal holidays), charging_duration, parking_duration (hours).
"""
import sys
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

RATE_KW = 3.150423511
MIN_KWH, MAX_KWH = 0.5, 40.0
MIN_PARK_H, MAX_PARK_H = 5 / 60, 48.0
MIN_CHG_H, MAX_CHG_H = 5 / 60, 24.0
DONE_AFTER_DISCONNECT_TOL_H = 61 / 3600
CLOSURE_START, CLOSURE_END = pd.Timestamp('2020-04-01'), pd.Timestamp('2021-02-01')
FIXED_OFFSET = pd.Timedelta(hours=7)
SEASON = {10: 0, 11: 0, 12: 0, 1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3}
COLUMNS = ['sessionID', 'stationID', 'siteID', 'connectionTime', 'disconnectTime', 'kWhDelivered',
           'doneChargingTime', 'hour', 'day_of_week', 'month', 'month_sin', 'month_cos', 'is_weekend',
           'seasonal', 'hour_sin', 'hour_cos', 'day_of_year', 'week_of_year', 'is_holiday',
           'charging_duration', 'parking_duration']


def clean(original: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    o = original.copy()
    co = pd.to_datetime(o.connectionTime, utc=True)
    di = pd.to_datetime(o.disconnectTime, utc=True)
    dn = pd.to_datetime(o.doneChargingTime, utc=True)
    o['ct'] = (co - FIXED_OFFSET).dt.tz_localize(None)       # fixed UTC-7 clock
    o['dt'] = (di - FIXED_OFFSET).dt.tz_localize(None)
    o['dn'] = (dn - FIXED_OFFSET).dt.tz_localize(None)
    o['park_h'] = (o.dt - o.ct).dt.total_seconds() / 3600
    local_date = co.dt.tz_convert('America/Los_Angeles').dt.normalize().dt.tz_localize(None)

    log = [('original', len(o))]
    o = o[(o.kWhDelivered > MIN_KWH) & (o.kWhDelivered < MAX_KWH)]; log.append(('kWh in (0.5, 40)', len(o)))
    o = o[(o.park_h >= MIN_PARK_H) & (o.park_h <= MAX_PARK_H)]; log.append(('parking 5 min to 48 h', len(o)))
    imputed = o.dn.isna()
    o['dn'] = o.dn.where(~imputed, o.ct + pd.to_timedelta(o.kWhDelivered / RATE_KW, unit='h'))
    o['chg_h'] = (o.dn - o.ct).dt.total_seconds() / 3600
    o = o[(o.chg_h >= MIN_CHG_H) & (o.chg_h <= MAX_CHG_H)]; log.append(('charging 5 min to 24 h (after imputation)', len(o)))
    o = o[o.chg_h <= o.park_h + DONE_AFTER_DISCONNECT_TOL_H]; log.append(('done <= disconnect + 61 s', len(o)))
    ld = local_date.loc[o.index]
    o = o[~((ld >= CLOSURE_START) & (ld < CLOSURE_END))]; log.append(('remove 2020-04-01 to 2021-01-31', len(o)))
    if verbose:
        prev = None
        for name, n in log:
            print(f'{name:48s} {n:7,d}' + ('' if prev is None else f'  (removed {prev - n:,d})'))
            prev = n

    o = o.sort_values('ct', kind='stable')
    o['dn'] = o[['dn', 'dt']].min(axis=1)
    ct = o.ct
    out = pd.DataFrame({'sessionID': o.sessionID, 'stationID': o.stationID, 'siteID': o.siteID,
                        'connectionTime': ct, 'disconnectTime': o.dt, 'kWhDelivered': o.kWhDelivered,
                        'doneChargingTime': o.dn})
    out['hour'] = ct.dt.hour + ct.dt.minute / 60 + ct.dt.second / 3600
    out['day_of_week'] = ct.dt.dayofweek
    out['month'] = ct.dt.month
    out['month_sin'] = np.sin(2 * np.pi * out.month / 12)
    out['month_cos'] = np.cos(2 * np.pi * out.month / 12)
    out['is_weekend'] = (out.day_of_week >= 5).astype(int)
    out['seasonal'] = out.month.map(SEASON)
    out['hour_sin'] = np.sin(2 * np.pi * out.hour / 24)
    out['hour_cos'] = np.cos(2 * np.pi * out.hour / 24)
    out['day_of_year'] = ct.dt.dayofyear
    out['week_of_year'] = ct.dt.isocalendar().week.astype(int)
    hol = USFederalHolidayCalendar().holidays('2018-01-01', '2021-12-31')
    out['is_holiday'] = ct.dt.normalize().isin(hol).astype(int)
    out['charging_duration'] = (o.dn - ct).dt.total_seconds() / 3600
    out['parking_duration'] = (o.dt - ct).dt.total_seconds() / 3600
    return out[COLUMNS].reset_index(drop=True)


def verify(mine: pd.DataFrame, ref: pd.DataFrame) -> bool:
    """Compare with the cleaned file session by session (the order of sessions that connect in the
    same second may differ from the cleaned file, so rows are matched by sessionID)."""
    ref = ref[COLUMNS]
    same_set = len(mine) == len(ref) and set(mine.sessionID) == set(ref.sessionID)
    print('same sessions:', same_set, f'({len(mine):,} vs {len(ref):,})')
    if not same_set:
        return False
    ref = ref.set_index('sessionID').loc[mine.sessionID].reset_index()
    ok = True
    worst = {}
    for col in COLUMNS:
        a, b = mine[col], ref[col]
        if pd.api.types.is_datetime64_any_dtype(a) or pd.api.types.is_datetime64_any_dtype(b):
            diff = (pd.to_datetime(a) - pd.to_datetime(b)).abs().dt.total_seconds().max()
        elif pd.api.types.is_numeric_dtype(a):
            diff = float(np.abs(a.astype(float) - b.astype(float)).max())
        else:
            diff = float((a.astype(str) != b.astype(str)).sum())
        worst[col] = diff
    # tolerance: 1e-6 for numbers, 1 millisecond for times (imputed done times differ by < 1 ms)
    time_cols = {'connectionTime', 'disconnectTime', 'doneChargingTime'}
    bad = {k: v for k, v in worst.items() if v > (1e-3 if k in time_cols else 1e-6)}
    print('columns that differ from the cleaned file:', bad if bad else 'none')
    return not bad


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    ref_path = args[args.index('--verify') + 1] if '--verify' in args else None
    result = clean(pd.read_excel(args[0]))
    result.to_excel(args[1], sheet_name='full_data', index=False)
    print('written', args[1], result.shape)
    if ref_path:
        sys.exit(0 if verify(result, pd.read_excel(ref_path, sheet_name='full_data')) else 1)
