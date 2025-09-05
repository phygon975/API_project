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
                        elif next_line in ['Pump', 'Compr', 'MCompr', 'Vacuum', 'Flash', 'Sep', 'Mixer', 'FSplit', 'Valve', 'Utility']:
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
            print("Warning: Units-Sets node not found")
            return units_sets
        
        print("Found Units-Sets node, collecting unit sets...")
        
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
        
        print(f"Found {len(units_sets)} unit sets")
        
    except Exception as e:
        print(f"Error collecting unit sets: {str(e)}")
    
    return units_sets

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
print(f"\n📋 Using hardcoded unit data...")
unit_table = get_hardcoded_unit_table()

print(f"Unit table loaded successfully: {len(unit_table)} unit types found")

# 각 unit_type별로 몇 개의 unit이 있는지 출력
for csv_col_idx in sorted(unit_table.keys()):
    unit_type_name = unit_table[csv_col_idx]['unit_type']
    unit_count = len(unit_table[csv_col_idx]['units'])
    print(f"  Column {csv_col_idx} ({unit_type_name}): {unit_count} units")

print("\nDetecting unit sets from Aspen Plus...")
units_spinner = Spinner('Detecting unit sets')
units_spinner.start()

# 모든 unit set들 감지
units_sets = get_units_sets(Application)
units_spinner.stop('Unit sets detected successfully!')

# 단위 세트 요약 출력
print_units_sets_summary(units_sets)

# 모든 경우에 하드코딩된 데이터 사용
if units_sets:
    print("\n" + "="*80)
    print("UNIT SETS DETAILS (WITH HARDCODED DATA)")
    print("="*80)
    
    for unit_set_name in units_sets:
        unit_details = get_unit_set_details(Application, unit_set_name, unit_table)
        print_unit_set_details(unit_details)

else:
    print("No unit sets found in Aspen Plus")

print(f"\n" + "="*60)
print("UNITS SETS DETECTION COMPLETED")
print("="*60)
    