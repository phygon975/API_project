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
                        if next_line in ['Heater', 'Cooler', 'HeatX', 'Condenser']:
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

def _read_and_convert(Application, node_path: str, unit_type: str, aspen_unit: Optional[str]) -> Optional[float]:
    """Aspen 노드에서 값을 읽어와 SI 단위로 변환합니다."""
    try:
        node = Application.Tree.FindNode(node_path)
        if node is None or node.Value is None:
            return None
        
        # 값이 빈 문자열이거나 None인 경우 처리
        raw_value = node.Value
        if raw_value is None or str(raw_value).strip() == '':
            return None
            
        raw_value = float(raw_value)
        
        # 단위가 None인 경우 그대로 반환 (이미 SI 단위일 가능성)
        if aspen_unit is None:
            return raw_value
            
        return unit_converter.convert_to_si_units(raw_value, aspen_unit, unit_type)[0]
    except Exception as e:
        print(f"Error reading node {node_path}: {e}", file=sys.stderr)
        return None

def _read_vessel_data(Application, block_name: str, pressure_unit: str, volume_unit: str, flow_unit: str) -> Dict[str, float]:
    """용기(Vessel)의 압력과 부피 유량을 추출합니다."""
    extracted_data = {'max_pressure_si': None, 'max_flow_si': None}
    stream_names = _get_stream_names(Application, block_name)
    
    max_pressure = -1.0
    max_flow = -1.0
    
    for stream_name in stream_names:
        pressure_path = f"\\Data\\Blocks\\{block_name}\\Stream Results\\Table\\Pressure {pressure_unit} {stream_name}"
        flow_path = f"\\Data\\Blocks\\{block_name}\\Stream Results\\Table\\Volume Flow {flow_unit} {stream_name}"

        pressure_si = _read_and_convert(Application, pressure_path, "PRESSURE", pressure_unit)
        flow_si = _read_and_convert(Application, flow_path, "VOLUME-FLOW", flow_unit)

        if pressure_si is not None and pressure_si > max_pressure:
            max_pressure = pressure_si
        if flow_si is not None and flow_si > max_flow:
            max_flow = flow_si
    
    if max_pressure >= 0:
        extracted_data['max_pressure_si'] = max_pressure
    if max_flow >= 0:
        extracted_data['max_flow_si'] = max_flow
        
    return extracted_data

def _extract_mcompr_stage_data(Application, block_name: str, power_unit: Optional[str], pressure_unit: Optional[str], heat_unit: Optional[str]) -> Dict[int, Dict[str, Optional[float]]]:
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
            
            pressure_si = _aspen_cache.get_data(f"pressure_{block_name}_{stage_num}", _read_and_convert, Application, pressure_path, "PRESSURE", pressure_unit)
            power_si = _aspen_cache.get_data(f"power_{block_name}_{stage_num}", _read_and_convert, Application, power_path, "POWER", power_unit)
            temp_si = _aspen_cache.get_data(f"temp_{block_name}_{stage_num}", _read_and_convert, Application, temp_path, "TEMPERATURE", None)
            cool_temp_si = _aspen_cache.get_data(f"cool_temp_{block_name}_{stage_num}", _read_and_convert, Application, cool_temp_path, "TEMPERATURE", None)
            q_calc_si = _aspen_cache.get_data(f"q_calc_{block_name}_{stage_num}", _read_and_convert, Application, q_calc_path, "HEAT", heat_unit)

            stage_data[stage_num] = {
                'outlet_pressure_bar': unit_converter.convert_pressure_to_bar(pressure_si, 'N/sqm') if pressure_si is not None else None,
                'power_kilowatt': unit_converter.convert_power_to_kw(power_si, 'Watt') if power_si is not None else None,
                'B_TEMP_K': temp_si,
                'COOL_TEMP_K': cool_temp_si,
                'q_watt': unit_converter.convert_to_si_units(q_calc_si, heat_unit, 'HEAT')[0] if q_calc_si is not None else None
            }
    except Exception as e:
        print(f"Error extracting MCompr stage data for {block_name}: {e}", file=sys.stderr)
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
    flow_unit = get_unit_type_value(Application, unit_set_name, 'VOLUME-FLOW')
    heat_unit = get_unit_type_value(Application, unit_set_name, 'HEAT')
    
    for name, cat in block_info.items():
        if cat in ('Pump', 'Compr', 'MCompr', 'Heater', 'Cooler', 'HeatX', 'Condenser', 'RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield', 'Flash', 'Sep', 'RadFrac', 'Distl', 'DWSTU'):
            device_data = _extract_device_data(Application, name, cat, power_unit, pressure_unit, flow_unit, heat_unit, volume_unit)
            all_devices_data.append(device_data)
        elif cat in ('Valve', 'Mixer', 'FSplit'):
            all_devices_data.append({"name": name, "category": "Ignored", "error": "Device type ignored (Valve/Mixer/Splitter)"})
        else:
            all_devices_data.append({"name": name, "category": "Ignored", "error": "Unsupported device type"})
        
    return all_devices_data


def _extract_device_data(Application, name: str, cat: str, power_unit: str, pressure_unit: str, flow_unit: str, heat_unit: str, volume_unit: str) -> Dict[str, Any]:
    """단일 장치의 데이터를 추출하고 표준화합니다."""
    device = {"name": name, "category": cat, "error": None}
    
    try:
        if cat == 'MCompr':
            stage_data = _extract_mcompr_stage_data(Application, name, power_unit, pressure_unit, heat_unit)
            total_power_kw = sum(s['power_kilowatt'] for s in stage_data.values() if s['power_kilowatt'] is not None)
            
            device.update({
                "size_value": total_power_kw,
                "size_unit": "kW",
                "stage_data": stage_data,
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "multi-stage compressor",
                "selected_subtype": "centrifugal",
                "notes": "Cost calculated by summing individual stages and intercoolers."
            })
        
        elif cat in ('Pump', 'Compr'):
            power_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Output\\WNET", "POWER", power_unit)
            power_kw = unit_converter.convert_power_to_kw(power_si, 'Watt')
            
            in_pres_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Output\\IN_PRES", "PRESSURE", pressure_unit)
            out_pres_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Output\\POC", "PRESSURE", pressure_unit)
            
            in_pres_bar = unit_converter.convert_pressure_to_bar(in_pres_si, 'N/sqm')
            out_pres_bar = unit_converter.convert_pressure_to_bar(out_pres_si, 'N/sqm')
            
            if cat == 'Pump':
                pressure_delta_bar = in_pres_bar
                in_pres_bar = out_pres_bar - pressure_delta_bar if out_pres_bar is not None and pressure_delta_bar is not None else None
            else:
                pressure_delta_bar = out_pres_bar - in_pres_bar if in_pres_bar is not None and out_pres_bar is not None else None
            
            vol_flow_m3_s = None
            if _suggest_pressure_device_type(cat, in_pres_bar, out_pres_bar) == 'fan':
                vol_flow_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Output\\FEED_VFLOW", "VOLUME-FLOW", flow_unit)
                vol_flow_m3_s = unit_converter.convert_flow_to_m3_s(vol_flow_si, 'cum/sec')
            
            device.update({
                "size_value": power_kw,
                "size_unit": "kW",
                "power_kilowatt": power_kw,
                "inlet_bar": in_pres_bar,
                "outlet_bar": out_pres_bar,
                "pressure_delta_bar": pressure_delta_bar,
                "volumetric_flow_m3_s": vol_flow_m3_s,
                "material": config.DEFAULT_MATERIAL,
                "selected_type": _suggest_pressure_device_type(cat, in_pres_bar, out_pres_bar),
                "selected_subtype": _get_default_subtype(_suggest_pressure_device_type(cat, in_pres_bar, out_pres_bar)),
            })
            
        elif cat in ('Heater', 'Cooler', 'HeatX', 'Condenser'):
            q_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Output\\HX_DUTY", "HEAT", heat_unit)
            u_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Input\\U", "UA", None)
            lmtd_si = _read_and_convert(Application, f"\\Data\\Blocks\\{name}\\Output\\HX_DTLM", "TEMPERATURE", None)
            
            area_sqm = None
            if q_si is not None and u_si is not None and lmtd_si is not None and u_si != 0 and lmtd_si != 0:
                area_sqm = q_si / (u_si * lmtd_si)
            
            device.update({
                "size_value": area_sqm,
                "size_unit": "sqm",
                "q_watt": q_si,
                "u_w_m2k": u_si,
                "lmtd_k": lmtd_si,
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "heat_exchanger",
                "selected_subtype": "fixed_tube",
                "shell_material": config.DEFAULT_MATERIAL,
                "tube_material": config.DEFAULT_MATERIAL,
            })
            
        elif cat in ('RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield'):
            v_data = _read_vessel_data(Application, name, pressure_unit, volume_unit, flow_unit)
            holdup_time_sec = 2.0 * 3600 # 2시간을 초 단위로
            volume_cum = v_data['max_flow_si'] * holdup_time_sec if v_data['max_flow_si'] is not None else None
            
            device.update({
                "size_value": volume_cum,
                "size_unit": "cum",
                "outlet_bar": unit_converter.convert_pressure_to_bar(v_data['max_pressure_si'], 'N/sqm'),
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "reactor",
                "selected_subtype": "autoclave",
            })
        
        elif cat in ('Flash', 'Sep'):
            v_data = _read_vessel_data(Application, name, pressure_unit, volume_unit, flow_unit)
            holdup_time_sec = 5.0 * 60 # 5분을 초 단위로
            volume_cum = (v_data['max_flow_si'] * holdup_time_sec) if v_data['max_flow_si'] is not None else None
            
            if volume_cum is not None:
                diameter = (4 * volume_cum / (3 * math.pi))**(1/3)
                height = diameter * 3
            else:
                diameter, height = None, None
            
            device.update({
                "size_value": volume_cum,
                "size_unit": "cum",
                "outlet_bar": unit_converter.convert_pressure_to_bar(v_data['max_pressure_si'], 'N/sqm'),
                "diameter": diameter,
                "height_or_length": height,
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "vessel",
                "selected_subtype": "vertical",
            })
        
        elif cat in ('RadFrac', 'Distl', 'DWSTU'):
            # 증류탑들을 별도 카테고리로 분류 (비용 계산 로직은 추후 구현 예정)
            device.update({
                "size_value": None,  # 추후 구현 예정
                "size_unit": "N/A",
                "material": config.DEFAULT_MATERIAL,
                "selected_type": "distillation_column",
                "selected_subtype": "tray_column",  # 기본값
                "notes": f"Distillation column ({cat}) - cost calculation logic to be implemented",
            })

    except Exception as e:
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