"""
Aspen Plus 데이터 추출 및 분류 모듈

이 모듈은 Aspen Plus COM 인터페이스를 통해 데이터를 추출하고,
장치를 카테고리별로 분류하는 기능을 제공합니다.
"""

from typing import Optional, Dict, Any, List, Union
import win32com.client as win32
import os
import sys
import math

import unit_converter
import logger
import config

# =============================================================================
# Aspen COM 통신 및 파일 관리
# =============================================================================

def find_aspen_file(current_dir: str) -> Optional[str]:
    """현재 디렉토리에서 가장 최근에 수정된 .bkp 파일을 찾고 사용자에게 선택을 받습니다."""
    all_bkps = [f for f in os.listdir(current_dir) if f.lower().endswith('.bkp')]
    bkp_files = sorted(all_bkps, key=lambda f: os.path.getmtime(os.path.join(current_dir, f)), reverse=True)

    if not bkp_files:
        print("경고: 현재 폴더에서 .bkp 파일을 찾지 못했습니다.")
        return None

    print("\n감지된 .bkp 파일 목록:")
    for i, fname in enumerate(bkp_files, 1):
        print(f"  {i}. {fname}")

    while True:
        try:
            choice = input("사용할 .bkp 파일 번호를 선택하세요 (숫자): ").strip()
            if not choice:
                return None
            idx = int(choice)
            if 1 <= idx <= len(bkp_files):
                return os.path.join(current_dir, bkp_files[idx - 1])
            else:
                print("잘못된 번호입니다. 다시 입력해주세요.")
        except ValueError:
            print("숫자를 입력해주세요.")

def connect_to_aspen(file_path: str):
    """COM 객체를 통해 Aspen Plus 파일에 연결합니다."""
    try:
        print('\nConnecting to Aspen Plus... Please wait...')
        Application = win32.Dispatch('Apwn.Document')
        Application.InitFromArchive2(file_path)
        Application.visible = 1
        print('Aspen Plus COM object created and file opened successfully!')
        return Application
    except Exception as e:
        print(f"ERROR connecting to Aspen Plus: {e}")
        print("\nPossible solutions:")
        print("1. Make sure Aspen Plus is installed on your computer")
        print("2. Make sure Aspen Plus is properly licensed")
        print("3. Try running Aspen Plus manually first to ensure it works")
        print("4. Check if the .bkp file is compatible with your Aspen Plus version")
        sys.exit(1)

# =============================================================================
# 장치 분류 및 단위 세트 추출
# =============================================================================

def get_block_names(Application) -> List[str]:
    """Blocks 하위의 가장 상위 노드(블록 이름)들을 수집하는 함수"""
    block_names = []
    try:
        blocks_node = Application.Tree.FindNode("\\Data\\Blocks")
        if blocks_node is None:
            print("Warning: Blocks node not found")
            return block_names
        if hasattr(blocks_node, 'Elements') and blocks_node.Elements is not None:
            for element in blocks_node.Elements:
                try:
                    block_names.append(element.Name)
                except:
                    pass
        return block_names
    except Exception as e:
        print(f"Error collecting block names: {str(e)}")
        return []

def parse_bkp_file_for_blocks(file_path: str, block_names: List[str]) -> Dict[str, str]:
    """
    .bkp 파일을 텍스트로 읽어서 주어진 블록 이름들의 카테고리를 파싱하는 함수
    """
    block_info = {}
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        lines = content.split('\n')
        for block_name in block_names:
            category = "Unknown"
            for i, line in enumerate(lines):
                if line.strip() == block_name:
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line in ['Heater', 'HeatX']:
                            category = next_line
                            break
                        elif next_line in ['RadFrac', 'Distl', 'DWSTU']:
                            category = next_line
                            break
                        elif next_line in ['RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield']:
                            category = next_line
                            break
                        elif next_line in ['Pump', 'Compr', 'MCompr', 'Vacuum', 'Flash', 'Sep', 'Mixer', 'FSplit', 'Valve']:
                            category = next_line
                            break
                    break
            block_info[block_name] = category
        return block_info
    except Exception as e:
        print(f"Error parsing BKP file: {str(e)}")
        return {}

def get_current_unit_set(Application) -> Optional[str]:
    """현재 사용 중인 Unit Set을 가져오는 함수"""
    try:
        outset_node = Application.Tree.FindNode("\\Data\\Setup\\Global\\Input\\OUTSET")
        if outset_node is None or outset_node.Value is None:
            return None
        return str(outset_node.Value)
    except Exception:
        return None

def get_unit_type_value(Application, unit_set_name: str, unit_type: str) -> Optional[str]:
    """특정 단위 타입의 값을 반환"""
    try:
        node_path = f"\\Data\\Setup\\Units-Sets\\{unit_set_name}\\Unit-Types\\{unit_type}"
        node = Application.Tree.FindNode(node_path)
        if node is not None and node.Value is not None:
            return str(node.Value)
    except:
        pass
    return None

def get_utility_names(Application) -> List[str]:
    """Utilities 하위의 유틸리티 이름들을 수집하는 함수"""
    utility_names = []
    try:
        utilities_node = Application.Tree.FindNode("\\Data\\Utilities")
        if utilities_node is None:
            print("Warning: Utilities node not found")
            return utility_names
        if hasattr(utilities_node, 'Elements') and utilities_node.Elements is not None:
            for element in utilities_node.Elements:
                try:
                    utility_names.append(element.Name)
                except:
                    pass
        return utility_names
    except Exception as e:
        print(f"Error collecting utility names: {str(e)}")
        return []

def get_utility_data(Application, utility_name: str) -> Dict[str, Any]:
    """특정 유틸리티의 데이터를 추출하는 함수"""
    utility_data = {"name": utility_name, "error": None}
    try:
        # 유틸리티 기본 정보 추출
        utility_node = Application.Tree.FindNode(f"\\Data\\Utilities\\{utility_name}")
        if utility_node is None:
            utility_data["error"] = f"Utility node not found: {utility_name}"
            return utility_data
        
        # Temperature 추출 - 입구온도와 출구온도
        inlet_temp_raw = _read_raw_value(Application, f"\\Data\\Utilities\\{utility_name}\\Output\\UTL_IN_TEMP")
        outlet_temp_raw = _read_raw_value(Application, f"\\Data\\Utilities\\{utility_name}\\Output\\UTL_OUT_TEMP")
        temp_unit = get_unit_type_value(Application, get_current_unit_set(Application), 'TEMPERATURE')
        
        # 지정된 항목(입/출구 온도)만 반환
        utility_data.update({
            "inlet_temperature_value": inlet_temp_raw,
            "outlet_temperature_value": outlet_temp_raw,
            "temperature_unit": temp_unit
        })
        
    except Exception as e:
        utility_data["error"] = str(e)
    return utility_data

def _get_stream_names(Application, block_name: str) -> List[str]:
    """블록에 연결된 모든 스트림 이름을 가져옵니다."""
    stream_names = []
    try:
        connections_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Connections")
        if connections_node and hasattr(connections_node, 'Elements'):
            for element in connections_node.Elements:
                try:
                    stream_names.append(element.Name)
                except:
                    pass
    except Exception:
        pass
    return stream_names

def _get_stream_temperatures(Application, block_name: str, temperature_unit: str) -> Dict[str, float]:
    """블록에 연결된 스트림들의 입구/출구 온도를 추출합니다."""
    stream_data = {}
    stream_names = _get_stream_names(Application, block_name)
    
    for stream_name in stream_names:
        # 스트림 온도 추출 (RES_TEMP 노드 사용)
        temp_raw = _read_raw_value(Application, f"\\Data\\Streams\\{stream_name}\\Output\\RES_TEMP")
        if temp_raw is not None:
            stream_data[stream_name] = temp_raw
    
    return stream_data

def _get_inlet_outlet_streams(Application, block_name: str) -> (Optional[str], Optional[str]):
    """Connections 하위에서 각 스트림의 IN/OUT 라벨을 읽어 입구/출구 스트림명을 반환합니다."""
    inlet_name = None
    outlet_name = None
    try:
        connections_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Connections")
        if not connections_node or not hasattr(connections_node, 'Elements'):
            return None, None
        for element in connections_node.Elements:
            try:
                stream_name = element.Name
                role_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Connections\\{stream_name}")
                role_val = str(role_node.Value).upper() if role_node and role_node.Value is not None else ''
                # 예: "F(IN)", "P(OUT)" 등 → IN/OUT 판단
                if 'IN' in role_val and inlet_name is None:
                    inlet_name = stream_name
                elif 'OUT' in role_val and outlet_name is None:
                    outlet_name = stream_name
            except:
                continue
    except Exception:
        return None, None
    return inlet_name, outlet_name

def _find_heater_utility(Application, block_name: str) -> Optional[str]:
    """Heater 블록에서 사용 중인 유틸리티 이름을 UTL_ID 노드에서 읽어옵니다."""
    try:
        utl_id_path = f"\\Data\\Blocks\\{block_name}\\Output\\UTL_ID"
        node = Application.Tree.FindNode(utl_id_path)
        if node is None or node.Value is None:
            return None
        value = str(node.Value).strip()
        return value if value != '' else None
    except Exception:
        return None

def _find_intercooler_utility(Application, block_name: str, stage_num: int) -> Optional[str]:
    """다단 압축기 블록의 특정 스테이지에서 사용하는 인터쿨러 유틸리티 이름을 찾습니다."""
    try:
        cooler_utl_path = f"\\Data\\Blocks\\{block_name}\\Input\\COOLER_UTL\\{stage_num}"
        node = Application.Tree.FindNode(cooler_utl_path)
        if node is None or node.Value is None:
            return None
        value = str(node.Value).strip()
        return value if value != '' else None
    except Exception:
        return None


def _calculate_lmtd_for_heater(Application, block_name: str, temperature_unit: str) -> Optional[float]:
    """Heater에서 스트림 온도와 유틸리티 온도를 기반으로 LMTD를 계산합니다."""
    try:
        # 스트림 온도 추출
        stream_temps = _get_stream_temperatures(Application, block_name, temperature_unit)
        
        if len(stream_temps) < 2:
            return None  # 입구/출구 스트림이 모두 필요
        
        # Connections 라벨 기반으로 입구/출구 스트림 결정
        inlet_name, outlet_name = _get_inlet_outlet_streams(Application, block_name)
        if not inlet_name or not outlet_name:
            return None
        t1_raw = stream_temps.get(inlet_name)
        t2_raw = stream_temps.get(outlet_name)
        
        if t1_raw is None or t2_raw is None:
            return None
        
        # 온도를 SI 단위로 변환 (K)
        t1_k = unit_converter.convert_units(t1_raw, temperature_unit, 'K', 'TEMPERATURE')
        t2_k = unit_converter.convert_units(t2_raw, temperature_unit, 'K', 'TEMPERATURE')
        
        if t1_k is None or t2_k is None:
            return None
        
        # 온도 차가 너무 작으면 LMTD 계산이 불가능
        if abs(t2_k - t1_k) < 0.1:  # 0.1K 미만
            return None
        
        # Heater와 연결된 유틸리티 찾기 및 온도 확보
        heater_utility = _find_heater_utility(Application, block_name)
        if not heater_utility:
            return None

        utility_data = get_utility_data(Application, heater_utility)
        utility_inlet_temp = utility_data.get("inlet_temperature_value")
        utility_outlet_temp = utility_data.get("outlet_temperature_value")
        utility_temp_unit = utility_data.get("temperature_unit")
        if utility_inlet_temp is None or utility_outlet_temp is None or not utility_temp_unit:
            return None

        utility_inlet_k = unit_converter.convert_units(utility_inlet_temp, utility_temp_unit, 'K', 'TEMPERATURE')
        utility_outlet_k = unit_converter.convert_units(utility_outlet_temp, utility_temp_unit, 'K', 'TEMPERATURE')
        if utility_inlet_k is None or utility_outlet_k is None:
            return None

        # 라벨링: 유틸리티가 냉각(Hot utility: 온도 하강)인지 가열(Cold utility: 온도 상승)인지 판단
        # hot_utility: utility_inlet_k > utility_outlet_k
        is_hot_utility = utility_inlet_k > utility_outlet_k

        # 프로세스 스트림 평균/유틸리티 평균 비교로 hot/cold side 최종 결정 (대향류 가정)
        process_avg_k = 0.5 * (t1_k + t2_k)
        utility_avg_k = 0.5 * (utility_inlet_k + utility_outlet_k)

        if is_hot_utility:
            # 유틸리티가 hot side, 프로세스가 cold side (Heater 일반 케이스)
            hot_in, hot_out = utility_inlet_k, utility_outlet_k
            cold_in, cold_out = t1_k, t2_k
        else:
            # 유틸리티가 cold side, 프로세스가 hot side 이어야 일관
            # 프로세스가 실제로 가열(상승) 중이면 Heater 맥락과 불일치 → 계산 불가 처리
            if t2_k > t1_k:
                
                return None
            hot_in, hot_out = t1_k, t2_k
            cold_in, cold_out = utility_inlet_k, utility_outlet_k

        # 대향류(counter-current) LMTD 계산
        # ΔT1 = Th,i - Tc,o, ΔT2 = Th,o - Tc,i
        delta_t1 = hot_in - cold_out
        delta_t2 = hot_out - cold_in
        if delta_t1 <= 0 or delta_t2 <= 0:
            return None
            
        if delta_t1 == delta_t2:
            lmtd_k = delta_t1
        else:
            lmtd_k = (delta_t2 - delta_t1) / math.log(delta_t2 / delta_t1)

        # LMTD는 물리적으로 양수여야 함
        if lmtd_k <= 0:
            return None
        
        # LMTD는 온도차이이므로 K 단위로 반환 (절대온도 변환 금지)
        return lmtd_k
        
    except Exception as e:
        print(f"Error calculating LMTD for {block_name}: {e}", file=sys.stderr)
        return None

# =============================================================================
# 데이터 추출 및 캐싱
# =============================================================================

class AspenDataCache:
    """Aspen Plus 데이터 캐싱 클래스"""
    def __init__(self):
        self._cache = {}

    def get_data(self, key: str, extract_func, *args, **kwargs) -> Any:
        """캐시에서 데이터를 가져오거나, 없으면 추출 후 저장합니다."""
        if key not in self._cache:
            self._cache[key] = extract_func(*args, **kwargs)
        return self._cache[key]

    def clear(self):
        """캐시 초기화"""
        self._cache.clear()

_aspen_cache = AspenDataCache()

def clear_aspen_cache():
    _aspen_cache.clear()

def get_cache_stats() -> Dict[str, int]:
    return {"cached_items": len(_aspen_cache._cache)}

def _read_raw_value(Application, node_path: str) -> Optional[float]:
    """Aspen 노드에서 원시값만 읽어 반환합니다. 단위 변환은 수행하지 않습니다."""
    try:
        node = Application.Tree.FindNode(node_path)
        if node is None or node.Value is None:
            return None
        
        # 값이 빈 문자열이거나 None인 경우 처리
        raw_value = node.Value
        if raw_value is None or str(raw_value).strip() == '':
            return None
            
        return float(raw_value)
    except Exception as e:
        print(f"Error reading node {node_path}: {e}", file=sys.stderr)
        return None

def _read_vessel_data(Application, block_name: str, pressure_unit: str, volume_unit: str, volumetric_flow_unit: str) -> Dict[str, any]:
    """용기(Vessel)의 압력과 부피 유량을 추출합니다."""
    extracted_data = {'max_pressure_value': None, 'max_pressure_unit': pressure_unit, 'max_flow_value': None, 'max_flow_unit': volumetric_flow_unit}
    stream_names = _get_stream_names(Application, block_name)
    
    max_pressure = -1.0
    max_flow = -1.0
    
    for stream_name in stream_names:
        pressure_path = f"\\Data\\Blocks\\{block_name}\\Stream Results\\Table\\Pressure {pressure_unit} {stream_name}"
        flow_path = f"\\Data\\Blocks\\{block_name}\\Stream Results\\Table\\Volume Flow {volumetric_flow_unit} {stream_name}"

        pressure_raw = _read_raw_value(Application, pressure_path)
        flow_raw = _read_raw_value(Application, flow_path)

        if pressure_raw is not None and pressure_raw > max_pressure:
            max_pressure = pressure_raw
        if flow_raw is not None and flow_raw > max_flow:
            max_flow = flow_raw
    
    if max_pressure >= 0:
        extracted_data['max_pressure_value'] = max_pressure
    if max_flow >= 0:
        extracted_data['max_flow_value'] = max_flow
        
    return extracted_data

def _extract_mcompr_stage_data(Application, block_name: str, power_unit: Optional[str], pressure_unit: Optional[str], heat_unit: Optional[str], temperature_unit: Optional[str]) -> Dict[int, Dict[str, Optional[float]]]:
    """MCompr 블록의 단계별 데이터를 추출하는 함수"""
    stage_data = {}
    try:
        bpres_node = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Output\\B_PRES")
        if not bpres_node or not hasattr(bpres_node, 'Elements'):
            return {}
        
        stage_numbers = sorted([int(elem.Name) for elem in bpres_node.Elements if elem.Name.isdigit()])
        
        for stage_num in stage_numbers:
            pressure_path = f"\\Data\\Blocks\\{block_name}\\Output\\B_PRES\\{stage_num}"
            power_path = f"\\Data\\Blocks\\{block_name}\\Output\\BRAKE_POWER\\{stage_num}"
            temp_path = f"\\Data\\Blocks\\{block_name}\\Output\\B_TEMP\\{stage_num}"
            cool_temp_path = f"\\Data\\Blocks\\{block_name}\\Output\\COOL_TEMP\\{stage_num}"
            q_calc_path = f"\\Data\\Blocks\\{block_name}\\Output\\QCALC\\{stage_num}"
            
            pressure_raw = _aspen_cache.get_data(f"pressure_{block_name}_{stage_num}", _read_raw_value, Application, pressure_path)
            power_raw = _aspen_cache.get_data(f"power_{block_name}_{stage_num}", _read_raw_value, Application, power_path)
            temp_raw = _aspen_cache.get_data(f"temp_{block_name}_{stage_num}", _read_raw_value, Application, temp_path)
            cool_temp_raw = _aspen_cache.get_data(f"cool_temp_{block_name}_{stage_num}", _read_raw_value, Application, cool_temp_path)
            q_calc_raw = _aspen_cache.get_data(f"q_calc_{block_name}_{stage_num}", _read_raw_value, Application, q_calc_path)

            # 인터쿨러 LMTD 계산 (Heater와 동일한 방식)
            intercooler_lmtd = None
            try:
                if temp_raw is not None and cool_temp_raw is not None and temperature_unit:
                    # 인터쿨러 유틸리티 찾기
                    cooler_utility = _find_intercooler_utility(Application, block_name, stage_num)
                    if cooler_utility:
                        # 유틸리티 온도 데이터 가져오기
                        utility_data = get_utility_data(Application, cooler_utility)
                        utility_inlet_temp = utility_data.get("inlet_temperature_value")
                        utility_outlet_temp = utility_data.get("outlet_temperature_value")
                        utility_temp_unit = utility_data.get("temperature_unit")
                        
                        if utility_inlet_temp is not None and utility_outlet_temp is not None and utility_temp_unit:
                            # 온도를 SI 단위로 변환 (K)
                            T_h_in = unit_converter.convert_units(temp_raw, temperature_unit, 'K', 'TEMPERATURE')
                            T_h_out = unit_converter.convert_units(cool_temp_raw, temperature_unit, 'K', 'TEMPERATURE')
                            T_c_in = unit_converter.convert_units(utility_inlet_temp, utility_temp_unit, 'K', 'TEMPERATURE')
                            T_c_out = unit_converter.convert_units(utility_outlet_temp, utility_temp_unit, 'K', 'TEMPERATURE')
                            
                            if T_h_in is not None and T_h_out is not None and T_c_in is not None and T_c_out is not None:
                                # 온도 차가 너무 작으면 LMTD 계산이 불가능
                                if abs(T_h_out - T_h_in) >= 0.1:  # 0.1K 이상
                                    # 대향류(counter-current) LMTD 계산
                                    # ΔT1 = Th,i - Tc,o, ΔT2 = Th,o - Tc,i
                                    delta_t1 = T_h_in - T_c_out
                                    delta_t2 = T_h_out - T_c_in
                                    
                                    if delta_t1 > 0 and delta_t2 > 0:
                                        if delta_t1 == delta_t2:
                                            intercooler_lmtd = delta_t1
                                        else:
                                            intercooler_lmtd = (delta_t2 - delta_t1) / math.log(delta_t2 / delta_t1)
            except Exception as e:
                intercooler_lmtd = None

            stage_data[stage_num] = {
                'pressure_value': pressure_raw,
                'pressure_unit': pressure_unit,
                'power_value': power_raw,
                'power_unit': power_unit,
                'temp_value': temp_raw,
                'temp_unit': temperature_unit,
                'cool_temp_value': cool_temp_raw,
                'cool_temp_unit': temperature_unit,
                'q_value': q_calc_raw,
                'q_unit': heat_unit,
                'intercooler_lmtd': intercooler_lmtd
            }
    except Exception as e:
        print(f"Error extracting MCompr stage data for {block_name}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {}
    return stage_data

# =============================================================================
# 통합 데이터 추출 (프리뷰 및 계산용)
# =============================================================================

def extract_all_device_data(Application, block_info: Dict[str, str], unit_set_name: str) -> List[Dict]:
    """
    모든 장치 데이터를 한 번에 추출하고 표준화된 딕셔너리 리스트로 반환합니다.
    이 함수는 Aspen COM 객체에 직접 접근하는 유일한 인터페이스 역할을 합니다.
    """
    all_devices_data = []
    
    # 단위 세트 정보 추출
    power_unit = get_unit_type_value(Application, unit_set_name, 'POWER')
    pressure_unit = get_unit_type_value(Application, unit_set_name, 'PRESSURE')
    volume_unit = get_unit_type_value(Application, unit_set_name, 'VOLUME')
    volumetric_flow_unit = get_unit_type_value(Application, unit_set_name, 'VOLUME-FLOW')
    heat_unit = get_unit_type_value(Application, unit_set_name, 'ENTHALPY-FLO')
    heat_transfer_coeff_unit = get_unit_type_value(Application, unit_set_name, 'HEAT-TRANS-C')
    temperature_unit = get_unit_type_value(Application, unit_set_name, 'TEMPERATURE')
    
    for name, cat in block_info.items():
        if cat in ('Pump', 'Compr', 'MCompr', 'Heater', 'HeatX', 'RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield', 'Flash', 'Sep', 'RadFrac', 'Distl', 'DWSTU'):
            try:
                device_data = _extract_device_data(Application, name, cat, power_unit, pressure_unit, volumetric_flow_unit, heat_unit, heat_transfer_coeff_unit, temperature_unit, volume_unit)
                all_devices_data.append(device_data)
            except Exception as e:
                print(f"Debug: Failed to extract data for {name} ({cat}): {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                all_devices_data.append({"name": name, "category": cat, "error": f"Data extraction failed: {e}"})
        elif cat == 'Unknown':
            # Unknown 장치들은 추가 정보 없이 처리 불가능
            all_devices_data.append({
                "name": name, 
                "category": "Unknown", 
                "error": "Block type could not be classified - manual input required"
            })
        elif cat in ('Valve', 'Mixer', 'FSplit'):
            all_devices_data.append({"name": name, "category": "Ignored", "error": "Device type ignored (Valve/Mixer/Splitter)"})
        else:
            all_devices_data.append({"name": name, "category": "Ignored", "error": "Unsupported device type"})
    
        
    return all_devices_data

def extract_all_utility_data(Application) -> List[Dict[str, Any]]:
    """
    모든 유틸리티 데이터를 추출합니다.
    """
    utilities_data = []
    utility_names = get_utility_names(Application)
    
    for utility_name in utility_names:
        utility_data = get_utility_data(Application, utility_name)
        utilities_data.append({
            "name": utility_name,  # UTILITY_ 접두사 제거
            "category": "Utility",
            "utility_data": utility_data
        })
        
    return utilities_data


def _extract_device_data(Application, name: str, cat: str, power_unit: str, pressure_unit: str, volumetric_flow_unit: str, heat_unit: str, heat_transfer_coeff_unit: str, temperature_unit: str, volume_unit: str) -> Dict[str, Any]:
    """단일 장치의 데이터를 추출하고 표준화합니다."""
    device = {"name": name, "category": cat, "error": None}
    
    try:
        if cat == 'MCompr':
            stage_data = _extract_mcompr_stage_data(Application, name, power_unit, pressure_unit, heat_unit, temperature_unit)
            device.update({
                "stage_data": stage_data,
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "multi-stage compressor",
                "selected_subtype": "centrifugal",
                "notes": "Cost calculated by summing individual stages and intercoolers."
            })
        
        elif cat in ('Pump', 'Compr'):
            power_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\WNET")
            in_pres_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\IN_PRES")
            out_pres_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\POC")
            
            # 팬 판정을 위해 임시로 변환하여 사용 (나중에 cost_calculator에서 제대로 처리)
            # 팬 판정에서만 단위 변환 수행
            temp_power_kw = power_raw
            temp_in_pres_bar = unit_converter.convert_units(in_pres_raw, pressure_unit, 'bar', 'PRESSURE') if in_pres_raw is not None and pressure_unit else in_pres_raw
            temp_out_pres_bar = unit_converter.convert_units(out_pres_raw, pressure_unit, 'bar', 'PRESSURE') if out_pres_raw is not None and pressure_unit else out_pres_raw
            
            if cat == 'Pump':
                temp_pressure_delta = temp_in_pres_bar
                temp_in_pres_bar = temp_out_pres_bar - temp_pressure_delta if temp_out_pres_bar is not None and temp_pressure_delta is not None else None
            else:
                temp_pressure_delta = temp_out_pres_bar - temp_in_pres_bar if temp_in_pres_bar is not None and temp_out_pres_bar is not None else None
            
            vol_flow_raw = None
            if _suggest_pressure_device_type(cat, temp_in_pres_bar, temp_out_pres_bar) == 'fan':
                vol_flow_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\FEED_VFLOW")
            
            device.update({
                "power_value": power_raw,
                "power_unit": power_unit,
                "inlet_pressure_value": in_pres_raw,
                "inlet_pressure_unit": pressure_unit,
                "outlet_pressure_value": out_pres_raw,
                "outlet_pressure_unit": pressure_unit,
                "pressure_drop_value": temp_pressure_delta,
                "pressure_drop_unit": pressure_unit,
                "volumetric_flow_value": vol_flow_raw,
                "volumetric_flow_unit": volumetric_flow_unit,
                "operating_pressure_value": out_pres_raw,  # 펌프의 작업 압력으로 배압 사용
                "operating_pressure_unit": pressure_unit,
                "material": config.DEFAULT_MATERIAL,
                "selected_type": _suggest_pressure_device_type(cat, temp_in_pres_bar, temp_out_pres_bar),
                "selected_subtype": _get_default_subtype(_suggest_pressure_device_type(cat, temp_in_pres_bar, temp_out_pres_bar)),
            })
            
        elif cat in ('Heater', 'HeatX'):
            # 열교환기 데이터 추출
            u_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Input\\U")
            
            # Heat duty 노드는 블록 타입에 따라 다름
            if cat == 'Heater':
                q_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\QNET")
                # Heater의 경우 계산된 LMTD만 사용
                calculated_lmtd = _calculate_lmtd_for_heater(Application, name, temperature_unit)
                if calculated_lmtd is None:
                    device["error"] = f"Heater LMTD calculation failed - insufficient temperature data"
                    return device
                lmtd_raw = calculated_lmtd
                
                # Heater의 경우 U값이 없으면 기본값 사용
                if u_raw is None:
                    u_raw = 850.0  # W/m²·K (Heater 기본 열전달 계수)
            else:  # HeatX
                q_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\HX_DUTY")
                lmtd_raw = _read_raw_value(Application, f"\\Data\\Blocks\\{name}\\Output\\HX_DTLM")

            # 열교환기 기본 타입 설정 (사용자가 나중에 오버라이드로 변경 가능)
            heat_exchanger_type = "fixed_tube"  # 기본값: 고정관 열교환기
            
            # heat duty가 None인 경우 적절한 메시지 설정
            if q_raw is None:
                device["error"] = "Heat duty calculation failed or device has no heat exchange (possibly bypass condition)"
                return device
            
            device.update({
                "heat_duty_value": q_raw,
                "heat_duty_unit": heat_unit,
                "heat_transfer_coefficient_value": u_raw,
                "heat_transfer_coefficient_unit": heat_transfer_coeff_unit,
                "log_mean_temp_difference_value": lmtd_raw,
                "log_mean_temp_difference_unit": "K",
                "log_mean_temp_difference_unit_type": "DELTA-T",
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "heat_exchanger",
                "selected_subtype": heat_exchanger_type,
                "shell_material": config.DEFAULT_MATERIAL,
                "tube_material": config.DEFAULT_MATERIAL,
            })
            
        elif cat in ('RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield'):
            v_data = _read_vessel_data(Application, name, pressure_unit, volume_unit, volumetric_flow_unit)
            
            device.update({
                "volume_value": None,  # 체적 계산은 cost_calculator에서 수행
                "volume_unit": volume_unit,
                "operating_pressure_value": v_data['max_pressure_value'],
                "operating_pressure_unit": v_data['max_pressure_unit'],
                "mass_flow_value": v_data['max_flow_value'],
                "mass_flow_unit": v_data['max_flow_unit'],
                "residence_time_hours_value": 2.0,  # 체류시간 설정값 전달
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "reactor",
                "selected_subtype": "autoclave",
            })
        
        elif cat in ('Flash', 'Sep'):
            v_data = _read_vessel_data(Application, name, pressure_unit, volume_unit, volumetric_flow_unit)
            
            device.update({
                "volume_value": None,  # 체적 계산은 cost_calculator에서 수행
                "volume_unit": volume_unit,
                "operating_pressure_value": v_data['max_pressure_value'],
                "operating_pressure_unit": v_data['max_pressure_unit'],
                "mass_flow_value": v_data['max_flow_value'],
                "mass_flow_unit": v_data['max_flow_unit'],
                "residence_time_minutes_value": 5.0,  # 체류시간 설정값 전달
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "vessel",
                "selected_subtype": "vertical",
            })
        
        elif cat in ('RadFrac', 'Distl', 'DWSTU'):
            # 증류탑들을 별도 카테고리로 분류 (비용 계산 로직은 추후 구현 예정)
            device.update({
                "volume_value": None,  # 추후 구현 예정
                "volume_unit": "N/A",
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "distillation_column",
                "selected_subtype": "tray_column",  # 기본값
                "notes": f"Distillation column ({cat}) - cost calculation logic to be implemented",
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        device["error"] = str(e)
    return device


def _suggest_pressure_device_type(category: str, inlet_bar: Optional[float], outlet_bar: Optional[float]) -> str:
    """압력 조건에 따라 장치 유형(펌프/압축기/팬/터빈)을 제안합니다."""
    if category == 'Pump':
        return 'pump'
    if inlet_bar is not None and outlet_bar is not None:
        if inlet_bar > outlet_bar:
            if inlet_bar - outlet_bar >= config.TURBINE_MIN_PRESSURE_DROP:
                return 'turbine'
        else:
            if outlet_bar - inlet_bar <= config.FAN_MAX_PRESSURE_RISE:
                return 'fan'
            else:
                return 'compressor'
    return 'compressor'

def _get_default_subtype(device_type: str) -> str:
    """장치 유형에 따른 기본 세부 타입을 반환합니다."""
    if device_type == 'pump': return 'centrifugal'
    elif device_type == 'compressor': return 'centrifugal'
    elif device_type == 'fan': return 'centrifugal_radial'
    elif device_type == 'turbine': return 'axial'
    elif device_type == 'heat_exchanger': return 'fixed_tube'
    elif device_type == 'vessel': return 'vertical'
    elif device_type == 'reactor': return 'autoclave'
    else: return 'unknown'