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
from typing import Literal, Optional, Dict, Tuple, List


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
    power_kilowatt: float  # shaft power in kW (SI)
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


# watt_to_kilowatt 함수 제거 - 이제 직접 kW로 변환하므로 불필요


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
    power_kw = inputs.power_kilowatt
    if _split:
        max_kw = _WMAX_KW.get("pump", {}).get(pump_type)
        if max_kw and power_kw > max_kw:
            import math
            n = int(math.ceil(power_kw / max_kw))
            per_kw = power_kw / n
            per_inputs = CostInputs(
                power_kilowatt=per_kw,
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
    power_kw = inputs.power_kilowatt
    if _split:
        max_kw = _WMAX_KW.get("compressor", {}).get(comp_type)
        if max_kw and power_kw > max_kw:
            import math
            n = int(math.ceil(power_kw / max_kw))
            per_kw = power_kw / n
            per_inputs = CostInputs(
                power_kilowatt=per_kw,
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
    power_kw = inputs.power_kilowatt
    if _split:
        max_kw = _WMAX_KW.get("turbine", {}).get(turbine_type)
        if max_kw and power_kw > max_kw:
            import math
            n = int(math.ceil(power_kw / max_kw))
            per_kw = power_kw / n
            per_inputs = CostInputs(
                power_kilowatt=per_kw,
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


def estimate_mcompr_cost(
    inputs: CostInputs,
    cepci: CEPCIOptions = CEPCIOptions(),
    bm_factor: Optional[float] = None,
    material: MaterialType = "CS",
    install_factor: float = 1.0
) -> Dict[str, float]:
    """
    MCompr (Multi-stage Compressor) 비용 추정
    MCompr는 일반적으로 더 복잡한 구조를 가지므로 별도의 비용 계산이 필요할 수 있음
    현재는 일반 압축기와 동일한 방식으로 처리하되, 향후 MCompr 전용 상관관계 추가 가능
    """
    power_kw = inputs.power_kilowatt
    
    # MCompr는 일반적으로 더 큰 용량이므로 분할 처리
    max_kw = 5000.0  # MCompr 전용 최대 용량 설정
    if power_kw > max_kw:
        import math
        n = int(math.ceil(power_kw / max_kw))
        per_kw = power_kw / n
        per_inputs = CostInputs(
            power_kilowatt=per_kw,
            material_factor=inputs.material_factor,
            pressure_factor=inputs.pressure_factor,
            pressure_bar=inputs.pressure_bar,
            notes=inputs.notes,
        )
        parts = [
            estimate_mcompr_cost(per_inputs, cepci=cepci, bm_factor=bm_factor, material=material, install_factor=install_factor)
            for _ in range(n)
        ]
        return _sum_costs(parts)
    
    # MCompr는 일반적으로 원심 압축기로 가정
    purchased_base = _turton_purchased_cost_compressor_kw(power_kw, "centrifugal")
    purchased_base = _apply_material_pressure_factors(purchased_base, 1.0, 1.0)
    purchased_adj = adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index or cepci.base_index)
    
    # MCompr는 더 복잡한 구조이므로 BM 인수가 일반 압축기보다 높을 수 있음
    effective_bm = bm_factor if bm_factor is not None else _resolve_bm("compressor", "centrifugal", material) * 1.2  # 20% 추가
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
    power_kw = inputs.power_kilowatt
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
# Data Caching System
# --------------------------------------------------------------------------------------

class AspenDataCache:
    """Aspen Plus 데이터를 캐싱하여 중복 읽기를 방지하는 클래스"""
    
    def __init__(self):
        self._block_data = {}
        self._unit_data = {}
        self._pressure_data = {}
        self._power_data = {}
    
    def get_block_data(self, Application, block_name: str) -> Dict[str, any]:
        """블록의 모든 데이터를 한 번에 읽어서 캐싱"""
        if block_name not in self._block_data:
            self._block_data[block_name] = self._extract_block_data(Application, block_name)
        return self._block_data[block_name]
    
    def _extract_block_data(self, Application, block_name: str) -> Dict[str, any]:
        """블록에서 모든 필요한 데이터를 한 번에 추출"""
        data = {
            'power_kilowatt': None,
            'inlet_pressure_bar': None,
            'outlet_pressure_bar': None,
            'available_nodes': {}
        }
        
        # Output 섹션에서만 노드 정보 수집
        try:
            section_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output")
            if section_node and hasattr(section_node, 'Elements'):
                for element in section_node.Elements:
                    try:
                        data['available_nodes'][element.Name] = element.Value
                    except:
                        pass
        except:
            pass
        
        return data
    
    def get_power_data(self, Application, block_name: str, power_unit: Optional[str]) -> Optional[float]:
        """전력 데이터를 캐싱하여 반환"""
        cache_key = f"{block_name}_{power_unit}"
        if cache_key not in self._power_data:
            self._power_data[cache_key] = self._extract_power_data(Application, block_name, power_unit)
        return self._power_data[cache_key]
    
    def _extract_power_data(self, Application, block_name: str, power_unit: Optional[str]) -> Optional[float]:
        """전력 데이터 추출"""
        try:
            node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\WNET")
            if node is None or node.Value is None:
                return None
            return _convert_power_to_kilowatt(float(node.Value), power_unit)
        except Exception:
            return None
    
    def get_pressure_data(self, Application, block_name: str, pressure_unit: Optional[str], which: str) -> Optional[float]:
        """압력 데이터를 캐싱하여 반환"""
        cache_key = f"{block_name}_{pressure_unit}_{which}"
        if cache_key not in self._pressure_data:
            self._pressure_data[cache_key] = self._extract_pressure_data(Application, block_name, pressure_unit, which)
        return self._pressure_data[cache_key]
    
    def _extract_pressure_data(self, Application, block_name: str, pressure_unit: Optional[str], which: str) -> Optional[float]:
        """압력 데이터 추출"""
        node_name = 'IN_PRES' if which == 'inlet' else 'POC'
        
        try:
            node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\{node_name}")
            if node is None or node.Value is None:
                return None
                
            sval = str(node.Value).strip()
            if not sval:
                return None
                
            return _convert_pressure_to_bar(float(sval), pressure_unit)
            
        except Exception:
            return None
    
    def clear_cache(self):
        """캐시 초기화"""
        self._block_data.clear()
        self._unit_data.clear()
        self._pressure_data.clear()
        self._power_data.clear()

# 전역 캐시 인스턴스
_aspen_cache = AspenDataCache()

def clear_aspen_cache():
    """Aspen Plus 데이터 캐시를 초기화하는 함수"""
    _aspen_cache.clear_cache()

def get_cache_stats():
    """캐시 통계를 반환하는 함수"""
    return {
        'block_data_count': len(_aspen_cache._block_data),
        'power_data_count': len(_aspen_cache._power_data),
        'pressure_data_count': len(_aspen_cache._pressure_data),
        'unit_data_count': len(_aspen_cache._unit_data)
    }

# --------------------------------------------------------------------------------------
# Aspen helpers (optional): read power/pressure and convert internally
# --------------------------------------------------------------------------------------

_POWER_TO_KILOWATT: Dict[str, float] = {
    "Watt": 0.001,      # W to kW
    "W": 0.001,         # W to kW
    "kW": 1.0,          # kW to kW (no conversion)
    "MW": 1000.0,       # MW to kW
    "hp": 0.7457,       # hp to kW
    "Btu/hr": 0.000293071,  # Btu/hr to kW
}

def _convert_power_to_kilowatt(value: float, unit: Optional[str]) -> float:
    """Aspen에서 추출한 파워 값을 단위에 따라 kW로 변환합니다."""
    if unit is None:
        # 단위가 없으면 값이 이미 kW라고 가정
        return float(value)
    factor = _POWER_TO_KILOWATT.get(unit)
    if factor is None:
        # 알 수 없는 단위면 값이 이미 kW라고 가정
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
    """캐시를 사용하여 압력 데이터를 읽어옴"""
    return _aspen_cache.get_pressure_data(Application, block_name, pressure_unit, which)


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
        power_kilowatt = _aspen_cache.get_power_data(Application, block_name, power_unit)
        if power_kilowatt is None:
            raise ValueError("WNET not found")
        return estimate_pump_cost(CostInputs(power_kilowatt=power_kilowatt), cepci=cepci, pump_type=pump_type, material=material, install_factor=install_factor)
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
        power_kilowatt = _aspen_cache.get_power_data(Application, block_name, power_unit)
        if power_kilowatt is None:
            raise ValueError("WNET not found")
        
        pressure_bar = _aspen_cache.get_pressure_data(Application, block_name, pressure_unit, 'outlet')
        
        # If within fan operating pressure (by outlet gauge pressure), compute fan cost
        if auto_use_fan_when_low_pressure and pressure_bar is not None:
            limit = _PRESSURE_LIMIT_BAR.get("fan", 0.16)
            outlet_gauge_bar = pressure_bar - 1.01325 if not _is_gauge_pressure_unit(pressure_unit) else pressure_bar
            if outlet_gauge_bar <= limit:
                return estimate_fan_cost(
                    CostInputs(power_kilowatt=power_kilowatt, pressure_bar=pressure_bar),
                    cepci=cepci,
                    fan_type=fan_type,
                    material=material,
                    install_factor=install_factor,
                )
        return estimate_compressor_cost(CostInputs(power_kilowatt=power_kilowatt, pressure_bar=pressure_bar), cepci=cepci, comp_type=comp_type, material=material, install_factor=install_factor)
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
        power_kilowatt = _aspen_cache.get_power_data(Application, block_name, power_unit)
        if power_kilowatt is None:
            raise ValueError("WNET not found")
        return estimate_fan_cost(CostInputs(power_kilowatt=power_kilowatt, pressure_bar=pressure_bar), cepci=cepci, fan_type=fan_type, material=material, install_factor=install_factor)
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
        power_kilowatt = _aspen_cache.get_power_data(Application, block_name, power_unit)
        if power_kilowatt is None:
            raise ValueError("WNET not found")
        return estimate_turbine_cost(CostInputs(power_kilowatt=power_kilowatt), cepci=cepci, turbine_type=turbine_type, material=material, install_factor=install_factor)
    except Exception as e:
        raise e


def _extract_mcompr_stage_data(
    Application,
    block_name: str,
    power_unit: Optional[str],
    pressure_unit: Optional[str],
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    MCompr 블록의 각 단계별 데이터를 추출하는 함수
    Elements를 통해 B_PRES와 BRAKE_POWER의 하위 노드를 파악하여 단계 수를 자동 결정
    """
    stage_data = {}
    
    try:
        # B_PRES 노드에서 하위 요소들 확인
        bpres_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\B_PRES")
        if bpres_node is None:
            return {}
        
        # Elements에서 단계 번호들 추출
        stage_numbers = []
        try:
            elements = bpres_node.Elements
            for i in range(elements.Count):
                element_name = elements.Item(i).Name
                if element_name.isdigit():
                    stage_numbers.append(int(element_name))
        except Exception as e:
            return {}
        
        if not stage_numbers:
            return {}
        
        stage_numbers.sort()  # 단계 번호 정렬
        
        # 각 단계별 토출 압력 추출
        for stage_num in stage_numbers:
            node_path = f"\\Data\\Blocks\\{block_name}\\Output\\B_PRES\\{stage_num}"
            node = Application.Tree.FindNode(node_path)
            
            if node is not None and node.Value is not None:
                pressure_bar = _convert_pressure_to_bar(float(node.Value), pressure_unit)
                stage_data[stage_num] = {'outlet_pressure_bar': pressure_bar}
        
        # BRAKE_POWER 노드에서 하위 요소들 확인
        brake_power_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\BRAKE_POWER")
        if brake_power_node is not None:
            try:
                elements = brake_power_node.Elements
                for i in range(elements.Count):
                    element_name = elements.Item(i).Name
                    if element_name.isdigit():
                        stage_num = int(element_name)
                        if stage_num in stage_data:  # B_PRES에서 확인된 단계만 처리
                            node_path = f"\\Data\\Blocks\\{block_name}\\Output\\BRAKE_POWER\\{stage_num}"
                            node = Application.Tree.FindNode(node_path)
                            
                            if node is not None and node.Value is not None:
                                power_kilowatt = _convert_power_to_kilowatt(float(node.Value), power_unit)
                                stage_data[stage_num]['power_kilowatt'] = power_kilowatt
            except Exception as e:
                # Error reading BRAKE_POWER Elements
                pass
        
        return stage_data
        
    except Exception as e:
        return {}


def _calculate_mcompr_stage_costs(
    stage_data: Dict[str, Dict[str, Optional[float]]],
    cepci: CEPCIOptions,
    material: MaterialType = "CS",
    install_factor: float = 1.0,
    include_intercoolers: bool = True
) -> Dict[str, Dict[str, float]]:
    """
    각 단계별 압축기 비용을 계산하는 함수
    Intercooler 비용도 포함하여 계산
    """
    stage_costs = {}
    intercooler_costs = {}
    total_costs = {"purchased": 0.0, "purchased_adj": 0.0, "bare_module": 0.0, "installed": 0.0}
    
    for stage_num, data in stage_data.items():
        power_kilowatt = data.get('power_kilowatt')
        outlet_pressure_bar = data.get('outlet_pressure_bar')
        
        if power_kilowatt is None:
            continue
            
        try:
            # 각 단계를 개별 압축기로 계산
            compressor_costs = estimate_compressor_cost(
                CostInputs(
                    power_kilowatt=power_kilowatt,
                    pressure_bar=outlet_pressure_bar
                ),
                cepci=cepci,
                comp_type="centrifugal",  # 일반적으로 원심 압축기로 가정
                material=material,
                install_factor=install_factor
            )
            
            stage_costs[f"Stage_{stage_num}"] = compressor_costs
            
            # 총 비용에 압축기 비용 추가
            for key in total_costs:
                total_costs[key] += compressor_costs.get(key, 0.0)
            
            # Intercooler 비용 계산 (마지막 단계 제외)
            if include_intercoolers and int(stage_num) < len(stage_data):
                # MCompr에서는 입구 압력이 없으므로 토출 압력만 사용
                intercooler_cost = _estimate_intercooler_cost(
                    None, outlet_pressure_bar, cepci, material
                )
                if intercooler_cost:
                    intercooler_costs[f"Intercooler_{stage_num}"] = intercooler_cost
                    
                    # 총 비용에 Intercooler 비용 추가
                    for key in total_costs:
                        total_costs[key] += intercooler_cost.get(key, 0.0)
                
        except Exception as e:
            # Error calculating cost for stage
            stage_costs[f"Stage_{stage_num}"] = {"error": str(e)}
    
    return stage_costs, intercooler_costs, total_costs


def _estimate_intercooler_cost(
    inlet_pressure_bar: Optional[float],
    outlet_pressure_bar: Optional[float],
    cepci: CEPCIOptions,
    material: MaterialType = "CS"
) -> Optional[Dict[str, float]]:
    """
    Intercooler 비용을 추정하는 함수 (Placeholder)
    향후 heat exchanger 모듈과 연동될 예정
    MCompr의 경우 입구 압력이 없을 수 있으므로 토출 압력만 사용
    """
    if outlet_pressure_bar is None:
        return None
    
    try:
        # TODO: 향후 heat exchanger 모듈과 연동
        # 현재는 간단한 추정치 제공
        
        # 압력 기반 간단한 추정 (실제로는 열교환기 설계 필요)
        if inlet_pressure_bar is not None:
            pressure_avg = (inlet_pressure_bar + outlet_pressure_bar) / 2
        else:
            # MCompr의 경우 토출 압력만 사용
            pressure_avg = outlet_pressure_bar
        
        # 간단한 추정 공식 (실제 구현 시 heat exchanger 모듈 사용)
        # 이는 임시 추정치이며, 실제로는 열교환기 설계 데이터가 필요
        estimated_cost = 10000 * (pressure_avg / 10) ** 0.6  # 임시 공식
        
        purchased_adj = adjust_cost_to_index(estimated_cost, cepci.base_index, cepci.target_index or cepci.base_index)
        
        # 간단한 BM 인수 적용
        bm_factor = 2.5  # 열교환기 일반적인 BM 인수
        bare = _to_bare_module_cost(purchased_adj, bm_factor)
        installed = _to_installed_cost(bare, 1.0)
        
        return {
            "purchased": estimated_cost,
            "purchased_adj": purchased_adj,
            "bare_module": bare,
            "installed": installed,
            "note": "Intercooler cost - placeholder implementation"
        }
        
    except Exception as e:
        # Error estimating intercooler cost
        return None


def estimate_intercooler_cost_from_heat_exchanger_module(
    heat_exchanger_data: Dict[str, float],
    cepci: CEPCIOptions,
    material: MaterialType = "CS"
) -> Dict[str, float]:
    """
    향후 heat exchanger 모듈과 연동될 Intercooler 비용 계산 함수
    heat_exchanger_data: {"area_m2": float, "pressure_bar": float, "temperature_c": float, ...}
    """
    # TODO: heat_exchanger_module.py와 연동
    # 현재는 placeholder 구현
    
    try:
        area_m2 = heat_exchanger_data.get("area_m2", 100)  # 기본값
        pressure_bar = heat_exchanger_data.get("pressure_bar", 10)  # 기본값
        
        # 간단한 추정 공식 (실제로는 heat exchanger 모듈 사용)
        estimated_cost = 500 * area_m2 * (pressure_bar / 10) ** 0.6
        
        purchased_adj = adjust_cost_to_index(estimated_cost, cepci.base_index, cepci.target_index or cepci.base_index)
        
        bm_factor = 2.5
        bare = _to_bare_module_cost(purchased_adj, bm_factor)
        installed = _to_installed_cost(bare, 1.0)
        
        return {
            "purchased": estimated_cost,
            "purchased_adj": purchased_adj,
            "bare_module": bare,
            "installed": installed,
            "note": "Intercooler cost from heat exchanger module"
        }
        
    except Exception as e:
        # Error calculating intercooler cost from heat exchanger module
        return {"error": str(e)}


def estimate_mcompr_cost_from_aspen(
    Application,
    block_name: str,
    power_unit: Optional[str],
    pressure_unit: Optional[str],
    cepci: CEPCIOptions,
    material: MaterialType = "CS",
    install_factor: float = 1.0
) -> Dict[str, float]:
    """
    MCompr 블록의 비용을 추정하는 함수
    각 단계별로 개별 압축기 비용을 계산하여 합산
    """
    try:
        # 단계별 데이터 추출
        stage_data = _extract_mcompr_stage_data(Application, block_name, power_unit, pressure_unit)
        
        if not stage_data:
            # 단계별 데이터가 없으면 기존 방식으로 처리
            power_kilowatt = _aspen_cache.get_power_data(Application, block_name, power_unit)
            if power_kilowatt is None:
                raise ValueError("WNET not found")
            
            inlet_bar = _aspen_cache.get_pressure_data(Application, block_name, pressure_unit, 'inlet')
            outlet_bar = _aspen_cache.get_pressure_data(Application, block_name, pressure_unit, 'outlet')
            
            return estimate_mcompr_cost(
                CostInputs(power_kilowatt=power_kilowatt, pressure_bar=outlet_bar), 
                cepci=cepci, 
                material=material, 
                install_factor=install_factor
            )
        
        # 각 단계별 비용 계산 (Intercooler 포함)
        stage_costs, intercooler_costs, total_costs = _calculate_mcompr_stage_costs(
            stage_data, cepci, material, install_factor, include_intercoolers=True
        )
        
        # 결과에 단계별 상세 정보 포함
        result = {
            "purchased": total_costs["purchased"],
            "purchased_adj": total_costs["purchased_adj"],
            "bare_module": total_costs["bare_module"],
            "installed": total_costs["installed"],
            "stage_details": stage_costs,
            "intercooler_details": intercooler_costs,
            "stage_count": len(stage_data),
            "intercooler_count": len(intercooler_costs)
        }
        
        return result
        
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


def _extract_all_pressure_device_data(
    Application,
    block_info: Dict[str, str],
    power_unit: Optional[str],
    pressure_unit: Optional[str],
) -> Dict[str, Dict[str, Optional[float]]]:
    """모든 압력 장치의 데이터를 추출"""
    data = {}
    for name, cat in block_info.items():
        if cat in ('Pump', 'Compr'):
            power_kilowatt = _aspen_cache.get_power_data(Application, name, power_unit)
            inlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'inlet')
            outlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'outlet')
            data[name] = {
                'power_kilowatt': power_kilowatt,
                'inlet_bar': inlet_bar,
                'outlet_bar': outlet_bar,
            }
        elif cat == 'MCompr':
            # MCompr는 단계별 데이터를 추출
            stage_data = _extract_mcompr_stage_data(Application, name, power_unit, pressure_unit)
            
            if stage_data:
                # 총 파워 계산
                total_power = sum(data.get('power_kilowatt', 0) for data in stage_data.values() if data.get('power_kilowatt') is not None)
                # 최종 토출 압력 (마지막 단계)
                final_outlet = None
                if stage_data:
                    max_stage = max(stage_data.keys())
                    final_outlet = stage_data[max_stage].get('outlet_pressure_bar')
                
                data[name] = {
                    'power_kilowatt': total_power if total_power > 0 else None,
                    'inlet_bar': None,  # MCompr는 입구 압력 없음
                    'outlet_bar': final_outlet,
                    'stage_data': stage_data  # 단계별 데이터도 포함
                }
            else:
                # 단계별 데이터가 없으면 기본 방식으로 처리
                power_kilowatt = _aspen_cache.get_power_data(Application, name, power_unit)
                outlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'outlet')
                data[name] = {
                    'power_kilowatt': power_kilowatt,
                    'inlet_bar': None,
                    'outlet_bar': outlet_bar,
                }
    return data


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
    type_overrides: Optional[Dict[str, str]] = None,
    subtype_overrides: Optional[Dict[str, str]] = None,
):
    results = []
    totals = {"purchased": 0.0, "purchased_adj": 0.0, "bare_module": 0.0, "installed": 0.0}
    for name, cat in block_info.items():
        pdata = pre_extracted.get(name, {})
        pw = pdata.get('power_kilowatt')
        inlet_bar = pdata.get('inlet_bar')
        outlet_bar = pdata.get('outlet_bar')
        m = (material_overrides or {}).get(name, material)
        try:
            if cat == 'Pump':
                if pw is None:
                    raise ValueError('Missing power_kilowatt for pump')
                # 사용자가 선택한 세부 타입이 있으면 사용
                selected_subtype = (subtype_overrides or {}).get(name, 'centrifugal')
                costs = estimate_pump_cost(CostInputs(power_kilowatt=pw), cepci=cepci, pump_type=selected_subtype, material=m)
                dtype = 'pump'
            elif cat == 'Compr':
                if pw is None:
                    raise ValueError('Missing power_kilowatt for compressor')
                
                # 사용자가 선택한 타입이 있으면 우선 사용
                selected_type = (type_overrides or {}).get(name)
                selected_subtype = (subtype_overrides or {}).get(name)
                
                if selected_type:
                    if selected_type == 'fan':
                        fan_type = selected_subtype if selected_subtype else 'centrifugal_radial'
                        costs = estimate_fan_cost(CostInputs(power_kilowatt=pw, pressure_bar=outlet_bar), cepci=cepci, fan_type=fan_type, material=m)
                        dtype = 'fan'
                    elif selected_type == 'compressor':
                        comp_type = selected_subtype if selected_subtype else 'centrifugal'
                        costs = estimate_compressor_cost(CostInputs(power_kilowatt=pw, pressure_bar=outlet_bar), cepci=cepci, comp_type=comp_type, material=m)
                        dtype = 'compressor'
                    elif selected_type == 'turbine':
                        turbine_type = selected_subtype if selected_subtype else 'axial'
                        costs = estimate_turbine_cost(CostInputs(power_kilowatt=pw), cepci=cepci, turbine_type=turbine_type, material=m)
                        dtype = 'turbine'
                    else:
                        # 잘못된 타입이면 기본 로직 사용
                        selected_type = None
                
                # 사용자 선택이 없으면 기존 자동 분류 로직 사용
                if not selected_type:
                    if inlet_bar is not None and outlet_bar is not None and inlet_bar > outlet_bar:
                        costs = estimate_turbine_cost(CostInputs(power_kilowatt=pw), cepci=cepci, turbine_type='axial', material=m)
                        dtype = 'turbine'
                    else:
                        # 압력 상승이 낮으면 팬, 높으면 압축기로 분류
                        if outlet_bar is not None and inlet_bar is not None:
                            pressure_rise = outlet_bar - inlet_bar
                            if pressure_rise <= 0.16:  # 팬 범위
                                costs = estimate_fan_cost(CostInputs(power_kilowatt=pw, pressure_bar=outlet_bar), cepci=cepci, material=m)
                                dtype = 'fan'
                            else:
                                costs = estimate_compressor_cost(CostInputs(power_kilowatt=pw, pressure_bar=outlet_bar), cepci=cepci, comp_type='centrifugal', material=m)
                                dtype = 'compressor'
                        else:
                            # 압력 정보가 없으면 압축기로 가정
                            costs = estimate_compressor_cost(CostInputs(power_kilowatt=pw, pressure_bar=outlet_bar), cepci=cepci, comp_type='centrifugal', material=m)
                            dtype = 'compressor'
            elif cat == 'MCompr':
                if pw is None:
                    raise ValueError('Missing power_kilowatt for multi-stage compressor')
                
                # MCompr: 단계별 데이터가 있으면 단계별 계산, 없으면 기본 계산
                stage_data = pdata.get('stage_data')
                
                if stage_data:
                    # 단계별 비용 계산
                    stage_costs, intercooler_costs, total_costs = _calculate_mcompr_stage_costs(
                        stage_data, cepci, m, install_factor=1.0, include_intercoolers=True
                    )
                    costs = {
                        "purchased": total_costs["purchased"],
                        "purchased_adj": total_costs["purchased_adj"],
                        "bare_module": total_costs["bare_module"],
                        "installed": total_costs["installed"],
                        "stage_details": stage_costs,
                        "intercooler_details": intercooler_costs,
                        "stage_count": len(stage_data),
                        "intercooler_count": len(intercooler_costs)
                    }
                    dtype = 'multi-stage compressor (stage-by-stage)'
                else:
                    # 단계별 데이터가 없으면 기본 계산
                    costs = estimate_mcompr_cost(CostInputs(power_kilowatt=pw, pressure_bar=outlet_bar), cepci=cepci, material=m)
                    dtype = 'multi-stage compressor (simplified)'
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
    # 장치 이름 오름차순으로 정렬
    all_blocks = sorted(block_info.items(), key=lambda x: x[0])
    preview = []
    
    for name, cat in all_blocks:
        if cat == 'Pump':
            try:
                pw = _aspen_cache.get_power_data(Application, name, power_unit)
                inlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'inlet')
                outlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'outlet')
                preview.append({
                    "name": name,
                    "category": "Pump",
                    "power_kilowatt": pw,
                    "inlet_bar": inlet_bar,
                    "outlet_bar": outlet_bar,
                    "suggested": "pump",
                    "material": "CS",  # 기본 재질
                    "selected_type": "pump",  # 선택된 타입
                    "selected_subtype": "centrifugal",  # 선택된 세부 타입
                })
            except Exception as e:
                preview.append({"name": name, "category": "Pump", "error": f"failed to read: {str(e)}"})

        elif cat == 'Compr':
            try:
                pw = _aspen_cache.get_power_data(Application, name, power_unit)
                inlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'inlet')
                outlet_bar = _aspen_cache.get_pressure_data(Application, name, pressure_unit, 'outlet')
                suggested = None
                if inlet_bar is not None and outlet_bar is not None:
                    if outlet_bar > inlet_bar:
                        pressure_rise = outlet_bar - inlet_bar
                        if pressure_rise <= 0.16:  # 팬 범위
                            suggested = 'fan'
                        else:
                            suggested = 'compressor'
                    elif inlet_bar > outlet_bar:
                        suggested = 'turbine'
                preview.append({
                    "name": name,
                    "category": "Compr",
                    "power_kilowatt": pw,
                    "inlet_bar": inlet_bar,
                    "outlet_bar": outlet_bar,
                    "suggested": suggested,
                    "material": "CS",  # 기본 재질
                    "selected_type": suggested,  # 선택된 타입 (기본값은 suggested)
                    "selected_subtype": "centrifugal" if suggested == "compressor" else ("centrifugal_radial" if suggested == "fan" else "axial"),  # 기본 세부 타입
                })
            except Exception as e:
                preview.append({"name": name, "category": "Compr", "error": f"failed to read: {str(e)}"})

        elif cat == 'MCompr':
            try:
                # 기본 정보
                pw = _aspen_cache.get_power_data(Application, name, power_unit)
                
                # 단계별 정보 추출
                stage_data = _extract_mcompr_stage_data(Application, name, power_unit, pressure_unit)
                
                # 최종 토출 압력 계산 (가장 마지막 단계의 토출 압력)
                final_outlet_bar = None
                if stage_data:
                    max_stage = max(stage_data.keys())
                    final_outlet_bar = stage_data[max_stage].get('outlet_pressure_bar')
                
                preview.append({
                    "name": name,
                    "category": "MCompr",
                    "power_kilowatt": pw,
                    "suggested": "multi-stage compressor",
                    "stage_count": len(stage_data),
                    "final_outlet_bar": final_outlet_bar,
                    "stage_data": stage_data,  # stage_data도 포함
                    "material": "CS",  # 기본 재질
                    "selected_type": "multi-stage compressor",  # 선택된 타입
                    "selected_subtype": "centrifugal",  # 선택된 세부 타입
                })
            except Exception as e:
                preview.append({"name": name, "category": "MCompr", "error": f"failed to read: {str(e)}"})

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


def get_device_type_options(category: str) -> Dict[str, List[str]]:
    """장치 카테고리별로 선택 가능한 타입과 세부 타입 목록을 반환합니다."""
    if category == 'Pump':
        return {
            'pump': ['centrifugal', 'reciprocating']
        }
    elif category == 'Compr':
        return {
            'fan': ['centrifugal_radial', 'centrifugal_backward', 'centrifugal_forward', 'axial'],
            'compressor': ['centrifugal', 'axial', 'reciprocating'],
            'turbine': ['axial', 'radial']
        }
    elif category == 'MCompr':
        return {
            'multi-stage compressor': ['centrifugal', 'axial']
        }
    else:
        return {}


def print_preview_results(preview: list, Application, power_unit: Optional[str], pressure_unit: Optional[str]):
    """
    프리뷰 결과를 포맷팅하여 출력하는 함수
    """
    print("\n" + "="*60)
    print("PREVIEW: PRESSURE-DRIVEN DEVICES (extracted data)")
    print("="*60)
    
    for p in preview:
        name = p.get('name')
        cat = p.get('category')
        
        # 오류가 있는 장치 처리
        if 'error' in p:
            error_msg = p.get('error', 'Unknown error')
            print(f"{name:20s} | {cat:12s} | ERROR: {error_msg}")
            continue
            
        pw = p.get('power_kilowatt')
        inlet_bar = p.get('inlet_bar')
        outlet_bar = p.get('outlet_bar')
        sug = p.get('suggested')
        material = p.get('material', 'CS')  # 기본값 CS
        selected_type = p.get('selected_type', sug)  # 기본값은 suggested
        selected_subtype = p.get('selected_subtype', 'N/A')  # 세부 타입
        
        if cat == 'MCompr':
            # MCompr의 경우 Aspen에서 직접 단계 수와 최종 토출 압력 추출
            try:
                # Elements를 통해 B_PRES 하위 노드들 확인하여 단계 수 결정
                bpres_elements_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{name}\\Output\\B_PRES")
                stage_count = 0
                final_outlet_bar = None
                
                if bpres_elements_node is not None:
                    try:
                        elements = bpres_elements_node.Elements
                        stage_numbers = []
                        for i in range(elements.Count):
                            element_name = elements.Item(i).Name
                            if element_name.isdigit():
                                stage_numbers.append(int(element_name))
                        
                        if stage_numbers:
                            stage_numbers.sort()
                            stage_count = len(stage_numbers)
                            # 가장 마지막 단계의 토출 압력이 최종 토출 압력
                            max_stage = max(stage_numbers)
                            final_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{name}\\Output\\B_PRES\\{max_stage}")
                            if final_node is not None and final_node.Value is not None:
                                final_outlet_bar = _convert_pressure_to_bar(float(final_node.Value), pressure_unit)
                    except Exception as e:
                        # Error reading B_PRES Elements
                        pass
                
                print(f"{name:20s} | {cat:12s} | P={pw if pw is not None else 'NA'} kW | Stages={stage_count} | Pout_final={final_outlet_bar if final_outlet_bar is not None else 'NA'} bar | Material={material} | Type={selected_type} | Subtype={selected_subtype}")
            except Exception as e:
                print(f"{name:20s} | {cat:12s} | P={pw if pw is not None else 'NA'} kW | Stages=NA | Pout_final=NA bar | Material={material} | Type={selected_type} | Subtype={selected_subtype} | Error: {e}")
        else:
            # Pump, Compr의 경우 기존 형식 (게이지 압력 제외)
            print(f"{name:20s} | {cat:12s} | P={pw if pw is not None else 'NA'} kW | Pin={inlet_bar if inlet_bar is not None else 'NA'} bar | Pout={outlet_bar if outlet_bar is not None else 'NA'} bar | Material={material} | Type={selected_type} | Subtype={selected_subtype}")
