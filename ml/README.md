# MedCycle AI — ML package

**Status: not yet implemented — lands in Milestone C.**

This will be a plain, installable Python package (`ml/pyproject.toml`) with
no FastAPI/SQLAlchemy imports, exposing typed functions the backend calls
directly (fast synchronous paths, e.g. scoring one inventory batch's
expiry risk) and from Celery tasks (batch jobs, e.g. a nightly 90-day
forecast refresh across every hospital × medicine pair). See
[../docs/architecture.md](../docs/architecture.md#backend--ml-boundary-milestone-c)
for the integration contract.

Planned subpackages:

- `ml/forecasting/` — demand forecasting. Chronos first, LightGBM fallback
  (invisible to the backend — the fallback decision lives in here).
- `ml/expiry/` — expiry-risk probability + estimated financial loss.
- `ml/shortage/` — stockout date + probability prediction.
- `ml/optimization/` — OR-Tools transfer-quantity and procurement optimizer.

None of these models produce natural-language explanations — that's the
LLM layer's job (also Milestone C), which explains recommendations these
models compute but never predicts anything itself.
