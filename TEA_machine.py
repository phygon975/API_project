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

print("\nBlock categories:")
for category, blocks in block_categories.items():
    if blocks:  # 빈 리스트가 아닌 경우만 출력
        print(f"\n{category.replace('_', ' ').title()}:")
        for block in blocks:
            print(f"  - {block}")

print(f"\nDetailed block information:")
for block_name, category in block_info.items():
    print(f"  {block_name}: {category}")
    