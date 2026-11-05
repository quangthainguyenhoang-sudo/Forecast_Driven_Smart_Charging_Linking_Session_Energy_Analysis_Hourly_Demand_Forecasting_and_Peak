# DAP391m

Code for the paper "Forecast-Driven Smart Charging: Linking Session Energy Analysis, Hourly Demand Forecasting and Peak Reduction on ACN-Data" (FPT University, DAP391m, Fall 2026).

- RQ1: factors of session energy (sites 1, 2, 19)
- RQ2: hourly demand forecasting (sites 1, 2; horizons 1 h and 24 h)
- RQ3: cap-based smart charging scheduler driven by the RQ2 forecasts

## Notebooks (`notebooks/`)

Some notebooks are saved with the outputs of the final runs and some without. A notebook without outputs has to be run to reproduce its results.

| Notebook | Content |
|---|---|
| `rq1-session-factors.ipynb` | Earlier RQ1 version (not used for the current results) |
| `persistence.ipynb` | RQ2 baseline: persistence |
| `seasonal-naive.ipynb` | RQ2 baseline: seasonal naive |
| `linear-regression.ipynb` | RQ1 session energy: tuned linear model (elastic net) |
| `xgboost.ipynb` | RQ1 session energy: tuned XGBoost |
| `lightgbm.ipynb` | RQ1 session energy: tuned LightGBM |
| `lstm-rq2-ev-charging.ipynb` | RQ2 recurrent network |
| `hybrid-rq2-ev-charging.ipynb` | RQ2 hybrid base learners |
| `ridge-meta-learner.ipynb` | RQ2 Ridge stacking of the hybrid |
| `rq2-aggregate.ipynb` | RQ2 aggregation of results |
| `rq3-smart-charging.ipynb` | RQ3 smart charging simulation |
| `../scripts/rq1_group_importance_v3.py`, `../scripts/rq1_oof_importance.py` | RQ1 factor importance (Table 3): test-block and out-of-fold permutation |

## Data

The ACN-Data sessions are not included. Download them from the ACN-Data portal (Lee, Li and Low, 2019): https://ev.caltech.edu/dataset . Set the input path inside each notebook.

## Split and data cleaning

All experiments use one chronological split: Train to 31/10/2019, Validation to 15/01/2020, Test from 16/01/2020 to the end of the data.

**Sessions (removed).** Before any modelling, the session table drops duplicate sessions (same station and connection time), sessions with non-positive delivered energy, and sessions that disconnect before they connect. Only the sites used by each question are kept (RQ1: sites 1, 2, 19; RQ2 and RQ3: sites 1, 2).

**Hourly series (flagged, not deleted).** For RQ2 and RQ3 each site becomes an hourly series, and the energy of a session is spread over the hours between connection and the end of charging so that the total energy is conserved. No hour is removed from the series. Hours are flagged instead, and a flagged hour is never used as a target:

| Flag | Rule |
|---|---|
| Outage (`in_gap`) | at least 7 consecutive days with zero energy are treated as a data outage, not as demand |
| After an outage (`post_gap`) | the 672 hours (4 weeks) after each outage |
| Warm-up | the first 672 hours (4 weeks) of each series |

The remaining hours are the valid target hours (`valid`), identical for every model. Flagged hours stay in the series so that the lag windows stay aligned, but they are excluded from the targets of training, validation and test scoring.
