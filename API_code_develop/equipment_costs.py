"""
Equipment cost module (Turton-based)

This module provides a flexible API to estimate equipment costs for
pumps, compressors, turbines, and fans using Turton's correlations.

Design goals:
- SI inputs (power in Watt) and SI-aware outputs
- Adjustable CEPCI and base year/index as inputs (defaults provided)
- Returns purchased, bare-module, and installed costs for TIC workflows
- Supports material and pressure factors (F_M, F_P) hooks
- Device subtypes with sensible defaults:
  - Pump: centrifugal (default)
  - Compressor: centrifugal (default)
  - Turbine: axial (default)
  - Fan: four types; default is centrifugal radial; limited to ~0.16 barg

NOTE:
- Turton correlation coefficients and BM/installation factors must be
  filled in the indicated placeholders during the next step.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Tuple


# --------------------------------------------------------------------------------------
# Types
# --------------------------------------------------------------------------------------

PumpType = Literal["centrifugal", "reciprocating"]
CompressorType = Literal["centrifugal", "axial", "reciprocating"]
TurbineType = Literal["axial", "radial"]
FanType = Literal[
    "centrifugal_radial",  # default
    "centrifugal_backward_curved",
    "axial_tubeaxial",
    "axial_vaneless"
]

MaterialType = Literal[
    "CS",          # carbon steel
    "SS",          # stainless steel
    "Ni",          # nickel alloy
    "Cu",          # copper
    "Cl",          # cast iron (for pumps table)
    "Ti",          # titanium
    "Fiberglass"   # for fans table
]


@dataclass
class CEPCIOptions:
    base_year: int = 2017
    base_index: float = 567.5  # CEPCI 2017 (Turton tables base)
    target_index: Optional[float] = None  # if None, equals base_index


@dataclass
class CostInputs:
    power_watt: float  # shaft power in W (SI)
    material_factor: float = 1.0  # F_M
    pressure_factor: float = 1.0  # F_P (rating/MAWP correction)
    pressure_bar: Optional[float] = None  # optional pressure rating or rise in bar
    # Optional meta
    notes: Optional[str] = None


# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------

def adjust_cost_to_index(cost_at_base_index: float, base_index: float, target_index: Optional[float]) -> float:
    """
    Scale a cost reported at CEPCI base_index to target_index.
    If target_index is None, returns the original cost.
    """
    if target_index is None or target_index == 0:
        return cost_at_base_index
    if base_index is None or base_index == 0:
        return cost_at_base_index
    return cost_at_base_index * (target_index / base_index)


def watt_to_kilowatt(power_watt: float) -> float:
    return power_watt / 1000.0


# --------------------------------------------------------------------------------------
# Placeholder correlation helpers (to be completed in next steps)
# --------------------------------------------------------------------------------------

@dataclass
class LogQuadraticCoeff:
    """
    Represents Turton-style purchased cost correlation of the form:
      log10(Cp) = k1 + k2*log10(S) + k3*(log10(S))^2
    where S is the sizing variable (e.g., kW or hp).
    """
    k1: float
    k2: float
    k3: float
    size_basis: Literal["kW", "hp"] = "kW"


# In-memory registries for coefficients per equipment subtype
_PUMP_COEFFS: Dict[PumpType, LogQuadraticCoeff] = {}
_COMP_COEFFS: Dict[CompressorType, LogQuadraticCoeff] = {}
_TURB_COEFFS: Dict[TurbineType, LogQuadraticCoeff] = {}
_FAN_COEFFS: Dict[FanType, LogQuadraticCoeff] = {}


def register_pump_correlation(pump_type: PumpType, coeff: LogQuadraticCoeff) -> None:
    _PUMP_COEFFS[pump_type] = coeff


def register_compressor_correlation(comp_type: CompressorType, coeff: LogQuadraticCoeff) -> None:
    _COMP_COEFFS[comp_type] = coeff


def register_turbine_correlation(turbine_type: TurbineType, coeff: LogQuadraticCoeff) -> None:
    _TURB_COEFFS[turbine_type] = coeff


def register_fan_correlation(fan_type: FanType, coeff: LogQuadraticCoeff) -> None:
    _FAN_COEFFS[fan_type] = coeff


def _eval_log_quadratic_cost(size_value: float, coeff: LogQuadraticCoeff) -> float:
    import math
    if size_value <= 0:
        raise ValueError("Size value must be positive for cost correlation")
    logS = math.log10(size_value)
    logC = coeff.k1 + coeff.k2 * logS + coeff.k3 * (logS ** 2)
    return 10.0 ** logC


def _turton_purchased_cost_pump_kw(power_kw: float, pump_type: PumpType) -> float:
    """
    Turton purchased cost correlation for pumps (base material, base pressure).
    RETURN: purchased cost at base CEPCI (in USD)

    Uses registered coefficients; size basis may be kW or hp depending on data source.
    """
    coeff = _PUMP_COEFFS.get(pump_type)
    if coeff is None:
        raise NotImplementedError(f"Pump coefficients not registered for type: {pump_type}")
    if coeff.size_basis == "kW":
        size_val = power_kw
    else:  # hp basis
        size_val = power_kw / 0.7457  # kW to hp
    return _eval_log_quadratic_cost(size_val, coeff)


def _turton_purchased_cost_compressor_kw(power_kw: float, comp_type: CompressorType) -> float:
    """Turton purchased cost correlation for compressors."""
    coeff = _COMP_COEFFS.get(comp_type)
    if coeff is None:
        raise NotImplementedError(f"Compressor coefficients not registered for type: {comp_type}")
    if coeff.size_basis == "kW":
        size_val = power_kw
    else:
        size_val = power_kw / 0.7457
    return _eval_log_quadratic_cost(size_val, coeff)


def _turton_purchased_cost_turbine_kw(power_kw: float, turbine_type: TurbineType) -> float:
    """Turton purchased cost correlation for turbines."""
    coeff = _TURB_COEFFS.get(turbine_type)
    if coeff is None:
        raise NotImplementedError(f"Turbine coefficients not registered for type: {turbine_type}")
    if coeff.size_basis == "kW":
        size_val = power_kw
    else:
        size_val = power_kw / 0.7457
    return _eval_log_quadratic_cost(size_val, coeff)


def _turton_purchased_cost_fan_kw(power_kw: float, fan_type: FanType) -> float:
    """
    Turton purchased cost correlation for fans.
    Constraint: fans generally for pressure rise up to ~0.16 barg.
    """
    coeff = _FAN_COEFFS.get(fan_type)
    if coeff is None:
        raise NotImplementedError(f"Fan coefficients not registered for type: {fan_type}")
    if coeff.size_basis == "kW":
        size_val = power_kw
    else:
        size_val = power_kw / 0.7457
    return _eval_log_quadratic_cost(size_val, coeff)


def _apply_material_pressure_factors(purchased_cost: float, F_M: float, F_P: float) -> float:
    return purchased_cost * F_M * F_P


def _to_bare_module_cost(purchased_cost: float, bm_factor: float) -> float:
    return purchased_cost * bm_factor


def _to_installed_cost(bare_module_cost: float, install_factor: float) -> float:
    return bare_module_cost * install_factor


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

# Wmax(kW) limits from provided Turton tables
_WMAX_KW: Dict[str, Dict[str, float]] = {
    "pump": {
        "centrifugal": 300.0,
        "reciprocating": 200.0,
    },
    "compressor": {
        "centrifugal": 3000.0,
        "axial": 3000.0,
        "reciprocating": 3000.0,
    },
    "turbine": {
        "axial": 4000.0,
        "radial": 1500.0,
    },
}

def _sum_costs(parts):
    total = {"purchased": 0.0, "purchased_adj": 0.0, "bare_module": 0.0, "installed": 0.0}
    for c in parts:
        for k in total:
            total[k] += float(c.get(k, 0.0))
    return total

def estimate_pump_cost(
    inputs: CostInputs,
    cepci: CEPCIOptions = CEPCIOptions(),
    pump_type: PumpType = "centrifugal",
    bm_factor: Optional[float] = None,  # if None, computed from Turton B1,B2 and material Fm
    material: MaterialType = "CS",
    install_factor: float = 1.0,  # placeholder
    _split: bool = True
) -> Dict[str, float]:
    """
    Returns a dict with keys: purchased, purchased_adj, bare_module, installed
    - purchased: at base CEPCI
    - purchased_adj: adjusted to target CEPCI (if provided)
    """
    # Split by Wmax if needed
    power_kw = watt_to_kilowatt(inputs.power_watt)
    if _split:
        max_kw = _WMAX_KW.get("pump", {}).get(pump_type)
        if max_kw and power_kw > max_kw:
            import math
            n = int(math.ceil(power_kw / max_kw))
            per_kw = power_kw / n
            per_inputs = CostInputs(
                power_watt=per_kw * 1000.0,
                material_factor=inputs.material_factor,
                pressure_factor=inputs.pressure_factor,
                pressure_bar=inputs.pressure_bar,
                notes=inputs.notes,
            )
            parts = [
                estimate_pump_cost(per_inputs, cepci=cepci, pump_type=pump_type, bm_factor=bm_factor, material=material, install_factor=install_factor, _split=False)
                for _ in range(n)
            ]
            return _sum_costs(parts)
    purchased_base = _turton_purchased_cost_pump_kw(power_kw, pump_type)
    # material factor: pumps table provides Fm*; multiply purchased
    fm = _resolve_material_factor("pump", pump_type, material)
    fp = _resolve_pressure_factor("pump", pump_type, inputs.pressure_bar)
    purchased_base = _apply_material_pressure_factors(purchased_base, fm, fp)
    purchased_adj = adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index or cepci.base_index)
    # Pump BM from Turton: FBM = B1 + B2 * Fm(material)
    if bm_factor is None:
        B1, B2 = _resolve_pump_b1b2(pump_type)
        effective_bm = B1 + B2 * fm
    else:
        effective_bm = bm_factor
    bare = _to_bare_module_cost(purchased_adj, effective_bm)
    installed = _to_installed_cost(bare, install_factor)
    return {
        "purchased": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module": bare,
        "installed": installed,
    }


def estimate_compressor_cost(
    inputs: CostInputs,
    cepci: CEPCIOptions = CEPCIOptions(),
    comp_type: CompressorType = "centrifugal",
    bm_factor: Optional[float] = None,
    material: MaterialType = "CS",
    install_factor: float = 1.0,
    _split: bool = True
) -> Dict[str, float]:
    power_kw = watt_to_kilowatt(inputs.power_watt)
    if _split:
        max_kw = _WMAX_KW.get("compressor", {}).get(comp_type)
        if max_kw and power_kw > max_kw:
            import math
            n = int(math.ceil(power_kw / max_kw))
            per_kw = power_kw / n
            per_inputs = CostInputs(
                power_watt=per_kw * 1000.0,
                material_factor=inputs.material_factor,
                pressure_factor=inputs.pressure_factor,
                pressure_bar=inputs.pressure_bar,
                notes=inputs.notes,
            )
            parts = [
                estimate_compressor_cost(per_inputs, cepci=cepci, comp_type=comp_type, bm_factor=bm_factor, material=material, install_factor=install_factor, _split=False)
                for _ in range(n)
            ]
            return _sum_costs(parts)
    purchased_base = _turton_purchased_cost_compressor_kw(power_kw, comp_type)
    # compressor table provides FBM by material; material factor defaults to 1
    purchased_base = _apply_material_pressure_factors(purchased_base, 1.0, 1.0)
    purchased_adj = adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index or cepci.base_index)
    effective_bm = bm_factor if bm_factor is not None else _resolve_bm("compressor", comp_type, material)
    bare = _to_bare_module_cost(purchased_adj, effective_bm)
    installed = _to_installed_cost(bare, install_factor)
    return {
        "purchased": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module": bare,
        "installed": installed,
    }


def estimate_turbine_cost(
    inputs: CostInputs,
    cepci: CEPCIOptions = CEPCIOptions(),
    turbine_type: TurbineType = "axial",
    bm_factor: Optional[float] = None,
    material: MaterialType = "CS",
    install_factor: float = 1.0,
    _split: bool = True
) -> Dict[str, float]:
    power_kw = watt_to_kilowatt(inputs.power_watt)
    if _split:
        max_kw = _WMAX_KW.get("turbine", {}).get(turbine_type)
        if max_kw and power_kw > max_kw:
            import math
            n = int(math.ceil(power_kw / max_kw))
            per_kw = power_kw / n
            per_inputs = CostInputs(
                power_watt=per_kw * 1000.0,
                material_factor=inputs.material_factor,
                pressure_factor=inputs.pressure_factor,
                pressure_bar=inputs.pressure_bar,
                notes=inputs.notes,
            )
            parts = [
                estimate_turbine_cost(per_inputs, cepci=cepci, turbine_type=turbine_type, bm_factor=bm_factor, material=material, install_factor=install_factor, _split=False)
                for _ in range(n)
            ]
            return _sum_costs(parts)
    purchased_base = _turton_purchased_cost_turbine_kw(power_kw, turbine_type)
    purchased_base = _apply_material_pressure_factors(purchased_base, 1.0, 1.0)
    purchased_adj = adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index or cepci.base_index)
    effective_bm = bm_factor if bm_factor is not None else _resolve_bm("turbine", turbine_type, material)
    bare = _to_bare_module_cost(purchased_adj, effective_bm)
    installed = _to_installed_cost(bare, install_factor)
    return {
        "purchased": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module": bare,
        "installed": installed,
    }


def estimate_fan_cost(
    inputs: CostInputs,
    cepci: CEPCIOptions = CEPCIOptions(),
    fan_type: FanType = "centrifugal_radial",
    bm_factor: Optional[float] = None,
    material: MaterialType = "CS",
    install_factor: float = 1.0
) -> Dict[str, float]:
    power_kw = watt_to_kilowatt(inputs.power_watt)
    purchased_base = _turton_purchased_cost_fan_kw(power_kw, fan_type)
    fp = _resolve_pressure_factor("fan", fan_type, inputs.pressure_bar)
    purchased_base = _apply_material_pressure_factors(purchased_base, 1.0, fp)
    purchased_adj = adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index or cepci.base_index)
    effective_bm = bm_factor if bm_factor is not None else _resolve_bm("fan", fan_type, material)
    bare = _to_bare_module_cost(purchased_adj, effective_bm)
    installed = _to_installed_cost(bare, install_factor)
    return {
        "purchased": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module": bare,
        "installed": installed,
    }


# Convenience function for TIC breakdown (sum or per-equipment handled externally)
def format_cost_breakdown(costs: Dict[str, float]) -> str:
    return (
        f"Purchased (base): {costs['purchased']:.2f}\n"
        f"Purchased (adj):  {costs['purchased_adj']:.2f}\n"
        f"Bare module:      {costs['bare_module']:.2f}\n"
        f"Installed:        {costs['installed']:.2f}"
    )


# --------------------------------------------------------------------------------------
# Default correlation and BM-factor registration from provided tables
# --------------------------------------------------------------------------------------

_BM_MAP: Dict[str, Dict[str, Dict[str, float]]] = {
    # category -> subtype -> material -> BM
    "compressor": {
        "centrifugal": {"CS": 2.7, "SS": 5.8, "Ni": 11.5},
        "axial": {"CS": 3.8, "SS": 8.0, "Ni": 15.9},
        # rotary and reciprocating present in data; subtype names differ from our CompressorType
        # they can be added later if needed
        "reciprocating": {"CS": 3.4, "SS": 7.0, "Ni": 13.9},
    },
    "fan": {
        "centrifugal_radial": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
        "centrifugal_backward_curved": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
        "axial_tubeaxial": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
        "axial_vaneless": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
    },
    "turbine": {
        "axial": {"CS": 3.5, "SS": 6.1, "Ni": 11.7},
        "radial": {"CS": 3.5, "SS": 6.1, "Ni": 11.7},
    },
    # Pumps table shows material correction factors (Fm*): use as material factors, not BM
}


def _resolve_bm(category: str, subtype: str, material: MaterialType = "CS") -> float:
    by_cat = _BM_MAP.get(category, {})
    by_type = by_cat.get(subtype, {})
    # default to CS if not found
    return by_type.get(material, by_type.get("CS", 1.0))


_FM_MAP: Dict[str, Dict[str, Dict[str, float]]] = {
    # category -> subtype -> material -> F_M
    "pump": {
        "centrifugal": {"Cl": 1.0, "CS": 1.6, "SS": 2.3, "Ni": 4.4},
        "reciprocating": {"Cl": 1.0, "CS": 1.5, "SS": 2.4, "Ni": 4.0, "Ti": 6.4},
    }
}


def _resolve_material_factor(category: str, subtype: str, material: MaterialType = "CS") -> float:
    by_cat = _FM_MAP.get(category, {})
    by_type = by_cat.get(subtype, {})
    return by_type.get(material, 1.0)


_PUMP_B1B2: Dict[PumpType, Tuple[float, float]] = {
    # From provided Pump Data table (B1, B2 columns)
    "centrifugal": (1.89, 1.35),
    "reciprocating": (1.89, 1.35),  # table shows same B1,B2 for listed pump types
}


def _resolve_pump_b1b2(pump_type: PumpType) -> Tuple[float, float]:
    return _PUMP_B1B2.get(pump_type, (1.89, 1.35))


def register_default_correlations() -> None:
    """Register k1,k2,k3 coefficients parsed from the provided tables (kW basis)."""
    # Compressors (without electric motors) — power basis kW
    register_compressor_correlation("centrifugal", LogQuadraticCoeff(k1=2.2891, k2=1.3604, k3=-0.1027, size_basis="kW"))
    register_compressor_correlation("axial", LogQuadraticCoeff(k1=2.2891, k2=1.3604, k3=-0.1027, size_basis="kW"))
    register_compressor_correlation("reciprocating", LogQuadraticCoeff(k1=2.2891, k2=1.3604, k3=-0.1027, size_basis="kW"))
    # (Rotary available but not in enum; can be added if needed)

    # Fans (include electric motors) — treat size basis as kW per requirement
    register_fan_correlation("centrifugal_radial", LogQuadraticCoeff(k1=3.5391, k2=-0.3533, k3=0.4477, size_basis="kW"))
    register_fan_correlation("centrifugal_backward_curved", LogQuadraticCoeff(k1=3.3471, k2=-0.0734, k3=0.3090, size_basis="kW"))
    register_fan_correlation("axial_tubeaxial", LogQuadraticCoeff(k1=3.0414, k2=-0.3375, k3=0.4722, size_basis="kW"))
    register_fan_correlation("axial_vaneless", LogQuadraticCoeff(k1=3.1761, k2=-0.1373, k3=0.3414, size_basis="kW"))

    # Pumps (including electric drives)
    register_pump_correlation("centrifugal", LogQuadraticCoeff(k1=3.3892, k2=0.0536, k3=0.1538, size_basis="kW"))
    register_pump_correlation("reciprocating", LogQuadraticCoeff(k1=3.8696, k2=0.3161, k3=0.1220, size_basis="kW"))
    # Positive displacement available in table; add later if needed

    # Turbines
    register_turbine_correlation("axial", LogQuadraticCoeff(k1=2.7051, k2=1.4398, k3=-0.1776, size_basis="kW"))
    register_turbine_correlation("radial", LogQuadraticCoeff(k1=2.2476, k2=1.4965, k3=-0.1618, size_basis="kW"))


# Pressure factor resolution based on table constraints
_PRESSURE_LIMIT_BAR: Dict[str, float] = {
    # category-specific maximum applicable pressure rise (approximate)
    "fan": 0.16,  # as provided in the fan table (Pmax)
}


def _resolve_pressure_factor(category: str, subtype: str, pressure_bar: Optional[float]) -> float:
    if pressure_bar is None:
        return 1.0
    limit = _PRESSURE_LIMIT_BAR.get(category)
    if limit is None:
        return 1.0
    # If requested pressure exceeds limit, naive linear penalty (can be refined with exact spec)
    if pressure_bar <= limit:
        return 1.0
    return pressure_bar / limit


# --------------------------------------------------------------------------------------
# Aspen helpers (optional): read power/pressure and convert internally
# --------------------------------------------------------------------------------------

_POWER_TO_WATT: Dict[str, float] = {
    "Watt": 1.0,
    "W": 1.0,
    "kW": 1000.0,
    "MW": 1_000_000.0,
    "hp": 745.7,
    "Btu/hr": 0.293071,  # W per (Btu/hr)
}

def _convert_power_to_watt(value: float, unit: Optional[str]) -> float:
    if unit is None:
        return float(value)
    factor = _POWER_TO_WATT.get(unit)
    if factor is None:
        # fall back: assume already Watt
        return float(value)
    return float(value) * factor

_PRESSURE_TO_BAR: Dict[str, float] = {
    "N/sqm": 1e-5,   # Pa to bar
    "Pa": 1e-5,
    "pa": 1e-5,
    "kPa": 1e-2,
    "MPa": 10.0,
    "bar": 1.0,
    "bara": 1.0,
    "atm": 1.01325,
    "psi": 0.0689476,
    "PsIa": 0.0689476,
    "mbar": 0.001,
}

def _convert_pressure_to_bar(value: float, unit: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    if unit is None:
        return None
    # Handle gauge units explicitly by converting to absolute bar
    u = unit.strip()
    try:
        if u.lower() == 'barg':
            return float(value) + 1.01325
        if u.lower() == 'psig':
            return float(value) * 0.0689476 + 1.01325
        if u.lower() == 'atmg':
            return float(value) * 1.01325 + 1.01325
        if u.lower() == 'pag':
            return float(value) * 1e-5 + 1.01325
        if u.lower() == 'kpag':
            return float(value) * 1e-2 + 1.01325
        if u.lower() == 'mpag':
            return float(value) * 10.0 + 1.01325
        if u.lower() == 'mbarg':
            return float(value) * 1e-3 + 1.01325
    except Exception:
        return None
    factor = _PRESSURE_TO_BAR.get(u)
    if factor is None:
        return None
    return float(value) * factor


def _is_gauge_pressure_unit(unit: Optional[str]) -> bool:
    if not unit:
        return False
    u = unit.strip().lower()
    return u in {"barg", "pag", "kpag", "mpag", "psig", "atmg", "mbarg"}


def _read_pressure_bar(Application, block_name: str, pressure_unit: Optional[str], which: str) -> Optional[float]:
    node_name = 'IN_PRES' if which == 'inlet' else 'POC'
    for section in ('Output', 'Results'):
        try:
            node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\{section}\\{node_name}")
            if node is None or node.Value is None:
                continue
            sval = str(node.Value).strip()
            if not sval:
                continue
            return _convert_pressure_to_bar(float(sval), pressure_unit)
        except Exception:
            continue
    return None


def estimate_pump_cost_from_aspen(
    Application,
    block_name: str,
    power_unit: Optional[str],
    cepci: CEPCIOptions,
    pump_type: PumpType = "centrifugal",
    material: MaterialType = "CS",
    install_factor: float = 1.0
) -> Dict[str, float]:
    try:
        node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\WNET")
        if node is None:
            raise ValueError("WNET not found")
        power_watt = _convert_power_to_watt(float(node.Value), power_unit)
        return estimate_pump_cost(CostInputs(power_watt=power_watt), cepci=cepci, pump_type=pump_type, material=material, install_factor=install_factor)
    except Exception as e:
        raise e


def estimate_compressor_cost_from_aspen(
    Application,
    block_name: str,
    power_unit: Optional[str],
    pressure_unit: Optional[str],
    cepci: CEPCIOptions,
    comp_type: CompressorType = "centrifugal",
    material: MaterialType = "CS",
    install_factor: float = 1.0,
    auto_use_fan_when_low_pressure: bool = True,
    fan_type: FanType = "centrifugal_radial"
) -> Dict[str, float]:
    try:
        nP = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\WNET")
        if nP is None:
            raise ValueError("WNET not found")
        power_watt = _convert_power_to_watt(float(nP.Value), power_unit)
        nPr = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\POC")
        pressure_bar = _convert_pressure_to_bar(float(nPr.Value), pressure_unit) if nPr is not None else None
        # If within fan operating pressure (by outlet gauge pressure), compute fan cost
        if auto_use_fan_when_low_pressure and pressure_bar is not None:
            limit = _PRESSURE_LIMIT_BAR.get("fan", 0.16)
            outlet_gauge_bar = pressure_bar - 1.01325 if not _is_gauge_pressure_unit(pressure_unit) else pressure_bar
            if outlet_gauge_bar <= limit:
                return estimate_fan_cost(
                    CostInputs(power_watt=power_watt, pressure_bar=pressure_bar),
                    cepci=cepci,
                    fan_type=fan_type,
                    material=material,
                    install_factor=install_factor,
                )
        return estimate_compressor_cost(CostInputs(power_watt=power_watt, pressure_bar=pressure_bar), cepci=cepci, comp_type=comp_type, material=material, install_factor=install_factor)
    except Exception as e:
        raise e


def estimate_fan_cost_from_aspen(
    Application,
    block_name: str,
    power_unit: Optional[str],
    pressure_unit: Optional[str],
    cepci: CEPCIOptions,
    fan_type: FanType = "centrifugal_radial",
    material: MaterialType = "CS",
    install_factor: float = 1.0
) -> Dict[str, float]:
    try:
        nP = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\WNET")
        if nP is None:
            raise ValueError("WNET not found")
        power_watt = _convert_power_to_watt(float(nP.Value), power_unit)
        nPr = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\POC")
        pressure_bar = _convert_pressure_to_bar(float(nPr.Value), pressure_unit) if nPr is not None else None
        return estimate_fan_cost(CostInputs(power_watt=power_watt, pressure_bar=pressure_bar), cepci=cepci, fan_type=fan_type, material=material, install_factor=install_factor)
    except Exception as e:
        raise e


def estimate_turbine_cost_from_aspen(
    Application,
    block_name: str,
    power_unit: Optional[str],
    cepci: CEPCIOptions,
    turbine_type: TurbineType = "axial",
    material: MaterialType = "CS",
    install_factor: float = 1.0
) -> Dict[str, float]:
    try:
        nP = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\WNET")
        if nP is None:
            raise ValueError("WNET not found")
        power_watt = _convert_power_to_watt(float(nP.Value), power_unit)
        return estimate_turbine_cost(CostInputs(power_watt=power_watt), cepci=cepci, turbine_type=turbine_type, material=material, install_factor=install_factor)
    except Exception as e:
        raise e



# High-level batch helper to compute costs for pressure-driven equipment modeled
# as compressors in Aspen (auto-detect fan/turbine where applicable)
def calculate_pressure_device_costs_from_aspen(
    Application,
    block_info: Dict[str, str],
    power_unit: Optional[str],
    pressure_unit: Optional[str],
    material: MaterialType = "CS",
    cepci: CEPCIOptions = CEPCIOptions(target_index=None),
    material_overrides: Optional[Dict[str, MaterialType]] = None,
):
    """
    Parameters
    -----------
    Application: Aspen Plus COM object
    block_info: dict mapping block_name -> category (as parsed in main)
    power_unit: current unit set's POWER unit string
    pressure_unit: current unit set's PRESSURE unit string

    Returns
    -------
    (results, totals): list of per-device dicts, and totals dict
    """
    compressor_blocks = [name for name, cat in block_info.items() if cat in ('Compr', 'MCompr')]
    pump_blocks = [name for name, cat in block_info.items() if cat in ('Pump',)]
    results = []
    totals = {"purchased": 0.0, "purchased_adj": 0.0, "bare_module": 0.0, "installed": 0.0}

    # Pumps
    for name in pump_blocks:
        try:
            m = (material_overrides or {}).get(name, material)
            costs = estimate_pump_cost_from_aspen(Application, name, power_unit, cepci, pump_type="centrifugal", material=m)
            results.append({"name": name, "type": "pump", **costs})
            for k in totals:
                totals[k] += float(costs.get(k, 0.0))
        except Exception as e:
            results.append({"name": name, "type": "error", "error": str(e)})

    # Compressors / Turbines (auto fan)
    for name in compressor_blocks:
        try:
            # inlet/outlet absolute pressures to classify
            inlet_bar = _read_pressure_bar(Application, name, pressure_unit, 'inlet')
            outlet_bar = _read_pressure_bar(Application, name, pressure_unit, 'outlet')

            m = (material_overrides or {}).get(name, material)
            if inlet_bar is not None and outlet_bar is not None and inlet_bar > outlet_bar:
                costs = estimate_turbine_cost_from_aspen(Application, name, power_unit, cepci, turbine_type='axial', material=m)
                dtype = 'turbine'
            else:
                costs = estimate_compressor_cost_from_aspen(Application, name, power_unit, pressure_unit, cepci, comp_type='centrifugal', material=m)
                dtype = 'compressor/fan'

            results.append({"name": name, "type": dtype, **costs})
            for k in totals:
                totals[k] += float(costs.get(k, 0.0))
        except Exception as e:
            results.append({"name": name, "type": "error", "error": str(e)})

    return results, totals


# Convenience: auto-resolve POWER/PRESSURE units from a Unit Set name,
# then compute costs for compressor-like blocks
def _get_unit_type_value(Application, unit_set_name: str, unit_type: str) -> Optional[str]:
    try:
        node = Application.Tree.FindNode(f"\\Data\\Setup\\Units-Sets\\{unit_set_name}\\Unit-Types\\{unit_type}")
        return node.Value if node is not None else None
    except Exception:
        return None


def calculate_pressure_device_costs_auto(
    Application,
    block_info: Dict[str, str],
    current_unit_set: Optional[str],
    material: MaterialType = "CS",
    cepci: CEPCIOptions = CEPCIOptions(target_index=None),
    material_overrides: Optional[Dict[str, MaterialType]] = None,
):
    power_unit = None
    pressure_unit = None
    if current_unit_set:
        power_unit = _get_unit_type_value(Application, current_unit_set, 'POWER')
        pressure_unit = _get_unit_type_value(Application, current_unit_set, 'PRESSURE')
    return calculate_pressure_device_costs_from_aspen(
        Application,
        block_info,
        power_unit,
        pressure_unit,
        material=material,
        cepci=cepci,
        material_overrides=material_overrides,
    )


# ----------------------------------------------------------------------------
# Calculation using pre-extracted data (no COM reads inside)
# ----------------------------------------------------------------------------

def calculate_pressure_device_costs_with_data(
    pre_extracted: Dict[str, Dict[str, Optional[float]]],
    block_info: Dict[str, str],
    material: MaterialType = "CS",
    cepci: CEPCIOptions = CEPCIOptions(target_index=None),
    material_overrides: Optional[Dict[str, MaterialType]] = None,
):
    results = []
    totals = {"purchased": 0.0, "purchased_adj": 0.0, "bare_module": 0.0, "installed": 0.0}
    for name, cat in block_info.items():
        pdata = pre_extracted.get(name, {})
        pw = pdata.get('power_watt')
        inlet_bar = pdata.get('inlet_bar')
        outlet_bar = pdata.get('outlet_bar')
        m = (material_overrides or {}).get(name, material)
        try:
            if cat == 'Pump':
                if pw is None:
                    raise ValueError('Missing power_watt for pump')
                costs = estimate_pump_cost(CostInputs(power_watt=pw), cepci=cepci, pump_type='centrifugal', material=m)
                dtype = 'pump'
            elif cat in ('Compr', 'MCompr'):
                if pw is None:
                    raise ValueError('Missing power_watt for compressor-like device')
                # classify
                if inlet_bar is not None and outlet_bar is not None and inlet_bar > outlet_bar:
                    costs = estimate_turbine_cost(CostInputs(power_watt=pw), cepci=cepci, turbine_type='axial', material=m)
                    dtype = 'turbine'
                else:
                    # fan auto handled inside estimate_compressor_cost_from_aspen earlier; here use compressor cost directly
                    costs = estimate_compressor_cost(CostInputs(power_watt=pw, pressure_bar=outlet_bar), cepci=cepci, comp_type='centrifugal', material=m)
                    dtype = 'compressor/fan'
            else:
                continue
            results.append({"name": name, "type": dtype, **costs})
            for k in totals:
                totals[k] += float(costs.get(k, 0.0))
        except Exception as e:
            results.append({"name": name, "type": "error", "error": str(e)})
    return results, totals


# ----------------------------------------------------------------------------
# Preview helpers (to show extracted data before cost calculation)
# ----------------------------------------------------------------------------

def preview_pressure_devices_from_aspen(
    Application,
    block_info: Dict[str, str],
    power_unit: Optional[str],
    pressure_unit: Optional[str],
):
    compressor_blocks = [name for name, cat in block_info.items() if cat in ('Compr', 'MCompr')]
    pump_blocks = [name for name, cat in block_info.items() if cat in ('Pump',)]
    preview = []
    # Pumps: power + pressures (if available on pump blocks)
    for name in pump_blocks:
        try:
            nP = Application.Tree.FindNode(f"\\Data\\Blocks\\{name}\\Output\\WNET")
            pw = _convert_power_to_watt(float(nP.Value), power_unit) if nP is not None else None
            inlet_bar = _read_pressure_bar(Application, name, pressure_unit, 'inlet')
            outlet_bar = _read_pressure_bar(Application, name, pressure_unit, 'outlet')
            outlet_gauge = None
            if outlet_bar is not None:
                outlet_gauge = outlet_bar - 1.01325 if not _is_gauge_pressure_unit(pressure_unit) else outlet_bar
            preview.append({
                "name": name,
                "category": "Pump",
                "power_watt": pw,
                "inlet_bar": inlet_bar,
                "outlet_bar": outlet_bar,
                "outlet_gauge_bar": outlet_gauge,
                "suggested": "pump",
            })
        except Exception:
            preview.append({"name": name, "category": "Pump", "error": "failed to read"})

    # Compressors-like: power + pressures + suggested type
    for name in compressor_blocks:
        try:
            nP = Application.Tree.FindNode(f"\\Data\\Blocks\\{name}\\Output\\WNET")
            pw = _convert_power_to_watt(float(nP.Value), power_unit) if nP is not None else None
            inlet_bar = _read_pressure_bar(Application, name, pressure_unit, 'inlet')
            outlet_bar = _read_pressure_bar(Application, name, pressure_unit, 'outlet')
            outlet_gauge = None
            suggested = None
            if outlet_bar is not None:
                outlet_gauge = outlet_bar - 1.01325 if not _is_gauge_pressure_unit(pressure_unit) else outlet_bar
            if inlet_bar is not None and outlet_bar is not None:
                if outlet_bar > inlet_bar:
                    suggested = 'fan' if (outlet_gauge is not None and outlet_gauge <= _PRESSURE_LIMIT_BAR.get('fan', 0.16)) else 'compressor'
                elif inlet_bar > outlet_bar:
                    suggested = 'turbine'
            preview.append({
                "name": name,
                "category": "Compr/MCompr",
                "power_watt": pw,
                "inlet_bar": inlet_bar,
                "outlet_bar": outlet_bar,
                "outlet_gauge_bar": outlet_gauge,
                "suggested": suggested,
            })
        except Exception:
            preview.append({"name": name, "category": "Compr/MCompr", "error": "failed to read"})

    return preview


def preview_pressure_devices_auto(
    Application,
    block_info: Dict[str, str],
    current_unit_set: Optional[str],
):
    power_unit = None
    pressure_unit = None
    if current_unit_set:
        power_unit = _get_unit_type_value(Application, current_unit_set, 'POWER')
        pressure_unit = _get_unit_type_value(Application, current_unit_set, 'PRESSURE')
    return preview_pressure_devices_from_aspen(Application, block_info, power_unit, pressure_unit)
