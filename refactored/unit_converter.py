"""
통합 단위 변환 시스템

이 모듈은 Aspen Plus와 호환되는 모든 단위 변환을 통합적으로 처리합니다.
"""

from typing import Dict, Optional, Union
import math
import sys

# =============================================================================
# 단위 변환 데이터
# =============================================================================
UNIT_DATA = {
    'DELTA-T': {
        'si_base': 'K',
        'units': {
            'K': 1.0,
            'Kelvin': 1.0,
            'delta-K': 1.0,
            'C': 1.0,
            'degC': 1.0,
            'DELTA-C': 1.0,
            'F': 5.0/9.0,
            'degF': 5.0/9.0,
            'DELTA-F': 5.0/9.0,
            'R': 5.0/9.0,
            'degR': 5.0/9.0,
            'DELTA-R': 5.0/9.0,
        }
    },
    'AREA': {
        'si_base': 'sqm',
        'units': {
            'sqm': 1.0, 'sqft': 0.092903, 'sqcm': 0.0001,
            'sqin': 0.00064516, 'sqmile': 2589988.11, 'sqmm': 0.000001
        }
    },
    'COMPOSITION': {
        'si_base': 'mol-fr',
        'units': {'mol-fr': 1.0, 'mass-fr': 1.0}
    },
    'DENSITY': {
        'si_base': 'kg/cum',
        'units': {
            'kg/cum': 1.0, 'lb/cuft': 16.0185, 'gm/cc': 1000.0, 'lb/gal': 119.826,
            'gm/cum': 0.001, 'gm/ml': 1000.0, 'lb/bbl': 2.85301, 'gm/l': 1.0,
            'mg/l': 0.001, 'mg/cc': 1.0, 'mg/cum': 0.000001
        }
    },
    'ENERGY': {
        'si_base': 'J',
        'units': {
            'J': 1.0, 'Btu': 1055.06, 'cal': 4.184, 'kcal': 4184.0, 'kWhr': 3600000.0,
            'ft-lbf': 1.35582, 'GJ': 1000000000.0, 'kJ': 1000.0, 'N-m': 1.0, 'MJ': 1000000.0,
            'Mcal': 4184000.0, 'Gcal': 4184000000.0, 'Mbtu': 1055060000.0,
            'MMBtu': 1055060000000.0, 'hp-hr': 2684520.0, 'MMkcal': 4184000000000.0
        }
    },
    'MASS-FLOW': {
        'si_base': 'kg/sec',
        'units': {
            'kg/sec': 1.0, 'lb/hr': 0.000125998, 'kg/hr': 0.000277778, 'lb/sec': 0.453592,
            'Mlb/hr': 125.998, 'tons/day': 0.0115741, 'Mcfh': 0.00786579, 'tonne/hr': 0.277778,
            'lb/day': 5.24991e-06, 'kg/day': 1.15741e-05, 'tons/hr': 0.277778, 'kg/min': 0.0166667,
            'kg/year': 3.17098e-08, 'gm/min': 1.66667e-05, 'gm/hr': 2.77778e-07, 'gm/day': 1.15741e-08,
            'Mgm/hr': 0.277778, 'Ggm/hr': 277.778, 'Mgm/day': 0.0115741, 'Ggm/day': 11.5741,
            'lb/min': 0.00755987, 'MMlb/hr': 125998.0, 'Mlb/day': 5.24991, 'MMlb/day': 5249.91,
            'lb/year': 1.43833e-08, 'Mlb/year': 1.43833e-05, 'MMIb/year': 0.0143833,
            'tons/min': 16.6667, 'Mtons/year': 31.7098, 'MMtons/year': 31709.8,
            'L-tons/min': 16.9333, 'L-tons/hr': 0.282222, 'L-tons/day': 0.0117593,
            'ML-tons/year': 32.1507, 'MML-tons/year': 32150.7, 'ktonne/year': 0.0317098,
            'kg/oper-year': 3.52775e-08, 'lb/oper-year': 1.59891e-08, 'Mlb/oper-year': 1.59891e-05,
            'MIMIb/oper-year': 0.0159891, 'Mtons/oper-year': 35.2775, 'MMtons/oper-year': 35277.5,
            'ML-tons/oper-year': 35.7230, 'MML-tons/oper-year': 35723.0, 'ktonne/oper-year': 0.0352775,
        }
    },
    'MASS': {
        'si_base': 'kg',
        'units': {'kg': 1.0, 'lb': 0.453592, 'gm': 0.001, 'ton': 1000.0, 'Mlb': 453592.0,
                  'tonne': 1000.0, 'L-ton': 1016.05, 'MMlb': 453592000.0}
    },
    'MOLE-FLOW': {
        'si_base': 'kmol/sec',
        'units': {
            'kmol/sec': 1.0, 'lbmol/hr': 0.000125998, 'kmol/hr': 0.000277778, 'MMscfh': 0.000783986,
            'MMscmh': 0.000022414, 'mol/sec': 0.001, 'lbmol/sec': 0.453592, 'scmh': 0.000022414,
            'bmol/day': 1.15741e-05, 'kmol/day': 1.15741e-05, 'MMscfd': 0.00000907407,
            'Mlscfd': 0.00000907407, 'scfm': 0.000000471947, 'mol/min': 1.66667e-05,
            'kmol/khr': 0.000277778, 'kmol/Mhr': 0.277778, 'mol/hr': 2.77778e-07,
            'Mmol/hr': 0.277778, 'Mlbmol/hr': 0.125998, 'lbmol/Mhr': 0.125998,
            'lbmol/MMhr': 125.998, 'Mscfm': 0.000471947, 'scfh': 7.86579e-08, 'scfd': 3.27741e-09,
            'ncmh': 0.000022414, 'ncmd': 9.33917e-07, 'ACFM': 0.000000471947, 'kmol/min': 0.0166667,
            'kmol/week': 1.65344e-06, 'kmol/month': 3.80517e-07, 'kmol/year': 3.17098e-08,
            'kmol/oper-year': 3.52775e-08, 'lbmol/min': 0.00755987
        }
    },
    'MOLE-VOLUME': {
        'si_base': 'cum/kmol',
        'units': {'cum/kmol': 1.0, 'cuft/lbmol': 0.0624280, 'cc/mol': 0.001, 'ml/mol': 0.001,
                  'bbl/mscf': 0.158987}
    },
    'MOLE-DENSITY': {
        'si_base': 'kmol/cum',
        'units': {
            'kmol/cum': 1.0, 'lbmol/cuft': 16.0185, 'mol/cc': 1000.0, 'lbmol/gal': 119.826,
            'mol/l': 1.0, 'mmol/cc': 1.0, 'mmol/l': 0.001
        }
    },
    'MASS-DENSITY': {
        'si_base': 'kg/cum',
        'units': {
            'kg/cum': 1.0, 'lb/cuft': 16.0185, 'gm/cc': 1000.0, 'lb/gal': 119.826,
            'gm/cum': 0.001, 'gm/ml': 1000.0, 'gm/l': 1.0, 'mg/l': 0.001,
            'mg/cc': 1.0, 'mg/cum': 0.000001
        }
    },
    'VOLUME-FLOW': {
        'si_base': 'cum/sec',
        'units': {
            'cum/sec': 1.0, 'm3/s': 1.0, 'm^3/s': 1.0, 'cuft/hr': 7.86579e-06,
            'l/min': 1.66667e-05, 'gal/min': 6.30902e-05, 'gal/hr': 1.05150e-06,
            'bbl/day': 1.84013e-06, 'cum/hr': 0.000277778, 'm3/h': 0.000277778,
            'm^3/h': 0.000277778, 'cuft/min': 0.000471947, 'bbl/hr': 4.41631e-05,
            'cuft/sec': 0.0283168, 'cum/day': 1.15741e-05, 'cum/year': 3.17098e-08,
            'l/hr': 2.77778e-07, 'kbbl/day': 0.00184013, 'MMcuft/hr': 7.86579,
            'MMcuft/day': 0.327741, 'Mcuft/day': 0.000327741, 'l/sec': 0.001,
            'l/day': 1.15741e-08, 'cum/min': 0.0166667, 'kcum/sec': 1000.0,
            'kcum/hr': 0.277778, 'kcum/day': 0.0115741, 'Mcum/sec': 1000000.0,
            'Mcum/hr': 277.778, 'Mcum/day': 11.5741, 'cuft/day': 3.27741e-07,
            'Mcuft/min': 0.471947, 'Mcuft/hr': 0.00786579, 'Mgal/min': 63.0902,
            'MMgal/min': 63090.2, 'Mgal/hr': 1.05150, 'MMgal/hr': 1051.50,
            'Mbbl/hr': 44.1631, 'MMbbl/hr': 44163.1, 'Mbbl/day': 1.84013,
            'MMbbl/day': 1840.13, 'cum/oper-year': 3.52775e-08
        }
    },
    'VOLUME': {
        'si_base': 'cum',
        'units': {
            'cum': 1.0, 'cuft': 0.0283168, 'l': 0.001, 'cuin': 1.63871e-05,
            'gal': 0.00378541, 'bbl': 0.158987, 'cc': 0.000001, 'kcum': 1000.0,
            'Mcum': 1000000.0, 'Mcuft': 28316.8, 'MMcuft': 28316800.0, 'ml': 0.000001,
            'kl': 1.0, 'MMl': 1000000.0, 'Mgal': 3785.41, 'MMgal': 3785410.0,
            'UKgal': 0.00454609, 'MUKgal': 4546.09, 'MMUKgal': 4546090.0,
            'Mbbl': 158987.0, 'MMbbl': 158987000.0, 'kbbl': 158.987, 'cuyd': 0.764555
        }
    },
    'POWER': {
        'si_base': 'Watt',
        'units': {
            'Watt': 1.0, 'hp': 745.7, 'kW': 1000.0, 'Btu/hr': 0.293071,
            'cal/sec': 4.184, 'ft-lbf/sec': 1.35582, 'MIW': 1000000.0,
            'GW': 1000000000.0, 'MJ/hr': 277.778, 'kcal/hr': 1.16222,
            'Gcal/hr': 1162220.0, 'MMBtu/hr': 293071.0, 'MBtu/hr': 293.071,
            'Mhp': 745700000.0
        }
    },
    'ELEC-POWER': {
        'si_base': 'Watt',
        'units': {'Watt': 1.0, 'W': 1.0, 'kW': 1000.0, 'MW': 1000000.0, 'GW': 1000000000.0}
    },
    'PRESSURE': {
        'si_base': 'N/sqm',
        'units': {
            'N/sqm': 1.0, 'Psia': 6894.76, 'atm': 101325.0, 'lbf/sqft': 47.8803,
            'bar': 100000.0, 'torr': 133.322, 'in-water': 249.089, 'kg/sqcm': 98066.5,
            'mmHg': 133.322, 'kPa': 1000.0, 'mm-water': 9.80665, 'mbar': 100.0,
            'psig': 'gauge_to_abs_psi', 'atmg': 'gauge_to_abs_atm', 'barg': 'gauge_to_abs_bar',
            'Pa': 1.0, 'MiPa': 1000000.0, 'Pag': 'gauge_to_abs_Pa', 'kPag': 'gauge_to_abs_kPa',
            'MPag': 'gauge_to_abs_MPa', 'mbarg': 'gauge_to_abs_mbar', 'psi': 6894.76, 'bara': 100000.0,
            'in-Hg': 3386.39, 'mm-Hg-vac': -133.322, 'in-Hg-vac': -3386.39
        }
    },
    'TEMPERATURE': {
        'si_base': 'K',
        'units': {'K': 1.0, 'C': 'C_to_K', 'F': 'F_to_K', 'R': 'R_to_K'}
    },
    'TIME': {
        'si_base': 'sec',
        'units': {
            'sec': 1.0, 'hr': 3600.0, 'day': 86400.0, 'min': 60.0, 'year': 31536000.0,
            'month': 2628000.0, 'week': 604800.0, 'nsec': 1e-9, 'oper-year': 28382400.0
        }
    },
    'VELOCITY': {
        'si_base': 'm/sec',
        'units': {
            'm/sec': 1.0, 'ft/sec': 0.3048, 'mile/hr': 0.44704, 'km/hr': 0.277778,
            'ft/min': 0.00508, 'mm/day': 1.15741e-08, 'mm/hr': 2.77778e-07,
            'mm/day30': 1.15741e-08, 'in/day': 2.93995e-07
        }
    },
    'ENTHALPY-FLO': {
        'si_base': 'Watt',
        'units': {
            'Watt': 1.0, 'J/sec': 1.0, 'kW': 1000.0, 'MW': 1000000.0, 'GW': 1000000000.0,
            'kJ/sec': 1000.0, 'Btu/hr': 0.293071, 'cal/sec': 4.184, 'kcal/hr': 1.16222,
            'Gcal/hr': 1162220.0, 'Mcal/hr': 1162.22, 'kJ/hr': 0.277778, 'MJ/hr': 277.778,
            'GJ/hr': 277778.0, 'MMBtu/hr': 293071.0, 'MBtu/hr': 293.071, 'Pcu/hr': 0.293071,
            'MMPcu/hr': 293071.0, 'MMkcal/hr': 1162220.0, 'MMkcal/day': 48342.5,
            'Gcal/day': 48503.7, 'Mcal/day': 48.5037
        }
    },
    'HEAT-TRANS-C': {
        'si_base': 'Watt/sqm-K',
        'units': {
            'Watt/sqm-K': 1.0, 'Btu/hr-sqft-R': 5.67826, 'Btu/hr-sqft-F': 5.67826,
            'cal/sec-sqcm-K': 41840.0, 'kcal/sec-sqm-K': 4184.0, 'kcal/hr-sqm-K': 1.16222,
            'kcal/hr-sqm-C': 1.16222, 'kW/sqm-K': 1000.0, 'MW/sqm-K': 1000000.0,
            'J/sec-sqm-K': 1.0, 'kJ/sec-sqm-K': 1040.0, 'MJ/sec-sqm-K': 1000000.0,
            'kJ/sec-sqm-C': 1000.0, 'MJ/sec-sqm-C': 1000000.0,
            'GJ/hr-sqm-K': 277.778, 'GJ/hr-sqm-C': 277.778,
            'Pcu/hr-sqft-K': 5.67826, 'MMBtu/hr-sqft-R': 5678.26, 'MMBtu/hr-sqft-F': 5678.26
        }
    },
    'UA': {
        'si_base': 'J/sec-K',
        'units': {
            'J/sec-K': 1.0, 'Btu/hr-R': 0.527527, 'cal/sec-K': 4.184, 'kJ/sec-K': 1000.0,
            'kcal/sec-K': 4184.0, 'kcal/hr-K': 1.16222, 'Btu/hr-F': 0.527527,
            'kW/k': 1000.0
        }
    },
    'WORK': {
        'si_base': 'J',
        'units': {
            'J': 1.0, 'hp-hr': 2684520.0, 'kW-hr': 3600000.0, 'ft-lbf': 1.35582,
            'kJ': 1000.0, 'N-m': 1.0, 'MJ': 1000000.0, 'Mbtu': 1055060000.0,
            'MMBtu': 1055060000000.0, 'Mcal': 4184000.0, 'Gcal': 4184000000.0
        }
    },
    'HEAT': {
        'si_base': 'J',
        'units': {
            'J': 1.0, 'Btu': 1055.06, 'cal': 4.184, 'kcal': 4184.0, 'Mmkcal': 4184000000000.0,
            'MMBtu': 1055060000000.0, 'Pcu': 1055.06, 'MMPcu': 1055060000000.0,
            'kJ': 1000.0, 'GJ': 1000000000.0, 'N-m': 1.0, 'MJ': 1000000.0,
            'Mcal': 4184000.0, 'Gcal': 4184000000.0, 'Mbtu': 1055060000.0,
            'kW-hr': 3600000.0
        }
    }
}

# =============================================================================
# 유닛 변환기 클래스
# =============================================================================
class UnitConverter:
    def __init__(self):
        self._unit_data = UNIT_DATA

    def convert_to_si(self, value: float, from_unit: str, unit_type: str) -> tuple[float, str]:
        # None 값 체크
        if value is None or from_unit is None:
            return None, None
            
        unit_type = unit_type.upper()
        from_unit = from_unit.strip()

        if unit_type not in self._unit_data:
            raise ValueError(f"Unsupported unit type: {unit_type}")

        unit_info = self._unit_data[unit_type]
        si_unit = unit_info['si_base']

        if isinstance(unit_info['units'].get(from_unit), str):
            method = unit_info['units'][from_unit]
            if method == 'C_to_K':
                return value + 273.15, si_unit
            elif method == 'F_to_K':
                return (value - 32) * 5/9 + 273.15, si_unit
            elif method == 'R_to_K':
                return value * 5/9, si_unit
            elif method.startswith('gauge_to_abs'):
                abs_value = self._convert_pressure_gauge_to_absolute(value, from_unit)
                base_unit = from_unit.replace('g', '')
                if base_unit not in unit_info['units']:
                     raise ValueError(f"Unsupported gauge base unit: {base_unit}")
                factor = unit_info['units'][base_unit]
                return abs_value * factor, si_unit
            else:
                raise NotImplementedError(f"Special conversion for '{from_unit}' not implemented")

        if from_unit not in unit_info['units']:
            raise ValueError(f"Unsupported unit: '{from_unit}' for type '{unit_type}'")

        factor = unit_info['units'][from_unit]
        converted_value = value * factor
        return converted_value, si_unit

    def _convert_pressure_gauge_to_absolute(self, value: float, from_unit: str) -> float:
        if from_unit.lower() == 'psig': return value + 14.696
        elif from_unit.lower() == 'atmg': return value + 1.0
        elif from_unit.lower() == 'barg': return value + 1.01325
        elif from_unit.lower() == 'pag': return value + 101325.0
        elif from_unit.lower() == 'kpag': return value + 101.325
        elif from_unit.lower() == 'mpag': return value + 0.101325
        elif from_unit.lower() == 'mbarg': return value + 1013.25
        else: return value

    def convert_from_si(self, value_si: float, to_unit: str, unit_type: str) -> float:
        unit_type = unit_type.upper()
        to_unit = to_unit.strip()

        if unit_type not in self._unit_data:
            raise ValueError(f"Unsupported unit type: {unit_type}")

        unit_info = self._unit_data[unit_type]

        if unit_type == 'TEMPERATURE':
            if to_unit == 'K': return value_si
            elif to_unit == 'C': return value_si - 273.15
            elif to_unit == 'F': return (value_si - 273.15) * 9/5 + 32
            elif to_unit == 'R': return value_si * 9/5
            else: raise ValueError(f"Unsupported temperature unit: {to_unit}")

        if to_unit not in unit_info['units']:
            raise ValueError(f"Unsupported unit: '{to_unit}' for type '{unit_type}'")

        factor = unit_info['units'][to_unit]
        if isinstance(factor, str):
            raise NotImplementedError("Conversion from SI to special unit not yet implemented")

        return value_si / factor

_unit_converter = UnitConverter()

def get_unit_converter() -> UnitConverter: return _unit_converter
def convert_to_si_units(value: float, from_unit: str, unit_type: str) -> tuple[float, str]: return _unit_converter.convert_to_si(value, from_unit, unit_type)
def convert_units(value: float, from_unit: str, to_unit: str, unit_type: str) -> Optional[float]:
    """
    일반적인 단위 변환 함수 - 모든 단위 타입에 대해 입력/출력 단위를 자유롭게 지정 가능
    
    Args:
        value: 변환할 값
        from_unit: 입력 단위 (예: 'hp', 'kPa', 'cuft/min')
        to_unit: 출력 단위 (예: 'kW', 'bar', 'm3/s')
        unit_type: 단위 타입 ('POWER', 'PRESSURE', 'VOLUME-FLOW', 'VOLUME', 'AREA' 등)
    
    Returns:
        변환된 값 (단위 오류 시 None)
        
    Examples:
        >>> convert_units(100, 'hp', 'kW', 'POWER')
        74.57
        >>> convert_units(1000, 'kPa', 'bar', 'PRESSURE')
        10.0
        >>> convert_units(1000, 'cuft/min', 'm3/s', 'VOLUME-FLOW')
        0.471947
    """
    if value is None or from_unit is None or to_unit is None:
        return None
    
    try:
        # 먼저 SI 단위로 변환
        si_value, _ = _unit_converter.convert_to_si(value, from_unit, unit_type)
        if si_value is None:
            return None
            
        # SI 단위에서 목표 단위로 변환
        converted_value = _unit_converter.convert_from_si(si_value, to_unit, unit_type)
        return converted_value
        
    except Exception as e:
        print(f"UNIT CONVERSION ERROR ({unit_type}): {e}", file=sys.stderr)
        return None

# 사용 예시 (코드 일관성을 위해 명시적 변환 사용):
#
# 동력 변환:
# power_kw = convert_units(motor_power, 'hp', 'kW', 'POWER')
# shaft_power_hp = convert_units(calculated_power, 'kW', 'hp', 'POWER')
#
# 압력 변환:
# pressure_bar = convert_units(process_pressure, 'barg', 'bar', 'PRESSURE')
# pressure_psi = convert_units(vessel_pressure, 'bar', 'psi', 'PRESSURE')
#
# 유량 변환:
# volumetric_flow = convert_units(pump_flow, 'gal/min', 'm3/s', 'VOLUME-FLOW')
# mass_flow_kg_s = convert_units(stream_mass_flow, 'lb/hr', 'kg/sec', 'MASS-FLOW')
#
# 체적/면적 변환:
# tank_volume_cum = convert_units(design_volume, 'gal', 'cum', 'VOLUME')
# heat_area_sqm = convert_units(heat_transfer_area, 'sqft', 'sqm', 'AREA')
#
# 열전달 계수 변환:
# u_wattsqmk = convert_units(u_value, 'Btu/hr-sqft-F', 'Watt/sqm-K', 'HEAT-TRANS-C')
# u_kcalhrsqmk = convert_units(u_value, 'Watt/sqm-K', 'kcal/hr-sqm-K', 'HEAT-TRANS-C')
#
# 열부하(Heat Duty) 변환:
# heat_duty_watt = convert_units(duty_value, 'Btu/hr', 'Watt', 'ENTHALPY-FLO')
# heat_duty_kw = convert_units(duty_value, 'MMBtu/hr', 'kW', 'ENTHALPY-FLO')
# heat_duty_mw = convert_units(duty_value, 'kcal/hr', 'MW', 'ENTHALPY-FLO')
