"""
Create on Sep 2, 2025

@author: Pyeong-Gon Jung
"""

import numpy as np


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
        'pumps': [],
        'vacuum_systems': [],
        'evaporators': [],
        'other_blocks': []
    }
    
    for block_name, category in block_info.items():
        if category in ['Heater', 'Cooler', 'HeatX', 'Condenser']:
            block_categories['heat_exchangers'].append(block_name)
        elif category in ['RadFrac', 'Distl', 'DWSTU']:
            block_categories['distillation_columns'].append(block_name)
        elif category in ['RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield']:
            block_categories['reactors'].append(block_name)
        elif category in ['Pump', 'Compr', 'MCompr', 'Vacuum', 'Flash', 'Sep', 'Mixer', 'FSplit', 'Valve', 'Utility']:
            block_categories['pumps'].append(block_name)
        elif category in ['EVAP1', 'EVAP2', 'EVAP3']:
            block_categories['evaporators'].append(block_name)
        else:
            block_categories['other_blocks'].append(block_name)
    
    return block_categories, block_info


def print_elements(obj, level=0):
    """
    Aspen Plus Tree 구조를 재귀적으로 출력하는 함수
    매트랩 함수를 Python으로 변환
    """
    try:
        if hasattr(obj, 'Elements') and obj.Elements is not None:
            # List node (has children)
            print(' ' * level + obj.Name)
            for o in obj.Elements:
                print_elements(o, level + 1)
        else:
            # Leaf node (no children, has value)
            try:
                value = obj.Value
                print(' ' * level + obj.Name + ' = ' + str(value))
            except:
                # Value가 없는 경우 - 출력하지 않음
                pass
    except:
        # 예외 발생 시 출력하지 않음
        pass


def print_aspen_tree_safe(Application, max_depth=3):
    """
    안전한 Aspen Plus Tree 구조 출력 함수 (깊이 제한)
    """
    print("=" * 60)
    print("Aspen Plus Tree Structure (Safe Mode)")
    print("=" * 60)
    
    def print_elements_safe(obj, level=0, max_depth=max_depth):
        if level > max_depth:
            print(' ' * level + obj.Name + ' ... (depth limit reached)')
            return
            
        try:
            if hasattr(obj, 'Elements') and obj.Elements is not None:
                # List node (has children)
                print(' ' * level + obj.Name)
                for o in obj.Elements:
                    print_elements_safe(o, level + 1, max_depth)
            else:
                # Leaf node (no children, has value)
                try:
                    value = obj.Value
                    print(' ' * level + obj.Name + ' = ' + str(value))
                except:
                    # Value가 없는 경우 - 출력하지 않음
                    pass
        except:
            # 예외 발생 시 출력하지 않음
            pass
    
    try:
        print_elements_safe(Application.Tree, 0, max_depth)
    except Exception as e:
        print(f"Error accessing Aspen Tree: {str(e)}")
    
    print("=" * 60)


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


def save_block_names(Application, filename="block_names.txt"):
    """
    Blocks 하위의 가장 상위 노드(블록 이름)들을 파일로 저장하는 함수
    """
    try:
        block_names = get_block_names(Application)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Aspen Plus Block Names\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total blocks: {len(block_names)}\n")
            f.write("=" * 50 + "\n\n")
            
            for i, block_name in enumerate(block_names, 1):
                f.write(f"{i:3d}. {block_name}\n")
        
        print(f"Block names saved to: {filename}")
        print(f"Total blocks found: {len(block_names)}")
        
        return block_names
        
    except Exception as e:
        print(f"Error saving block names: {str(e)}")
        return []


def print_aspen_tree(Application):
    """
    Aspen Plus 전체 Tree 구조를 출력하는 함수
    """
    print("=" * 60)
    print("Aspen Plus Tree Structure")
    print("=" * 60)
    print_elements(Application.Tree)
    print("=" * 60)


def block_classifier(Application, block_names):

    block_categories = {
        'heat_exchangers': [],
        'distillation_columns': [],
        'reactors': [],
        'pumps': [],
        'vacuum_systems': [],
        'evaporators': [],
        'other_blocks': []
    }

    #While loop for detecting all block names
    i = 0
    for i in range(len(block_names)):
        block_name = block_names[i]
        record_type_path = None  # 초기값 설정
        
        try:
            record_type_path = Application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}\\Record Type").value
            
        except:
            print(f"Warning: Could not get RECORD_TYPE for block {block_name}")
            record_type_path = "Unknown"  # 기본값 설정
        print(record_type_path)
        # 블록 분류
        if record_type_path in ['HeatX', 'Heater', 'Cooler', 'Condenser']:
            block_categories['heat_exchangers'].append(block_name)
        elif record_type_path in ['RadFrac', 'Distl', 'DWSTU']:
            block_categories['distillation_columns'].append(block_name)
        elif record_type_path in ['RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield']:
            block_categories['reactors'].append(block_name)
        elif record_type_path in ['Pump', 'Compr', 'Vacuum', 'Flash', 'Sep', 'Mixer', 'FSplit', 'Valve', 'Utility']:
            block_categories['pumps'].append(block_name)
        elif record_type_path in ['EVAP1', 'EVAP2', 'EVAP3']:
            block_categories['evaporators'].append(block_name)
        else:
            block_categories['other_blocks'].append(block_name)

    return block_categories

        

    









