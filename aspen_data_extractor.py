"""
Aspen Plus 데이터 추출 모듈

이 모듈은 Aspen Plus COM 인터페이스를 통해 데이터를 추출하는 기능을 제공합니다.
캐싱 기능을 포함하여 COM 호출을 최소화합니다.
"""

from typing import Optional, Dict, Any
import win32com.client


class AspenDataCache:
    """Aspen Plus 데이터 캐싱 클래스"""
    
    def __init__(self):
        self._block_data = {}
        self._unit_data = {}
        self._pressure_data = {}
        self._power_data = {}
        self._flow_data = {}
    
    def get_block_data(self, Application, block_name: str) -> Dict[str, Any]:
        """블록 데이터를 캐싱하여 반환"""
        if block_name not in self._block_data:
            self._block_data[block_name] = self._extract_block_data(Application, block_name)
        return self._block_data[block_name]
    
    def _extract_block_data(self, Application, block_name: str) -> Dict[str, Any]:
        """블록의 모든 출력 데이터 추출"""
        data = {
            'block_name': block_name,
            'available_nodes': {}
        }
        
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
        """전력 데이터 추출: WNET → kW로 변환"""
        try:
            node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\WNET")
            if node is None or node.Value is None:
                return None
            
            raw_value = float(node.Value)
            converted_value = _convert_power_to_kilowatt(raw_value, power_unit)
            
            # 디버깅: 단위 변환 확인
            print(f"POWER DEBUG [{block_name}]: Raw={raw_value}, Unit={power_unit}, Converted={converted_value}")
            
            return converted_value
        except Exception as e:
            print(f"POWER ERROR [{block_name}]: {e}")
            return None

    def _extract_fan_flow(self, Application, block_name: str, flow_unit: Optional[str]) -> Optional[float]:
        """팬 유량(부피유량) 데이터 추출: FEED_VFLOW → m^3/s 로 변환"""
        try:
            node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\FEED_VFLOW")
            if node is None or node.Value is None:
                return None
            return _convert_flow_to_m3_s(float(node.Value), flow_unit)
        except Exception:
            return None
    
    def get_pressure_data(self, Application, block_name: str, pressure_unit: Optional[str], which: str) -> Optional[float]:
        """압력 데이터를 캐싱하여 반환"""
        cache_key = f"{block_name}_{pressure_unit}_{which}"
        if cache_key not in self._pressure_data:
            self._pressure_data[cache_key] = self._extract_pressure_data(Application, block_name, pressure_unit, which)
        return self._pressure_data[cache_key]
    
    def _extract_pressure_data(self, Application, block_name: str, pressure_unit: Optional[str], which: str) -> Optional[float]:
        """압력 데이터 추출: INLET/OUTLET → bar로 변환"""
        try:
            node_path = f"\\Data\\Blocks\\{block_name}\\Output\\{which}"
            node = Application.Tree.FindNode(node_path)
            if node is None or node.Value is None:
                return None
            
            sval = node.Value
            if not sval:
                return None
            
            raw_value = float(sval)
            converted_value = _convert_pressure_to_bar(raw_value, pressure_unit)
            
            # 디버깅: 단위 변환 확인
            print(f"PRESSURE DEBUG [{block_name}_{which}]: Raw={raw_value}, Unit={pressure_unit}, Converted={converted_value}")
                
            return converted_value
            
        except Exception as e:
            print(f"PRESSURE ERROR [{block_name}_{which}]: {e}")
            return None
    
    def get_flow_data(self, Application, block_name: str, flow_unit: Optional[str]) -> Optional[float]:
        """유량 데이터를 캐싱하여 반환"""
        cache_key = f"{block_name}_{flow_unit}"
        if cache_key not in self._flow_data:
            self._flow_data[cache_key] = self._extract_flow_data(Application, block_name, flow_unit)
        return self._flow_data[cache_key]
    
    def _extract_flow_data(self, Application, block_name: str, flow_unit: Optional[str]) -> Optional[float]:
        """유량 데이터 추출: FEED_VFLOW → m³/s로 변환"""
        try:
            node_path = f"\\Data\\Blocks\\{block_name}\\Output\\FEED_VFLOW"
            node = Application.Tree.FindNode(node_path)
            if node is None or node.Value is None:
                return None
            
            sval = node.Value
            if not sval:
                return None
                
            return _convert_flow_to_m3_s(float(sval), flow_unit)
            
        except Exception:
            return None
        """압력 데이터 추출: INLET/OUTLET → bar로 변환"""
        try:
            node_path = f"\\Data\\Blocks\\{block_name}\\Output\\{which}"
            node = Application.Tree.FindNode(node_path)
            if node is None or node.Value is None:
                return None
            
            sval = node.Value
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
        self._flow_data.clear()


# 전역 캐시 인스턴스
_aspen_cache = AspenDataCache()


def get_aspen_cache() -> AspenDataCache:
    """Aspen 캐시 인스턴스 반환"""
    return _aspen_cache


def _convert_power_to_kilowatt(value: float, unit: Optional[str]) -> Optional[float]:
    """전력 단위를 kW로 변환"""
    # 단위가 None이면 기본적으로 Watt로 가정
    if unit is None:
        unit = 'Watt'
    
    # 단위 변환 인수 (kW 기준)
    power_conversion_factors = {
        'Watt': 0.001, 'W': 0.001, 'kW': 1.0, 'MW': 1000.0, 
        'hp': 0.7457, 'Btu/hr': 0.000293071
    }
    
    factor = power_conversion_factors.get(unit)
    if factor is None:
        # 알 수 없는 단위면 기본적으로 Watt로 가정
        factor = 0.001
        print(f"WARNING: Unknown power unit '{unit}', assuming Watt")
    
    return value * factor


def _convert_flow_to_m3_s(value: float, unit: Optional[str]) -> Optional[float]:
    """유량 단위를 m³/s로 변환"""
    if unit is None:
        return value
    
    # 단위 변환 인수 (m³/s 기준)
    flow_conversion_factors = {
        'm3/s': 1.0, 'm^3/s': 1.0, 'm3/h': 1/3600.0, 'm^3/h': 1/3600.0,
        'cum/hr': 1/3600.0, 'cum/h': 1/3600.0, 'Nm3/h': 1/3600.0,
        'L/s': 0.001, 'L/min': 1/60000.0, 'L/h': 1/3600000.0,
        'ft3/s': 0.0283168, 'ft3/min': 0.000471947, 'cfm': 0.000471947,
    }
    
    factor = flow_conversion_factors.get(unit)
    if factor is None:
        return None
    
    return value * factor


def _convert_pressure_to_bar(value: float, unit: Optional[str]) -> Optional[float]:
    """압력 단위를 bar로 변환"""
    # 단위가 None이면 기본적으로 bar로 가정
    if unit is None:
        unit = 'bar'
    
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
        
    # 절대 압력 단위 변환 인수 (bar 기준)
    pressure_conversion_factors = {
        'bar': 1.0, 'bara': 1.0, 'atm': 1.01325, 'Pa': 1e-5, 'kPa': 0.01,
        'MPa': 10.0, 'psi': 0.0689476, 'psia': 0.0689476, 'mmHg': 0.00133322,
        'torr': 0.00133322, 'mbar': 0.001, 'inH2O': 0.00249089, 'inHg': 0.0338639
    }
    
    factor = pressure_conversion_factors.get(unit)
    if factor is None:
        return None
        
    return float(value) * factor


def extract_mcompr_stage_data(
    Application,
    block_name: str,
    power_unit: Optional[str],
    pressure_unit: Optional[str],
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    MCompr 블록의 단계별 데이터 추출
    """
    stage_data = {}
    
    try:
        # 단계 번호 추출
        stage_numbers = []
        bpres_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\B_PRES")
        if bpres_node and hasattr(bpres_node, 'Elements'):
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
            stage_data[stage_num] = {
                'outlet_pressure_bar': pressure_bar,
                'power_kilowatt': None
            }
    
    # 각 단계별 전력 추출
    brake_power_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\BRAKE_POWER")
    if brake_power_node and hasattr(brake_power_node, 'Elements'):
        try:
            elements = brake_power_node.Elements
            for i in range(elements.Count):
                element_name = elements.Item(i).Name
                if element_name.isdigit():
                    stage_num = int(element_name)
                    if stage_num in stage_data:
                        node_path = f"\\Data\\Blocks\\{block_name}\\Output\\BRAKE_POWER\\{stage_num}"
                        node = Application.Tree.FindNode(node_path)
                        
                        if node is not None and node.Value is not None:
                            power_kilowatt = _convert_power_to_kilowatt(float(node.Value), power_unit)
                            stage_data[stage_num]['power_kilowatt'] = power_kilowatt
        except Exception as e:
            # Error reading BRAKE_POWER Elements
            pass
    
    return stage_data


def get_unit_set_info(Application, unit_set_name: str) -> Dict[str, str]:
    """단위 세트의 상세 정보 반환"""
    unit_info = {}
    
    try:
        unit_set_node = Application.Tree.FindNode(f"\\Data\\Units\\{unit_set_name}")
        if unit_set_node and hasattr(unit_set_node, 'Elements'):
            for element in unit_set_node.Elements:
                try:
                    unit_info[element.Name] = element.Value
                except:
                    pass
    except:
        pass
    
    return unit_info


def get_unit_type_value(Application, unit_set_name: str, unit_type: str) -> Optional[str]:
    """특정 단위 타입의 값을 반환"""
    try:
        node_path = f"\\Data\\Units\\{unit_set_name}\\{unit_type}"
        node = Application.Tree.FindNode(node_path)
        if node is not None and node.Value is not None:
            return str(node.Value)
    except:
        pass
    return None
