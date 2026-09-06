#!/usr/bin/env python3
"""Seed the database from data/processed + data/synthetic CSVs (see
data/README.md and data/synthetic/generate.py for how they're produced).

Run inside the backend container, which has the real DB connection and ORM
models — this is the one script outside `infrastructure/db/repositories`
sanctioned to construct ORM models directly, since it's a bulk data-load
path, not a request-serving one (see docs/architecture.md):

    docker compose -f docker/docker-compose.yml --env-file docker/.env \\
        run --rm backend python scripts/seed_database.py [--reset]

Reads with the stdlib `csv` module, not pandas — keeps /backend free of
data-science dependencies. Reference tables (suppliers, hospitals,
medicines) are upserted by natural key, so reruns are always safe without
--reset. The high-volume tables (inventory + inventory_history, patients,
consumption, weather) are only (re)seeded if empty, or unconditionally
with --reset — which clears only those tables, never auth/hospital/
medicine data, so it's safe to run against a DB with real user accounts.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import random
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.domain.shared.enums import HospitalType, InventoryChangeReason
from app.infrastructure.db.demo_insights import initialize_insights
from app.infrastructure.db.models import (
    ConsumptionModel,
    HospitalModel,
    InventoryHistoryModel,
    InventoryModel,
    MedicineModel,
    PatientModel,
    SupplierModel,
    WeatherModel,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"

# How many trailing days of synthetic inventory_history CONSUMPTION rows to
# write per (hospital, medicine) pair — this is what
# InventoryRepository.average_daily_consumption() (used by Expiry's and
# Procurement's naive scorers) actually reads. A *different* table from
# consumption.csv/ConsumptionModel, which is the demand-forecasting signal
# for Milestone C — see the comment on `avg_daily_consumption` in
# data/synthetic/generate.py for why both need seeding.
CONSUMPTION_TRAIL_DAYS = 30


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _bool(value: str) -> bool:
    return value.strip().lower() == "true"


async def _seed_suppliers(session: AsyncSession) -> dict[str, UUID]:
    rows = _read_csv(SYNTHETIC_DIR / "suppliers.csv")
    by_name: dict[str, UUID] = {}
    created = 0
    for row in rows:
        existing = await session.scalar(
            select(SupplierModel).where(SupplierModel.name == row["name"])
        )
        if existing is not None:
            by_name[row["name"]] = existing.id
            continue
        model = SupplierModel(
            id=uuid4(),
            name=row["name"],
            contact_email=row["contact_email"] or None,
            lead_time_days=int(row["lead_time_days"]),
            reliability_score=float(row["reliability_score"]),
            is_active=True,
        )
        session.add(model)
        await session.flush()
        by_name[row["name"]] = model.id
        created += 1
    print(f"Suppliers: {created} created, {len(by_name) - created} already present")
    return by_name


async def _seed_hospitals(session: AsyncSession) -> dict[str, UUID]:
    rows = _read_csv(SYNTHETIC_DIR / "hospitals.csv")
    by_code: dict[str, UUID] = {}
    created = 0
    for row in rows:
        existing = await session.scalar(
            select(HospitalModel).where(HospitalModel.code == row["code"])
        )
        if existing is not None:
            by_code[row["code"]] = existing.id
            continue
        model = HospitalModel(
            id=uuid4(),
            name=row["name"],
            code=row["code"],
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            city=row["city"],
            region=row["region"],
            bed_capacity=int(row["bed_capacity"]),
            occupancy_rate=float(row["occupancy_rate"]),
            type=HospitalType(row["type"]),
            is_active=True,
        )
        session.add(model)
        await session.flush()
        by_code[row["code"]] = model.id
        created += 1
    print(f"Hospitals: {created} created, {len(by_code) - created} already present")
    return by_code


async def _seed_medicines(session: AsyncSession) -> dict[str, UUID]:
    rows = _read_csv(SYNTHETIC_DIR / "medicines.csv")
    by_name: dict[str, UUID] = {}
    created = 0
    for row in rows:
        existing = await session.scalar(
            select(MedicineModel).where(MedicineModel.name == row["name"])
        )
        if existing is not None:
            by_name[row["name"]] = existing.id
            continue
        model = MedicineModel(
            id=uuid4(),
            name=row["name"],
            generic_name=row["generic_name"],
            atc_code=None,
            category=row["category"],
            unit=row["unit"],
            unit_cost=float(row["unit_cost"]),
            requires_refrigeration=_bool(row["requires_refrigeration"]),
            is_controlled=_bool(row["is_controlled"]),
            is_active=True,
        )
        session.add(model)
        await session.flush()
        by_name[row["name"]] = model.id
        created += 1
    print(f"Medicines: {created} created, {len(by_name) - created} already present")
    return by_name


def _consumption_trail_rows(
    inventory_id: UUID, hospital_id: UUID, medicine_id: UUID, avg_daily: float
) -> list[dict[str, object]]:
    today = date.today()
    trail = []
    for offset in range(CONSUMPTION_TRAIL_DAYS):
        day = today - timedelta(days=offset)
        quantity = max(round(random.gauss(avg_daily, avg_daily * 0.3)), 0)
        if quantity <= 0:
            continue
        trail.append(
            {
                "id": uuid4(),
                "recorded_at": datetime.combine(day, time(18, 0), tzinfo=UTC),
                "inventory_id": inventory_id,
                "hospital_id": hospital_id,
                "medicine_id": medicine_id,
                "change_qty": -quantity,
                "reason": InventoryChangeReason.CONSUMPTION,
            }
        )
    return trail


async def _seed_inventory(
    session: AsyncSession,
    hospitals: dict[str, UUID],
    medicines: dict[str, UUID],
    suppliers: dict[str, UUID],
) -> None:
    rows = _read_csv(SYNTHETIC_DIR / "inventory.csv")
    history_rows: list[dict[str, object]] = []

    for row in rows:
        hospital_id = hospitals[row["hospital_code"]]
        medicine_id = medicines[row["medicine_name"]]
        inventory_id = uuid4()
        manufactured_date = date.fromisoformat(row["manufactured_date"])
        current_stock = int(row["current_stock"])

        session.add(
            InventoryModel(
                id=inventory_id,
                hospital_id=hospital_id,
                medicine_id=medicine_id,
                batch_number=row["batch_number"],
                current_stock=current_stock,
                safety_stock=int(row["safety_stock"]),
                storage_location=row["storage_location"] or None,
                expiry_date=date.fromisoformat(row["expiry_date"]),
                manufactured_date=manufactured_date,
                supplier_id=suppliers.get(row["supplier_name"]),
                unit_cost_at_receipt=float(row["unit_cost_at_receipt"]),
            )
        )
        history_rows.append(
            {
                "id": uuid4(),
                "recorded_at": datetime.combine(manufactured_date, time(9, 0), tzinfo=UTC),
                "inventory_id": inventory_id,
                "hospital_id": hospital_id,
                "medicine_id": medicine_id,
                "change_qty": current_stock,
                "reason": InventoryChangeReason.RECEIPT,
            }
        )

        avg_daily = float(row["avg_daily_consumption"])
        if avg_daily > 0:
            history_rows.extend(
                _consumption_trail_rows(inventory_id, hospital_id, medicine_id, avg_daily)
            )

    await session.flush()  # inventory rows need real PKs before history FKs reference them
    if history_rows:
        await session.execute(insert(InventoryHistoryModel), history_rows)
    print(
        f"Inventory: {len(rows)} batches, {len(history_rows)} history rows "
        "(receipt + consumption trail)"
    )


async def _seed_patients(session: AsyncSession, hospitals: dict[str, UUID]) -> None:
    rows = _read_csv(SYNTHETIC_DIR / "patients.csv")
    payload = [
        {
            "id": uuid4(),
            "hospital_id": hospitals[row["hospital_code"]],
            "anonymized_ref": row["anonymized_ref"],
            "age_band": row["age_band"],
            "admission_date": date.fromisoformat(row["admission_date"]),
            "discharge_date": (
                date.fromisoformat(row["discharge_date"]) if row["discharge_date"] else None
            ),
            "primary_diagnosis_code": row["primary_diagnosis_code"] or None,
        }
        for row in rows
    ]
    if payload:
        await session.execute(insert(PatientModel), payload)
    print(f"Patients: {len(payload)}")


async def _seed_consumption(
    session: AsyncSession, hospitals: dict[str, UUID], medicines: dict[str, UUID]
) -> None:
    rows = _read_csv(SYNTHETIC_DIR / "consumption.csv")
    payload = [
        {
            "id": uuid4(),
            "consumed_at": datetime.combine(
                date.fromisoformat(row["consumed_at"]), time(12, 0), tzinfo=UTC
            ),
            "hospital_id": hospitals[row["hospital_code"]],
            "medicine_id": medicines[row["medicine_name"]],
            "patient_id": None,
            "quantity": int(row["quantity"]),
            "department": row["department"] or None,
        }
        for row in rows
    ]
    if payload:
        await session.execute(insert(ConsumptionModel), payload)
    print(f"Consumption: {len(payload)}")


async def _seed_weather(session: AsyncSession) -> None:
    rows = _read_csv(SYNTHETIC_DIR / "weather.csv")
    payload = [
        {
            "id": uuid4(),
            "recorded_date": date.fromisoformat(row["recorded_date"]),
            "region": row["region"],
            "temperature_c": float(row["temperature_c"]),
            "humidity_pct": float(row["humidity_pct"]),
            "flu_activity_index": float(row["flu_activity_index"]),
        }
        for row in rows
    ]
    if payload:
        await session.execute(insert(WeatherModel), payload)
    print(f"Weather: {len(payload)}")


async def _clear_volume_tables(session: AsyncSession) -> None:
    """Only the high-volume synthetic tables — never hospitals/medicines/
    suppliers (upserted, never destructive) or anything auth-related."""
    volume_models = (
        ConsumptionModel,
        WeatherModel,
        InventoryHistoryModel,
        InventoryModel,
        PatientModel,
    )
    for model in volume_models:
        await session.execute(delete(model))
    print("Reset: cleared inventory, inventory_history, patients, consumption, weather.")


async def seed(*, reset: bool) -> None:
    random.seed(42)  # reproducible synthetic consumption-trail jitter, matching generate.py
    required_files = (
        "hospitals.csv",
        "suppliers.csv",
        "medicines.csv",
        "inventory.csv",
        "patients.csv",
        "consumption.csv",
        "weather.csv",
    )
    for name in required_files:
        if not (SYNTHETIC_DIR / name).exists():
            msg = (
                f"{SYNTHETIC_DIR / name} not found — "
                "run the data pipeline first (see data/README.md)."
            )
            raise SystemExit(msg)

    async with AsyncSessionLocal() as session:
        suppliers = await _seed_suppliers(session)
        hospitals = await _seed_hospitals(session)
        medicines = await _seed_medicines(session)
        await session.commit()

        if reset:
            await _clear_volume_tables(session)
            await session.commit()

        existing_inventory = await session.scalar(select(func.count()).select_from(InventoryModel))
        if existing_inventory and not reset:
            print(
                f"inventory already has {existing_inventory} rows — skipping volume tables "
                "(pass --reset to clear and reseed them)."
            )
        else:
            await _seed_inventory(session, hospitals, medicines, suppliers)
            await _seed_patients(session, hospitals)
            await _seed_consumption(session, hospitals, medicines)
            await _seed_weather(session)
            await session.commit()

    async with AsyncSessionLocal() as session:
        await initialize_insights(session)

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear inventory/inventory_history/patients/consumption/weather before reseeding.",
    )
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))


if __name__ == "__main__":
    main()
