"""
프로그램 전반에 사용되는 상수 및 설정 (최종 버전)
"""
import math

# =============================================================================
# 일반 설정
# =============================================================================

DEFAULT_MATERIAL = "CS"
DEFAULT_TARGET_YEAR = 2024
ENABLE_DEBUG_OUTPUT = True
DEFAULT_VERBOSITY = 1


# =============================================================================
# CEPCI 인덱스 데이터
# =============================================================================

CEPCI_BY_YEAR = {
    2001: 397.0, 2005: 468.2, 2006: 499.6, 2007: 525.4, 2008: 575.4,
    2009: 521.9, 2010: 550.8, 2011: 585.7, 2012: 584.6, 2013: 567.3,
    2014: 576.1, 2015: 556.8, 2016: 541.7, 2017: 567.5, 2018: 603.1,
    2019: 607.5, 2020: 596.2, 2021: 708.8, 2022: 816.0, 2023: 797.9,
    2024: 799.0,
}


# =============================================================================
# 장비별 상세 설정 (통합 구조)
# =============================================================================
EQUIPMENT_SETTINGS = {
    "pump": {
        "centrifugal": {
            # Turton 방법론: power_kilowatt (kW) 기준 대용량 펌프 비용 계산
            "correlation_coeffs": {"k1": 3.3892, "k2": 0.0536, "k3": 0.1538},
            "bm_factors_b1b2": (1.89, 1.35),
            "material_factors": {"Cl": 1.0, "CS": 1.6, "SS": 2.3, "Ni": 4.4},
            "size_ranges": [{"min": 1.0, "max": 300.0, "unit": "kW"}],
            "pressure_ranges": [
                {"min": None, "max": 10.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 10.0, "max": 100.0, "c1": -0.3935, "c2": 0.3957, "c3": -0.00226, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "positive_displacement": {
            # Turton 방법론: power_kilowatt (kW) 기준 양변위 펌프 비용 계산
            "correlation_coeffs": {"k1": 3.4771, "k2": 0.1350, "k3": 0.1438},
            "bm_factors_b1b2": (1.89, 1.35),
            "material_factors": {"Cl": 1.0, "CS": 1.4, "Cu": 1.3, "SS": 2.7, "Ni": 4.7, "Ti": 10.7},
            "size_ranges": [{"min": 1.0, "max": 100.0, "unit": "kW"}],
            "pressure_ranges": [
                {"min": None, "max": 10.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 10.0, "max": 100.0, "c1": -0.245382, "c2": 0.259016, "c3": -0.01363, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "reciprocating": {
            # Turton 방법론: power_kilowatt (kW) 기준 왕복 펌프 비용 계산
            "correlation_coeffs": {"k1": 3.8696, "k2": 0.3161, "k3": 0.1220},
            "bm_factors_b1b2": (1.89, 1.35),
            "material_factors": {"Cl": 1.0, "CS": 1.5, "Cu": 1.3, "SS": 2.4, "Ni": 4.0, "Ti": 6.4},
            "size_ranges": [{"min": 0.1, "max": 200.0, "unit": "kW"}],
            "pressure_ranges": [
                {"min": None, "max": 10.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 10.0, "max": 100.0, "c1": -0.245382, "c2": 0.259016, "c3": -0.01363, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        }
    },
    "compressor": {
        "centrifugal": {
            # Turton 방법론: power_kilowatt (kW) 기준 원심 압축기 비용 계산
            "correlation_coeffs": {"k1": 2.2897, "k2": 1.3604, "k3": -0.1027},
            "bm_factors_fixed": {"CS": 2.7, "SS": 5.8, "Ni": 11.5},
            "size_ranges": [{"min": 450.0, "max": 3000.0, "unit": "kW"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "axial": {
            # Turton 방법론: power_kilowatt (kW) 기준 축류 압축기 비용 계산
            "correlation_coeffs": {"k1": 2.2897, "k2": 1.3604, "k3": -0.1027},
            "bm_factors_fixed": {"CS": 3.8, "SS": 8.0, "Ni": 15.9},
            "size_ranges": [{"min": 450.0, "max": 3000.0, "unit": "kW"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "rotary": {
            # Turton 방법론: power_kilowatt (kW) 기준 회전 압축기 비용 계산
            "correlation_coeffs": {"k1": 5.0355, "k2": -1.8002, "k3": 0.8253},
            "bm_factors_fixed": {"CS": 2.4, "SS": 5.0, "Ni": 9.9},
            "size_ranges": [{"min": 18.0, "max": 950.0, "unit": "kW"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "reciprocating": {
            # Turton 방법론: power_kilowatt (kW) 기준 왕복 압축기 비용 계산
            "correlation_coeffs": {"k1": 2.2897, "k2": 1.3604, "k3": -0.1027},
            "bm_factors_fixed": {"CS": 3.4, "SS": 7.0, "Ni": 13.9},
            "size_ranges": [{"min": 450.0, "max": 3000.0, "unit": "kW"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
    },
    "fan": {
        "centrifugal_radial": {
            # Turton 방법론: volumetric_flow_m3_s (m³/s) 기준 원심 방사형 팬 비용 계산
            "correlation_coeffs": {"k1": 3.5391, "k2": -0.3533, "k3": 0.4477},
            "bm_factors_fixed": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
            "size_ranges": [{"min": 1.0, "max": 100.0, "unit": "cum/sec"}],
            "pressure_ranges": [
                {"min": None, "max": 1.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "pressure_difference", "unit": "kPa"},
                {"min": 1.0, "max": 16.0, "c1": 0.0, "c2": 0.20899, "c3": -0.0328, "type": "pressure_difference", "unit": "kPa"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "centrifugal_backward_curved": {
            # Turton 방법론: volumetric_flow_m3_s (m³/s) 기준 원심 후곡 팬 비용 계산
            "correlation_coeffs": {"k1": 3.3471, "k2": -0.0734, "k3": 0.3090},
            "bm_factors_fixed": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
            "size_ranges": [{"min": 1.0, "max": 100.0, "unit": "cum/sec"}],
            "pressure_ranges": [
                {"min": None, "max": 1.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "pressure_difference", "unit": "kPa"},
                {"min": 1.0, "max": 16.0, "c1": 0.0, "c2": 0.20899, "c3": -0.0328, "type": "pressure_difference", "unit": "kPa"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "axial_vane": {
            # Turton 방법론: volumetric_flow_m3_s (m³/s) 기준 축류 베인 팬 비용 계산
            "correlation_coeffs": {"k1": 3.1761, "k2": -0.1373, "k3": 0.3414},
            "bm_factors_fixed": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
            "size_ranges": [{"min": 1.0, "max": 100.0, "unit": "cum/sec"}],
            "pressure_ranges": [
                {"min": None, "max": 1.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "pressure_difference", "unit": "kPa"},
                {"min": 1.0, "max": 4.0, "c1": 0.0, "c2": 0.20899, "c3": -0.0328, "type": "pressure_difference", "unit": "kPa"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "axial_tube": {
            # Turton 방법론: volumetric_flow_m3_s (m³/s) 기준 축류 튜브 팬 비용 계산
            "correlation_coeffs": {"k1": 3.0414, "k2": -0.3375, "k3": 0.4722},
            "bm_factors_fixed": {"CS": 2.7, "Fiberglass": 5.0, "SS": 5.8, "Ni": 11.5},
            "size_ranges": [{"min": 1.0, "max": 100.0, "unit": "cum/sec"}],
            "pressure_ranges": [
                {"min": None, "max": 1.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "pressure_difference", "unit": "kPa"},
                {"min": 1.0, "max": 4.0, "c1": 0.0, "c2": 0.20899, "c3": -0.0328, "type": "pressure_difference", "unit": "kPa"}
            ],
            "pressure_calc_method": "coefficient"
        },
    },
    "turbine": {
        "axial": {
            # Turton 방법론: power_kilowatt (kW) 기준 축류 터빈 비용 계산
            "correlation_coeffs": {"k1": 2.7051, "k2": 1.4398, "k3": -0.1776},
            "bm_factors_fixed": {"CS": 3.5, "SS": 6.1, "Ni": 11.7},
            "size_ranges": [{"min": 100.0, "max": 4000.0, "unit": "kW"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "radial": {
            # Turton 방법론: power_kilowatt (kW) 기준 방사형 터빈 비용 계산
            "correlation_coeffs": {"k1": 2.2476, "k2": 1.4965, "k3": -0.1618},
            "bm_factors_fixed": {"CS": 3.5, "SS": 6.1, "Ni": 11.7},
            "size_ranges": [{"min": 100.0, "max": 1500.0, "unit": "kW"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
    },
    "heat_exchanger": {
        "double_pipe": {
            # Turton 방법론: heat_area_sqm (m²) 기준 이중관 열교환기 비용 계산
            "correlation_coeffs": {"k1": 3.3444, "k2": 0.2745, "k3": -0.0472},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 10.5, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 40.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 40.0, "max": 100.0, "c1": 0.6072, "c2": -0.9120, "c3": 0.3327, "type": "gauge", "unit": "barg"},
                {"min": 100.0, "max": 300.0, "c1": 13.1467, "c2": -12.6574, "c3": 3.0705, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "multiple_pipe": {
            # Turton 방법론: heat_area_sqm (m²) 기준 다관 열교환기 비용 계산
            "correlation_coeffs": {"k1": 2.7652, "k2": 0.7282, "k3": 0.0783},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 10.5, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 40.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 40.0, "max": 100.0, "c1": 0.6072, "c2": -0.9120, "c3": 0.3327, "type": "gauge", "unit": "barg"},
                {"min": 100.0, "max": 300.0, "c1": 13.1467, "c2": -12.6574, "c3": 3.0705, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "fixed_tube": {
            # Turton 방법론: heat_area_sqm (m²) 기준 고정관 열교환기 비용 계산
            "correlation_coeffs": {"k1": 4.3247, "k2": -0.3030, "k3": 0.1634},
            "bm_factors_b1b2": (1.63, 1.66),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 520.0, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 5.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 5.0, "max": 140.0, "c1": -0.00164, "c2": -0.00627, "c3": 0.0123, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "floating_head": {
            # Turton 방법론: heat_area_sqm (m²) 기준 플로팅헤드 열교환기 비용 계산
            "correlation_coeffs": {"k1": 4.8306, "k2": -0.8509, "k3": 0.3187},
            "bm_factors_b1b2": (1.63, 1.66),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 520.0, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 5.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 5.0, "max": 140.0, "c1": -0.00164, "c2": -0.00627, "c3": 0.0123, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "bayonet": {
            # Turton 방법론: heat_area_sqm (m²) 기준 베이옷 열교환기 비용 계산
            "correlation_coeffs": {"k1": 4.2768, "k2": -0.0495, "k3": 0.1431},
            "bm_factors_b1b2": (1.63, 1.66),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 520.0, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 5.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 5.0, "max": 140.0, "c1": -0.00164, "c2": -0.00627, "c3": 0.0123, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "kettle_reboiler": {
            # Turton 방법론: heat_area_sqm (m²) 기준 케로일러 비용 계산
            "correlation_coeffs": {"k1": 4.4646, "k2": -0.5277, "k3": 0.3955},
            "bm_factors_b1b2": (1.63, 1.66),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 520.0, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 5.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 5.0, "max": 140.0, "c1": -0.00164, "c2": -0.00627, "c3": 0.0123, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "scraped_wall": {
            "correlation_coeffs": {"k1": 3.7803, "k2": 0.8569, "k3": 0.0349},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 10.5, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 40.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 40.0, "max": 100.0, "c1": 0.6072, "c2": -0.9120, "c3": 0.3327, "type": "gauge", "unit": "barg"},
                {"min": 100.0, "max": 300.0, "c1": 13.1467, "c2": -12.6574, "c3": 3.0705, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "teflon_tube": {
            "correlation_coeffs": {"k1": 3.8062, "k2": 0.8924, "k3": -0.1671},
            "bm_factors_b1b2": (1.63, 1.66),
            "material_factors_matrix": {"CS": 1.00, "Cu": 1.20, "SS": 1.30, "Ni": 1.60, "Ti": 3.30},
            "size_ranges": [{"min": 0.07, "max": 520.0, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 15.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "air_cooler": {
            "correlation_coeffs": {"k1": 4.0336, "k2": 0.2341, "k3": 0.0497},
            "bm_factors_b1b2": (0.96, 1.21),
            "material_factors_matrix": {"CS": 1.00, "Al": 1.42, "SS": 2.93},
            "size_ranges": [{"min": 0.07, "max": 520.0, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 10.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 10.0, "max": 100.0, "c1": -0.1250, "c2": 0.15361, "c3": -0.02861, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "spiral_tube": {
            "correlation_coeffs": {"k1": 3.9912, "k2": 0.0668, "k3": 0.2430},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": {"CS": 1.00, "Cu": 1.35, "SS": 1.81, "Ni": 2.68, "Ti": 4.63}, "Cu": {"Cu": 1.69}, "SS": {"SS": 2.73}, "Ni": {"Ni": 3.73}, "Ti": {"Ti": 11.38}},
            "size_ranges": [{"min": 0.07, "max": 10.5, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 150.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"},
                {"min": 150.0, "max": 400.0, "c1": -0.4045, "c2": 0.1859, "c3": 0.0, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "spiral_plate": {
            "correlation_coeffs": {"k1": 4.6561, "k2": -0.2947, "k3": 0.2207},
            "bm_factors_b1b2": (0.96, 1.21),
            "material_factors_matrix": {"CS": 1.00, "Cu": 1.35, "SS": 2.45, "Ni": 2.68, "Ti": 4.63},
            "size_ranges": [{"min": 0.07, "max": 10.5, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 19.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
        "flat_plate": {
            "correlation_coeffs": {"k1": 4.6656, "k2": -0.1557, "k3": 0.1547},
            "bm_factors_b1b2": (0.96, 1.21),
            "material_factors_matrix": {"CS": 1.00, "Cu": 1.35, "SS": 2.45, "Ni": 2.68, "Ti": 4.63},
            "size_ranges": [{"min": 0.07, "max": 10.5, "unit": "sqm"}],
            "pressure_ranges": [
                {"min": None, "max": 19.0, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "coefficient"
        },
    },
    "reactor": {
        "autoclave": {
            # Turton 방법론: volume_value (m³) 기준 오토클레프 반응기 비용 계산
            "correlation_coeffs": {"k1": 4.5587, "k2": 0.2986, "k3": 0.0020},
            "bm_factors_fixed": {"CS": 4.0, "SS": 5.0, "Ni": 7.0},
            "size_ranges": [{"min": 1.0, "max": 15.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "fermenter": {
            "correlation_coeffs": {"k1": 4.1052, "k2": 0.5320, "k3": -0.0005},
            "bm_factors_fixed": {"CS": 4.0, "SS": 5.0, "Ni": 7.0},
            "size_ranges": [{"min": 0.1, "max": 35.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "inoculum_tank": {
            "correlation_coeffs": {"k1": 3.7957, "k2": 0.4593, "k3": 0.0160},
            "bm_factors_fixed": {"CS": 4.0, "SS": 5.0, "Ni": 7.0},
            "size_ranges": [{"min": 0.07, "max": 1.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "jacketed_agitated": {
            "correlation_coeffs": {"k1": 4.1052, "k2": 0.5320, "k3": -0.0005},
            "bm_factors_fixed": {"CS": 4.0, "SS": 5.0, "Ni": 7.0},
            "size_ranges": [{"min": 0.1, "max": 35.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "jacketed_non_agitated": {
            "correlation_coeffs": {"k1": 3.3496, "k2": 0.7235, "k3": 0.0025},
            "bm_factors_fixed": {"CS": 4.0, "SS": 5.0, "Ni": 7.0},
            "size_ranges": [{"min": 5.0, "max": 45.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
        "mixer_settler": {
            "correlation_coeffs": {"k1": 4.7116, "k2": 0.4479, "k3": 0.0004},
            "bm_factors_fixed": {"CS": 4.0, "SS": 5.0, "Ni": 7.0},
            "size_ranges": [{"min": 0.04, "max": 60.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
    },
    "vessel": {
        "vertical": {
            # Turton 방법론: volume_value (m³) 기준 수직 용기 비용 계산
            "correlation_coeffs": {"k1": 3.4974, "k2": 0.4485, "k3": 0.1074},
            "bm_factors_b1b2": (1.49, 1.52),
            "material_factors_matrix": {"CS": 1.0, "SS_clad": 1.7, "SS": 3.1, "Ni_clad": 3.6, "Ni": 7.1, "Ti_clad": 4.7, "Ti": 9.4},
            "size_ranges": [{"min": 0.3, "max": 520.0, "unit": "cum"}],
            "pressure_ranges": [
                {"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "formula",
            "pressure_formula_config": {
                "S": 944.0, "E": 0.9, "CA": 0.00315, "t_min": 0.0063
            }
        },
        "horizontal": {
            "correlation_coeffs": {"k1": 3.5565, "k2": 0.3776, "k3": 0.0905},
            "bm_factors_b1b2": (2.25, 1.82),
            "material_factors_matrix": {"CS": 1.0, "SS_clad": 1.7, "SS": 3.1, "Ni_clad": 3.6, "Ni": 7.1, "Ti_clad": 4.7, "Ti": 9.4},
            "size_ranges": [{"min": 0.1, "max": 628.0, "unit": "cum"}],
            "pressure_ranges": [
                {"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}
            ],
            "pressure_calc_method": "formula",
            "pressure_formula_config": {
                "S": 944.0, "E": 0.9, "CA": 0.00315, "t_min": 0.0063
            }
        },
    },
    "tower": {
        "tray_and_packed": {
            "correlation_coeffs": {"k1": 3.4974, "k2": 0.4485, "k3": 0.1074},
            "bm_factors_b1b2": (1.49, 1.52),
            "material_factors_matrix": {},
            "size_ranges": [{"min": 0.3, "max": 520.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
    },
    "tray": {
        "sieve": {
            "correlation_coeffs": {"k1": 2.9949, "k2": 0.4465, "k3": 0.3961},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": 1.0, "SS": 1.8, "Ni-alloy": 5.6},
            "size_ranges": [{"min": 0.07, "max": 12.30, "unit": "sqm"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient",
            "quantity_factor_calc_method": "formula"
        },
        "valve": {
            "correlation_coeffs": {"k1": 3.3322, "k2": 0.4838, "k3": 0.3434},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": 1.0, "SS": 1.83, "Ni-alloy": 5.58},
            "size_ranges": [{"min": 0.70, "max": 10.50, "unit": "sqm"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient",
            "quantity_factor_calc_method": "formula"
        },
        "demisters": {
            "correlation_coeffs": {"k1": 3.2353, "k2": 0.4838, "k3": 0.3434},
            "bm_factors_b1b2": (1.74, 1.55),
            "material_factors_matrix": {"CS": 1.0, "SS": 1.0, "Fluorocarbon": 1.8, "Ni-alloy": 5.6},
            "size_ranges": [{"min": 0.70, "max": 10.50, "unit": "sqm"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient",
            "quantity_factor_calc_method": "formula"
        },
    },
    "packing": {
        "loose": {
            "correlation_coeffs": {"k1": 2.4493, "k2": 0.9744, "k3": 0.0055},
            "bm_factors_fixed": {"Ceramic": 4.14, "304SS": 7.09, "Plastic_Saddle": 1.00},
            "size_ranges": [{"min": 0.03, "max": 628.0, "unit": "cum"}],
            "pressure_ranges": [{"min": None, "max": None, "c1": 0.0, "c2": 0.0, "c3": 0.0, "type": "gauge", "unit": "barg"}],
            "pressure_calc_method": "coefficient"
        },
    },
}

def get_equipment_setting(equipment_type: str, subtype: str) -> dict:
    """장비 타입과 서브타입에 따른 모든 설정 정보 반환"""
    try:
        return EQUIPMENT_SETTINGS[equipment_type][subtype]
    except KeyError:
        return {}

# =============================================================================
# 추가 상수들 (기존 코드에서 누락된 것들)
# =============================================================================

FAN_MAX_PRESSURE_RISE = 0.16  # bar - 팬 범위 판정 기준
TURBINE_MIN_PRESSURE_DROP = 0.1  # bar - 터빈 범위 판정 기준