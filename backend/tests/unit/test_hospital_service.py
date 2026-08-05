"""Unit tests for HospitalService business rules — no DB, no Docker."""

from __future__ import annotations

import pytest

from app.application.hospitals.service import HospitalService
from app.domain.hospitals.exceptions import HospitalCodeAlreadyExistsError, HospitalNotFoundError
from app.domain.shared.enums import HospitalType
from tests.unit.fakes import FakeHospitalRepository


@pytest.fixture
def service() -> HospitalService:
    return HospitalService(FakeHospitalRepository())


async def test_create_hospital_normalizes_code_to_uppercase(service: HospitalService) -> None:
    hospital = await service.create(
        name="St. Mary's",
        code="stm-01",
        latitude=24.71,
        longitude=46.67,
        city="Riyadh",
        region="Central",
        bed_capacity=250,
        type=HospitalType.GENERAL,
    )
    assert hospital.code == "STM-01"


async def test_create_hospital_rejects_duplicate_code(service: HospitalService) -> None:
    await service.create(
        name="Hospital A",
        code="DUP-01",
        latitude=0.0,
        longitude=0.0,
        city="City",
        region="Region",
        bed_capacity=100,
        type=HospitalType.GENERAL,
    )

    with pytest.raises(HospitalCodeAlreadyExistsError):
        await service.create(
            name="Hospital B",
            code="DUP-01",
            latitude=0.0,
            longitude=0.0,
            city="City",
            region="Region",
            bed_capacity=100,
            type=HospitalType.GENERAL,
        )


async def test_get_missing_hospital_raises_not_found(service: HospitalService) -> None:
    import uuid

    with pytest.raises(HospitalNotFoundError):
        await service.get(uuid.uuid4())


async def test_update_occupancy_rejects_out_of_range_value(service: HospitalService) -> None:
    hospital = await service.create(
        name="Hospital C",
        code="C-01",
        latitude=0.0,
        longitude=0.0,
        city="City",
        region="Region",
        bed_capacity=100,
        type=HospitalType.CLINIC,
    )

    with pytest.raises(ValueError, match="occupancy_rate"):
        await service.update_occupancy(hospital.id, 1.5)


async def test_deactivate_hospital_flips_is_active(service: HospitalService) -> None:
    hospital = await service.create(
        name="Hospital D",
        code="D-01",
        latitude=0.0,
        longitude=0.0,
        city="City",
        region="Region",
        bed_capacity=50,
        type=HospitalType.SPECIALTY,
    )

    deactivated = await service.deactivate(hospital.id)

    assert deactivated.is_active is False
    assert hospital.id not in {h.id for h in await service.list()}
