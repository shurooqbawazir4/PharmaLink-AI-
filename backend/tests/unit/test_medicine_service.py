"""Unit tests for MedicineService business rules — no DB, no Docker."""

from __future__ import annotations

import uuid

import pytest

from app.application.medicines.service import MedicineService
from app.domain.medicines.exceptions import MedicineNotFoundError
from tests.unit.fakes import FakeMedicineRepository


@pytest.fixture
def service() -> MedicineService:
    return MedicineService(FakeMedicineRepository())


async def test_create_medicine_rejects_non_positive_unit_cost(service: MedicineService) -> None:
    with pytest.raises(ValueError, match="unit_cost"):
        await service.create(
            name="Insulin",
            generic_name="Insulin human",
            category="Endocrine",
            unit="vial",
            unit_cost=0,
        )


async def test_create_and_get_medicine_round_trips(service: MedicineService) -> None:
    created = await service.create(
        name="Insulin",
        generic_name="Insulin human",
        category="Endocrine",
        unit="vial",
        unit_cost=12.5,
        requires_refrigeration=True,
    )

    fetched = await service.get(created.id)

    assert fetched.name == "Insulin"
    assert fetched.requires_refrigeration is True


async def test_get_missing_medicine_raises_not_found(service: MedicineService) -> None:
    with pytest.raises(MedicineNotFoundError):
        await service.get(uuid.uuid4())


async def test_update_unit_cost_rejects_non_positive_value(service: MedicineService) -> None:
    medicine = await service.create(
        name="Amoxicillin",
        generic_name="Amoxicillin",
        category="Antibiotic",
        unit="tablet",
        unit_cost=0.2,
    )

    with pytest.raises(ValueError, match="unit_cost"):
        await service.update_unit_cost(medicine.id, -1)


async def test_list_filters_by_category(service: MedicineService) -> None:
    await service.create(
        name="Amoxicillin",
        generic_name="Amoxicillin",
        category="Antibiotic",
        unit="tablet",
        unit_cost=0.2,
    )
    await service.create(
        name="Insulin",
        generic_name="Insulin human",
        category="Endocrine",
        unit="vial",
        unit_cost=12.5,
    )

    antibiotics = await service.list(category="Antibiotic")

    assert [m.name for m in antibiotics] == ["Amoxicillin"]
