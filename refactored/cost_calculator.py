"""
장비 비용 계산 모듈 (Turton 기반)
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Tuple, List, Any
import math
import sys

import config
import unit_converter

# =============================================================================
# 데이터 모델
# =============================================================================

@dataclass
class CEPCIOptions:
    """CEPCI 관련 옵션을 담는 데이터 클래스"""
    # Turton 책의 기준년도인 2001년 CEPCI 인덱스를 사용
    base_year: int = 2001
    base_index: float = 397.0
    target_index: Optional[float] = None

@dataclass
class CostInputs:
    """비용 계산에 필요한 모든 입력 데이터를 담는 데이터 클래스"""
    size_value: Optional[float] = None
    size_unit: str = ""
    pressure_bar: Optional[float] = None
    pressure_delta_bar: Optional[float] = None
    material: str = "CS"
    selected_type: str = "default"
    selected_subtype: str = "default"
    q_watt: Optional[float] = None
    u_w_m2k: Optional[float] = None
    lmtd_k: Optional[float] = None
    tray_count: Optional[int] = None
    stage_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    vessel_volume: Optional[float] = None
    diameter: Optional[float] = None
    height_or_length: Optional[float] = None
    shell_material: Optional[str] = None
    tube_material: Optional[str] = None
    
# =============================================================================
# 내부 계산 헬퍼 함수들
# =============================================================================

def _adjust_cost_to_index(cost_at_base_index: float, base_index: float, target_index: float) -> float:
    """CEPCI를 사용하여 비용을 조정합니다."""
    if target_index is None or target_index == 0 or base_index is None or base_index == 0:
        return cost_at_base_index
    return cost_at_base_index * (target_index / base_index)

def _eval_log_quadratic_cost(size_value: float, coeffs: dict) -> float:
    """구매 비용 상관관계식을 계산합니다."""
    if size_value <= 0:
        raise ValueError("Size value must be positive for cost correlation")
    
    logS = math.log10(size_value)
    logC = coeffs["k1"] + coeffs["k2"] * logS + coeffs["k3"] * (logS ** 2)
    return 10.0 ** logC

def _resolve_bm(equipment_type: str, subtype: str, material: str, fm: float, fp: float) -> float:
    """Bare Module Factor를 결정합니다."""
    settings = config.get_equipment_setting(equipment_type, subtype)
    
    if "bm_factors_b1b2" in settings:
        b1, b2 = settings["bm_factors_b1b2"]
        return b1 + b2 * fm * fp
    
    if "bm_factors_fixed" in settings:
        return settings["bm_factors_fixed"].get(material, 1.0)
    
    return 1.0

def _resolve_material_factor(equipment_type: str, subtype: str, material: str, shell_material: Optional[str] = None, tube_material: Optional[str] = None) -> float:
    """재질 계수 (Fm)를 결정합니다."""
    settings = config.get_equipment_setting(equipment_type, subtype)
    
    if "material_factors" in settings:
        return settings["material_factors"].get(material, 1.0)
    
    if "material_factors_matrix" in settings:
        matrix = settings["material_factors_matrix"]
        if equipment_type == "heat_exchanger":
            if not shell_material or not tube_material:
                raise ValueError("Heat exchanger requires shell_material and tube_material for material_factors_matrix")
            if shell_material not in matrix:
                raise ValueError(f"Unknown shell_material '{shell_material}' for heat_exchanger subtype '{subtype}'")
            shell_row = matrix[shell_material]
            if not isinstance(shell_row, dict):
                raise ValueError(f"Material matrix row for shell_material '{shell_material}' must be a dict")
            if tube_material not in shell_row:
                raise ValueError(f"Unknown tube_material '{tube_material}' for heat_exchanger subtype '{subtype}' with shell '{shell_material}'")
            return float(shell_row[tube_material])
        else:
            # 비-열교환기에서도 매트릭스 사용 시 material 단일 키로 접근
            if material not in matrix:
                raise ValueError(f"Unknown material '{material}' for equipment '{equipment_type}:{subtype}'")
            value = matrix[material]
            if isinstance(value, dict):
                # 비-열교환기인데 매트릭스가 중첩이면 정의 불명 → 에러
                raise ValueError(f"Material factors matrix for '{equipment_type}:{subtype}' should be flat, got nested for '{material}'")
            return float(value)
            
    return 1.0

def _resolve_pressure_factor(equipment_type: str, subtype: str, pressure: Optional[float], pressure_type: str, diameter: Optional[float] = None) -> float:
    """압력 계수 (Fp)를 결정합니다."""
    settings = config.get_equipment_setting(equipment_type, subtype)
    calc_method = settings.get("pressure_calc_method", "coefficient")
    
    if pressure is None:
        return 1.0
        
    if calc_method == "coefficient":
        pressure_ranges = settings.get("pressure_ranges", [])
        for p_range in pressure_ranges:
            min_p, max_p = p_range.get("min"), p_range.get("max")
            
            p_value = pressure
            if p_range["unit"] == "kPa" and pressure_type == "pressure_difference":
                p_value = pressure * 100 # bar -> kPa
            
            if (min_p is None or p_value >= min_p) and (max_p is None or p_value < max_p):
                c1, c2, c3 = p_range["c1"], p_range["c2"], p_range["c3"]
                return max(_calc_fp_from_coeffs(p_value, c1, c2, c3), 1.0)
        return 1.0
    
    elif calc_method == "formula" and equipment_type == "vessel":
        return _calculate_vessel_pressure_factor(subtype, pressure, diameter)
    
    return 1.0

def _calc_fp_from_coeffs(P_value: float, C1: float, C2: float, C3: float) -> float:
    """압력 계수 공식을 계산합니다."""
    if P_value is None or P_value <= 0:
        return 1.0
    try:
        logP = math.log10(P_value)
        logFp = C1 + C2 * logP + C3 * (logP ** 2)
        return 10.0 ** logFp
    except (ValueError, ZeroDivisionError):
        return 1.0

def _calculate_vessel_pressure_factor(subtype: str, pressure: Optional[float], diameter: Optional[float]) -> float:
    """Vessel의 압력 계수를 직접 계산식으로 계산합니다."""
    if diameter is None or pressure is None:
        return 1.0
        
    vessel_config = config.EQUIPMENT_SETTINGS.get("vessel", {}).get(subtype)
    if not vessel_config:
        return 1.0
        
    formula_config = vessel_config.get("pressure_formula_config", {})
    S = formula_config.get("S", 944.0)
    E = formula_config.get("E", 0.9)
    CA = formula_config.get("CA", 0.00315)
    t_min = formula_config.get("t_min", 0.0063)

    if pressure < -0.5:
        return 1.25
        
    try:
        denominator = 2 * S * E - 1.2 * pressure
        if denominator <= 0:
            return 1.0
        fp = (pressure * diameter / denominator + CA) / t_min
        return max(fp, 1.0)
    except (ValueError, ZeroDivisionError):
        return 1.0

def _sum_costs(parts: List[Dict]) -> Dict[str, float]:
    """분할된 장치들의 비용을 합산합니다."""
    total = {"purchased_base": 0.0, "purchased_adj": 0.0, "bare_module_cost": 0.0}
    for c in parts:
        for k in total:
            total[k] += float(c.get(k, 0.0))
    return total
    
# =============================================================================
# 장비별 비용 계산 메인 함수들
# =============================================================================

def estimate_pump_cost(inputs: CostInputs, cepci: CEPCIOptions, _split: bool = True) -> Dict[str, Any]:
    """펌프 비용을 계산합니다."""
    power_kw = inputs.size_value
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("pump", subtype)
    coeffs = settings.get("correlation_coeffs")

    if power_kw is None or power_kw <= 0:
        raise ValueError(f"Missing or invalid power for pump ({subtype})")
    
    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if _split and max_size and power_kw > max_size:
        num_units = math.ceil(power_kw / max_size)
        power_per_unit = power_kw / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                size_value=power_per_unit,
                size_unit=inputs.size_unit,
                pressure_bar=inputs.pressure_bar,
                material=inputs.material,
                selected_subtype=subtype
            )
            parts.append(estimate_pump_cost(sub_inputs, cepci, _split=False))
        return _sum_costs(parts)

    purchased_base = _eval_log_quadratic_cost(power_kw, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    
    b1, b2 = settings.get("bm_factors_b1b2")
    fm = _resolve_material_factor("pump", subtype, inputs.material)
    fp = _resolve_pressure_factor("pump", subtype, inputs.pressure_bar, "gauge")
    
    effective_bm = b1 + b2 * fm * fp
    bare_module_cost = purchased_adj * effective_bm
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": fm,
        "pressure_factor": fp,
        "size_value": power_kw
    }

def estimate_compressor_cost(inputs: CostInputs, cepci: CEPCIOptions, _split: bool = True) -> Dict[str, Any]:
    power_kw = inputs.size_value
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("compressor", subtype)
    coeffs = settings.get("correlation_coeffs")

    if power_kw is None or power_kw <= 0:
        raise ValueError(f"Missing or invalid power for compressor ({subtype})")
    
    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")

    if _split and max_size and power_kw > max_size:
        num_units = math.ceil(power_kw / max_size)
        power_per_unit = power_kw / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                size_value=power_per_unit,
                size_unit=inputs.size_unit,
                material=inputs.material,
                selected_subtype=subtype
            )
            parts.append(estimate_compressor_cost(sub_inputs, cepci, _split=False))
        return _sum_costs(parts)

    purchased_base = _eval_log_quadratic_cost(power_kw, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    bare_module_cost = purchased_adj * effective_bm
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": power_kw
    }

def estimate_fan_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    flow_m3_s = inputs.size_value
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("fan", subtype)
    coeffs = settings.get("correlation_coeffs")

    if flow_m3_s is None or flow_m3_s <= 0:
        raise ValueError(f"Missing or invalid flowrate for fan ({subtype})")
    
    purchased_base = _eval_log_quadratic_cost(flow_m3_s, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    fp = _resolve_pressure_factor("fan", subtype, inputs.pressure_delta_bar, "pressure_difference")
    
    effective_bm_with_fp = effective_bm * fp
    bare_module_cost = purchased_adj * effective_bm_with_fp
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm_with_fp,
        "material_factor": 1.0,
        "pressure_factor": fp,
        "size_value": flow_m3_s
    }

def estimate_mcompr_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    total_power_kw = inputs.size_value
    stage_data = inputs.stage_data
    material = inputs.material
    
    if total_power_kw is None or not stage_data:
        raise ValueError("Missing power or stage data for multi-stage compressor")
        
    total_costs = {"purchased_base": 0.0, "purchased_adj": 0.0, "bare_module_cost": 0.0}
    
    for stage_num, data in stage_data.items():
        stage_power = data.get("power_kilowatt")
        stage_pressure = data.get("outlet_pressure_bar")
        
        if stage_power is not None:
            stage_inputs = CostInputs(
                size_value=stage_power,
                material=material,
                selected_subtype="centrifugal"
            )
            comp_costs = estimate_compressor_cost(stage_inputs, cepci)
            for k in total_costs:
                total_costs[k] += comp_costs[k]
                
        # 인터쿨러 비용 계산 (단계 간 냉각기)
        if stage_num < len(stage_data):
            try:
                Q_watt = data.get("q_watt")
                if Q_watt is None:
                    continue
                
                T_h_in = data.get("B_TEMP_K")
                T_h_out = data.get("COOL_TEMP_K")
                
                if T_h_in is None or T_h_out is None:
                    continue
                
                T_c_in = T_h_out - 10
                T_c_out = T_h_out
                
                delta_T1 = T_h_in - T_c_out
                delta_T2 = T_h_out - T_c_in
                
                if delta_T1 <= 0 or delta_T2 <= 0:
                    lmtd_k = 0
                else:
                    lmtd_k = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2)
                
                if lmtd_k == 0:
                    continue

                intercooler_inputs = CostInputs(
                    size_value=None,
                    q_watt=Q_watt,
                    u_w_m2k=850.0,
                    lmtd_k=lmtd_k,
                    material=material,
                    selected_subtype="fixed_tube",
                    shell_material=config.DEFAULT_MATERIAL,
                    tube_material=config.DEFAULT_MATERIAL,
                )
                intercooler_costs = estimate_heat_exchanger_cost(intercooler_inputs, cepci)
                for k in total_costs:
                    total_costs[k] += intercooler_costs[k]
            except Exception:
                continue

    return total_costs

def estimate_heat_exchanger_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    area_sqm = inputs.size_value
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("heat_exchanger", subtype)
    coeffs = settings.get("correlation_coeffs")

    if area_sqm is None:
        missing = []
        if inputs.q_watt is None:
            missing.append("Q")
        if inputs.u_w_m2k is None:
            missing.append("U")
        if inputs.lmtd_k is None:
            missing.append("LMTD")
        if missing:
            raise ValueError(f"Missing inputs for heat exchanger ({subtype}): {', '.join(missing)}")
        
        if inputs.u_w_m2k == 0 or inputs.lmtd_k == 0:
             raise ValueError(f"U or LMTD is zero for heat exchanger ({subtype})")
        
        area_sqm = inputs.q_watt / (inputs.u_w_m2k * inputs.lmtd_k)
    
    if area_sqm <= 0:
        raise ValueError(f"Invalid calculated area for heat exchanger ({subtype})")

    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if max_size and area_sqm > max_size:
        num_units = math.ceil(area_sqm / max_size)
        area_per_unit = area_sqm / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                size_value=area_per_unit,
                material=inputs.material,
                selected_subtype=subtype
            )
            parts.append(estimate_heat_exchanger_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    purchased_base = _eval_log_quadratic_cost(area_sqm, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)

    fm = _resolve_material_factor(
        "heat_exchanger", subtype, inputs.material,
        shell_material=inputs.shell_material, tube_material=inputs.tube_material
    )
    fp = _resolve_pressure_factor("heat_exchanger", subtype, inputs.pressure_bar, "gauge")
    
    b1, b2 = settings.get("bm_factors_b1b2")
    effective_bm = b1 + b2 * fm * fp
    bare_module_cost = purchased_adj * effective_bm
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": fm,
        "pressure_factor": fp,
        "size_value": area_sqm
    }

def estimate_vessel_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    volume_cum = inputs.size_value
    diameter_m = inputs.diameter
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("vessel", subtype)
    coeffs = settings.get("correlation_coeffs")

    if volume_cum is None or volume_cum <= 0:
        raise ValueError(f"Missing or invalid volume for vessel ({subtype})")

    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if max_size and volume_cum > max_size:
        num_units = math.ceil(volume_cum / max_size)
        volume_per_unit = volume_cum / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                size_value=volume_per_unit,
                material=inputs.material,
                selected_subtype=subtype,
                diameter=diameter_m
            )
            parts.append(estimate_vessel_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    purchased_base = _eval_log_quadratic_cost(volume_cum, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    
    fm = _resolve_material_factor("vessel", subtype, inputs.material)
    fp = _resolve_pressure_factor("vessel", subtype, inputs.pressure_bar, "gauge", diameter=diameter_m)
    
    b1, b2 = settings.get("bm_factors_b1b2")
    effective_bm = b1 + b2 * fm * fp
    bare_module_cost = purchased_adj * effective_bm
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": fm,
        "pressure_factor": fp,
        "size_value": volume_cum
    }

def estimate_reactor_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    volume_cum = inputs.size_value
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("reactor", subtype)
    coeffs = settings.get("correlation_coeffs")

    if volume_cum is None or volume_cum <= 0:
        raise ValueError(f"Missing or invalid volume for reactor ({subtype})")

    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if max_size and volume_cum > max_size:
        num_units = math.ceil(volume_cum / max_size)
        volume_per_unit = volume_cum / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                size_value=volume_per_unit,
                material=inputs.material,
                selected_subtype=subtype,
            )
            parts.append(estimate_reactor_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    purchased_base = _eval_log_quadratic_cost(volume_cum, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    bare_module_cost = purchased_adj * effective_bm
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": volume_cum
    }


def calculate_all_costs_with_data(all_device_data: List[Dict], cepci: CEPCIOptions) -> Dict[str, Any]:
    results = []
    total_bare_module_cost = 0.0
    
    for device in all_device_data:
        name = device.get("name")
        category = device.get("category")
        
        if device.get("error"):
            results.append({"name": name, "category": category, "error": device.get("error")})
            continue
            
        try:
            inputs = CostInputs(
                size_value=device.get("size_value"),
                size_unit=device.get("size_unit"),
                pressure_bar=device.get("outlet_bar"),
                pressure_delta_bar=device.get("pressure_delta_bar"),
                material=device.get("material", config.DEFAULT_MATERIAL),
                selected_type=device.get("selected_type"),
                selected_subtype=device.get("selected_subtype"),
                q_watt=device.get("q_watt"),
                u_w_m2k=device.get("u_w_m2k"),
                lmtd_k=device.get("lmtd_k"),
                tray_count=device.get("tray_count"),
                stage_data=device.get("stage_data"),
                diameter=device.get("diameter"),
                height_or_length=device.get("height_or_length"),
                shell_material=device.get("shell_material"),
                tube_material=device.get("tube_material"),
            )
            
            costs = {}
            if category == 'Pump':
                costs = estimate_pump_cost(inputs, cepci)
            elif category == 'Compr':
                if inputs.selected_type == 'fan':
                    costs = estimate_fan_cost(inputs, cepci)
                elif inputs.selected_type == 'turbine':
                    costs = estimate_turbine_cost(inputs, cepci)
                else:
                    costs = estimate_compressor_cost(inputs, cepci)
            elif category == 'MCompr':
                costs = estimate_mcompr_cost(inputs, cepci)
            elif category in ('Heater', 'Cooler', 'HeatX', 'Condenser'):
                costs = estimate_heat_exchanger_cost(inputs, cepci)
            elif category in ('RadFrac', 'Distl', 'DWSTU'):
                costs = {"error": "Distillation cost not implemented (requires tower/tray/packing/HX)"}
            elif category in ('Flash', 'Sep'):
                costs = estimate_vessel_cost(inputs, cepci)
            elif category in ('RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield'):
                costs = estimate_reactor_cost(inputs, cepci)
            else:
                costs = {"error": "Unsupported device category"}
                
            costs["name"] = name
            costs["category"] = category
            results.append(costs)
            total_bare_module_cost += costs.get("bare_module_cost", 0.0)
            
        except Exception as e:
            results.append({"name": name, "category": category, "error": str(e)})

    return {"results": results, "total_bare_module_cost": total_bare_module_cost}

def get_equipment_cost_details(equipment_type: str, subtype: str) -> dict:
    return config.get_equipment_setting(equipment_type, subtype)

def estimate_turbine_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    """터빈 비용을 계산합니다."""
    power_kw = inputs.size_value
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("turbine", subtype)
    coeffs = settings.get("correlation_coeffs")

    if power_kw is None or power_kw <= 0:
        raise ValueError(f"Missing or invalid power for turbine ({subtype})")

    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if max_size and power_kw > max_size:
        num_units = math.ceil(power_kw / max_size)
        power_per_unit = power_kw / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                size_value=power_per_unit,
                size_unit=inputs.size_unit,
                material=inputs.material,
                selected_subtype=subtype
            )
            parts.append(estimate_turbine_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    purchased_base = _eval_log_quadratic_cost(power_kw, coeffs)
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    bare_module_cost = purchased_adj * effective_bm
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": power_kw
    }