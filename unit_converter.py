"""
단위 변환 및 상수 데이터 모듈

이 모듈은 단위 변환 함수들과 장비별 상수 데이터를 제공합니다.
"""

from typing import Dict, Optional


# =============================================================================
# 단위 변환 함수들
# =============================================================================

def convert_power_to_target_unit(value_kw: float, target_unit: str) -> float:
    """전력을 kW에서 목표 단위로 변환"""
    power_conversion_factors = {
        'Watt': 1000.0, 'W': 1000.0, 'kW': 1.0, 'MW': 0.001, 
        'hp': 1.34102, 'Btu/hr': 3412.14,
    }
    factor = power_conversion_factors.get(target_unit)
    if factor is None:
        raise ValueError(f"Unsupported power unit '{target_unit}' for equipment cost calculation. Supported units: {list(power_conversion_factors.keys())}")
    return value_kw * factor


def convert_flow_to_target_unit(value_m3_s: float, target_unit: str) -> float:
    """유량을 m³/s에서 목표 단위로 변환"""
    flow_conversion_factors = {
        'm3/s': 1.0, 'm^3/s': 1.0, 'm3/h': 3600.0, 'm^3/h': 3600.0, 
        'cum/hr': 3600.0, 'cum/h': 3600.0, 'Nm3/h': 3600.0, 
        'L/s': 1000.0, 'L/min': 60000.0, 'L/h': 3600000.0, 
        'ft3/s': 35.3147, 'ft3/min': 2118.88, 'cfm': 2118.88,
    }
    factor = flow_conversion_factors.get(target_unit)
    if factor is None:
        raise ValueError(f"Unsupported flow unit '{target_unit}' for fan cost calculation. Supported units: {list(flow_conversion_factors.keys())}")
    return value_m3_s * factor


# =============================================================================
# 장비별 최소 크기 제한
# =============================================================================

MIN_SIZE_LIMITS = {
    "pump": {
        "centrifugal": 1.0,      # kW
        "reciprocating": 0.1,    # kW
    },
    "compressor": {
        "centrifugal": 450.0,    # kW
        "axial": 450.0,          # kW
        "reciprocating": 450.0,  # kW
    },
    "turbine": {
        "axial": 1.0,           # kW (100 kW에서 1 kW로 낮춤)
        "radial": 1.0,          # kW (100 kW에서 1 kW로 낮춤)
    },
    "fan": {
        "centrifugal_radial": 1.0,    # m³/s
        "centrifugal_backward": 1.0,  # m³/s
        "centrifugal_forward": 1.0,   # m³/s
        "axial": 1.0,                 # m³/s
    }
}


def check_minimum_size_limit(equipment_type: str, subtype: str, size_value: float, size_unit: str) -> tuple[bool, str]:
    """
    장치 크기가 최소 제한을 만족하는지 확인
    Returns: (is_valid, error_message)
    """
    min_limit = MIN_SIZE_LIMITS.get(equipment_type, {}).get(subtype)
    
    if min_limit is None:
        return True, ""  # 제한이 정의되지 않은 경우 통과
    
    if size_value < min_limit:
        return False, f"under limit (min: {min_limit} {size_unit})"
    
    return True, ""


# =============================================================================
# 장비별 최대 크기 제한 (분할 기준)
# =============================================================================

MAX_SIZE_LIMITS = {
    "pump": {
        "centrifugal": 1000.0,   # kW
        "reciprocating": 1000.0, # kW
    },
    "compressor": {
        "centrifugal": 10000.0,  # kW
        "axial": 10000.0,        # kW
        "reciprocating": 10000.0,# kW
    },
    "turbine": {
        "axial": 10000.0,        # kW
        "radial": 10000.0,       # kW
    },
    "fan": {
        "centrifugal_radial": 100.0,    # m³/s
        "centrifugal_backward": 100.0,  # m³/s
        "centrifugal_forward": 100.0,   # m³/s
        "axial": 100.0,                 # m³/s
    }
}


def get_max_size_limit(equipment_type: str, subtype: str) -> Optional[float]:
    """장비별 최대 크기 제한 반환"""
    return MAX_SIZE_LIMITS.get(equipment_type, {}).get(subtype)


# =============================================================================
# CEPCI 인덱스 데이터
# =============================================================================

CEPCI_BY_YEAR = {
    2017: 567.5,  # Turton 기준년도
    2018: 603.1,
    2019: 607.5,
    2020: 596.2,
    2021: 708.0,
    2022: 778.8,
    2023: 789.6,
    2024: 800.0,  # 추정값
    2025: 810.0,  # 추정값
}


def get_cepi_index(year: int) -> float:
    """연도별 CEPCI 인덱스 반환"""
    return CEPCI_BY_YEAR.get(year, 800.0)  # 기본값 2024년


# =============================================================================
# 압력 단위 변환 상수
# =============================================================================

PRESSURE_TO_BAR = {
    'bar': 1.0, 'bara': 1.0, 'atm': 1.01325, 'Pa': 1e-5, 'kPa': 0.01,
    'MPa': 10.0, 'psi': 0.0689476, 'psia': 0.0689476, 'mmHg': 0.00133322,
    'torr': 0.00133322, 'mbar': 0.001, 'inH2O': 0.00249089, 'inHg': 0.0338639
}


def convert_pressure_to_bar(value: float, unit: Optional[str]) -> Optional[float]:
    """압력 단위를 bar로 변환"""
    if unit is None:
        return value
    
    # 게이지 압력인 경우 절대 압력으로 변환
    try:
        u = unit.lower()
        if u == 'barg':
            return float(value) + 1.01325
        if u == 'psig':
            return float(value) * 0.0689476 + 1.01325
        if u == 'kpag':
            return float(value) * 1e-2 + 1.01325
        if u == 'mpag':
            return float(value) * 10.0 + 1.01325
        if u == 'mbarg':
            return float(value) * 1e-3 + 1.01325
    except Exception:
        return None
        
    factor = PRESSURE_TO_BAR.get(unit)
    if factor is None:
        return None
        
    return float(value) * factor


def is_gauge_pressure_unit(unit: Optional[str]) -> bool:
    """게이지 압력 단위인지 확인"""
    if unit is None:
        return False
    gauge_units = {'barg', 'psig', 'kpag', 'mpag', 'mbarg'}
    return unit.lower() in gauge_units
