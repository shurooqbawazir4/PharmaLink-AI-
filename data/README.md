# MedCycle AI — Data

Real-signal ingestion + synthetic layer generation, run via the `pipeline`
Docker service (its own minimal image — pandas/numpy/requests — kept
separate from `/backend` so the API image stays free of data-science
dependencies; see `docker/Dockerfile.pipeline`).

## Pipeline

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env build pipeline
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm pipeline python pipeline/fetch_fluview.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm pipeline python pipeline/build_processed.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm pipeline python synthetic/generate.py
docker compose -f docker/docker-compose.yml --env-file docker/.env run --rm backend python scripts/seed_database.py [--reset]
```

1. **`pipeline/fetch_fluview.py`** — pulls the real national US weekly
   ILI (influenza-like illness) series from the [Delphi Epidata
   API](https://cmu-delphi.github.io/delphi-epidata/api/fluview.html)
   (CMU) — no auth, no rate limiting hit in practice. → `raw/fluview/`.
2. **`pipeline/build_processed.py`** — collapses the raw weekly series into
   a smooth **day-of-year seasonality climatology** (average activity by
   calendar day across every fetched year), since Delphi's reporting lag
   (recent weeks can be ~90 days behind) means the raw series alone can't
   cover the most recent portion of the trailing window the synthetic
   generator needs. → `processed/flu_seasonality_by_doy.csv`.
3. **`synthetic/generate.py`** — the layer public data can't provide:
   hospitals, suppliers, medicines, inventory, patients, consumption,
   weather. Consumption for each (hospital, medicine) pair is scaled by
   the real climatology above, weighted by a per-medicine
   **flu-sensitivity** (antibiotics/respiratory/antiviral react strongly;
   cardiovascular/endocrine maintenance drugs barely move) — this is what
   "statistically anchored to real demand" means concretely. Reproducible
   (fixed random seed). → `synthetic/*.csv`.
4. **`backend/scripts/seed_database.py`** — loads those CSVs into Postgres
   via the real SQLAlchemy models (not pandas — see
   `docs/architecture.md`). Reference tables (hospitals/medicines/
   suppliers) upsert by natural key; the high-volume tables only seed once
   unless `--reset`.

### About OpenPrescribing

The original plan (see the project's build log) paired FluView with **NHS
OpenPrescribing** for a second real demand series. Live testing found
OpenPrescribing now sits behind Cloudflare bot-protection that blocks
automated access entirely — 403 on every request, including the plain
homepage, not just the API. Rather than force it or route around the
protection, FluView's real seasonality climatology became the sole
real-data anchor, applied across medicine categories via the
flu-sensitivity weights above. NHSBSA's official Open Data Portal
(`opendata.nhsbsa.net`, the same underlying data, CKAN-based, not
Cloudflare-protected) is a viable path back to UK prescribing-specific
volumes if that's wanted later — its datasets are just large enough
(national-scale monthly dispensing) to need more than a lightweight fetch
script.

### Narrative seeding — documented, not hidden

`synthetic/generate.py` deliberately plants a subset of inventory batches
into demo-relevant states, tagged `narrative_seed` in `inventory.csv`:

- **`near_expiry`** (~15% of hospital×medicine pairs): a batch expiring in
  5-25 days, so the Expiry Risk story has real material.
- **`understocked`** (~10%): current stock deliberately below safety
  stock, so the Shortage/Transfer story does too.

This is standard practice for demo datasets — the point of calling it out
here is that it's inspectable, not a hidden thumb on the scale.

## Directories

- `raw/` — untouched API pulls (`fetch_fluview.py`'s output).
- `processed/` — the seasonality climatology (`build_processed.py`'s output).
- `synthetic/` — the generated layer (`generate.py`'s output) — what
  `seed_database.py` actually loads.
- `pipeline/` — the ingestion/generation scripts themselves + their
  `requirements.txt`.

None of the generated CSVs are committed (see `.gitignore`) — only the
scripts that produce them.
