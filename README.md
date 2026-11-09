# DAP391m

Code for the paper "Forecast-Driven Smart Charging: Linking Session Energy Analysis, Hourly Demand Forecasting and Peak Reduction on ACN-Data" (FPT University, DAP391m, Fall 2026).

- RQ1: factors of session energy (sites 1, 2, 19)
- RQ2: hourly demand forecasting (sites 1, 2; horizons 1 h and 24 h)
- RQ3: cap-based smart charging scheduler driven by the RQ2 forecasts

## Notebooks (repository root)

Some notebooks are saved with the outputs of the final runs and some without. A notebook without outputs has to be run to reproduce its results.

| Notebook | Content |
|---|---|
| `persistence.ipynb` | RQ2 baseline: persistence |
| `seasonal_naive.ipynb` | RQ2 baseline: seasonal naive |
| `linear_regression.ipynb` | RQ1 session energy: tuned linear model (elastic net) |
| `xgboost.ipynb` | RQ1 session energy: tuned XGBoost |
| `lightgbm.ipynb` | RQ1 session energy: tuned LightGBM |
| `lstm.ipynb` | RQ2 recurrent network |
| `hybrid.ipynb` | RQ2 hybrid base learners |
| `ridge_meta_learner.ipynb` | RQ2 Ridge stacking of the hybrid |
| `rq2_aggregate.ipynb` | RQ2 aggregation of results |
| `rq3_smart_charging.ipynb` | RQ3 smart charging simulation |
| `scripts/rq1_group_importance_v3.py`, `scripts/rq1_oof_importance.py` | RQ1 factor importance (Table 3): test-block and out-of-fold permutation |
| `scripts/clean_acn_sessions.py` | Rebuilds the cleaned session table from the original export (see below) |
| `scripts/make_fig2_fig3.py` | Fig. 2 (data description) and Fig. 3 (load and MAE by hour) |

## Reproduction guide

`REPRODUCE.md` lists the environment, the order of the notebooks, the expected results and the mapping of tables and figures to notebooks.

## Data

The ACN-Data sessions are not included. Download them from the ACN-Data portal (Lee, Li and Low, 2019): https://ev.caltech.edu/dataset . Set the input path inside each notebook. The scripts read the cleaned session table from the path in the environment variable `ACN_XLSX` and write their results to the folder in `RQ1_OUT` (current folder by default).

## Split and data cleaning

All experiments use one chronological split: Train to 31/10/2019, Validation to 15/01/2020, Test from 16/01/2020 to the end of the data.

**Sessions (removed).** The cleaned table (60,105 of the 66,745 original sessions) is obtained with the rules below, which `scripts/clean_acn_sessions.py` applies to the original export (`python scripts/clean_acn_sessions.py acn_data_full_original.xlsx out.xlsx --verify "acn_data(cleaned).xlsx"` reproduces the cleaned file). The rules were inferred by comparing the original and the cleaned table.

| Step | Rule | Sessions left |
|---|---|---|
| 0 | Original export | 66,745 |
| 1 | `kWhDelivered` between 0.5 and 40 (exclusive) | 64,761 |
| 2 | Parking time (disconnect minus connection) from 5 minutes to 48 hours | 64,654 |
| 3 | A missing `doneChargingTime` is set to connection time + kWh / 3.1504 kW; charging time then from 5 minutes to 24 hours | 64,591 |
| 4 | Remove sessions whose `doneChargingTime` is more than 61 seconds after the disconnection; for the others it is cut to the disconnection | 62,883 |
| 5 | Remove sessions connected from 1 April 2020 to 31 January 2021 (local date) | 60,105 |

Step 5 removes 3,157 sessions of the original export, so the gap between April 2020 and February 2021 in the hourly series comes from this step. The time columns of the cleaned table use a fixed UTC-7 clock (no switch to UTC-8 in winter). Only the sites used by each question are kept (RQ1: sites 1, 2, 19; RQ2 and RQ3: sites 1, 2; for RQ2 and RQ3 one duplicated session, same station and connection time, is also dropped).

**Hourly series (flagged, not deleted).** For RQ2 and RQ3 each site becomes an hourly series, and the energy of a session is spread over the hours between connection and the end of charging so that the total energy is conserved. No hour is removed from the series. Hours are flagged instead, and a flagged hour is never used as a target:

| Flag | Rule |
|---|---|
| Outage (`in_gap`) | at least 7 consecutive days with zero energy are treated as a data outage, not as demand |
| After an outage (`post_gap`) | the 672 hours (4 weeks) after each outage |
| Warm-up | the first 672 hours (4 weeks) of each series |

The remaining hours are the valid target hours (`valid`), identical for every model. Flagged hours stay in the series so that the lag windows stay aligned, but they are excluded from the targets of training, validation and test scoring.
