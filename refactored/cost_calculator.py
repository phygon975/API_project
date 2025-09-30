"""
장비 비용 계산 모듈 (Turton 기반)
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Tuple, List, Any
import math
import sys

import config
import unit_converter
import data_manager

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
    # 기본 정보
    material: str = "CS"
    selected_type: str = "default"
    selected_subtype: str = "default"
    notes: Optional[str] = None
    
    # 장치별 전용 크기 필드들
    # 펌퓨/압축기/터빈/팬
    power_value: Optional[float] = None
    power_unit: Optional[str] = None
    
    # 열교환기
    heat_duty_value: Optional[float] = None
    heat_duty_unit: Optional[str] = None
    heat_transfer_area_value: Optional[float] = None
    heat_transfer_area_unit: Optional[str] = None
    
    # 용기/반응기/탑
    volume_value: Optional[float] = None
    volume_unit: Optional[str] = None
    
    # 트레이/패킹
    tray_count: Optional[int] = None
    packing_volume_value: Optional[float] = None
    packing_volume_unit: Optional[str] = None
    
    # 압력 관련 (단위 변환 가능)
    inlet_pressure_value: Optional[float] = None
    inlet_pressure_unit: Optional[str] = None
    outlet_pressure_value: Optional[float] = None
    outlet_pressure_unit: Optional[str] = None
    pressure_drop_value: Optional[float] = None
    pressure_drop_unit: Optional[str] = None
    operating_pressure_value: Optional[float] = None
    operating_pressure_unit: Optional[str] = None
    
    # 유량 관련
    volumetric_flow_value: Optional[float] = None
    volumetric_flow_unit: Optional[str] = None
    mass_flow_value: Optional[float] = None
    mass_flow_unit: Optional[str] = None
    
    # 열교환기 특화
    heat_transfer_coefficient_value: Optional[float] = None
    heat_transfer_coefficient_unit: Optional[str] = None
    log_mean_temp_difference_value: Optional[float] = None
    log_mean_temp_difference_unit: Optional[str] = None
    
    # 온도 관련
    inlet_temperature_value: Optional[float] = None
    inlet_temperature_unit: Optional[str] = None
    outlet_temperature_value: Optional[float] = None
    outlet_temperature_unit: Optional[str] = None
    
    # 기타 물리적 특성
    diameter_value: Optional[float] = None
    diameter_unit: Optional[str] = None
    height_value: Optional[float] = None
    height_unit: Optional[str] = None
    
    # 시간 관련
    residence_time_hours_value: Optional[float] = None
    residence_time_minutes_value: Optional[float] = None
    residence_time_seconds_value: Optional[float] = None
    
    # 다단 압축기 특화
    stage_data: Optional[Dict[str, Any]] = None
    
    # 열교환기 재질 특화
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

def _push(steps: List[str], msg: str) -> None:
    try:
        steps.append(msg)
    except Exception:
        pass

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
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("pump", subtype)
    coeffs = settings.get("correlation_coeffs")
    debug_steps: List[str] = []
    
    if inputs.power_value is None or inputs.power_unit is None:
        raise ValueError(f"Missing power value or power unit for pump ({subtype})")
    
    power_kw = unit_converter.convert_units(inputs.power_value, inputs.power_unit, 'kW', 'POWER')
    _push(debug_steps, f"size S=Power={inputs.power_value} {inputs.power_unit} → {power_kw:.2f} kW")

    if power_kw <= 0:
        raise ValueError(f"Invalid power after conversion for pump ({subtype})")
    
    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if _split and max_size and power_kw > max_size:
        num_units = math.ceil(power_kw / max_size)
        power_per_unit = power_kw / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                power_value=power_per_unit * 1000.0,  # watt로 변환
                power_unit=inputs.power_unit,
                material=inputs.material,
                selected_subtype=subtype,
                operating_pressure_value=inputs.operating_pressure_value,
                operating_pressure_unit=inputs.operating_pressure_unit
            )
            parts.append(estimate_pump_cost(sub_inputs, cepci, _split=False))
        return _sum_costs(parts)

    _push(debug_steps, f"logC(S={power_kw:.2f}) = {coeffs['k1']:.4f} + {coeffs['k2']:.4f}·log10(S) + {coeffs['k3']:.4f}·log10(S)^2")
    purchased_base = _eval_log_quadratic_cost(power_kw, coeffs)
    _push(debug_steps, f"Purchased base (2001, CEPCI=397) = {purchased_base:,.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"CEPCI adjusted (target={cepci.target_index}) = {purchased_adj:,.2f}")
    
    b1, b2 = settings.get("bm_factors_b1b2")
    fm = _resolve_material_factor("pump", subtype, inputs.material)
    
    # 압력 계산
    if inputs.operating_pressure_value is None or inputs.operating_pressure_unit is None:
        raise ValueError(f"Missing operating pressure value or unit for pump ({subtype})")
    
    pressure_bar = unit_converter.convert_units(inputs.operating_pressure_value, inputs.operating_pressure_unit, 'bar', 'PRESSURE')
    _push(debug_steps, f"Operating pressure = {inputs.operating_pressure_value} {inputs.operating_pressure_unit} → {pressure_bar:.2f} bar")
    
    fp = _resolve_pressure_factor("pump", subtype, pressure_bar, "gauge")
    
    _push(debug_steps, f"Factors: Fm={fm:.2f} ({inputs.material}), Fp={fp:.2f}")
    effective_bm = b1 + b2 * fm * fp
    _push(debug_steps, f"BM = {b1} + {b2}·Fm·Fp = {effective_bm:.3f}")
    bare_module_cost = purchased_adj * effective_bm
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm:.3f} = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": fm,
        "pressure_factor": fp,
        "size_value": power_kw,
        "debug_steps": debug_steps
    }

def estimate_compressor_cost(inputs: CostInputs, cepci: CEPCIOptions, _split: bool = True) -> Dict[str, Any]:
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("compressor", subtype)
    coeffs = settings.get("correlation_coeffs")
    debug_steps: List[str] = []

    if inputs.power_value is None or inputs.power_unit is None:
        raise ValueError(f"Missing power value or power unit for compressor ({subtype})")
    
    power_kw = unit_converter.convert_units(inputs.power_value, inputs.power_unit, 'kW', 'POWER')
    _push(debug_steps, f"size S=Power={inputs.power_value} {inputs.power_unit} → {power_kw} kW")

    if power_kw <= 0:
        raise ValueError(f"Invalid power after conversion for compressor ({subtype})")
    
    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")

    if _split and max_size and power_kw > max_size:
        num_units = math.ceil(power_kw / max_size)
        power_per_unit = power_kw / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                power_value=power_per_unit * 1000.0,
                power_unit=inputs.power_unit,
                material=inputs.material,
                selected_subtype=subtype
            )
            parts.append(estimate_compressor_cost(sub_inputs, cepci, _split=False))
        return _sum_costs(parts)

    _push(debug_steps, f"logC with S={power_kw}")
    purchased_base = _eval_log_quadratic_cost(power_kw, coeffs)
    _push(debug_steps, f"Purchased base (2001, CEPCI=397) = {purchased_base:,.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"Cost adjusted = {purchased_adj:.2f}")
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    _push(debug_steps, f"BM = fixed(material={inputs.material}) = {effective_bm:.3f}")
    
    bare_module_cost = purchased_adj * effective_bm
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm:.3f} = {bare_module_cost:,.2f}")
    _push(debug_steps, f"BM={effective_bm:.3f}; Bare Module Cost = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": power_kw,
        "debug_steps": debug_steps
    }

def estimate_fan_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("fan", subtype)
    coeffs = settings.get("correlation_coeffs")
    debug_steps: List[str] = []

    if inputs.volumetric_flow_value is None or inputs.volumetric_flow_unit is None:
        raise ValueError(f"Missing volumetric flow value or unit for fan ({subtype})")
    
    flow_m3_s = unit_converter.convert_units(inputs.volumetric_flow_value, inputs.volumetric_flow_unit, 'm3/s', 'VOLUME-FLOW')
    _push(debug_steps, f"S=Volumetric flow={inputs.volumetric_flow_value} {inputs.volumetric_flow_unit} → {flow_m3_s:.2f} m³/s")

    if flow_m3_s <= 0:
        raise ValueError(f"Invalid flow after conversion for fan ({subtype})")
    
    _push(debug_steps, f"logC(S={flow_m3_s:.2f}) = {coeffs['k1']:.4f} + {coeffs['k2']:.4f}·log10(S) + {coeffs['k3']:.4f}·log10(S)^2")
    purchased_base = _eval_log_quadratic_cost(flow_m3_s, coeffs)
    _push(debug_steps, f"Purchased base (2001, CEPCI=397) = {purchased_base:,.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"CEPCI adjusted (target={cepci.target_index}) = {purchased_adj:,.2f}")
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    if inputs.pressure_drop_value is None or inputs.pressure_drop_unit is None:
        raise ValueError(f"Missing pressure drop value or unit for fan ({subtype})")
    
    fp = _resolve_pressure_factor("fan", subtype, inputs.pressure_drop_value, "pressure_difference")
    effective_bm_with_fp = effective_bm * fp
    _push(debug_steps, f"BM = fixed(material={inputs.material})·Fp = {effective_bm:.3f}·{fp:.2f} = {effective_bm_with_fp:.3f}")
    bare_module_cost = purchased_adj * effective_bm_with_fp
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm_with_fp:.3f} = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm_with_fp,
        "material_factor": 1.0,
        "pressure_factor": fp,
        "size_value": flow_m3_s,
        "debug_steps": debug_steps
    }

def estimate_mcompr_cost(inputs: CostInputs, cepci: CEPCIOptions, Application=None) -> Dict[str, Any]:
    stage_data = inputs.stage_data
    material = inputs.material
    debug_steps: List[str] = []
    
    if not stage_data:
        raise ValueError("Missing stage data for multi-stage compressor")
        
    total_costs = {"purchased_base": 0.0, "purchased_adj": 0.0, "bare_module_cost": 0.0}
    total_compressor_cost = 0.0
    total_intercooler_cost = 0.0
    total_power_kw = 0.0
    
    # 각 스테이지별로 압축기 비용 계산
    for stage_num, data in stage_data.items():
        power_value = data.get("power_value")
        power_unit = data.get("power_unit")
        
        if power_value is None or power_unit is None:
            raise ValueError(f"Missing power value or unit for stage {stage_num}")
            
        # 파워를 kW로 단위 변환
        power_kw = unit_converter.convert_units(power_value, power_unit, 'kW', 'POWER')
        total_power_kw += power_kw
        
        # 스테이지 압축기 비용 계산 - 기존 함수 사용
        stage_inputs = CostInputs(
            material=material,
            selected_subtype="centrifugal",
            power_value=power_value,
            power_unit=power_unit,
            inlet_pressure_value=data.get("inlet_pressure_value"),
            inlet_pressure_unit=data.get("inlet_pressure_unit"),
            outlet_pressure_value=data.get("outlet_pressure_value"), 
            outlet_pressure_unit=data.get("outlet_pressure_unit"),
            operating_pressure_value=data.get("outlet_pressure_value"),
            operating_pressure_unit=data.get("outlet_pressure_unit"),
            pressure_drop_value=data.get("pressure_drop_value"),
            pressure_drop_unit=data.get("pressure_drop_unit"),
            volumetric_flow_value=data.get("volumetric_flow_value"),
            volumetric_flow_unit=data.get("volumetric_flow_unit")
        )
        
        comp_costs = estimate_compressor_cost(stage_inputs, cepci)
        _push(debug_steps, f"Stage {stage_num} Compressor:")
        # 압축기 상세 계산 과정을 debug_steps에 추가
        for step in comp_costs.get('debug_steps', []):
            _push(debug_steps, f"    - {step}")
        for k in total_costs:
            total_costs[k] += comp_costs[k]
        total_compressor_cost += comp_costs.get('bare_module_cost', 0.0)
        
        # 인터쿨러 비용 계산 - data_manager에서 계산된 LMTD 사용
        q_value = data.get("q_value")
        q_unit = data.get("q_unit")
        intercooler_lmtd = data.get("intercooler_lmtd")
        
        if q_value is not None and q_unit is not None and intercooler_lmtd is not None:
            try:
                # 인터쿨러는 냉각이므로 Q값이 음수일 때 양수로 변환
                abs_q_value = abs(q_value)
                
                # 인터쿨러 비용 계산 - 기존 열교환기 함수 사용
                intercooler_inputs = CostInputs(
                    material=material,
                    selected_type="heat_exchanger",
                    selected_subtype="fixed_tube",
                    shell_material=config.DEFAULT_MATERIAL,
                    tube_material=config.DEFAULT_MATERIAL,
                    heat_duty_value=abs_q_value,
                    heat_duty_unit=q_unit,
                    heat_transfer_coefficient_value=850.0,
                    heat_transfer_coefficient_unit="Watt/sqm-K",
                    log_mean_temp_difference_value=intercooler_lmtd,
                    log_mean_temp_difference_unit="K"
                )
                intercooler_costs = estimate_heat_exchanger_cost(intercooler_inputs, cepci)
                _push(debug_steps, f"Stage {stage_num} Intercooler:")
                # 인터쿨러 상세 계산 과정을 debug_steps에 추가
                for step in intercooler_costs.get('debug_steps', []):
                    _push(debug_steps, f"    - {step}")
                for k in total_costs:
                    total_costs[k] += intercooler_costs[k]
                total_intercooler_cost += intercooler_costs.get('bare_module_cost', 0.0)
                        
            except Exception as e:
                _push(debug_steps, f"Stage {stage_num} intercooler calculation failed: {str(e)} - proceeding without intercooler")
                continue  # 인터쿨러 계산 실패는 무시

    # 다단 압축기 총 비용 계산 과정 추가
    _push(debug_steps, f"Total: Compressor=${total_compressor_cost:,.2f} + Intercooler=${total_intercooler_cost:,.2f} = ${total_costs['bare_module_cost']:,.2f}")

    return {
        "purchased_base": total_costs["purchased_base"],
        "purchased_adj": total_costs["purchased_adj"],
        "bare_module_cost": total_costs["bare_module_cost"],
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": total_power_kw,
        "debug_steps": debug_steps
    }

def estimate_heat_exchanger_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("heat_exchanger", subtype)
    coeffs = settings.get("correlation_coeffs")
    
    debug_steps: List[str] = []
    # 전용 필드 직접 사용
    area_value = inputs.heat_transfer_area_value
    area_unit = inputs.heat_transfer_area_unit
    
    # 면적이 직접 주어진 경우 SI 변환
    area_sqm = None
    if area_value is not None and area_unit:
        try:
            area_sqm = unit_converter.convert_units(area_value, area_unit, 'sqm', 'AREA')
        except Exception as e:
            raise ValueError(f"Unit conversion error for heat transfer area ({subtype}): {e}")

    if area_sqm is None:
        # 원시값과 단위를 사용하여 면적 계산 (전용 필드 우선 사용)
        heat_duty_value = inputs.heat_duty_value
        heat_duty_unit = inputs.heat_duty_unit
        htc_value = inputs.heat_transfer_coefficient_value
        htc_unit = inputs.heat_transfer_coefficient_unit
        lmtd_value = inputs.log_mean_temp_difference_value
        lmtd_unit = inputs.log_mean_temp_difference_unit
        
        if heat_duty_value is None or heat_duty_unit is None:
            raise ValueError(f"Missing heat duty value or unit for heat exchanger ({subtype})")
        if htc_value is None or htc_unit is None:
            raise ValueError(f"Missing heat transfer coefficient value or unit for heat exchanger ({subtype})")
        if lmtd_value is None or lmtd_unit is None:
            raise ValueError(f"Missing log mean temperature difference value or unit for heat exchanger ({subtype})")
        
        try:
            q_watt = unit_converter.convert_units(heat_duty_value, heat_duty_unit, 'Watt', 'ENTHALPY-FLO')
            u_si = unit_converter.convert_units(htc_value, htc_unit, 'Watt/sqm-K', 'HEAT-TRANS-C')
            lmtd_si = unit_converter.convert_units(lmtd_value, lmtd_unit, 'K', 'DELTA-T')
            _push(debug_steps, f"Q={heat_duty_value:.2f} {heat_duty_unit} → {q_watt:.2f} W, U={htc_value:.2f} {htc_unit} → {u_si:.2f} W/m²·K, ΔTlm={lmtd_value:.2f} {lmtd_unit} → {lmtd_si:.2f} K")
        except Exception as e:
            raise ValueError(f"Unit conversion error for heat exchanger ({subtype}): {e}")
        
        if u_si is None or u_si == 0 or lmtd_si is None or lmtd_si == 0:
            raise ValueError(f"U or LMTD is zero after unit conversion for heat exchanger ({subtype})")
        
        # Watt 단위의 열부하를 면적 계산에 사용: A = Q / (U × ΔT)
        # 여기서 Q는 Watt (J/sec), U는 Watt/sqm-K, ΔT는 K
        area_sqm = q_watt / (u_si * lmtd_si)
        _push(debug_steps, f"A = Q/(U·ΔTlm) = {q_watt:.2f}/({u_si:.2f}·{lmtd_si:.2f}) = {area_sqm:.4f} m²")
    
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
                heat_transfer_area_value=area_per_unit,
                heat_transfer_area_unit="sqm",
                material=inputs.material,
                selected_subtype=subtype,
                shell_material=inputs.shell_material,
                tube_material=inputs.tube_material
            )
            parts.append(estimate_heat_exchanger_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    _push(debug_steps, f"logC(S={area_sqm:.2f}) = {coeffs['k1']:.4f} + {coeffs['k2']:.4f}·log10(S) + {coeffs['k3']:.4f}·log10(S)^2")
    purchased_base = _eval_log_quadratic_cost(area_sqm, coeffs)
    _push(debug_steps, f"Purchased base (2001, CEPCI=397) = {purchased_base:,.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"CEPCI adjusted (target={cepci.target_index}) = {purchased_adj:,.2f}")

    fm = _resolve_material_factor(
        "heat_exchanger", subtype, inputs.material,
        shell_material=inputs.shell_material, tube_material=inputs.tube_material
    )
    # 압력 인자는 열교환기에서는 기본값 사용
    fp = 1.0  # 열교환기는 일반적으로 낮은 압력
    
    b1, b2 = settings.get("bm_factors_b1b2")
    _push(debug_steps, f"Fm={fm:.2f} (Shell={inputs.shell_material}, Tube={inputs.tube_material}), Fp={fp:.2f}; BM = {b1} + {b2}·Fm·Fp")
    effective_bm = b1 + b2 * fm * fp
    bare_module_cost = purchased_adj * effective_bm
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm:.3f} = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": fm,
        "pressure_factor": fp,
        "size_value": area_sqm,
        "debug_steps": debug_steps
    }

def estimate_vessel_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("vessel", subtype)
    coeffs = settings.get("correlation_coeffs")
    
    # 전용 필드 직접 사용
    volume_value = inputs.volume_value
    volume_unit = inputs.volume_unit
    diameter_value = inputs.diameter_value
    diameter_unit = inputs.diameter_unit

    if volume_value is None or volume_unit is None:
        raise ValueError(f"Missing volume value or unit for vessel ({subtype})")
    
    try:
        volume_cum = unit_converter.convert_units(volume_value, volume_unit, 'cum', 'VOLUME')
    except Exception as e:
        raise ValueError(f"Unit conversion error for vessel volume ({subtype}): {e}")

    debug_steps: List[str] = []
    _push(debug_steps, f"S=Volume={volume_value} {volume_unit} → {volume_cum} m³")
    if volume_cum is None or volume_cum <= 0:
        raise ValueError(f"Invalid volume after conversion for vessel ({subtype})")
    
    # 지름 변환 (필요한 경우)
    diameter_m = diameter_value
    if diameter_value is not None and inputs.diameter_unit is not None:
        try:
            # 지름은 길이 단위이므로 LENGTH 타입으로 변환
            # 지름은 일반적으로 면적의 평방근이므로 길이 단위로 변환할 수 있음
            diameter_area_sqm = unit_converter.convert_units(diameter_value, inputs.diameter_unit, 'sqm', 'AREA')
            diameter_m = diameter_area_sqm ** 0.5 if diameter_area_sqm else None
        except Exception as e:
            print(f"Warning: Could not convert diameter for vessel ({subtype}): {e}")
            diameter_m = diameter_value

    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if max_size and volume_cum > max_size:
        num_units = math.ceil(volume_cum / max_size)
        volume_per_unit = volume_cum / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                volume_value=volume_per_unit,
                volume_unit="cum",
                material=inputs.material,
                selected_subtype=subtype,
                diameter_value=diameter_m,
                diameter_unit="m"
            )
            parts.append(estimate_vessel_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    _push(debug_steps, f"logC(S={volume_cum:.2f}) = {coeffs['k1']:.4f} + {coeffs['k2']:.4f}·log10(S) + {coeffs['k3']:.4f}·log10(S)^2")
    purchased_base = _eval_log_quadratic_cost(volume_cum, coeffs)
    _push(debug_steps, f"Purchased base (2001, CEPCI=397) = {purchased_base:,.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"CEPCI adjusted (target={cepci.target_index}) = {purchased_adj:,.2f}")
    
    fm = _resolve_material_factor("vessel", subtype, inputs.material)
    
    # 압력 계산
    pressure_value = inputs.operating_pressure_value
    pressure_unit = inputs.operating_pressure_unit
    pressure_bar = None
    
    if pressure_value is not None and pressure_unit is not None:
        try:
            pressure_bar = unit_converter.convert_units(pressure_value, pressure_unit, 'bar', 'PRESSURE')
        except Exception as e:
            print(f"Warning: Could not convert pressure for vessel ({subtype}): {e}")
    
    fp = _resolve_pressure_factor("vessel", subtype, pressure_bar, "gauge", diameter=diameter_m)
    
    b1, b2 = settings.get("bm_factors_b1b2")
    _push(debug_steps, f"Fm={fm:.3f}, Fp={fp:.3f}; BM = {b1} + {b2}·Fm·Fp")
    effective_bm = b1 + b2 * fm * fp
    bare_module_cost = purchased_adj * effective_bm
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm:.3f} = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": fm,
        "pressure_factor": fp,
        "size_value": volume_cum,
        "debug_steps": debug_steps
    }

def estimate_reactor_cost(inputs: CostInputs, cepci: CEPCIOptions) -> Dict[str, Any]:
    subtype = inputs.selected_subtype
    settings = config.get_equipment_setting("reactor", subtype)
    coeffs = settings.get("correlation_coeffs")
    
    # 전용 필드 직접 사용
    volume_value = inputs.volume_value
    volume_unit = inputs.volume_unit

    debug_steps: List[str] = []
    if volume_value is None or volume_unit is None:
        raise ValueError(f"Missing volume value or unit for reactor ({subtype})")
    
    try:
        volume_cum = unit_converter.convert_units(volume_value, volume_unit, 'cum', 'VOLUME')
    except Exception as e:
        raise ValueError(f"Unit conversion error for reactor volume ({subtype}): {e}")

    _push(debug_steps, f"S=Volume={volume_value} {volume_unit} → {volume_cum} m³")
    if volume_cum is None or volume_cum <= 0:
        raise ValueError(f"Invalid volume after conversion for reactor ({subtype})")

    max_size_range = settings.get("size_ranges", [{}])[0]
    max_size = max_size_range.get("max")
    
    if max_size and volume_cum > max_size:
        num_units = math.ceil(volume_cum / max_size)
        volume_per_unit = volume_cum / num_units
        parts = []
        for _ in range(int(num_units)):
            sub_inputs = CostInputs(
                volume_value=volume_per_unit,
                volume_unit="cum",
                material=inputs.material,
                selected_subtype=subtype,
            )
            parts.append(estimate_reactor_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    _push(debug_steps, f"logC(S={volume_cum:.2f}) = {coeffs['k1']:.4f} + {coeffs['k2']:.4f}·log10(S) + {coeffs['k3']:.4f}·log10(S)^2")
    purchased_base = _eval_log_quadratic_cost(volume_cum, coeffs)
    _push(debug_steps, f"Purchased base (2001) = {purchased_base:.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"CEPCI adjusted (target={cepci.target_index}) = {purchased_adj:,.2f}")
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    bare_module_cost = purchased_adj * effective_bm
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm:.3f} = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": volume_cum,
        "debug_steps": debug_steps
    }


def calculate_all_costs_with_data(all_device_data: List[Dict], cepci: CEPCIOptions, Application=None) -> Dict[str, Any]:
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
                material=device.get("material", config.DEFAULT_MATERIAL),
                selected_type=device.get("selected_type"),
                selected_subtype=device.get("selected_subtype"),
                power_value=device.get("power_value"),
                power_unit=device.get("power_unit"),
                heat_duty_value=device.get("heat_duty_value"),
                heat_duty_unit=device.get("heat_duty_unit"),
                heat_transfer_coefficient_value=device.get("heat_transfer_coefficient_value"),
                heat_transfer_coefficient_unit=device.get("heat_transfer_coefficient_unit"),
                log_mean_temp_difference_value=device.get("log_mean_temp_difference_value"),
                log_mean_temp_difference_unit=device.get("log_mean_temp_difference_unit"),
                volume_value=device.get("volume_value"),
                volume_unit=device.get("volume_unit"),
                inlet_pressure_value=device.get("inlet_pressure_value"),
                inlet_pressure_unit=device.get("inlet_pressure_unit"),
                outlet_pressure_value=device.get("outlet_pressure_value"),
                outlet_pressure_unit=device.get("outlet_pressure_unit"),
                operating_pressure_value=device.get("operating_pressure_value"),
                operating_pressure_unit=device.get("operating_pressure_unit"),
                pressure_drop_value=device.get("pressure_drop_value"),
                pressure_drop_unit=device.get("pressure_drop_unit"),
                volumetric_flow_value=device.get("volumetric_flow_value"),
                volumetric_flow_unit=device.get("volumetric_flow_unit"),
                mass_flow_value=device.get("mass_flow_value"),
                mass_flow_unit=device.get("mass_flow_unit"),
                residence_time_hours_value=device.get("residence_time_hours_value"),
                residence_time_minutes_value=device.get("residence_time_minutes_value"),
                stage_data=device.get("stage_data"),
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
                costs = estimate_mcompr_cost(inputs, cepci, Application)
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
    debug_steps: List[str] = []
    
    if inputs.power_value is None or inputs.power_unit is None:
        raise ValueError("Missing power value or unit for turbine")
        
    power_kw = unit_converter.convert_units(inputs.power_value, inputs.power_unit, 'kW', 'POWER')
    # 터빈은 출력이므로 파워가 음수일 때 양수로 변환
    if power_kw is not None and power_kw < 0:
        power_kw = abs(power_kw)
    _push(debug_steps, f"S=Power={inputs.power_value} {inputs.power_unit} → {power_kw:.2f} kW")
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
                power_value=power_per_unit,
                power_unit="kw",
                material=inputs.material,
                selected_subtype=subtype
            )
            parts.append(estimate_turbine_cost(sub_inputs, cepci))
        return _sum_costs(parts)

    _push(debug_steps, f"logC with S={power_kw:.2f}")
    purchased_base = _eval_log_quadratic_cost(power_kw, coeffs)
    _push(debug_steps, f"Purchased base (2001, CEPCI=397) = {purchased_base:,.2f}")
    purchased_adj = _adjust_cost_to_index(purchased_base, cepci.base_index, cepci.target_index)
    _push(debug_steps, f"Cost adjusted = {purchased_adj:.2f}")
    
    fixed_bm_factors = settings.get("bm_factors_fixed")
    effective_bm = fixed_bm_factors.get(inputs.material, fixed_bm_factors.get(config.DEFAULT_MATERIAL))
    
    bare_module_cost = purchased_adj * effective_bm
    _push(debug_steps, f"BM = {effective_bm:.3f}")
    _push(debug_steps, f"Bare Module Cost = {purchased_adj:,.2f} × {effective_bm:.3f} = {bare_module_cost:,.2f}")
    
    return {
        "purchased_base": purchased_base,
        "purchased_adj": purchased_adj,
        "bare_module_cost": bare_module_cost,
        "bm_factor": effective_bm,
        "material_factor": 1.0,
        "pressure_factor": 1.0,
        "size_value": power_kw,
        "debug_steps": debug_steps
    }