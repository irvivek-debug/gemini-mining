"""Deterministic operational formulas. The model picks; Python computes."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from mining_agents.tools.base import ToolFailure, tool

NO_TABLES = ["(none — deterministic computation)"]


@dataclass(frozen=True)
class Formula:
    inputs: tuple[str, ...]
    expression: str
    fn: Callable[..., float]


def _rop(avg_daily_demand: float, lead_time_days: float, safety_stock: float) -> float:
    return avg_daily_demand * lead_time_days + safety_stock


def _eoq(annual_demand: float, order_cost: float, holding_cost: float) -> float:
    if holding_cost <= 0:
        raise ZeroDivisionError("holding_cost must be positive")
    return math.sqrt(2.0 * annual_demand * order_cost / holding_cost)


def _cpk(usl: float, lsl: float, mean: float, sigma: float) -> float:
    if sigma <= 0:
        raise ZeroDivisionError("sigma must be positive")
    return min((usl - mean) / (3.0 * sigma), (mean - lsl) / (3.0 * sigma))


def _oee(availability: float, performance: float, quality: float) -> float:
    return availability * performance * quality


def _littles_law(arrival_rate: float, wait_time: float) -> float:
    return arrival_rate * wait_time


_SPECS: dict[str, Formula] = {
    "rop": Formula(("avg_daily_demand", "lead_time_days", "safety_stock"),
                   "ROP = avg_daily_demand * lead_time_days + safety_stock", _rop),
    "eoq": Formula(("annual_demand", "order_cost", "holding_cost"),
                   "EOQ = sqrt(2 * D * S / H)", _eoq),
    "cpk": Formula(("usl", "lsl", "mean", "sigma"),
                   "Cpk = min((USL-mean)/(3*sigma), (mean-LSL)/(3*sigma))", _cpk),
    "oee": Formula(("availability", "performance", "quality"),
                   "OEE = availability * performance * quality", _oee),
    "littles_law": Formula(("arrival_rate", "wait_time"),
                           "L = lambda * W", _littles_law),
}

FORMULAS: dict[str, Callable[..., float]] = {k: v.fn for k, v in _SPECS.items()}


@tool(NO_TABLES)
def operational_math(formula: str, inputs: dict):
    """Compute ROP, EOQ, Cpk, OEE, or Little's Law deterministically."""
    spec = _SPECS.get(formula)
    if spec is None:
        raise ToolFailure(
            "UNKNOWN_FORMULA",
            f"no such formula {formula!r}",
            available=sorted(_SPECS),
        )
    missing = [name for name in spec.inputs if name not in inputs]
    if missing:
        raise ToolFailure(
            "INVALID_ARGUMENT",
            f"{formula} requires {list(spec.inputs)}",
            missing=missing,
        )
    try:
        value = spec.fn(**{name: float(inputs[name]) for name in spec.inputs})
    except (ZeroDivisionError, ValueError) as exc:
        raise ToolFailure("INVALID_ARGUMENT", str(exc), formula=formula) from exc
    return {"formula": formula, "expression": spec.expression, "value": value}, 0
