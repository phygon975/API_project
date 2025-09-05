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
                    units_sets.append(element.Name)
                except:
                    # 예외 발생 시 조용히 건너뛰기
                    pass
        
        print(f"Found {len(units_sets)} unit sets")
        
    except Exception as e:
        print(f"Error collecting unit sets: {str(e)}")
    
    return units_sets

def get_unit_set_details_with_csv(Application, unit_set_name, unit_table):
    """
    특정 단위 세트의 상세 정보를 가져오고 CSV 데이터와 연동하는 함수
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
                    
                    # CSV에서 해당 unit_type의 열 인덱스 찾기
                    csv_column_index = get_csv_column_by_unit_type(unit_table, unit_type)
                    
                    # CSV에서 해당 unit의 인덱스 찾기
                    unit_index_in_csv = None
                    if csv_column_index and csv_column_index in unit_table:
                        for unit_idx, csv_unit in unit_table[csv_column_index]['units'].items():
                            if csv_unit == unit_value:
                                unit_index_in_csv = unit_idx
                                break
                    
                    unit_details['unit_types'][unit_type] = {
                        'value': unit_value,
                        'aspen_index': aspen_index,
                        'csv_column_index': csv_column_index,
                        'unit_index_in_csv': unit_index_in_csv,
                        'csv_available': csv_column_index is not None
                    }
                else:
                    # 노드를 찾을 수 없는 경우
                    csv_column_index = get_csv_column_by_unit_type(unit_table, unit_type)
                    unit_details['unit_types'][unit_type] = {
                        'value': 'Not Found in Aspen',
                        'aspen_index': aspen_index,
                        'csv_column_index': csv_column_index,
                        'unit_index_in_csv': None,
                        'csv_available': csv_column_index is not None
                    }
            except Exception as e:
                # 예외 발생 시
                csv_column_index = get_csv_column_by_unit_type(unit_table, unit_type)
                unit_details['unit_types'][unit_type] = {
                    'value': f'Error: {str(e)}',
                    'aspen_index': aspen_index,
                    'csv_column_index': csv_column_index,
                    'unit_index_in_csv': None,
                    'csv_available': csv_column_index is not None
                }
                
    except Exception as e:
        print(f"Warning: Could not get details for unit set '{unit_set_name}': {e}")
    
    return unit_details

def print_unit_set_details_with_csv(unit_details):
    """
    단위 세트 상세 정보를 CSV 인덱스와 함께 출력하는 함수
    """
    print(f"\nUnit Set: {unit_details['name']}")
    print("-" * 100)
    
    if unit_details['unit_types']:
        print(f"{'Unit Type':<20} {'Aspen Index':<12} {'Value':<20} {'CSV Column':<12} {'CSV Index':<12} {'CSV Available':<15}")
        print("-" * 100)
        
        for unit_type, info in unit_details['unit_types'].items():
            csv_col = info['csv_column_index'] if info['csv_column_index'] is not None else 'N/A'
            csv_idx = info['unit_index_in_csv'] if info['unit_index_in_csv'] is not None else 'N/A'
            csv_avail = 'Yes' if info['csv_available'] else 'No'
            print(f"{unit_type:<20} {info['aspen_index']:<12} {info['value']:<20} {csv_col:<12} {csv_idx:<12} {csv_avail:<15}")
    else:
        print("  No unit types found")

def get_unit_by_type_and_csv_index(unit_table, csv_column_index, unit_index):
    """
    CSV 열 인덱스와 unit 인덱스로 unit 값을 가져오는 함수
    """
    return get_unit_by_index(unit_table, csv_column_index, unit_index)

def get_available_units_for_type(unit_table, unit_type_name):
    """
    특정 unit_type의 모든 사용 가능한 unit들을 가져오는 함수
    """
    csv_column_index = get_csv_column_by_unit_type(unit_table, unit_type_name)
    if csv_column_index:
        return get_units_by_csv_column(unit_table, csv_column_index)
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

def print_unit_set_details(unit_details):
    """
    단위 세트 상세 정보를 출력하는 함수
    """
    print(f"\nUnit Set: {unit_details['name']}")
    print("-" * 60)
    
    if unit_details['unit_types']:
        print(f"{'Unit Type':<20} {'Index':<8} {'Value':<15}")
        print("-" * 60)
        
        for unit_type, info in unit_details['unit_types'].items():
            print(f"{unit_type:<20} {info['index']:<8} {info['value']:<15}")
    else:
        print("  No unit types found")

def get_unit_by_type(unit_details, unit_type):
    """
    특정 unit_type의 정보를 가져오는 함수
    """
    if unit_type in unit_details['unit_types']:
        return unit_details['unit_types'][unit_type]
    return None

def get_units_by_index_range(unit_details, min_index, max_index):
    """
    특정 인덱스 범위의 unit_type들을 가져오는 함수
    """
    matching_units = {}
    
    for unit_type, info in unit_details['unit_types'].items():
        if min_index <= info['index'] <= max_index:
            matching_units[unit_type] = info
    
    return matching_units

#======================================================================
# Unit Table CSV Reader
#======================================================================

def load_unit_table_csv(csv_file_path):
    """
    Unit_table.csv 파일을 읽어서 unit_type 인덱스와 unit별 인덱스를 매핑하는 함수
    CSV 열 순서에 따라 unit_type을 매핑
    """
    import csv
    
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
    
    unit_table = {}
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            rows = list(csv_reader)
            
            if not rows:
                print("CSV file is empty")
                return unit_table
            
            # 첫 번째 행에서 최대 열 수 확인
            max_columns = max(len(row) for row in rows)
            print(f"CSV file loaded: {len(rows)} rows, {max_columns} columns")
            
            # 각 열(unit_type)에 대해 처리
            for col_index in range(max_columns):
                csv_column_index = col_index + 1  # CSV 열 인덱스는 1부터 시작
                
                # CSV 열이 unit_type에 매핑되는지 확인
                if csv_column_index in csv_column_to_unit_type:
                    unit_type_name = csv_column_to_unit_type[csv_column_index]
                    unit_table[csv_column_index] = {
                        'unit_type': unit_type_name,
                        'units': {}
                    }
                    
                    # 각 행에서 해당 열의 값 확인
                    for row_index, row in enumerate(rows):
                        unit_index = row_index + 1  # unit 인덱스는 1부터 시작
                        
                        # 해당 열이 존재하고 값이 있는 경우만 처리
                        if col_index < len(row) and row[col_index].strip():
                            unit_value = row[col_index].strip()
                            unit_table[csv_column_index]['units'][unit_index] = unit_value
        
        # 빈 unit_type 제거
        empty_types = [idx for idx, data in unit_table.items() if not data['units']]
        for idx in empty_types:
            del unit_table[idx]
        
        print(f"Unit table loaded successfully: {len(unit_table)} unit types found")
        print(f"Removed {len(empty_types)} empty unit types")
        
        # 각 unit_type별로 몇 개의 unit이 있는지 출력
        for csv_col_idx in sorted(unit_table.keys()):
            unit_type_name = unit_table[csv_col_idx]['unit_type']
            unit_count = len(unit_table[csv_col_idx]['units'])
            print(f"  CSV Column {csv_col_idx} ({unit_type_name}): {unit_count} units")
        
    except Exception as e:
        print(f"Error loading unit table CSV: {e}")
        return {}
    
    return unit_table

def get_unit_by_index(unit_table, csv_column_index, unit_index):
    """
    특정 CSV 열 인덱스와 unit 인덱스로 unit 값을 가져오는 함수
    """
    if csv_column_index in unit_table and unit_index in unit_table[csv_column_index]['units']:
        return unit_table[csv_column_index]['units'][unit_index]
    return None

def get_units_by_csv_column(unit_table, csv_column_index):
    """
    특정 CSV 열 인덱스의 모든 unit들을 가져오는 함수
    """
    if csv_column_index in unit_table:
        return unit_table[csv_column_index]['units']
    return {}

def get_unit_type_by_csv_column(unit_table, csv_column_index):
    """
    특정 CSV 열 인덱스에 해당하는 unit_type 이름을 가져오는 함수
    """
    if csv_column_index in unit_table:
        return unit_table[csv_column_index]['unit_type']
    return None

def get_csv_column_by_unit_type(unit_table, unit_type_name):
    """
    특정 unit_type 이름에 해당하는 CSV 열 인덱스를 가져오는 함수
    """
    for csv_col_idx, data in unit_table.items():
        if data['unit_type'] == unit_type_name:
            return csv_col_idx
    return None

def print_unit_table_summary(unit_table, required_unit_types):
    """
    Unit table 요약 정보를 출력하는 함수
    """
    print("\n" + "="*80)
    print("UNIT TABLE SUMMARY")
    print("="*80)
    
    print(f"{'Unit Type':<20} {'Index':<8} {'Available Units':<50}")
    print("-" * 80)
    
    for unit_type, index in required_unit_types.items():
        if index in unit_table:
            units = unit_table[index]
            unit_list = ", ".join([f"{idx}:{unit}" for idx, unit in units.items()])
            print(f"{unit_type:<20} {index:<8} {unit_list:<50}")
        else:
            print(f"{unit_type:<20} {index:<8} {'Not Found':<50}")
    
    print("="*80)

def debug_csv_structure(csv_file_path):
    """
    CSV 파일의 구조를 디버깅하는 함수
    """
    import csv
    
    print(f"\n" + "="*60)
    print("CSV FILE STRUCTURE DEBUG")
    print("="*60)
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            rows = list(csv_reader)
            
            print(f"Total rows: {len(rows)}")
            
            # 각 행의 열 수 확인
            col_counts = [len(row) for row in rows]
            print(f"Column counts per row: {col_counts[:10]}...")  # 처음 10개만 출력
            print(f"Max columns: {max(col_counts)}")
            print(f"Min columns: {min(col_counts)}")
            
            # 각 열별로 몇 개의 값이 있는지 확인
            max_cols = max(col_counts)
            col_value_counts = {}
            
            for col_idx in range(max_cols):
                col_value_counts[col_idx + 1] = 0
                for row_idx, row in enumerate(rows):
                    if col_idx < len(row) and row[col_idx].strip():
                        col_value_counts[col_idx + 1] += 1
            
            print(f"\nValues per column:")
            for col_idx in sorted(col_value_counts.keys()):
                if col_value_counts[col_idx] > 0:  # 값이 있는 열만 출력
                    print(f"  Column {col_idx}: {col_value_counts[col_idx]} values")
            
            # 첫 번째 행의 내용 확인
            print(f"\nFirst row content:")
            for i, value in enumerate(rows[0]):
                print(f"  Col {i+1}: '{value}'")
            
    except Exception as e:
        print(f"Error debugging CSV: {e}")
    
    print("="*60)

def validate_unit_types_with_csv(required_unit_types, unit_table):
    """
    지정한 unit_type 인덱스와 CSV 파일의 열 인덱스가 일치하는지 확인하는 함수
    """
    print("\n" + "="*60)
    print("UNIT TYPE INDEX VALIDATION")
    print("="*60)
    
    missing_indices = []
    extra_indices = []
    
    # CSV에 있는 인덱스들
    csv_indices = set(unit_table.keys())
    
    # 필요한 인덱스들
    required_indices = set(required_unit_types.values())
    
    # 누락된 인덱스 확인
    for unit_type, index in required_unit_types.items():
        if index not in csv_indices:
            missing_indices.append((unit_type, index))
    
    # 추가된 인덱스 확인
    for index in csv_indices:
        if index not in required_indices:
            extra_indices.append(index)
    
    print(f"Required unit types: {len(required_indices)}")
    print(f"Found in CSV: {len(csv_indices)}")
    print(f"Missing indices: {len(missing_indices)}")
    print(f"Extra indices: {len(extra_indices)}")
    
    if missing_indices:
        print("\nMissing unit types:")
        for unit_type, index in missing_indices:
            print(f"  {unit_type} (Index: {index})")
    
    if extra_indices:
        print("\nExtra indices in CSV:")
        for index in sorted(extra_indices):
            print(f"  Index: {index}")
    
    print("="*60)
    
    return len(missing_indices) == 0

#======================================================================
# Load Unit Table CSV
#======================================================================

# Unit_table.csv 파일 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
unit_table_csv_path = os.path.join(current_dir, 'Unit_table.csv')

print(f"\nLoading unit table from: {unit_table_csv_path}")

if os.path.exists(unit_table_csv_path):
    # CSV 구조 디버깅
    debug_csv_structure(unit_table_csv_path)
    
    unit_table = load_unit_table_csv(unit_table_csv_path)
    
    # Unit type 인덱스 검증
    required_unit_types = {
        'AREA': 1, 'COMPOSITION': 2, 'DENSITY': 3, 'ENERGY': 5, 'FLOW': 9,
        'MASS-FLOW': 10, 'MOLE-FLOW': 11, 'VOLUME-FLOW': 12, 'MASS': 18,
        'POWER': 19, 'PRESSURE': 20, 'TEMPERATURE': 22, 'TIME': 24,
        'VELOCITY': 25, 'VOLUME': 27, 'MOLE-DENSITY': 37, 'MASS-DENSITY': 38,
        'MOLE-VOLUME': 43, 'ELEC-POWER': 47, 'UA': 50, 'WORK': 52, 'HEAT': 53
    }
    
    validation_passed = validate_unit_types_with_csv(required_unit_types, unit_table)
    
    if validation_passed:
        print("✅ All required unit types found in CSV!")
    else:
        print("⚠️  Some unit types missing in CSV!")
    
    # Unit table 요약 출력
    print_unit_table_summary(unit_table, required_unit_types)
    
else:
    print(f"❌ Unit table CSV file not found: {unit_table_csv_path}")
    unit_table = {}

print("\nDetecting unit sets from Aspen Plus...")
units_spinner = Spinner('Detecting unit sets')
units_spinner.start()

units_sets = get_units_sets(Application)
units_spinner.stop('Unit sets detected successfully!')

# 단위 세트 요약 출력
print_units_sets_summary(units_sets)

# 각 단위 세트의 상세 정보 출력 (CSV 연동)
if units_sets and unit_table:
    print("\n" + "="*80)
    print("UNIT SETS DETAILS (WITH CSV INTEGRATION)")
    print("="*80)
    
    for unit_set_name in units_sets:
        unit_details = get_unit_set_details_with_csv(Application, unit_set_name, unit_table)
        print_unit_set_details_with_csv(unit_details)
    
    # 사용 예시
    print("\n" + "="*80)
    print("USAGE EXAMPLES (WITH CSV INTEGRATION)")
    print("="*80)
    
    if units_sets:
        first_unit_set = units_sets[0]
        unit_details = get_unit_set_details_with_csv(Application, first_unit_set, unit_table)
        
        # 특정 unit_type 정보 가져오기
        temp_info = get_unit_by_type(unit_details, 'TEMPERATURE')
        if temp_info:
            print(f"\nTemperature unit in '{first_unit_set}': {temp_info['value']} (Aspen Index: {temp_info['aspen_index']}, CSV Column: {temp_info['csv_column_index']}, CSV Index: {temp_info['unit_index_in_csv']})")
        
        pressure_info = get_unit_by_type(unit_details, 'PRESSURE')
        if pressure_info:
            print(f"Pressure unit in '{first_unit_set}': {pressure_info['value']} (Aspen Index: {pressure_info['aspen_index']}, CSV Column: {pressure_info['csv_column_index']}, CSV Index: {pressure_info['unit_index_in_csv']})")
        
        # CSV에서 직접 unit 정보 가져오기
        print(f"\nDirect CSV access examples:")
        
        # TEMPERATURE의 모든 사용 가능한 unit들
        temp_units = get_available_units_for_type(unit_table, 'TEMPERATURE')
        print(f"Available temperature units: {temp_units}")
        
        # PRESSURE의 모든 사용 가능한 unit들
        pressure_units = get_available_units_for_type(unit_table, 'PRESSURE')
        print(f"Available pressure units: {pressure_units}")
        
        # 특정 CSV 열과 인덱스로 unit 값 가져오기
        temp_csv_col = get_csv_column_by_unit_type(unit_table, 'TEMPERATURE')
        if temp_csv_col:
            temp_unit_1 = get_unit_by_type_and_csv_index(unit_table, temp_csv_col, 1)
            print(f"Temperature unit at CSV column {temp_csv_col}, index 1: {temp_unit_1}")
        
        pressure_csv_col = get_csv_column_by_unit_type(unit_table, 'PRESSURE')
        if pressure_csv_col:
            pressure_unit_1 = get_unit_by_type_and_csv_index(unit_table, pressure_csv_col, 1)
            print(f"Pressure unit at CSV column {pressure_csv_col}, index 1: {pressure_unit_1}")

elif units_sets and not unit_table:
    print("\n" + "="*60)
    print("UNIT SETS DETAILS (WITHOUT CSV)")
    print("="*60)
    
    for unit_set_name in units_sets:
        # 기존 함수 사용 (CSV 없이)
        unit_details = get_unit_set_details(Application, unit_set_name)
        print_unit_set_details(unit_details)

print(f"\n" + "="*60)
print("UNITS SETS DETECTION COMPLETED")
print("="*60)
    