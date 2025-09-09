"""
Create on Sep 4, 2025

@author: Pyeong-Gon Jung
"""

import os
import win32com.client as win32
import numpy as np
import sys
import time
from threading import Thread
from typing import Optional
from equipment_costs import (
    register_default_correlations,
    CEPCIOptions,
    calculate_pressure_device_costs_auto,
    preview_pressure_devices_auto,
    print_preview_results,
    calculate_pressure_device_costs_with_data,
    clear_aspen_cache,
    get_cache_stats,
    _get_unit_type_value,
)

#======================================================================
# Spinner
#======================================================================
class Spinner:
    """Simple CLI spinner to indicate progress during long-running tasks."""
    def __init__(self, message: str) -> None:
        self.message = message
        self._running = False
        self._thread = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        frames = ['|', '/', '-', '\\']
        idx = 0
        while self._running:
            sys.stdout.write(f"\r{self.message} {frames[idx % len(frames)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            idx += 1

    def stop(self, done_message: Optional[str] = None) -> None:
        if not self._running:
            return
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        sys.stdout.write('\r')
        if done_message:
            print(done_message)
        else:
            print('')

#======================================================================
# Aspen Plus Connection
#======================================================================
file = 'MIX_HEFA_20250716_after_HI_v1.bkp'  #아스펜 파일이 바뀔 시 여기를 수정해야 함

    # 2. Get absolute path to Aspen Plus file
current_dir = os.path.dirname(os.path.abspath(__file__))
aspen_Path = os.path.join(current_dir, file)
print(f"Looking for file: {aspen_Path}")

try:
    # 4. Initiate Aspen Plus application
    print('\nConnecting to Aspen Plus... Please wait...')
    connect_spinner = Spinner('Connecting to Aspen Plus')
    connect_spinner.start()
    Application = win32.Dispatch('Apwn.Document') # Registered name of Aspen Plus
    connect_spinner.stop('Aspen Plus COM object created successfully!')
    
    # 5. Try to open the file
    print(f'Attempting to open file: {aspen_Path}')
    open_spinner = Spinner('Opening Aspen backup')
    open_spinner.start()
    Application.InitFromArchive2(aspen_Path)    
    open_spinner.stop('File opened successfully!')
    
    # 6. Make the files visible
    Application.visible = 1   
    print('Aspen Plus is now visible')

except Exception as e:
    print(f"ERROR connecting to Aspen Plus: {e}")
    print("\nPossible solutions:")
    print("1. Make sure Aspen Plus is installed on your computer")
    print("2. Make sure Aspen Plus is properly licensed")
    print("3. Try running Aspen Plus manually first to ensure it works")
    print("4. Check if the .bkp file is compatible with your Aspen Plus version")
    exit()

#======================================================================
# Block Classifier
#======================================================================
def get_block_names(Application):
    """
    Blocks 하위의 가장 상위 노드(블록 이름)들을 수집하는 함수
    """
    block_names = []
    
    try:
        # Blocks 노드 찾기
        blocks_node = Application.Tree.FindNode("\\Data\\Blocks")
        if blocks_node is None:
            print("Warning: Blocks node not found")
            return block_names
        
        # Blocks 하위의 직접적인 자식들만 수집 (가장 상위 노드)
        if hasattr(blocks_node, 'Elements') and blocks_node.Elements is not None:
            for element in blocks_node.Elements:
                try:
                    block_names.append(element.Name)
                except:
                    # 예외 발생 시 조용히 건너뛰기(에러메시지 출력 x)
                    pass
        
        return block_names
        
    except Exception as e:
        print(f"Error collecting block names: {str(e)}")
        return block_names

block_names = get_block_names(Application)
print(block_names)

#======================================================================
#Block Classifier
#======================================================================
def parse_bkp_file_for_blocks(file_path, block_names):
    """
    .bkp 파일을 텍스트로 읽어서 주어진 블록 이름들의 카테고리를 파싱하는 함수
    """
    block_info = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # 각 블록 이름에 대해 카테고리 찾기
        for block_name in block_names:
            category = "Unknown"
            
            # 블록 이름이 있는 줄 찾기
            for i, line in enumerate(lines):
                if line.strip() == block_name:
                    # 다음 4줄에서 카테고리 정보 찾기
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        
                        # 카테고리 후보들
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
                        elif next_line in ['EVAP1', 'EVAP2', 'EVAP3']:
                            category = next_line
                            break
                        elif next_line in ['ABS', 'PSA']:
                            category = next_line
                            break
                        elif next_line in ['COMB']:
                            category = next_line
                            break
                    
                    break  # 블록 이름을 찾았으므로 루프 종료
            
            block_info[block_name] = category
        
        return block_info
        
    except Exception as e:
        print(f"Error parsing BKP file: {str(e)}")
        return {}

def classify_blocks_from_bkp(file_path, block_names):
    """
    .bkp 파일에서 주어진 블록 이름들의 카테고리를 분류하는 함수
    """
    block_info = parse_bkp_file_for_blocks(file_path, block_names)
    
    block_categories = {
        'heat_exchangers': [],
        'distillation_columns': [],
        'reactors': [],
        'pumps and compressors': [],
        'vessels': [],
        'vacuum_systems': [],
        'Ignore': [],
        'other_blocks': []
    }
    
    for block_name, category in block_info.items():
        if category in ['Heater', 'Cooler', 'HeatX', 'Condenser']:
            block_categories['heat_exchangers'].append(block_name)
        elif category in ['RadFrac', 'Distl', 'DWSTU']:
            block_categories['distillation_columns'].append(block_name)
        elif category in ['RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield']:
            block_categories['reactors'].append(block_name)
        elif category in ['Pump', 'Compr', 'MCompr']:
            block_categories['pumps and compressors'].append(block_name)
        elif category in ['Vacuum', 'Flash', 'Sep']:
            block_categories['vessels'].append(block_name)
        elif category in ['Mixer', 'FSplit', 'Valve']:
            block_categories['Ignore'].append(block_name)
        else:
            block_categories['other_blocks'].append(block_name)
    
    return block_categories, block_info

block_categories, block_info = classify_blocks_from_bkp(aspen_Path, block_names)

#======================================================================
# Device Loader Functions
#======================================================================

def get_heat_exchangers(block_categories):
    """
    열교환기 장치들만 반환하는 함수
    """
    return block_categories.get('heat_exchangers', [])

def get_distillation_columns(block_categories):
    """
    증류탑 장치들만 반환하는 함수
    """
    return block_categories.get('distillation_columns', [])

def get_reactors(block_categories):
    """
    반응기 장치들만 반환하는 함수
    """
    return block_categories.get('reactors', [])

def get_pumps_and_compressors(block_categories):
    """
    펌프와 압축기 장치들만 반환하는 함수
    """
    return block_categories.get('pumps and compressors', [])

def get_vessels(block_categories):
    """
    용기 장치들만 반환하는 함수
    """
    return block_categories.get('vessels', [])

def get_ignored_devices(block_categories):
    """
    무시할 장치들만 반환하는 함수
    """
    return block_categories.get('Ignore', [])

def get_other_devices(block_categories):
    """
    기타 장치들만 반환하는 함수
    """
    return block_categories.get('other_blocks', [])

#======================================================================
# Usage Examples
#======================================================================

print("\n" + "="*60)
print("DEVICE CATEGORIES")
print("="*60)

# 열교환기만 가져오기
heat_exchangers = get_heat_exchangers(block_categories)
print(f"\nHeat Exchangers ({len(heat_exchangers)} devices):")
for he in heat_exchangers:
    print(f"  - {he}")

# 증류탑만 가져오기
distillation_columns = get_distillation_columns(block_categories)
print(f"\nDistillation Columns ({len(distillation_columns)} devices):")
for dc in distillation_columns:
    print(f"  - {dc}")

# 반응기만 가져오기
reactors = get_reactors(block_categories)
print(f"\nReactors ({len(reactors)} devices):")
for reactor in reactors:
    print(f"  - {reactor}")

# 펌프와 압축기만 가져오기
pumps_compressors = get_pumps_and_compressors(block_categories)
print(f"\nPumps and Compressors ({len(pumps_compressors)} devices):")
for pc in pumps_compressors:
    print(f"  - {pc}")

# 용기만 가져오기
vessels = get_vessels(block_categories)
print(f"\nVessels ({len(vessels)} devices):")
for vessel in vessels:
    print(f"  - {vessel}")

# 무시할 장치들만 가져오기
ignored_devices = get_ignored_devices(block_categories)
print(f"\nIgnored Devices ({len(ignored_devices)} devices):")
for ignored in ignored_devices:
    print(f"  - {ignored}")

# 기타 장치들만 가져오기
other_devices = get_other_devices(block_categories)
print(f"\nOther Devices ({len(other_devices)} devices):")
for other in other_devices:
    print(f"  - {other}")

print(f"\n" + "="*60)
print("DEVICE LOADING COMPLETED")
print("="*60)
    

#======================================================================
# Unit detection
#======================================================================


def get_units_sets(Application):
    """
    Aspen Plus에서 사용된 단위 세트들을 가져오는 함수
    """
    units_sets = []
    
    try:
        # Units-Sets 노드 찾기
        units_sets_node = Application.Tree.FindNode("\\Data\\Setup\\Units-Sets")
        if units_sets_node is None:
            return units_sets
        
        # Units-Sets 하위의 직접적인 자식들 수집
        if hasattr(units_sets_node, 'Elements') and units_sets_node.Elements is not None:
            for element in units_sets_node.Elements:
                try:
                    # 'Current'는 제외하고 실제 unit set 이름들만 수집
                    if element.Name != 'Current':
                        units_sets.append(element.Name)
                except:
                    # 예외 발생 시 조용히 건너뛰기
                    pass
        
    except Exception as e:
        # 조용히 실패
        pass
    
    return units_sets

def get_current_unit_set(Application):
    """
    현재 사용 중인 Unit Set을 가져오는 함수
    
    Parameters:
    -----------
    Application : Aspen Plus COM object
        Aspen Plus 애플리케이션 객체
    
    Returns:
    --------
    str or None : 현재 사용 중인 Unit Set 이름
    """
    try:
        # OUTSET 노드에서 현재 사용 중인 Unit Set 가져오기
        outset_node = Application.Tree.FindNode("\\Data\\Setup\\Global\\Input\\OUTSET")
        
        if outset_node is None:
            print("Warning: OUTSET node not found")
            return None
        
        current_unit_set = outset_node.Value
        
        if current_unit_set:
            print(f"Current unit set: {current_unit_set}")
            return current_unit_set
        else:
            print("Warning: No current unit set found")
            return None
            
    except Exception as e:
        print(f"Error getting current unit set: {str(e)}")
        return None


# 사용하지 않는 함수 제거됨

def get_unit_set_details(Application, unit_set_name, unit_table):
    """
    특정 단위 세트의 상세 정보를 가져오고 하드코딩된 데이터와 연동하는 함수
    """
    # 필요한 unit_type들과 해당 인덱스 매핑
    required_unit_types = {
        'AREA': 1, 'COMPOSITION': 2, 'DENSITY': 3, 'ENERGY': 5, 'FLOW': 9,
        'MASS-FLOW': 10, 'MOLE-FLOW': 11, 'VOLUME-FLOW': 12, 'MASS': 18,
        'POWER': 19, 'PRESSURE': 20, 'TEMPERATURE': 22, 'TIME': 24,
        'VELOCITY': 25, 'VOLUME': 27, 'MOLE-DENSITY': 37, 'MASS-DENSITY': 38,
        'MOLE-VOLUME': 43, 'ELEC-POWER': 47, 'UA': 50, 'WORK': 52, 'HEAT': 53
    }
    
    unit_details = {
        'name': unit_set_name,
        'unit_types': {},
        'index_mapping': required_unit_types
    }
    
    try:
        # 각 unit_type에 대해 정보 가져오기
        for unit_type, aspen_index in required_unit_types.items():
            try:
                # Unit-Types 노드에서 해당 unit_type 찾기
                unit_type_node = Application.Tree.FindNode(f"\\Data\\Setup\\Units-Sets\\{unit_set_name}\\Unit-Types\\{unit_type}")
                if unit_type_node:
                    # 단위 값 가져오기
                    unit_value = unit_type_node.Value
                    
                    # 하드코딩된 데이터에서 해당 unit_type의 Physical Quantity 인덱스 찾기
                    physical_quantity_index = get_physical_quantity_by_unit_type(unit_table, unit_type)
                    
                    # 하드코딩된 데이터에서 해당 unit의 Unit of Measure 인덱스 찾기
                    unit_of_measure_index = None
                    if physical_quantity_index and physical_quantity_index in unit_table:
                        for unit_idx, hardcoded_unit in unit_table[physical_quantity_index]['units'].items():
                            if hardcoded_unit == unit_value:
                                unit_of_measure_index = unit_idx
                                break
                    
                    unit_details['unit_types'][unit_type] = {
                        'value': unit_value,
                        'aspen_index': aspen_index,
                        'csv_column_index': physical_quantity_index,
                        'unit_index_in_csv': unit_of_measure_index,
                        'data_available': physical_quantity_index is not None
                    }
                else:
                    # 노드를 찾을 수 없는 경우
                    physical_quantity_index = get_physical_quantity_by_unit_type(unit_table, unit_type)
                    unit_details['unit_types'][unit_type] = {
                        'value': 'Not Found in Aspen',
                        'aspen_index': aspen_index,
                        'csv_column_index': physical_quantity_index,
                        'unit_index_in_csv': None,
                        'data_available': physical_quantity_index is not None
                    }
            except Exception as e:
                # 예외 발생 시
                physical_quantity_index = get_physical_quantity_by_unit_type(unit_table, unit_type)
                unit_details['unit_types'][unit_type] = {
                    'value': f'Error: {str(e)}',
                    'aspen_index': aspen_index,
                    'csv_column_index': physical_quantity_index,
                    'unit_index_in_csv': None,
                    'data_available': physical_quantity_index is not None
                }
                
    except Exception as e:
        print(f"Warning: Could not get details for unit set '{unit_set_name}': {e}")
    
    return unit_details

def print_unit_set_details(unit_details):
    """
    단위 세트 상세 정보를 Physical Quantity와 Unit of Measure로 출력하는 함수
    """
    print(f"\nUnit Set: {unit_details['name']}")
    print("-" * 100)
    
    if unit_details['unit_types']:
        print(f"{'Unit Type':<20} {'Physical Quantity':<18} {'Value':<20} {'Unit of Measure':<15} {'Data Available':<15}")
        print("-" * 100)
        
        for unit_type, info in unit_details['unit_types'].items():
            csv_idx = info['unit_index_in_csv'] if info['unit_index_in_csv'] is not None else 'N/A'
            data_avail = 'Yes' if info['data_available'] else 'No'
            print(f"{unit_type:<20} {info['aspen_index']:<18} {info['value']:<20} {csv_idx:<15} {data_avail:<15}")
    else:
        print("  No unit types found")

def get_unit_by_indices(unit_table, physical_quantity_index, unit_of_measure_index):
    """
    Physical Quantity 인덱스와 Unit of Measure 인덱스로 unit 값을 가져오는 함수
    """
    return get_unit_by_index(unit_table, physical_quantity_index, unit_of_measure_index)

def get_available_units_for_type(unit_table, unit_type_name):
    """
    특정 unit_type의 모든 사용 가능한 unit들을 가져오는 함수
    """
    physical_quantity_index = get_physical_quantity_by_unit_type(unit_table, unit_type_name)
    if physical_quantity_index:
        return get_units_by_physical_quantity(unit_table, physical_quantity_index)
    return {}

def print_units_sets_summary(units_sets):
    """
    단위 세트 요약 정보를 출력하는 함수
    """
    print("\n" + "="*60)
    print("UNITS SETS SUMMARY")
    print("="*60)
    
    if not units_sets:
        print("No unit sets found")
        return
    
    print(f"Total unit sets found: {len(units_sets)}")
    print("\nUnit sets:")
    for i, unit_set in enumerate(units_sets, 1):
        print(f"  {i:2d}. {unit_set}")
    
    print("="*60)

# 사용하지 않는 함수 제거됨

# 사용하지 않는 함수 제거됨

# 사용하지 않는 함수 제거됨

#======================================================================
# Hardcoded Unit Data (for CSV-free operation)
#======================================================================

def get_hardcoded_unit_table():
    """
    CSV 파일 없이도 작동하도록 하드코딩된 단위 테이블을 반환하는 함수
    Unit_table.csv의 내용을 기반으로 함
    """
    # CSV 열 순서에 따른 unit_type 매핑 (1부터 시작)
    csv_column_to_unit_type = {
        1: 'AREA',           # sqm
        2: 'COMPOSITION',    # mol-fr
        3: 'DENSITY',        # kg/cum
        4: 'ENERGY',         # J
        5: 'FLOW',           # kg/sec
        6: 'MASS-FLOW',      # kg/sec
        7: 'MOLE-FLOW',      # kmol/sec
        8: 'VOLUME-FLOW',    # cum/sec
        9: 'MASS',           # kg
        10: 'POWER',         # Watt
        11: 'PRESSURE',      # N/sqm
        12: 'TEMPERATURE',   # K
        13: 'TIME',          # sec
        14: 'VELOCITY',      # m/sec
        15: 'VOLUME',        # cum
        16: 'MOLE-DENSITY',  # kmol/cum
        17: 'MASS-DENSITY',  # kg/cum
        18: 'MOLE-VOLUME',   # cum/kmol
        19: 'ELEC-POWER',    # Watt
        20: 'UA',            # J/sec-K
        21: 'WORK',          # J
        22: 'HEAT'           # J
    }
    
    # 하드코딩된 단위 데이터 (Unit_table.csv의 전체 내용)
    hardcoded_units = {
        1: {1: 'sqm', 2: 'sqft', 3: 'sqm', 4: 'sqcm', 5: 'sqin', 6: 'sqmile', 7: 'sqmm', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # AREA
        2: {1: 'mol-fr', 2: 'mol-fr', 3: 'mol-fr', 4: 'mass-fr', 5: '', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # COMPOSITION
        3: {1: 'kg/cum', 2: 'lb/cuft', 3: 'gm/cc', 4: 'lb/gal', 5: 'gm/cum', 6: 'gm/ml', 7: 'lb/bbl', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # DENSITY
        4: {1: 'J', 2: 'Btu', 3: 'cal', 4: 'kcal', 5: 'kWhr', 6: 'ft-lbf', 7: 'GJ', 8: 'kJ', 9: 'N-m', 10: 'MJ', 11: 'Mcal', 12: 'Gcal', 13: 'Mbtu', 14: 'MMBtu', 15: 'hp-hr', 16: 'MMkcal', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # ENERGY
        5: {1: 'kg/sec', 2: 'lb/hr', 3: 'kg/hr', 4: 'lb/sec', 5: 'Mlb/hr', 6: 'tons/day', 7: 'Mcfh', 8: 'tonne/hr', 9: 'lb/day', 10: 'kg/day', 11: 'tons/hr', 12: 'kg/min', 13: 'kg/year', 14: 'gm/min', 15: 'gm/hr', 16: 'gm/day', 17: 'Mgm/hr', 18: 'Ggm/hr', 19: 'Mgm/day', 20: 'Ggm/day', 21: 'lb/min', 22: 'MMlb/hr', 23: 'Mlb/day', 24: 'MMlb/day', 25: 'lb/year', 26: 'Mlb/year', 27: 'MMIb/year', 28: 'tons/min', 29: 'Mtons/year', 30: 'MMtons/year', 31: 'L-tons/min', 32: 'L-tons/hr', 33: 'L-tons/day', 34: 'ML-tons/year', 35: 'MML-tons/year', 36: 'ktonne/year', 37: 'kg/oper-year', 38: 'lb/oper-year', 39: 'Mlb/oper-year', 40: 'MIMIb/oper-year', 41: 'Mtons/oper-year', 42: 'MMtons/oper-year', 43: 'ML-tons/oper-year', 44: 'MML-tons/oper-year', 45: 'ktonne/oper-year', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # FLOW
        6: {1: 'kg/sec', 2: 'lb/hr', 3: 'kg/hr', 4: 'lb/sec', 5: 'Mlb/hr', 6: 'tons/day', 7: 'gm/sec', 8: 'tonne/hr', 9: 'lb/day', 10: 'kg/day', 11: 'tons/year', 12: 'tons/hr', 13: 'tonne/day', 14: 'tonne/year', 15: 'kg/min', 16: 'kg/year', 17: 'gm/min', 18: 'gm/hr', 19: 'gm/day', 20: 'Mgm/hr', 21: 'Ggm/hr', 22: 'Mgm/day', 23: 'Ggm/day', 24: 'lb/min', 25: 'MMlb/hr', 26: 'Mlb/day', 27: 'MMlb/day', 28: 'lb/year', 29: 'Mlb/year', 30: 'MMlb/year', 31: 'tons/min', 32: 'Mtons/year', 33: 'MMtons/year', 34: 'L-tons/min', 35: 'L-tons/hr', 36: 'L-tons/day', 37: 'ML-tons/year', 38: 'MML-tons/year', 39: 'ktonne/year', 40: 'tons/oper-year', 41: 'tonne/oper-year', 42: 'kg/oper-year', 43: 'lb/oper-year', 44: 'Mlb/oper-year', 45: 'MMlb/oper-year', 46: 'Mtons/oper-year', 47: 'MMtons/oper-year', 48: 'ML-tons/oper-year', 49: 'MML-tons/oper-year', 50: 'ktonne/oper-year', 51: ''},  # MASS-FLOW
        7: {1: 'kmol/sec', 2: 'lbmol/hr', 3: 'kmol/hr', 4: 'MMscfh', 5: 'MMscmh', 6: 'mol/sec', 7: 'lbmol/sec', 8: 'scmh', 9: 'bmol/day', 10: 'kmol/day', 11: 'MMscfd', 12: 'Mlscfd', 13: 'scfm', 14: 'mol/min', 15: 'kmol/khr', 16: 'kmol/Mhr', 17: 'mol/hr', 18: 'Mmol/hr', 19: 'Mlbmol/hr', 20: 'lbmol/Mhr', 21: 'lbmol/MMhr', 22: 'Mscfm', 23: 'scfh', 24: 'scfd', 25: 'ncmh', 26: 'ncmd', 27: 'ACFM', 28: 'kmol/min', 29: 'kmol/week', 30: 'kmol/month', 31: 'kmol/year', 32: 'kmol/oper-year', 33: 'lbmol/min', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MOLE-FLOW
        8: {1: 'cum/sec', 2: 'cuft/hr', 3: 'l/min', 4: 'gal/min', 5: 'gal/hr', 6: 'bbl/day', 7: 'cum/hr', 8: 'cuft/min', 9: 'bbl/hr', 10: 'cuft/sec', 11: 'cum/day', 12: 'cum/year', 13: 'l/hr', 14: 'kbbl/day', 15: 'MMcuft/hr', 16: 'MMcuft/day', 17: 'Mcuft/day', 18: 'l/sec', 19: 'l/day', 20: 'cum/min', 21: 'kcum/sec', 22: 'kcum/hr', 23: 'kcum/day', 24: 'Mcum/sec', 25: 'Mcum/hr', 26: 'Mcum/day', 27: 'ACFM', 28: 'cuft/day', 29: 'Mcuft/min', 30: 'Mcuft/hr', 31: 'MMcuft/hr', 32: 'Mgal/min', 33: 'MMgal/min', 34: 'Mgal/hr', 35: 'MMgal/hr', 36: 'Mbbl/hr', 37: 'MMbbl/hr', 38: 'Mbbl/day', 39: 'MMbbl/day', 40: 'cum/oper-year', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # VOLUME-FLOW
        9: {1: 'kg', 2: 'lb', 3: 'kg', 4: 'gm', 5: 'ton', 6: 'Mlb', 7: 'tonne', 8: 'L-ton', 9: 'MMlb', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MASS
        10: {1: 'Watt', 2: 'hp', 3: 'kW', 4: 'Btu/hr', 5: 'cal/sec', 6: 'ft-lbf/sec', 7: 'MIW', 8: 'GW', 9: 'MJ/hr', 10: 'kcal/hr', 11: 'Gcal/hr', 12: 'MMBtu/hr', 13: 'MBtu/hr', 14: 'Mhp', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # POWER
        11: {1: 'N/sqm', 2: 'PsIa', 3: 'atm', 4: 'lbf/sqft', 5: 'bar', 6: 'torr', 7: 'in-water', 8: 'kg/sqcm', 9: 'mmHg', 10: 'kPa', 11: 'mm-water', 12: 'mbar', 13: 'psig', 14: 'atmg', 15: 'barg', 16: 'kg/sqcmg', 17: 'lb/ft-sqsec', 18: 'kg/m-sqsec', 19: 'pa', 20: 'MiPa', 21: 'Pag', 22: 'kPag', 23: 'MPag', 24: 'mbarg', 25: 'in-Hg', 26: 'mmHg-vac', 27: 'in-Hg-vac', 28: 'in-water-60F', 29: 'in-water-vac', 30: 'in-water-60F-vac', 31: 'in-water-g', 32: 'in-water-60F-g', 33: 'mm-water-g', 34: 'mm-water-60F-g', 35: 'psi', 36: 'mm-water-60F', 37: 'bara', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # PRESSURE
        12: {1: 'K', 2: 'F', 3: 'K', 4: 'C', 5: 'R', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # TEMPERATURE
        13: {1: 'sec', 2: 'hr', 3: 'hr', 4: 'day', 5: 'min', 6: 'year', 7: 'month', 8: 'week', 9: 'nsec', 10: 'oper-year', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # TIME
        14: {1: 'm/sec', 2: 'ft/sec', 3: 'm/sec', 4: 'mile/hr', 5: 'km/hr', 6: 'ft/min', 7: 'mm/day', 8: 'mm/hr', 9: 'mm/day30', 10: 'in/day', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # VELOCITY
        15: {1: 'cum', 2: 'cuft', 3: 'l', 4: 'cuin', 5: 'gal', 6: 'bbl', 7: 'cc', 8: 'kcum', 9: 'Mcum', 10: 'Mcuft', 11: 'MMcuft', 12: 'ml', 13: 'kl', 14: 'MMl', 15: 'Mgal', 16: 'MMgal', 17: 'UKgal', 18: 'MUKgal', 19: 'MMUKgal', 20: 'Mbbl', 21: 'MMbbl', 22: 'kbbl', 23: 'cuyd', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # VOLUME
        16: {1: 'kmol/cum', 2: 'lbmol/cuft', 3: 'mol/cc', 4: 'lbmol/gal', 5: 'mol/l', 6: 'mmol/cc', 7: 'mmol/l', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MOLE-DENSITY
        17: {1: 'kg/cum', 2: 'lb/cuft', 3: 'gm/cc', 4: 'lb/gal', 5: 'gm/cum', 6: 'gm/ml', 7: 'gm/l', 8: 'mg/l', 9: 'mg/cc', 10: 'mg/cum', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MASS-DENSITY
        18: {1: 'cum/kmol', 2: 'cuft/lbmol', 3: 'cc/mol', 4: 'ml/mol', 5: 'bbl/mscf', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MOLE-VOLUME
        19: {1: 'Watt', 2: 'kW', 3: 'kW', 4: 'MW', 5: 'GW', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # ELEC-POWER
        20: {1: 'J/sec-K', 2: 'Btu/hr-R', 3: 'cal/sec-K', 4: 'kJ/sec-K', 5: 'kcal/sec-K', 6: 'kcal/hr-K', 7: 'Btu/hr-F', 8: 'kW/k', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # UA
        21: {1: 'J', 2: 'hp-hr', 3: 'kW-hr', 4: 'ft-lbf', 5: 'kJ', 6: 'N-m', 7: 'MJ', 8: 'Mbtu', 9: 'MMBtu', 10: 'Mcal', 11: 'Gcal', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # WORK
        22: {1: 'J', 2: 'Btu', 3: 'cal', 4: 'kcal', 5: 'Mmkcal', 6: 'MMBtu', 7: 'Pcu', 8: 'MMPcu', 9: 'kJ', 10: 'GJ', 11: 'N-m', 12: 'MJ', 13: 'Mcal', 14: 'Gcal', 15: 'Mbtu', 16: 'kW-hr', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''}  # HEAT
    }
    
    # unit_table 형태로 변환
    unit_table = {}
    for csv_col_idx, unit_type_name in csv_column_to_unit_type.items():
        if csv_col_idx in hardcoded_units:
            unit_table[csv_col_idx] = {
                'unit_type': unit_type_name,
                'units': {idx: unit for idx, unit in hardcoded_units[csv_col_idx].items() if unit.strip()}
            }
    
    return unit_table

#======================================================================
# SI Unit Conversion System
#======================================================================

def get_si_base_units():
    """
    각 물리량별 SI 기준 단위를 정의하는 함수
    """
    si_base_units = {
        'AREA': 'sqm',           # 제곱미터
        'COMPOSITION': 'mol-fr', # 몰분율 (무차원)
        'DENSITY': 'kg/cum',     # kg/m³
        'ENERGY': 'J',           # 줄
        'FLOW': 'kg/sec',        # kg/s
        'MASS-FLOW': 'kg/sec',   # kg/s
        'MOLE-FLOW': 'kmol/sec', # kmol/s
        'VOLUME-FLOW': 'cum/sec', # m³/s
        'MASS': 'kg',            # 킬로그램
        'POWER': 'Watt',         # 와트
        'PRESSURE': 'N/sqm',     # 파스칼 (N/m²)
        'TEMPERATURE': 'K',      # 켈빈
        'TIME': 'sec',           # 초
        'VELOCITY': 'm/sec',     # m/s
        'VOLUME': 'cum',         # m³
        'MOLE-DENSITY': 'kmol/cum', # kmol/m³
        'MASS-DENSITY': 'kg/cum',   # kg/m³
        'MOLE-VOLUME': 'cum/kmol',  # m³/kmol
        'ELEC-POWER': 'Watt',    # 와트
        'UA': 'J/sec-K',         # J/(s·K)
        'WORK': 'J',             # 줄
        'HEAT': 'J'              # 줄
    }
    return si_base_units

def get_unit_conversion_factors():
    """
    각 단위를 SI 기준 단위로 환산하는 계수를 정의하는 함수
    """
    conversion_factors = {
        # AREA (sqm 기준)
        'sqm': 1.0,
        'sqft': 0.092903,        # 1 sqft = 0.092903 sqm
        'sqcm': 0.0001,          # 1 sqcm = 0.0001 sqm
        'sqin': 0.00064516,      # 1 sqin = 0.00064516 sqm
        'sqmile': 2589988.11,    # 1 sqmile = 2,589,988.11 sqm
        'sqmm': 0.000001,        # 1 sqmm = 0.000001 sqm
        
        # MASS (kg 기준)
        'kg': 1.0,
        'lb': 0.453592,          # 1 lb = 0.453592 kg
        'gm': 0.001,             # 1 gm = 0.001 kg
        'ton': 1000.0,           # 1 ton = 1000 kg
        'Mlb': 453592.0,         # 1 Mlb = 453,592 kg
        'tonne': 1000.0,         # 1 tonne = 1000 kg
        'L-ton': 1016.05,        # 1 L-ton = 1016.05 kg
        'MMlb': 453592000.0,     # 1 MMlb = 453,592,000 kg
        
        # TIME (sec 기준)
        'sec': 1.0,
        'hr': 3600.0,            # 1 hr = 3600 sec
        'day': 86400.0,          # 1 day = 86400 sec
        'min': 60.0,             # 1 min = 60 sec
        'year': 31536000.0,      # 1 year = 31,536,000 sec
        'month': 2628000.0,      # 1 month = 2,628,000 sec
        'week': 604800.0,        # 1 week = 604,800 sec
        'nsec': 1e-9,            # 1 nsec = 1e-9 sec
        'oper-year': 28382400.0, # 1 oper-year = 28,382,400 sec (0.9 * 365 * 24 * 3600)
        
        # TEMPERATURE (K 기준) - 특별 처리 필요
        'K': 1.0,                # 기준 단위
        'C': 'C_to_K',           # 섭씨는 특별 변환 필요
        'F': 'F_to_K',           # 화씨는 특별 변환 필요
        'R': 0.555556,           # 1 R = 5/9 K
        
        # PRESSURE (N/sqm = Pa 기준)
        'N/sqm': 1.0,            # 파스칼
        'PsIa': 6894.76,         # 1 psia = 6894.76 Pa
        'atm': 101325.0,         # 1 atm = 101,325 Pa
        'lbf/sqft': 47.8803,     # 1 lbf/sqft = 47.8803 Pa
        'bar': 100000.0,         # 1 bar = 100,000 Pa
        'torr': 133.322,         # 1 torr = 133.322 Pa
        'in-water': 249.089,     # 1 in-water = 249.089 Pa
        'kg/sqcm': 98066.5,      # 1 kg/sqcm = 98,066.5 Pa
        'mmHg': 133.322,         # 1 mmHg = 133.322 Pa
        'kPa': 1000.0,           # 1 kPa = 1000 Pa
        'mm-water': 9.80665,     # 1 mm-water = 9.80665 Pa
        'mbar': 100.0,           # 1 mbar = 100 Pa
        'psig': 'psig_to_Pa',    # psig는 특별 변환 필요
        'atmg': 'atmg_to_Pa',    # atmg는 특별 변환 필요
        'barg': 'barg_to_Pa',    # barg는 특별 변환 필요
        'pa': 1.0,               # 파스칼 (소문자)
        'MiPa': 1000000.0,       # 1 MPa = 1,000,000 Pa
        'Pag': 'Pag_to_Pa',      # Pag는 특별 변환 필요
        'kPag': 'kPag_to_Pa',    # kPag는 특별 변환 필요
        'MPag': 'MPag_to_Pa',    # MPag는 특별 변환 필요
        'mbarg': 'mbarg_to_Pa',  # mbarg는 특별 변환 필요
        'psi': 6894.76,          # 1 psi = 6894.76 Pa
        'bara': 100000.0,        # 1 bara = 100,000 Pa
        
        # ENERGY (J 기준)
        'J': 1.0,
        'Btu': 1055.06,          # 1 Btu = 1055.06 J
        'cal': 4.184,            # 1 cal = 4.184 J
        'kcal': 4184.0,          # 1 kcal = 4184 J
        'kWhr': 3600000.0,       # 1 kWhr = 3,600,000 J
        'ft-lbf': 1.35582,       # 1 ft-lbf = 1.35582 J
        'GJ': 1000000000.0,      # 1 GJ = 1,000,000,000 J
        'kJ': 1000.0,            # 1 kJ = 1000 J
        'N-m': 1.0,              # 1 N-m = 1 J
        'MJ': 1000000.0,         # 1 MJ = 1,000,000 J
        'Mcal': 4184000.0,       # 1 Mcal = 4,184,000 J
        'Gcal': 4184000000.0,    # 1 Gcal = 4,184,000,000 J
        'Mbtu': 1055060000.0,    # 1 Mbtu = 1,055,060,000 J
        'MMBtu': 1055060000000.0, # 1 MMBtu = 1,055,060,000,000 J
        'hp-hr': 2684520.0,      # 1 hp-hr = 2,684,520 J
        'MMkcal': 4184000000000.0, # 1 MMkcal = 4,184,000,000,000 J
        'Mmkcal': 4184000000000000.0, # 1 Mmkcal = 4,184,000,000,000,000 J
        'Pcu': 1055.06,          # 1 Pcu = 1055.06 J
        'MMPcu': 1055060000000.0, # 1 MMPcu = 1,055,060,000,000 J
        'kW-hr': 3600000.0,      # 1 kW-hr = 3,600,000 J
        
        # POWER (Watt 기준)
        'Watt': 1.0,
        'hp': 745.7,             # 1 hp = 745.7 W
        'kW': 1000.0,            # 1 kW = 1000 W
        'Btu/hr': 0.293071,      # 1 Btu/hr = 0.293071 W
        'cal/sec': 4.184,        # 1 cal/sec = 4.184 W
        'ft-lbf/sec': 1.35582,   # 1 ft-lbf/sec = 1.35582 W
        'MIW': 1000000.0,        # 1 MW = 1,000,000 W
        'GW': 1000000000.0,      # 1 GW = 1,000,000,000 W
        'MJ/hr': 277.778,        # 1 MJ/hr = 277.778 W
        'kcal/hr': 1.16222,      # 1 kcal/hr = 1.16222 W
        'Gcal/hr': 1162220.0,    # 1 Gcal/hr = 1,162,220 W
        'MMBtu/hr': 293071.0,    # 1 MMBtu/hr = 293,071 W
        'MBtu/hr': 293.071,      # 1 MBtu/hr = 293.071 W
        'Mhp': 745700000.0,      # 1 Mhp = 745,700,000 W
        
        # FLOW (kg/sec 기준)
        'kg/sec': 1.0,
        'lb/hr': 0.000125998,    # 1 lb/hr = 0.000125998 kg/sec
        'kg/hr': 0.000277778,    # 1 kg/hr = 0.000277778 kg/sec
        'lb/sec': 0.453592,      # 1 lb/sec = 0.453592 kg/sec
        'Mlb/hr': 125.998,       # 1 Mlb/hr = 125.998 kg/sec
        'tons/day': 0.0115741,   # 1 tons/day = 0.0115741 kg/sec
        'Mcfh': 0.00786579,      # 1 Mcfh = 0.00786579 kg/sec (가정: 공기 밀도)
        'tonne/hr': 0.277778,    # 1 tonne/hr = 0.277778 kg/sec
        'lb/day': 5.24991e-06,   # 1 lb/day = 5.24991e-06 kg/sec
        'kg/day': 1.15741e-05,   # 1 kg/day = 1.15741e-05 kg/sec
        'tons/hr': 0.277778,     # 1 tons/hr = 0.277778 kg/sec
        'kg/min': 0.0166667,     # 1 kg/min = 0.0166667 kg/sec
        'kg/year': 3.17098e-08,  # 1 kg/year = 3.17098e-08 kg/sec
        'gm/min': 1.66667e-05,   # 1 gm/min = 1.66667e-05 kg/sec
        'gm/hr': 2.77778e-07,    # 1 gm/hr = 2.77778e-07 kg/sec
        'gm/day': 1.15741e-08,   # 1 gm/day = 1.15741e-08 kg/sec
        'Mgm/hr': 0.277778,      # 1 Mgm/hr = 0.277778 kg/sec
        'Ggm/hr': 277.778,       # 1 Ggm/hr = 277.778 kg/sec
        'Mgm/day': 0.0115741,    # 1 Mgm/day = 0.0115741 kg/sec
        'Ggm/day': 11.5741,      # 1 Ggm/day = 11.5741 kg/sec
        'lb/min': 0.00755987,    # 1 lb/min = 0.00755987 kg/sec
        'MMlb/hr': 125998.0,     # 1 MMlb/hr = 125,998 kg/sec
        'Mlb/day': 5.24991,      # 1 Mlb/day = 5.24991 kg/sec
        'MMlb/day': 5249.91,     # 1 MMlb/day = 5,249.91 kg/sec
        'lb/year': 1.43833e-08,  # 1 lb/year = 1.43833e-08 kg/sec
        'Mlb/year': 1.43833e-05, # 1 Mlb/year = 1.43833e-05 kg/sec
        'MMIb/year': 0.0143833,  # 1 MMIb/year = 0.0143833 kg/sec
        'tons/min': 16.6667,     # 1 tons/min = 16.6667 kg/sec
        'Mtons/year': 31.7098,   # 1 Mtons/year = 31.7098 kg/sec
        'MMtons/year': 31709.8,  # 1 MMtons/year = 31,709.8 kg/sec
        'L-tons/min': 16.9333,   # 1 L-tons/min = 16.9333 kg/sec
        'L-tons/hr': 0.282222,   # 1 L-tons/hr = 0.282222 kg/sec
        'L-tons/day': 0.0117593, # 1 L-tons/day = 0.0117593 kg/sec
        'ML-tons/year': 32.1507, # 1 ML-tons/year = 32.1507 kg/sec
        'MML-tons/year': 32150.7, # 1 MML-tons/year = 32,150.7 kg/sec
        'ktonne/year': 0.0317098, # 1 ktonne/year = 0.0317098 kg/sec
        'kg/oper-year': 3.52775e-08, # 1 kg/oper-year = 3.52775e-08 kg/sec
        'lb/oper-year': 1.59891e-08, # 1 lb/oper-year = 1.59891e-08 kg/sec
        'Mlb/oper-year': 1.59891e-05, # 1 Mlb/oper-year = 1.59891e-05 kg/sec
        'MIMIb/oper-year': 0.0159891, # 1 MIMIb/oper-year = 0.0159891 kg/sec
        'Mtons/oper-year': 35.2775,   # 1 Mtons/oper-year = 35.2775 kg/sec
        'MMtons/oper-year': 35277.5,  # 1 MMtons/oper-year = 35,277.5 kg/sec
        'ML-tons/oper-year': 35.7230, # 1 ML-tons/oper-year = 35.7230 kg/sec
        'MML-tons/oper-year': 35723.0, # 1 MML-tons/oper-year = 35,723.0 kg/sec
        'ktonne/oper-year': 0.0352775, # 1 ktonne/oper-year = 0.0352775 kg/sec
        'gm/sec': 0.001,         # 1 gm/sec = 0.001 kg/sec
        'tons/year': 0.0317098,  # 1 tons/year = 0.0317098 kg/sec
        'tonne/day': 0.0115741,  # 1 tonne/day = 0.0115741 kg/sec
        'tonne/year': 0.0317098, # 1 tonne/year = 0.0317098 kg/sec
        'tons/oper-year': 0.0352775, # 1 tons/oper-year = 0.0352775 kg/sec
        'tonne/oper-year': 0.0352775, # 1 tonne/oper-year = 0.0352775 kg/sec
        
        # MOLE-FLOW (kmol/sec 기준)
        'kmol/sec': 1.0,
        'lbmol/hr': 0.000125998, # 1 lbmol/hr = 0.000125998 kmol/sec
        'kmol/hr': 0.000277778,  # 1 kmol/hr = 0.000277778 kmol/sec
        'MMscfh': 0.000783986,   # 1 MMscfh = 0.000783986 kmol/sec (표준상태 가정)
        'MMscmh': 0.000022414,   # 1 MMscmh = 0.000022414 kmol/sec (표준상태 가정)
        'mol/sec': 0.001,        # 1 mol/sec = 0.001 kmol/sec
        'lbmol/sec': 0.453592,   # 1 lbmol/sec = 0.453592 kmol/sec
        'scmh': 0.000022414,     # 1 scmh = 0.000022414 kmol/sec
        'bmol/day': 1.15741e-05, # 1 bmol/day = 1.15741e-05 kmol/sec
        'kmol/day': 1.15741e-05, # 1 kmol/day = 1.15741e-05 kmol/sec
        'MMscfd': 0.00000907407, # 1 MMscfd = 0.00000907407 kmol/sec
        'Mlscfd': 0.00000907407, # 1 Mlscfd = 0.00000907407 kmol/sec
        'scfm': 0.000000471947,  # 1 scfm = 0.000000471947 kmol/sec
        'mol/min': 1.66667e-05,  # 1 mol/min = 1.66667e-05 kmol/sec
        'kmol/khr': 0.000277778, # 1 kmol/khr = 0.000277778 kmol/sec
        'kmol/Mhr': 0.277778,    # 1 kmol/Mhr = 0.277778 kmol/sec
        'mol/hr': 2.77778e-07,   # 1 mol/hr = 2.77778e-07 kmol/sec
        'Mmol/hr': 0.277778,     # 1 Mmol/hr = 0.277778 kmol/sec
        'Mlbmol/hr': 0.125998,   # 1 Mlbmol/hr = 0.125998 kmol/sec
        'lbmol/Mhr': 0.125998,   # 1 lbmol/Mhr = 0.125998 kmol/sec
        'lbmol/MMhr': 125.998,   # 1 lbmol/MMhr = 125.998 kmol/sec
        'Mscfm': 0.000471947,    # 1 Mscfm = 0.000471947 kmol/sec
        'scfh': 7.86579e-08,     # 1 scfh = 7.86579e-08 kmol/sec
        'scfd': 3.27741e-09,     # 1 scfd = 3.27741e-09 kmol/sec
        'ncmh': 0.000022414,     # 1 ncmh = 0.000022414 kmol/sec
        'ncmd': 9.33917e-07,     # 1 ncmd = 9.33917e-07 kmol/sec
        'ACFM': 0.000000471947,  # 1 ACFM = 0.000000471947 kmol/sec
        'kmol/min': 0.0166667,   # 1 kmol/min = 0.0166667 kmol/sec
        'kmol/week': 1.65344e-06, # 1 kmol/week = 1.65344e-06 kmol/sec
        'kmol/month': 3.80517e-07, # 1 kmol/month = 3.80517e-07 kmol/sec
        'kmol/year': 3.17098e-08, # 1 kmol/year = 3.17098e-08 kmol/sec
        'kmol/oper-year': 3.52775e-08, # 1 kmol/oper-year = 3.52775e-08 kmol/sec
        'lbmol/min': 0.00755987, # 1 lbmol/min = 0.00755987 kmol/sec
        
        # VOLUME-FLOW (cum/sec 기준)
        'cum/sec': 1.0,
        'cuft/hr': 7.86579e-06,  # 1 cuft/hr = 7.86579e-06 m³/sec
        'l/min': 1.66667e-05,    # 1 l/min = 1.66667e-05 m³/sec
        'gal/min': 6.30902e-05,  # 1 gal/min = 6.30902e-05 m³/sec
        'gal/hr': 1.05150e-06,   # 1 gal/hr = 1.05150e-06 m³/sec
        'bbl/day': 1.84013e-06,  # 1 bbl/day = 1.84013e-06 m³/sec
        'cum/hr': 0.000277778,   # 1 cum/hr = 0.000277778 m³/sec
        'cuft/min': 0.000471947, # 1 cuft/min = 0.000471947 m³/sec
        'bbl/hr': 4.41631e-05,   # 1 bbl/hr = 4.41631e-05 m³/sec
        'cuft/sec': 0.0283168,   # 1 cuft/sec = 0.0283168 m³/sec
        'cum/day': 1.15741e-05,  # 1 cum/day = 1.15741e-05 m³/sec
        'cum/year': 3.17098e-08, # 1 cum/year = 3.17098e-08 m³/sec
        'l/hr': 2.77778e-07,     # 1 l/hr = 2.77778e-07 m³/sec
        'kbbl/day': 0.00184013,  # 1 kbbl/day = 0.00184013 m³/sec
        'MMcuft/hr': 7.86579,    # 1 MMcuft/hr = 7.86579 m³/sec
        'MMcuft/day': 0.327741,  # 1 MMcuft/day = 0.327741 m³/sec
        'Mcuft/day': 0.000327741, # 1 Mcuft/day = 0.000327741 m³/sec
        'l/sec': 0.001,          # 1 l/sec = 0.001 m³/sec
        'l/day': 1.15741e-08,    # 1 l/day = 1.15741e-08 m³/sec
        'cum/min': 0.0166667,    # 1 cum/min = 0.0166667 m³/sec
        'kcum/sec': 1000.0,      # 1 kcum/sec = 1000 m³/sec
        'kcum/hr': 0.277778,     # 1 kcum/hr = 0.277778 m³/sec
        'kcum/day': 0.0115741,   # 1 kcum/day = 0.0115741 m³/sec
        'Mcum/sec': 1000000.0,   # 1 Mcum/sec = 1,000,000 m³/sec
        'Mcum/hr': 277.778,      # 1 Mcum/hr = 277.778 m³/sec
        'Mcum/day': 11.5741,     # 1 Mcum/day = 11.5741 m³/sec
        'cuft/day': 3.27741e-07, # 1 cuft/day = 3.27741e-07 m³/sec
        'Mcuft/min': 0.471947,   # 1 Mcuft/min = 0.471947 m³/sec
        'Mcuft/hr': 0.00786579,  # 1 Mcuft/hr = 0.00786579 m³/sec
        'MMcuft/hr': 7.86579,    # 1 MMcuft/hr = 7.86579 m³/sec
        'Mgal/min': 63.0902,     # 1 Mgal/min = 63.0902 m³/sec
        'MMgal/min': 63090.2,    # 1 MMgal/min = 63,090.2 m³/sec
        'Mgal/hr': 1.05150,      # 1 Mgal/hr = 1.05150 m³/sec
        'MMgal/hr': 1051.50,     # 1 MMgal/hr = 1,051.50 m³/sec
        'Mbbl/hr': 44.1631,      # 1 Mbbl/hr = 44.1631 m³/sec
        'MMbbl/hr': 44163.1,     # 1 MMbbl/hr = 44,163.1 m³/sec
        'Mbbl/day': 1.84013,     # 1 Mbbl/day = 1.84013 m³/sec
        'MMbbl/day': 1840.13,    # 1 MMbbl/day = 1,840.13 m³/sec
        'cum/oper-year': 3.52775e-08, # 1 cum/oper-year = 3.52775e-08 m³/sec
        
        # VOLUME (cum 기준)
        'cum': 1.0,
        'cuft': 0.0283168,       # 1 cuft = 0.0283168 m³
        'l': 0.001,              # 1 l = 0.001 m³
        'cuin': 1.63871e-05,     # 1 cuin = 1.63871e-05 m³
        'gal': 0.00378541,       # 1 gal = 0.00378541 m³
        'bbl': 0.158987,         # 1 bbl = 0.158987 m³
        'cc': 0.000001,          # 1 cc = 0.000001 m³
        'kcum': 1000.0,          # 1 kcum = 1000 m³
        'Mcum': 1000000.0,       # 1 Mcum = 1,000,000 m³
        'Mcuft': 28316.8,        # 1 Mcuft = 28,316.8 m³
        'MMcuft': 28316800.0,    # 1 MMcuft = 28,316,800 m³
        'ml': 0.000001,          # 1 ml = 0.000001 m³
        'kl': 1.0,               # 1 kl = 1 m³
        'MMl': 1000000.0,        # 1 MMl = 1,000,000 m³
        'Mgal': 3785.41,         # 1 Mgal = 3,785.41 m³
        'MMgal': 3785410.0,      # 1 MMgal = 3,785,410 m³
        'UKgal': 0.00454609,     # 1 UKgal = 0.00454609 m³
        'MUKgal': 4546.09,       # 1 MUKgal = 4,546.09 m³
        'MMUKgal': 4546090.0,    # 1 MMUKgal = 4,546,090 m³
        'Mbbl': 158987.0,        # 1 Mbbl = 158,987 m³
        'MMbbl': 158987000.0,    # 1 MMbbl = 158,987,000 m³
        'kbbl': 158.987,         # 1 kbbl = 158.987 m³
        'cuyd': 0.764555,        # 1 cuyd = 0.764555 m³
        
        # VELOCITY (m/sec 기준)
        'm/sec': 1.0,
        'ft/sec': 0.3048,        # 1 ft/sec = 0.3048 m/sec
        'mile/hr': 0.44704,      # 1 mile/hr = 0.44704 m/sec
        'km/hr': 0.277778,       # 1 km/hr = 0.277778 m/sec
        'ft/min': 0.00508,       # 1 ft/min = 0.00508 m/sec
        'mm/day': 1.15741e-08,   # 1 mm/day = 1.15741e-08 m/sec
        'mm/hr': 2.77778e-07,    # 1 mm/hr = 2.77778e-07 m/sec
        'mm/day30': 1.15741e-08, # 1 mm/day30 = 1.15741e-08 m/sec
        'in/day': 2.93995e-07,   # 1 in/day = 2.93995e-07 m/sec
        
        # DENSITY (kg/cum 기준)
        'kg/cum': 1.0,
        'lb/cuft': 16.0185,      # 1 lb/cuft = 16.0185 kg/m³
        'gm/cc': 1000.0,         # 1 gm/cc = 1000 kg/m³
        'lb/gal': 119.826,       # 1 lb/gal = 119.826 kg/m³
        'gm/cum': 0.001,         # 1 gm/cum = 0.001 kg/m³
        'gm/ml': 1000.0,         # 1 gm/ml = 1000 kg/m³
        'lb/bbl': 2.85301,       # 1 lb/bbl = 2.85301 kg/m³
        'gm/l': 1.0,             # 1 gm/l = 1 kg/m³
        'mg/l': 0.001,           # 1 mg/l = 0.001 kg/m³
        'mg/cc': 1.0,            # 1 mg/cc = 1 kg/m³
        'mg/cum': 0.000001,      # 1 mg/cum = 0.000001 kg/m³
        
        # MOLE-DENSITY (kmol/cum 기준)
        'kmol/cum': 1.0,
        'lbmol/cuft': 16.0185,   # 1 lbmol/cuft = 16.0185 kmol/m³
        'mol/cc': 1000.0,        # 1 mol/cc = 1000 kmol/m³
        'lbmol/gal': 119.826,    # 1 lbmol/gal = 119.826 kmol/m³
        'mol/l': 1.0,            # 1 mol/l = 1 kmol/m³
        'mmol/cc': 1.0,          # 1 mmol/cc = 1 kmol/m³
        'mmol/l': 0.001,         # 1 mmol/l = 0.001 kmol/m³
        
        # MASS-DENSITY (kg/cum 기준) - DENSITY와 동일
        'kg/cum': 1.0,
        'lb/cuft': 16.0185,      # 1 lb/cuft = 16.0185 kg/m³
        'gm/cc': 1000.0,         # 1 gm/cc = 1000 kg/m³
        'lb/gal': 119.826,       # 1 lb/gal = 119.826 kg/m³
        'gm/cum': 0.001,         # 1 gm/cum = 0.001 kg/m³
        'gm/ml': 1000.0,         # 1 gm/ml = 1000 kg/m³
        'lb/bbl': 2.85301,       # 1 lb/bbl = 2.85301 kg/m³
        'gm/l': 1.0,             # 1 gm/l = 1 kg/m³
        'mg/l': 0.001,           # 1 mg/l = 0.001 kg/m³
        'mg/cc': 1.0,            # 1 mg/cc = 1 kg/m³
        'mg/cum': 0.000001,      # 1 mg/cum = 0.000001 kg/m³
        
        # MOLE-VOLUME (cum/kmol 기준)
        'cum/kmol': 1.0,
        'cuft/lbmol': 0.0624280, # 1 cuft/lbmol = 0.0624280 m³/kmol
        'cc/mol': 0.001,         # 1 cc/mol = 0.001 m³/kmol
        'ml/mol': 0.001,         # 1 ml/mol = 0.001 m³/kmol
        'bbl/mscf': 0.158987,    # 1 bbl/mscf = 0.158987 m³/kmol
        
        # ELEC-POWER (Watt 기준) - POWER와 동일
        'Watt': 1.0,
        'kW': 1000.0,            # 1 kW = 1000 W
        'MW': 1000000.0,         # 1 MW = 1,000,000 W
        'GW': 1000000000.0,      # 1 GW = 1,000,000,000 W
        
        # UA (J/sec-K 기준)
        'J/sec-K': 1.0,
        'Btu/hr-R': 0.527527,    # 1 Btu/hr-R = 0.527527 J/(s·K)
        'cal/sec-K': 4.184,      # 1 cal/sec-K = 4.184 J/(s·K)
        'kJ/sec-K': 1000.0,      # 1 kJ/sec-K = 1000 J/(s·K)
        'kcal/sec-K': 4184.0,    # 1 kcal/sec-K = 4184 J/(s·K)
        'kcal/hr-K': 1.16222,    # 1 kcal/hr-K = 1.16222 J/(s·K)
        'Btu/hr-F': 0.527527,    # 1 Btu/hr-F = 0.527527 J/(s·K)
        'kW/k': 1000.0,          # 1 kW/k = 1000 J/(s·K)
        
        # WORK (J 기준) - ENERGY와 동일
        'J': 1.0,
        'hp-hr': 2684520.0,      # 1 hp-hr = 2,684,520 J
        'kW-hr': 3600000.0,      # 1 kW-hr = 3,600,000 J
        'ft-lbf': 1.35582,       # 1 ft-lbf = 1.35582 J
        'kJ': 1000.0,            # 1 kJ = 1000 J
        'N-m': 1.0,              # 1 N-m = 1 J
        'MJ': 1000000.0,         # 1 MJ = 1,000,000 J
        'Mbtu': 1055060000.0,    # 1 Mbtu = 1,055,060,000 J
        'MMBtu': 1055060000000.0, # 1 MMBtu = 1,055,060,000,000 J
        'Mcal': 4184000.0,       # 1 Mcal = 4,184,000 J
        'Gcal': 4184000000.0,    # 1 Gcal = 4,184,000,000 J
        
        # HEAT (J 기준) - ENERGY와 동일
        'J': 1.0,
        'Btu': 1055.06,          # 1 Btu = 1055.06 J
        'cal': 4.184,            # 1 cal = 4.184 J
        'kcal': 4184.0,          # 1 kcal = 4184 J
        'Mmkcal': 4184000000000000.0, # 1 Mmkcal = 4,184,000,000,000,000 J
        'MMBtu': 1055060000000.0, # 1 MMBtu = 1,055,060,000,000 J
        'Pcu': 1055.06,          # 1 Pcu = 1055.06 J
        'MMPcu': 1055060000000.0, # 1 MMPcu = 1,055,060,000,000 J
        'kJ': 1000.0,            # 1 kJ = 1000 J
        'GJ': 1000000000.0,      # 1 GJ = 1,000,000,000 J
        'N-m': 1.0,              # 1 N-m = 1 J
        'MJ': 1000000.0,         # 1 MJ = 1,000,000 J
        'Mcal': 4184000.0,       # 1 Mcal = 4,184,000 J
        'Gcal': 4184000000.0,    # 1 Gcal = 4,184,000,000 J
        'Mbtu': 1055060000.0,    # 1 Mbtu = 1,055,060,000 J
        'kW-hr': 3600000.0,      # 1 kW-hr = 3,600,000 J
        
        # COMPOSITION (mol-fr 기준) - 무차원이므로 변환 불필요
        'mol-fr': 1.0,
        'mass-fr': 1.0           # 질량분율도 무차원
    }
    
    return conversion_factors

def convert_temperature_to_kelvin(value, from_unit):
    """
    온도를 켈빈으로 변환하는 특별 함수
    """
    if from_unit == 'K':
        return value
    elif from_unit == 'C':
        return value + 273.15
    elif from_unit == 'F':
        return (value - 32) * 5/9 + 273.15
    elif from_unit == 'R':
        return value * 5/9
    else:
        raise ValueError(f"Unsupported temperature unit: {from_unit}")

def convert_pressure_gauge_to_absolute(value, from_unit):
    """
    게이지 압력을 절대 압력으로 변환하는 특별 함수
    """
    if from_unit == 'psig':
        return value + 14.696  # psig to psia
    elif from_unit == 'atmg':
        return value + 1.0     # atmg to atm
    elif from_unit == 'barg':
        return value + 1.01325 # barg to bar
    elif from_unit == 'Pag':
        return value + 101325.0 # Pag to Pa
    elif from_unit == 'kPag':
        return value + 101.325 # kPag to kPa
    elif from_unit == 'MPag':
        return value + 0.101325 # MPag to MPa
    elif from_unit == 'mbarg':
        return value + 1013.25 # mbarg to mbar
    else:
        return value  # 이미 절대 압력인 경우

def convert_to_si_units(value, from_unit, unit_type):
    """
    통합 단위 환산 함수: 임의의 단위를 SI 기준 단위로 변환
    
    Parameters:
    -----------
    value : float
        변환할 값
    from_unit : str
        원래 단위 (예: 'psig', 'lb/hr', 'F' 등)
    unit_type : str
        물리량 타입 (예: 'PRESSURE', 'MASS-FLOW', 'TEMPERATURE' 등)
    
    Returns:
    --------
    tuple : (converted_value, si_unit)
        변환된 값과 SI 단위
    """
    try:
        # SI 기준 단위 가져오기
        si_base_units = get_si_base_units()
        conversion_factors = get_unit_conversion_factors()
        
        # 단위 타입 검증
        if unit_type not in si_base_units:
            raise ValueError(f"Unsupported unit type: {unit_type}")
        
        si_unit = si_base_units[unit_type]
        
        # 이미 SI 단위인 경우
        if from_unit == si_unit:
            return value, si_unit
        
        # 특별 변환이 필요한 경우들
        if unit_type == 'TEMPERATURE':
            # 온도는 특별 변환 함수 사용
            converted_value = convert_temperature_to_kelvin(value, from_unit)
            return converted_value, si_unit
        
        elif unit_type == 'PRESSURE':
            # 압력의 경우 게이지 압력 처리
            if from_unit in ['psig', 'atmg', 'barg', 'Pag', 'kPag', 'MPag', 'mbarg']:
                # 게이지 압력을 절대 압력으로 변환
                abs_value = convert_pressure_gauge_to_absolute(value, from_unit)
                # 절대 압력 단위로 변환
                if from_unit == 'psig':
                    from_unit = 'PsIa'  # psia로 변환
                elif from_unit == 'atmg':
                    from_unit = 'atm'
                elif from_unit == 'barg':
                    from_unit = 'bar'
                elif from_unit == 'Pag':
                    from_unit = 'pa'
                elif from_unit == 'kPag':
                    from_unit = 'kPa'
                elif from_unit == 'MPag':
                    from_unit = 'MiPa'
                elif from_unit == 'mbarg':
                    from_unit = 'mbar'
                value = abs_value
            
            # 환산 계수 확인
            if from_unit not in conversion_factors:
                raise ValueError(f"Unsupported pressure unit: {from_unit}")
            
            factor = conversion_factors[from_unit]
            if isinstance(factor, str):
                raise ValueError(f"Special conversion required for {from_unit}, but not implemented")
            
            converted_value = value * factor
            return converted_value, si_unit
        
        else:
            # 일반적인 단위 변환
            if from_unit not in conversion_factors:
                raise ValueError(f"Unsupported unit: {from_unit}")
            
            factor = conversion_factors[from_unit]
            if isinstance(factor, str):
                raise ValueError(f"Special conversion required for {from_unit}, but not implemented")
            
            converted_value = value * factor
            return converted_value, si_unit
            
    except Exception as e:
        raise ValueError(f"Unit conversion error: {str(e)}")

def convert_multiple_values_to_si(values_dict, units_dict, unit_types_dict):
    """
    여러 값들을 한 번에 SI 단위로 변환하는 함수
    
    Parameters:
    -----------
    values_dict : dict
        변환할 값들의 딕셔너리 {parameter_name: value}
    units_dict : dict
        각 값의 단위 딕셔너리 {parameter_name: unit}
    unit_types_dict : dict
        각 값의 물리량 타입 딕셔너리 {parameter_name: unit_type}
    
    Returns:
    --------
    dict : {parameter_name: (converted_value, si_unit)}
    """
    converted_results = {}
    
    for param_name, value in values_dict.items():
        if param_name in units_dict and param_name in unit_types_dict:
            try:
                from_unit = units_dict[param_name]
                unit_type = unit_types_dict[param_name]
                converted_value, si_unit = convert_to_si_units(value, from_unit, unit_type)
                converted_results[param_name] = (converted_value, si_unit)
            except Exception as e:
                print(f"Warning: Failed to convert {param_name}: {str(e)}")
                converted_results[param_name] = (value, units_dict[param_name])
        else:
            print(f"Warning: Missing unit information for {param_name}")
            converted_results[param_name] = (value, "unknown")
    
    return converted_results



#======================================================================
# Unit Table Functions
#======================================================================

def get_unit_by_index(unit_table, physical_quantity_index, unit_of_measure_index):
    """
    특정 Physical Quantity 인덱스와 Unit of Measure 인덱스로 unit 값을 가져오는 함수
    """
    if physical_quantity_index in unit_table and unit_of_measure_index in unit_table[physical_quantity_index]['units']:
        return unit_table[physical_quantity_index]['units'][unit_of_measure_index]
    return None

def get_units_by_physical_quantity(unit_table, physical_quantity_index):
    """
    특정 Physical Quantity 인덱스의 모든 unit들을 가져오는 함수
    """
    if physical_quantity_index in unit_table:
        return unit_table[physical_quantity_index]['units']
    return {}

def get_unit_type_by_physical_quantity(unit_table, physical_quantity_index):
    """
    특정 Physical Quantity 인덱스에 해당하는 unit_type 이름을 가져오는 함수
    """
    if physical_quantity_index in unit_table:
        return unit_table[physical_quantity_index]['unit_type']
    return None

def get_physical_quantity_by_unit_type(unit_table, unit_type_name):
    """
    특정 unit_type 이름에 해당하는 Physical Quantity 인덱스를 가져오는 함수
    """
    for physical_quantity_idx, data in unit_table.items():
        if data['unit_type'] == unit_type_name:
            return physical_quantity_idx
    return None

#======================================================================
# Main Execution
#======================================================================

# 하드코딩된 단위 테이블 사용
# 하드코딩된 단위 테이블 사용
unit_table = get_hardcoded_unit_table()

# Unit table loaded successfully

# 각 unit_type별로 몇 개의 unit이 있는지 출력
for csv_col_idx in sorted(unit_table.keys()):
    unit_type_name = unit_table[csv_col_idx]['unit_type']
    unit_count = len(unit_table[csv_col_idx]['units'])
    # 각 unit_type별로 몇 개의 unit이 있는지 출력

# Detecting unit sets from Aspen Plus...
units_spinner = Spinner('Detecting unit sets')
units_spinner.start()

# 모든 unit set들 감지
units_sets = get_units_sets(Application)
units_spinner.stop('Unit sets detected successfully!')

# 단위 세트 요약 출력
print_units_sets_summary(units_sets)

# 현재 사용 중인 Unit Set 감지
current_unit_set = get_current_unit_set(Application)

#======================================================================
# Pressure-driven equipment cost estimation wrapper
#======================================================================

def calculate_pressure_device_costs(material: str = 'CS', cepci: CEPCIOptions = CEPCIOptions(target_index=None), material_overrides: dict = None):
    return calculate_pressure_device_costs_auto(
        Application,
        block_info,
        current_unit_set,
        material=material,
        cepci=cepci,
        material_overrides=material_overrides,
    )


#======================================================================
# Run cost calculation and print results
#======================================================================

try:
    register_default_correlations()
    
    # 캐시 초기화
    clear_aspen_cache()
    
    # 1) Preview
    preview = preview_pressure_devices_auto(Application, block_info, current_unit_set)
    
    # 캐시 통계 출력
    cache_stats = get_cache_stats()
    # 캐시 통계 출력
    
    # 프리뷰 결과 출력 (모듈 함수 사용)
    power_unit = None
    pressure_unit = None
    if current_unit_set:
        power_unit = _get_unit_type_value(Application, current_unit_set, 'POWER')
        pressure_unit = _get_unit_type_value(Application, current_unit_set, 'PRESSURE')
    print_preview_results(preview, Application, power_unit, pressure_unit)

    # 2) Build pre-extracted dict from preview (freeze values)
    pre_extracted = {}
    for p in preview:
        pre_extracted[p['name']] = {
            'power_kilowatt': p.get('power_kilowatt'),
            'inlet_bar': p.get('inlet_bar'),
            'outlet_bar': p.get('outlet_bar'),
            'stage_data': p.get('stage_data'),  # MCompr의 stage_data 포함
        }

    # 3) Material, Type and Subtype overrides (simple CLI prompt)
    material_overrides = {}
    type_overrides = {}
    subtype_overrides = {}
    while True:
        ans = input("\n설계 조건을 변경할 장치 이름을 입력하세요 (없으면 엔터): ").strip()
        if not ans:
            break
        
        # 해당 장치 찾기
        device_info = None
        for p in preview:
            if p['name'] == ans:
                device_info = p
                break
        
        if not device_info:
            print(f"장치 '{ans}'를 찾을 수 없습니다.")
            continue
        
        print(f"\n선택된 장치: {ans} ({device_info['category']})")
        print(f"현재 타입: {device_info.get('selected_type', 'N/A')}")
        print(f"현재 세부 타입: {device_info.get('selected_subtype', 'N/A')}")
        
        # 선택 가능한 타입과 세부 타입 표시
        from equipment_costs import get_device_type_options
        type_options = get_device_type_options(device_info['category'])
        
        if type_options:
            print("\n사용 가능한 타입과 세부 타입:")
            for main_type, subtypes in type_options.items():
                print(f"  {main_type}: {', '.join(subtypes)}")
            
            # 타입 변경
            type_input = input("\n타입을 변경하시겠습니까? (y/n): ").strip().lower()
            if type_input == 'y':
                print("\n사용 가능한 타입:")
                main_types = list(type_options.keys())
                for i, t in enumerate(main_types, 1):
                    print(f"  {i}. {t}")
                
                try:
                    type_choice = int(input("타입 번호를 선택하세요: ").strip())
                    if 1 <= type_choice <= len(main_types):
                        selected_type = main_types[type_choice - 1]
                        type_overrides[ans] = selected_type
                        print(f"{ans}의 타입이 {selected_type}로 변경되었습니다.")
                        
                        # 세부 타입 선택
                        available_subtypes = type_options[selected_type]
                        print(f"\n사용 가능한 세부 타입:")
                        for i, st in enumerate(available_subtypes, 1):
                            print(f"  {i}. {st}")
                        
                        try:
                            subtype_choice = int(input("세부 타입 번호를 선택하세요: ").strip())
                            if 1 <= subtype_choice <= len(available_subtypes):
                                selected_subtype = available_subtypes[subtype_choice - 1]
                                subtype_overrides[ans] = selected_subtype
                                print(f"{ans}의 세부 타입이 {selected_subtype}로 변경되었습니다.")
                            else:
                                print("잘못된 번호입니다.")
                        except ValueError:
                            print("숫자를 입력해주세요.")
                    else:
                        print("잘못된 번호입니다.")
                except ValueError:
                    print("숫자를 입력해주세요.")
        
        # 재질 변경
        mat = input("변경할 재질을 입력하세요 (예: CS, SS, Ni, Cl, Ti, Fiberglass, 없으면 엔터): ").strip()
        if mat:
            material_overrides[ans] = mat
            print(f"{ans}의 재질이 {mat}로 변경되었습니다.")
        
        # 변경사항이 있으면 프리뷰 다시 표시
        if ans in material_overrides or ans in type_overrides or ans in subtype_overrides:
            print("\n" + "="*60)
            print("UPDATED PREVIEW: PRESSURE-DRIVEN DEVICES")
            print("="*60)
            
            # 업데이트된 프리뷰 데이터 생성
            updated_preview = []
            for p in preview:
                updated_p = p.copy()
                device_name = p['name']
                
                # 모든 오버라이드 적용 (현재 장치와 이전에 변경한 장치들 모두)
                if device_name in material_overrides:
                    updated_p['material'] = material_overrides[device_name]
                if device_name in type_overrides:
                    updated_p['selected_type'] = type_overrides[device_name]
                if device_name in subtype_overrides:
                    updated_p['selected_subtype'] = subtype_overrides[device_name]
                    
                updated_preview.append(updated_p)
            
            # 업데이트된 프리뷰 출력
            print_preview_results(updated_preview, Application, power_unit, pressure_unit)
    confirm = input("\n위 데이터/재질로 비용 계산을 진행할까요? (y/n): ").strip().lower()
    if confirm != 'y':
        print("사용자에 의해 계산이 취소되었습니다.")
        raise SystemExit(0)

    # 4) Run using pre-extracted data (no further COM reads)
    pressure_device_costs, pressure_device_totals = calculate_pressure_device_costs_with_data(
        pre_extracted=pre_extracted,
        block_info=block_info,
        material='CS',
        cepci=CEPCIOptions(target_index=None),
        material_overrides=material_overrides,
        type_overrides=type_overrides,
        subtype_overrides=subtype_overrides,
    )
    if pressure_device_costs:
        print("\n" + "="*60)
        print("CALCULATED PRESSURE DEVICE COSTS")
        print("="*60)
        for item in pressure_device_costs:
            name = item.get('name')
            dtype = item.get('type')
            installed = item.get('installed', 0.0)
            bare = item.get('bare_module', 0.0)
            
            if dtype == 'error':
                error_msg = item.get('error', 'Unknown error')
                print(f"{name} (error): {error_msg}")
            else:
                print(f"{name} ({dtype}): Installed = {installed:,.2f} USD, Bare = {bare:,.2f} USD")
        print(f"\nTotal Installed Cost for Pressure Devices: {pressure_device_totals.get('installed', 0.0):,.2f} USD")
        print(f"Total Bare Module Cost for Pressure Devices: {pressure_device_totals.get('bare_module', 0.0):,.2f} USD")
        print("="*60)
    else:
        print("No pressure device costs calculated.")
        
    # 최종 캐시 통계 출력
    final_cache_stats = get_cache_stats()
    # 최종 캐시 통계 출력
    
except Exception as e:
    print(f"Error during pressure device cost calculation/printing: {e}")

    