# MedCycle AI — Data

**Status: pipeline lands in Milestone B.**

- `raw/` — untouched pulls from public sources: NHS OpenPrescribing (real
  UK prescription volumes) and CDC FluView (weekly flu activity, a demand
  feature) — chosen over MIMIC-IV/eICU because they need no credentialed
  access approval.
- `processed/` — cleaned/joined output of the ingestion pipeline.
- `synthetic/` — the generated inventory/expiry/transfer/hospital layer,
  built to be statistically consistent with the real demand series in
  `processed/` (public datasets don't cover hospital inventory or expiry
  dates — that layer has to be synthesized; see the project's dataset
  research for why).

None of these directories are committed with real data (see `.gitignore`)
— only the folder structure, so the pipeline has a fixed place to write to.
