# PharmaLink AI — ML package

Plain, installable Python package (no FastAPI/SQLAlchemy imports) exposing
typed functions/classes the backend calls directly — see
[../docs/architecture.md](../docs/architecture.md) for the `/backend` <->
`/ml` boundary.

## `forecasting/`

- `interface.py` — `ForecastResult`, the `Forecaster` `Protocol`.
- `features.py` — lag/rolling/day-of-week/categorical feature engineering,
  shared by training and prediction so the two paths can't drift apart.
- `lightgbm_forecaster.py` — **`LightGBMForecaster`, the real, load-bearing
  implementation.** Quantile regression (q=0.1/0.5/0.9) gives the
  confidence band; predicts a daily rate at the latest feature snapshot
  and scales by the horizon.
- `chronos_forecaster.py` — a documented, present-but-not-implemented swap
  point. The original design said "Chronos first, LightGBM fallback";
  after research this milestone ships the reverse as the *working*
  default — `chronos-forecasting` pulls in `torch` + `transformers`
  (multiple GB of CPU-only dependencies, materially slower inference) for
  a demo dataset that a well-featured LightGBM model already fits well,
  not just cheaply. `ChronosForecaster.fit`/`.predict` raise
  `NotImplementedError` with this reasoning — swap it in behind
  `core/di.py::get_forecaster` when there's a reason to (GPU inference, a
  foundation-model story), no other code changes needed.

## `optimization/`

- `transfer_optimizer.py` — `solve_network_transfers(states)`: the classic
  transportation problem (surplus hospitals → deficit hospitals), solved
  as a linear program with OR-Tools (GLOP). Maximizes total quantity
  moved (satisfying network-wide shortage is the dominant goal) with
  distance as a tie-breaker. Procurement's reorder-quantity decision
  stays a single-variable heuristic (see `backend/app/application/
  procurement/service.py`) — OR-Tools doesn't add anything there; the
  transfer allocation problem is the one that's genuinely
  multi-hospital/multi-variable.

None of this produces natural-language explanations — that's the LLM
layer's job (`backend/app/infrastructure/external/llm/`), which explains
recommendations these functions compute but never predicts anything
itself.
