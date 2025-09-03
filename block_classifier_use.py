"""
Create on Sep 2, 2025

@author: Pyeong-Gon Jung
"""

import os
import win32com.client as win32
import numpy as np
import sys
import time
from threading import Thread
from typing import Optional

# Add current directory to path to import HeatExchanger module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

# 블록 이름들을 자동으로 감지할 것이므로 초기값은 빈 리스트
block_names = []

try:
    from block_classifier import block_classifier
    print("block_classifier module imported successfully!")
except ImportError as e:
    print(f"Error importing block_classifier module: {e}")
    print("Make sure block_classifier.py is in the same directory")
    sys.exit(1)

def main():
    #%% Aspen Plus Connection
    
    # 1. Specify file name
    file = 'MIX_HEFA_20250716_after_HI_v1.bkp'  #아스펜 파일이 바뀔 시 여기를 수정해야 함
    
    # 2. Get absolute path to Aspen Plus file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    aspen_Path = os.path.join(current_dir, file)
    print(f"Looking for file: {aspen_Path}")
    
    # 3. Check if file exists
    if not os.path.exists(aspen_Path):
        print(f"ERROR: File not found: {aspen_Path}")
        print("Please make sure MIX_HEFA_20250716_after_HI_v1.bkp is in the same directory as this script")
        return
    
    print(f"File found: {aspen_Path}")
    
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
        return

    try:
        print("\nDetecting block names from Aspen Plus...")
        detect_spinner = Spinner('Detecting block names')
        detect_spinner.start()
        
        # 먼저 Aspen Plus에서 블록 이름들을 감지
        from block_classifier import get_block_names
        detected_block_names = get_block_names(Application)
        detect_spinner.stop('Block names detected successfully.')
        
        if not detected_block_names:
            print("ERROR: No blocks detected from Aspen Plus")
            return
        
        print(f"\nDetected {len(detected_block_names)} blocks from Aspen Plus:")
        for i, name in enumerate(detected_block_names, 1):
            print(f"{i:2d}. {name}")
        
        # 감지된 블록 이름들을 전역 변수에 할당
        global block_names
        block_names = detected_block_names
        
        print("\nParsing BKP file for block categories...")
        parse_spinner = Spinner('Parsing BKP file')
        parse_spinner.start()
        
        # BKP 파일에서 블록 카테고리 파싱
        from block_classifier import classify_blocks_from_bkp
        
        # 블록 정보와 카테고리 분류
        block_categories, block_info = classify_blocks_from_bkp(aspen_Path, block_names)
        parse_spinner.stop('BKP file parsed successfully.')
        
        print("\nBlock classification completed!")
        
    except Exception as e:
        print(f"ERROR Detecting blocks or parsing BKP file: {e}")
        return
    
    print("\nBlock categories:")
    for category, blocks in block_categories.items():
        if blocks:  # 빈 리스트가 아닌 경우만 출력
            print(f"\n{category.replace('_', ' ').title()}:")
            for block in blocks:
                print(f"  - {block}")
    
    print(f"\nDetailed block information:")
    for block_name, category in block_info.items():
        print(f"  {block_name}: {category}")
    
    # # 사용자에게 Tree 구조 출력 여부 묻기
    # print("\n" + "="*50)
    # show_tree = input("Aspen Plus Tree 구조를 출력하시겠습니까? (y/n/s): ").strip().lower()
    
    # if show_tree == 'y':
    #     try:
    #         print("\n" + "="*60)
    #         print("Aspen Plus Tree Structure")
    #         print("="*60)
    #         from block_classifier import print_aspen_tree
    #         print_aspen_tree(Application)
    #     except Exception as e:
    #         print(f"Warning: Could not print Aspen Tree structure: {e}")
    # elif show_tree == 's':
    #     try:
    #         print("\n" + "="*60)
    #         print("Aspen Plus Tree Structure (Safe Mode)")
    #         print("="*60)
    #         from block_classifier import print_aspen_tree_safe
    #         print_aspen_tree_safe(Application, max_depth=3)
    #     except Exception as e:
    #         print(f"Warning: Could not print Aspen Tree structure: {e}")
    # else:
    #     print("Tree 구조 출력을 건너뜁니다.")
    
    # # Blocks 하위 블록 이름 저장 기능 (이미 감지된 블록 이름들 사용)
    # print("\n" + "="*50)
    # save_blocks = input("감지된 블록 이름들을 파일로 저장하시겠습니까? (y/n): ").strip().lower()
    
    # if save_blocks == 'y':
    #     try:
    #         print("\n" + "="*60)
    #         print("Saving Detected Block Names")
    #         print("="*60)
    #         from block_classifier import save_block_names
            
    #         # 파일명 입력 받기
    #         filename = input("저장할 파일명을 입력하세요 (기본값: detected_block_names.txt): ").strip()
    #         if not filename:
    #             filename = "detected_block_names.txt"
            
    #         # 이미 감지된 블록 이름들을 파일로 저장
    #         with open(filename, 'w', encoding='utf-8') as f:
    #             f.write("Aspen Plus Detected Block Names\n")
    #             f.write("=" * 50 + "\n")
    #             f.write(f"Total blocks: {len(block_names)}\n")
    #             f.write("=" * 50 + "\n\n")
                
    #             for i, block_name in enumerate(block_names, 1):
    #                 f.write(f"{i:3d}. {block_name}\n")
            
    #         print(f"Detected block names saved to: {filename}")
    #         print(f"Total blocks saved: {len(block_names)}")
            
    #     except Exception as e:
    #         print(f"Warning: Could not save block names: {e}")
    # else:
    #     print("블록 이름 저장을 건너뜁니다.")
    

if __name__ == "__main__":
    main()



