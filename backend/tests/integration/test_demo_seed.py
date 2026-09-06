"""Render demo initialization preserves existing data on subsequent starts."""

import runpy
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.infrastructure.db.models import (
    AlertModel,
    ExpiryRiskModel,
    HospitalModel,
    InventoryModel,
    MedicineModel,
)
from scripts import seed_database


async def test_demo_seed_is_repeatable(session_factory, monkeypatch, tmp_path):
    generator = runpy.run_path(
        str(Path(__file__).resolve().parents[3] / "data/synthetic/generate.py")
    )
    generator["main"].__globals__["OUTPUT_DIR"] = tmp_path
    monkeypatch.setattr(sys, "argv", ["generate.py", "--demo"])
    generator["main"]()
    monkeypatch.setattr(seed_database, "SYNTHETIC_DIR", tmp_path)
    monkeypatch.setattr(seed_database, "AsyncSessionLocal", session_factory)
    await seed_database.seed(reset=False)
    async with session_factory() as session:
        counts = [
            await session.scalar(select(func.count()).select_from(model))
            for model in (HospitalModel, MedicineModel, InventoryModel, AlertModel, ExpiryRiskModel)
        ]
        hospital = await session.scalar(select(HospitalModel))
        hospital.name = "Preserved user edit"
        await session.commit()
    assert all(count > 0 for count in counts)
    await seed_database.seed(reset=False)
    async with session_factory() as session:
        assert counts == [
            await session.scalar(select(func.count()).select_from(model))
            for model in (HospitalModel, MedicineModel, InventoryModel, AlertModel, ExpiryRiskModel)
        ]
        assert await session.scalar(
            select(HospitalModel).where(HospitalModel.name == "Preserved user edit")
        )
