#!/usr/bin/env python3
"""Generate PharmaLink AI's synthetic layer: hospitals, suppliers, medicines,
inventory, patients, consumption, and weather — everything public data
can't provide (see data/README.md). Statistically anchored to the real
FluView seasonality climatology built by build_processed.py: consumption
for flu-sensitive medicine categories (antibiotics, respiratory, antiviral)
is scaled up during real historical flu-activity peaks, low-sensitivity
categories (cardiovascular, endocrine maintenance drugs) barely move.

Also does deliberate **narrative seeding** — a documented subset of
hospital/medicine pairs get planted near-expiry batches or understocked
positions, so the Expiry/Shortage/Transfer story has real material to work
with in a demo. This is standard practice for demo datasets, not hidden:
every planted row is tagged in the code below.

Reproducible: a fixed random seed means reruns produce the same dataset.

Usage: python generate.py  (run after build_processed.py)
Output: data/synthetic/{hospitals,suppliers,medicines,inventory,patients,consumption,weather}.csv
"""

from __future__ import annotations

import argparse
import math
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = Path(__file__).resolve().parent.parent
PROCESSED_PATH = DATA_DIR / "processed" / "flu_seasonality_by_doy.csv"
OUTPUT_DIR = Path(__file__).resolve().parent

CONSUMPTION_WINDOW_DAYS = 180
PATIENT_WINDOW_DAYS = 90
TODAY = date.today()

rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class HospitalSpec:
    code: str
    name: str
    city: str
    region: str
    latitude: float
    longitude: float
    type: str
    bed_capacity: int


HOSPITALS: list[HospitalSpec] = [
    HospitalSpec("KFSH-RUH", "King Faisal Specialist Hospital", "Riyadh", "Central", 24.7136, 46.6753, "teaching", 900),
    HospitalSpec("RUH-CTL", "Riyadh Central Hospital", "Riyadh", "Central", 24.6408, 46.7728, "general", 450),
    HospitalSpec("KAMC-JED", "King Abdulaziz Medical City", "Jeddah", "Western", 21.5433, 39.1728, "teaching", 700),
    HospitalSpec("JED-GEN", "Jeddah General Hospital", "Jeddah", "Western", 21.4858, 39.1925, "general", 350),
    HospitalSpec("DMM-MED", "Dammam Medical Complex", "Dammam", "Eastern", 26.4207, 50.0888, "general", 400),
    HospitalSpec("MAD-KFH", "King Fahd Hospital", "Madinah", "Western", 24.5247, 39.5692, "general", 300),
    HospitalSpec("ABHA-SPC", "Abha Specialist Hospital", "Abha", "Southern", 18.2164, 42.5053, "specialty", 250),
    HospitalSpec("TBK-CTL", "Tabuk Central Hospital", "Tabuk", "Northern", 28.3998, 36.5715, "clinic", 120),
]

SUPPLIERS: list[dict] = [
    {"name": "Gulf Pharma Distribution", "contact_email": "orders@gulfpharma.example", "lead_time_days": 5, "reliability_score": 0.95},
    {"name": "Saudi MedSupply Co", "contact_email": "sales@saudimedsupply.example", "lead_time_days": 7, "reliability_score": 0.90},
    {"name": "Al-Rajhi Healthcare Logistics", "contact_email": "info@alrajhihealth.example", "lead_time_days": 10, "reliability_score": 0.80},
    {"name": "National Pharma Trading", "contact_email": "contact@nationalpharma.example", "lead_time_days": 4, "reliability_score": 0.85},
]


@dataclass(slots=True)
class MedicineSpec:
    name: str
    generic_name: str
    category: str
    unit: str
    unit_cost: float
    requires_refrigeration: bool
    flu_sensitivity: float  # 0 (unrelated to flu season) .. 1 (directly flu-driven)
    base_daily_rate_per_100_beds: float
    shelf_life_days: tuple[int, int]  # (min, max) days from manufacture to expiry


MEDICINES: list[MedicineSpec] = [
    MedicineSpec("Insulin Human", "Insulin human", "Endocrine", "vial", 45.0, True, 0.05, 0.8, (365, 730)),
    MedicineSpec("Metformin", "Metformin hydrochloride", "Endocrine", "tablet", 0.15, False, 0.05, 3.0, (540, 900)),
    MedicineSpec("Amoxicillin", "Amoxicillin", "Antibiotic", "tablet", 0.30, False, 0.70, 2.5, (365, 545)),
    MedicineSpec("Azithromycin", "Azithromycin", "Antibiotic", "tablet", 0.90, False, 0.75, 1.2, (365, 545)),
    MedicineSpec("Ceftriaxone", "Ceftriaxone sodium", "Antibiotic", "vial", 3.5, True, 0.60, 1.0, (365, 545)),
    MedicineSpec("Salbutamol", "Salbutamol sulfate", "Respiratory", "inhaler", 4.0, False, 0.65, 1.5, (365, 730)),
    MedicineSpec("Budesonide", "Budesonide", "Respiratory", "inhaler", 12.0, False, 0.50, 0.9, (365, 730)),
    MedicineSpec("Paracetamol", "Paracetamol", "Analgesic", "tablet", 0.05, False, 0.60, 5.0, (540, 900)),
    MedicineSpec("Ibuprofen", "Ibuprofen", "Analgesic", "tablet", 0.08, False, 0.40, 3.5, (540, 900)),
    MedicineSpec("Atorvastatin", "Atorvastatin calcium", "Cardiovascular", "tablet", 0.25, False, 0.02, 2.8, (540, 900)),
    MedicineSpec("Amlodipine", "Amlodipine besylate", "Cardiovascular", "tablet", 0.20, False, 0.02, 2.6, (540, 900)),
    MedicineSpec("Omeprazole", "Omeprazole", "Gastrointestinal", "capsule", 0.18, False, 0.05, 2.2, (540, 900)),
    MedicineSpec("Oseltamivir", "Oseltamivir phosphate", "Antiviral", "capsule", 8.0, False, 0.95, 0.3, (365, 545)),
]

_DEPARTMENT_BY_CATEGORY = {
    "Endocrine": "Endocrinology",
    "Antibiotic": "Internal Medicine",
    "Respiratory": "Pulmonology",
    "Analgesic": "General Ward",
    "Cardiovascular": "Cardiology",
    "Gastrointestinal": "Gastroenterology",
    "Antiviral": "Infectious Disease",
}

_AGE_BANDS = ["0-17", "18-34", "35-54", "55-74", "75+"]
_AGE_BAND_WEIGHTS = [0.12, 0.18, 0.25, 0.28, 0.17]
_DIAGNOSIS_CODES = ["J06.9", "E11.9", "I10", "J45.9", "A09", "J18.9"]


def load_seasonality(*, demo: bool = False) -> np.ndarray:
    if demo:
        print("Demo mode: using synthetic seasonality, not observed FluView data.")
        days = np.arange(1, 367)
        return (1 + np.cos(2 * np.pi * (days - 15) / 366)) / 2
    if not PROCESSED_PATH.exists():
        print(f"{PROCESSED_PATH} not found — run build_processed.py first.", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(PROCESSED_PATH).sort_values("day_of_year")
    return df["flu_index"].to_numpy()


def flu_index_for(seasonality: np.ndarray, d: date) -> float:
    doy = min(d.timetuple().tm_yday, len(seasonality))
    return float(seasonality[doy - 1])


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_consumption(seasonality: np.ndarray) -> pd.DataFrame:
    """Daily consumption per hospital x medicine, real-signal-scaled. One
    row per (hospital, medicine, day) with that day's total quantity — an
    aggregated daily figure rather than individual dispensing transactions,
    which keeps row counts sane for a demo dataset while still giving the
    forecaster a genuine daily time series per hospital x medicine."""
    rows = []
    days = [TODAY - timedelta(days=offset) for offset in range(CONSUMPTION_WINDOW_DAYS, 0, -1)]

    for hospital in HOSPITALS:
        occupancy_rate = rng.uniform(0.55, 0.95)
        size_factor = (hospital.bed_capacity / 100) * (0.7 + 0.6 * occupancy_rate)

        for medicine in MEDICINES:
            # Fixed per (hospital, medicine) multiplier: some hospitals are
            # consistently heavier/lighter users of a given medicine.
            hospital_weight = rng.lognormal(mean=0.0, sigma=0.3)

            for d in days:
                flu_idx = flu_index_for(seasonality, d)
                seasonal_multiplier = 1 + medicine.flu_sensitivity * flu_idx * 2
                expected_qty = (
                    medicine.base_daily_rate_per_100_beds
                    * size_factor
                    * hospital_weight
                    * seasonal_multiplier
                )
                quantity = int(rng.poisson(max(expected_qty, 0.1)))
                if quantity <= 0:
                    continue
                rows.append(
                    {
                        "hospital_code": hospital.code,
                        "medicine_name": medicine.name,
                        "quantity": quantity,
                        "consumed_at": d.isoformat(),
                        "department": _DEPARTMENT_BY_CATEGORY[medicine.category],
                    }
                )

    return pd.DataFrame(rows)


def _avg_daily_recent(consumption: pd.DataFrame, hospital_code: str, medicine_name: str) -> float:
    cutoff = TODAY - timedelta(days=30)
    mask = (
        (consumption["hospital_code"] == hospital_code)
        & (consumption["medicine_name"] == medicine_name)
        & (pd.to_datetime(consumption["consumed_at"]).dt.date >= cutoff)
    )
    total = consumption.loc[mask, "quantity"].sum()
    return max(total / 30, 0.1)


def generate_inventory(consumption: pd.DataFrame) -> pd.DataFrame:
    """Batches sized off each pair's trailing consumption rate, with
    deliberate narrative seeding: ~15% of pairs get a near-expiry batch
    (feeds the Expiry Risk story), a disjoint ~10% get planted understocked
    (feeds Shortage/Transfer) — both tagged `narrative_seed` in the output
    for transparency, not hidden in the numbers."""
    rows = []
    supplier_names = [s["name"] for s in SUPPLIERS]
    supplier_weights = np.array([s["reliability_score"] for s in SUPPLIERS])
    supplier_weights = supplier_weights / supplier_weights.sum()

    for hospital in HOSPITALS:
        for medicine in MEDICINES:
            avg_daily = _avg_daily_recent(consumption, hospital.code, medicine.name)
            safety_stock = round(avg_daily * rng.uniform(7, 10))

            roll = rng.random()
            narrative_seed = "none"
            if roll < 0.10:
                # Planted shortage: below safety stock right now.
                target_stock = max(round(safety_stock * rng.uniform(0.3, 0.8)), 1)
                narrative_seed = "understocked"
                batch_plan = [(target_stock, rng.integers(200, 400))]
            elif roll < 0.25:
                # Planted near-expiry batch alongside a normal one.
                target_stock = round(avg_daily * rng.uniform(25, 45))
                near_expiry_qty = max(round(target_stock * rng.uniform(0.2, 0.4)), 1)
                remaining_qty = max(target_stock - near_expiry_qty, 1)
                narrative_seed = "near_expiry"
                batch_plan = [
                    (near_expiry_qty, int(rng.integers(5, 25))),
                    (remaining_qty, int(rng.integers(200, 500))),
                ]
            else:
                target_stock = round(avg_daily * rng.uniform(25, 45))
                if target_stock > 40 and rng.random() < 0.4:
                    split = target_stock // 2
                    batch_plan = [
                        (split, int(rng.integers(150, 400))),
                        (target_stock - split, int(rng.integers(400, 650))),
                    ]
                else:
                    batch_plan = [(target_stock, int(rng.integers(150, 500)))]

            supplier_name = rng.choice(supplier_names, p=supplier_weights)
            for seq, (qty, days_to_expiry) in enumerate(batch_plan, start=1):
                if qty <= 0:
                    continue
                expiry_date = TODAY + timedelta(days=int(days_to_expiry))
                shelf_life = int(rng.integers(*medicine.shelf_life_days))
                manufactured_date = expiry_date - timedelta(days=shelf_life)
                rows.append(
                    {
                        "hospital_code": hospital.code,
                        "medicine_name": medicine.name,
                        "batch_number": f"{hospital.code}-{medicine.name[:4].upper()}-{seq}",
                        "current_stock": int(qty),
                        "safety_stock": int(safety_stock),
                        "storage_location": "Cold Storage" if medicine.requires_refrigeration else "Main Pharmacy",
                        "expiry_date": expiry_date.isoformat(),
                        "manufactured_date": manufactured_date.isoformat(),
                        "supplier_name": supplier_name,
                        "unit_cost_at_receipt": round(medicine.unit_cost * rng.uniform(0.9, 1.1), 4),
                        "narrative_seed": narrative_seed,
                        # seed_database.py attaches a synthetic
                        # inventory_history consumption trail (what
                        # InventoryRepository.average_daily_consumption
                        # reads — a different table from consumption.csv,
                        # see docs/database.md) to exactly one batch per
                        # (hospital, medicine) pair, using this rate, so
                        # the pair's total apparent consumption isn't
                        # double-counted across multiple batches.
                        "avg_daily_consumption": round(avg_daily, 3) if seq == 1 else 0,
                    }
                )

    return pd.DataFrame(rows)


def generate_patients() -> pd.DataFrame:
    rows = []
    for hospital in HOSPITALS:
        occupancy_rate = rng.uniform(0.55, 0.95)
        admission_count = round(hospital.bed_capacity * occupancy_rate * rng.uniform(0.3, 0.6))
        for _ in range(admission_count):
            admission_offset = int(rng.integers(0, PATIENT_WINDOW_DAYS))
            admission_date = TODAY - timedelta(days=admission_offset)
            still_admitted = rng.random() < 0.10
            stay_days = int(rng.integers(1, 11))
            discharge_date = None if still_admitted else admission_date + timedelta(days=stay_days)
            rows.append(
                {
                    "hospital_code": hospital.code,
                    "anonymized_ref": f"PT-{uuid.uuid4().hex[:10]}",
                    "age_band": rng.choice(_AGE_BANDS, p=_AGE_BAND_WEIGHTS),
                    "admission_date": admission_date.isoformat(),
                    "discharge_date": discharge_date.isoformat() if discharge_date else "",
                    "primary_diagnosis_code": rng.choice(_DIAGNOSIS_CODES),
                }
            )
    return pd.DataFrame(rows)


def generate_weather(seasonality: np.ndarray) -> pd.DataFrame:
    """Synthetic-but-seasonally-plausible: real weather would need a second
    keyed API (NOAA) out of scope here. `flu_activity_index` is the one
    genuinely real-data-derived column — the same climatology consumption
    is scaled against."""
    rows = []
    regions = sorted({h.region for h in HOSPITALS})
    days = [TODAY - timedelta(days=offset) for offset in range(CONSUMPTION_WINDOW_DAYS, 0, -1)]

    for region in regions:
        for d in days:
            doy = d.timetuple().tm_yday
            temperature_c = 30 + 15 * math.cos(2 * math.pi * (doy - 200) / 365) + rng.normal(0, 2)
            humidity_pct = float(np.clip(35 - 10 * math.cos(2 * math.pi * (doy - 200) / 365) + rng.normal(0, 5), 5, 90))
            rows.append(
                {
                    "region": region,
                    "recorded_date": d.isoformat(),
                    "temperature_c": round(float(temperature_c), 1),
                    "humidity_pct": round(humidity_pct, 1),
                    "flu_activity_index": round(flu_index_for(seasonality, d), 4),
                }
            )
    return pd.DataFrame(rows)


def write_csv(df: pd.DataFrame, name: str) -> None:
    path = OUTPUT_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  {name}.csv: {len(df):,} rows -> {path}")


def main() -> None:
    print(f"Generating synthetic layer (seed={SEED}, as of {TODAY.isoformat()}) ...")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use offline synthetic seasonality.")
    args = parser.parse_args()
    seasonality = load_seasonality(demo=args.demo)

    hospitals_df = pd.DataFrame([asdict(h) for h in HOSPITALS])
    hospitals_df["occupancy_rate"] = [round(rng.uniform(0.55, 0.95), 3) for _ in HOSPITALS]
    suppliers_df = pd.DataFrame(SUPPLIERS)
    medicines_df = pd.DataFrame(
        [
            {
                "name": m.name,
                "generic_name": m.generic_name,
                "category": m.category,
                "unit": m.unit,
                "unit_cost": m.unit_cost,
                "requires_refrigeration": m.requires_refrigeration,
                "is_controlled": False,
            }
            for m in MEDICINES
        ]
    )

    consumption_df = generate_consumption(seasonality)
    inventory_df = generate_inventory(consumption_df)
    patients_df = generate_patients()
    weather_df = generate_weather(seasonality)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(hospitals_df, "hospitals")
    write_csv(suppliers_df, "suppliers")
    write_csv(medicines_df, "medicines")
    write_csv(inventory_df, "inventory")
    write_csv(patients_df, "patients")
    write_csv(consumption_df, "consumption")
    write_csv(weather_df, "weather")

    seeded = inventory_df["narrative_seed"].value_counts().to_dict()
    print(f"Narrative seeding: {seeded}")


if __name__ == "__main__":
    main()
