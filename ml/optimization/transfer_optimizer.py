"""Network-wide transfer recommendation: the classic transportation
problem (surplus hospitals -> deficit hospitals), solved as a linear
program with OR-Tools' GLOP solver.

Objective maximizes total quantity moved (satisfying as much network-wide
shortage as possible is the dominant goal — a hospital running out of
insulin matters far more than a few dollars of trucking cost), with
distance as a tiny tie-breaker among otherwise-equal allocations. Integer
results fall out naturally: transportation-problem constraint matrices are
totally unimodular, so an LP relaxation with integer supply/demand already
has an integer optimum (a standard OR result) — no MIP needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from ortools.linear_solver import pywraplp

# Deliberately duplicated from backend/app/domain/shared/geo.py rather than
# imported: /ml must stay importable standalone (a notebook, a script)
# without the backend installed — see docs/architecture.md's boundary design.
_EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2_r - lat1_r, lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * asin(sqrt(a))


# Tiny relative to 1.0-per-unit-moved — only breaks ties between
# allocations that satisfy the same total quantity, never trades away
# satisfied shortage for a shorter trip.
_DISTANCE_TIEBREAK_WEIGHT = 1e-5
_MIN_RECOMMENDED_QUANTITY = 5


@dataclass(slots=True, frozen=True)
class HospitalState:
    hospital_id: str
    current_stock: int
    safety_stock: int
    forecasted_demand: float
    """Forecasted demand over the optimization horizon."""
    latitude: float
    longitude: float

    @property
    def projected_position(self) -> float:
        """> 0 = surplus (can send); < 0 = deficit (needs to receive)."""
        return self.current_stock - self.safety_stock - self.forecasted_demand


@dataclass(slots=True, frozen=True)
class TransferRecommendation:
    source_hospital_id: str
    destination_hospital_id: str
    quantity: int
    distance_km: float


def solve_network_transfers(states: list[HospitalState]) -> list[TransferRecommendation]:
    surplus = [s for s in states if s.projected_position > 0]
    deficit = [s for s in states if s.projected_position < 0]
    if not surplus or not deficit:
        return []

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:  # pragma: no cover — GLOP always ships with ortools
        msg = "OR-Tools GLOP solver unavailable"
        raise RuntimeError(msg)

    distances: dict[tuple[int, int], float] = {}
    variables: dict[tuple[int, int], pywraplp.Variable] = {}
    for i, source in enumerate(surplus):
        for j, dest in enumerate(deficit):
            distance = _haversine_km(source.latitude, source.longitude, dest.latitude, dest.longitude)
            distances[i, j] = distance
            variables[i, j] = solver.NumVar(0, solver.infinity(), f"x_{i}_{j}")

    for i, source in enumerate(surplus):
        solver.Add(sum(variables[i, j] for j in range(len(deficit))) <= source.projected_position)
    for j, dest in enumerate(deficit):
        solver.Add(sum(variables[i, j] for i in range(len(surplus))) <= -dest.projected_position)

    objective = solver.Objective()
    for (i, j), var in variables.items():
        objective.SetCoefficient(var, 1.0 - _DISTANCE_TIEBREAK_WEIGHT * distances[i, j])
    objective.SetMaximization()

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return []

    recommendations = []
    for (i, j), var in variables.items():
        quantity = round(var.solution_value())
        if quantity < _MIN_RECOMMENDED_QUANTITY:
            continue
        recommendations.append(
            TransferRecommendation(
                source_hospital_id=surplus[i].hospital_id,
                destination_hospital_id=deficit[j].hospital_id,
                quantity=quantity,
                distance_km=round(distances[i, j], 2),
            )
        )
    return recommendations
