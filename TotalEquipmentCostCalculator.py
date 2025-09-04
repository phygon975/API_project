# -*- coding: utf-8 -*-
"""
전체 장비 비용 계산기 (Total Equipment Cost Calculator)
Created on 2025-01-22

이 코드는 Aspen Plus 시뮬레이션 파일(.bkp)에서 모든 장비의 비용을 계산합니다.
각 장비별 모듈을 불러와서 통합된 비용 분석을 제공합니다.

@author: Assistant
"""

import os
import sys
import time
import numpy as np
import win32com.client as win32
from threading import Thread
from typing import Optional, Dict, List, Any

# 각 장비 모듈의 경로를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
module_paths = [
    '0Heat-Exchanger',
    '1Distillation', 
    '2Reactor',
    '3Pumps',
    '4Vacuum-System',
    '5Evaporator'
]

for path in module_paths:
    module_path = os.path.join(current_dir, path)
    if module_path not in sys.path:
        sys.path.append(module_path)

# 각 장비 모듈 import
try:
    from HeatExchanger import heatexchanger
    print("✓ Heat Exchanger module imported")
except ImportError as e:
    print(f"✗ Heat Exchanger module import failed: {e}")

try:
    from Distillation import (distillationRADFRAC, distillationDWSTU, 
                             refluxdrumRADFRAC, refluxdrumDWSTU,
                             kettleRADFRAC, kettleDWSTU,
                             condenserRADFRAC, condenserDWSTU)
    print("✓ Distillation module imported")
except ImportError as e:
    print(f"✗ Distillation module import failed: {e}")

try:
    from Reactor import reactorCSTR
    print("✓ Reactor module imported")
except ImportError as e:
    print(f"✗ Reactor module import failed: {e}")

try:
    from pumps import pumps
    print("✓ Pumps module imported")
except ImportError as e:
    print(f"✗ Pumps module import failed: {e}")

try:
    from vacuumoperation import vacuumsystemSTEAMJET, vacuumsystemLIQUIDRING
    print("✓ Vacuum System module imported")
except ImportError as e:
    print(f"✗ Vacuum System module import failed: {e}")

try:
    from Evaporator import verticalEVAPORATORS
    print("✓ Evaporator module imported")
except ImportError as e:
    print(f"✗ Evaporator module import failed: {e}")

# 스마트 장비 탐지 시스템 import
try:
    from SmartEquipmentDetector import SmartEquipmentDetector, EquipmentType
    print("✓ Smart Equipment Detector module imported")
except ImportError as e:
    print(f"✗ Smart Equipment Detector module import failed: {e}")

class Spinner:
    """CLI 스피너 클래스"""
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

class TotalEquipmentCostCalculator:
    """전체 장비 비용 계산기 클래스"""
    
    def __init__(self, aspen_file_path: str, cost_index: float = 607.5):
        """
        초기화
        
        Parameters:
        -----------
        aspen_file_path : str
            Aspen Plus 백업 파일(.bkp) 경로
        cost_index : float
            현재 비용 지수 (기본값: 607.5 for 2019)
        """
        self.aspen_file_path = aspen_file_path
        self.cost_index = cost_index
        self.Application = None
        self.results = {}
        self.smart_detector = SmartEquipmentDetector() if 'SmartEquipmentDetector' in globals() else None
        
    def auto_detect_equipment(self) -> Dict[str, Any]:
        """Aspen Plus 파일을 자동으로 분석하여 장비 구성을 감지"""
        try:
            print("\n" + "="*60)
            print("         장비 자동 감지 시작")
            print("="*60)
            
            if not self.Application:
                print("ERROR: Aspen Plus에 먼저 연결해야 합니다.")
                return {}
            
            detected_config = {
                'calculate_heat_exchangers': False,
                'calculate_distillation': False,
                'calculate_reactors': False,
                'calculate_pumps': False,
                'calculate_vacuum': False,
                'calculate_evaporators': False
            }
            
            # 1. 열교환기 자동 감지
            heat_exchangers = self._detect_heat_exchangers()
            if heat_exchangers['count'] > 0:
                detected_config['calculate_heat_exchangers'] = True
                detected_config['no_heat_exchangers'] = heat_exchangers['count']
                detected_config['heat_exchanger_names'] = heat_exchangers['names']
                print(f"✓ 열교환기 {heat_exchangers['count']}개 감지됨: {', '.join(heat_exchangers['names'])}")
            
            # 2. 증류탑 자동 감지
            distillation_columns = self._detect_distillation_columns()
            if distillation_columns['count'] > 0:
                detected_config['calculate_distillation'] = True
                detected_config['radfrac_columns'] = distillation_columns['configs']
                print(f"✓ 증류탑 {distillation_columns['count']}개 감지됨: {', '.join(distillation_columns['names'])}")
            
            # 3. 반응기 자동 감지
            reactors = self._detect_reactors()
            if reactors['count'] > 0:
                detected_config['calculate_reactors'] = True
                detected_config['reactors'] = reactors['configs']
                print(f"✓ 반응기 {reactors['count']}개 감지됨: {', '.join(reactors['names'])}")
            
            # 4. 펌프 자동 감지
            pumps = self._detect_pumps()
            if pumps['count'] > 0:
                detected_config['calculate_pumps'] = True
                detected_config['no_pumps'] = pumps['count']
                detected_config['pump_names'] = pumps['names']
                print(f"✓ 펌프 {pumps['count']}개 감지됨: {', '.join(pumps['names'])}")
            
            # 5. 압축기 자동 감지
            compressors = self._detect_compressors()
            if compressors['count'] > 0:
                detected_config['calculate_compressors'] = True
                detected_config['no_compressors'] = compressors['count']
                detected_config['compressor_names'] = compressors['names']
                print(f"✓ 압축기 {compressors['count']}개 감지됨: {', '.join(compressors['names'])}")
            
            # 5. 기본값 설정
            detected_config.update({
                'fouling_factor': 0.9,
                'tube_length_factor': 1.05,
                'material_factor_hx': 1.0,        # 탄소강
                'material_factor_pumps': 2.0,     # 스테인리스강
                'material_factor_compressors': 2.0, # 스테인리스강
                'tray_spacing': 0.5,              # 기본 트레이 간격
                'top_space': 1.5,                 # 기본 상단 여유
                'bottom_space': 1.5,              # 기본 하단 여유
                'reactor_liquid_fill': 0.65,      # 기본 액체 충전률
                'reactor_h_d_ratio': 3.0,         # 기본 H/D 비
                'reactor_material_factor': 2.1,   # 기본 반응기 재질계수
                'reactor_density': 8000,          # 기본 반응기 재질 밀도
                'column_material_factor': 2.1,    # 기본 증류탑 재질계수
                'column_density': 8000            # 기본 증류탑 재질 밀도
            })
            
            print("\n" + "="*60)
            print("         장비 자동 감지 완료")
            print("="*60)
            
            return detected_config
            
        except Exception as e:
            print(f"ERROR during auto-detection: {e}")
            return {}
    
    def smart_detect_equipment(self) -> Dict[str, Any]:
        """Record Type 기반 스마트 장비 탐지 시스템을 사용한 고급 장비 감지"""
        try:
            if not self.smart_detector:
                print("스마트 탐지 시스템을 사용할 수 없습니다. 기본 탐지를 사용합니다.")
                return self.auto_detect_equipment()
            
            print("\n" + "="*60)
            print("         Record Type 기반 스마트 장비 탐지 시작")
            print("="*60)
            
            # Record Type 기반 스마트 탐지 실행
            detected_equipment = self.smart_detector.detect_equipment_from_aspen(self.Application)
            
            if not detected_equipment:
                print("ERROR: 장비 탐지에 실패했습니다.")
                return {}
            
            # 탐지 결과 리포트 생성
            detection_report = self.smart_detector.generate_detection_report(detected_equipment)
            print(detection_report)
            
            # 명명법 개선 제안
            naming_suggestions = self.smart_detector.suggest_naming_conventions(detected_equipment)
            print(naming_suggestions)
            
            # 통계 정보 출력
            stats = self.smart_detector.get_equipment_statistics(detected_equipment)
            print(f"\n📊 탐지 통계:")
            print(f"   총 장비 수: {stats['total_equipment']}")
            print(f"   분류된 장비: {stats['classified_equipment']}")
            print(f"   미분류 장비: {stats['unknown_equipment']}")
            print(f"   평균 신뢰도: {stats['confidence_stats']['average']:.3f}")
            
            # 기존 형식으로 변환
            config = self._convert_smart_detection_to_config(detected_equipment)
            
            return config
            
        except Exception as e:
            print(f"ERROR during smart detection: {e}")
            return self.auto_detect_equipment()
    
    def _get_all_block_names(self) -> List[str]:
        """Aspen Plus에서 모든 블록명 가져오기"""
        try:
            blocks_node = self.Application.Tree.FindNode("\\Data\\Blocks")
            if not blocks_node:
                return []
            
            block_names = []
            for i in range(blocks_node.Count):
                try:
                    block_name = blocks_node.Item(i).Name
                    if block_name:
                        block_names.append(block_name)
                except:
                    continue
            
            return block_names
            
        except Exception as e:
            print(f"블록명 가져오기 오류: {e}")
            return []
    
    def _convert_smart_detection_to_config(self, detected_equipment: Dict) -> Dict[str, Any]:
        """스마트 탐지 결과를 기존 설정 형식으로 변환"""
        config = {
            'calculate_heat_exchangers': False,
            'calculate_distillation': False,
            'calculate_reactors': False,
            'calculate_pumps': False,
            'calculate_vacuum': False,
            'calculate_evaporators': False
        }
        
        # 열교환기
        if detected_equipment.get(EquipmentType.HEAT_EXCHANGER):
            config['calculate_heat_exchangers'] = True
            config['no_heat_exchangers'] = len(detected_equipment[EquipmentType.HEAT_EXCHANGER])
            config['heat_exchanger_names'] = [e['name'] for e in detected_equipment[EquipmentType.HEAT_EXCHANGER]]
        
        # 증류탑
        if detected_equipment.get(EquipmentType.DISTILLATION_COLUMN):
            config['calculate_distillation'] = True
            config['radfrac_columns'] = []
            for equip in detected_equipment[EquipmentType.DISTILLATION_COLUMN]:
                config['radfrac_columns'].append({
                    'name': equip['name'],
                    'tray_spacing': 0.5,
                    'top_space': 1.5,
                    'bottom_space': 1.5,
                    'density': 8000,
                    'material_factor': 2.1
                })
        
        # 반응기
        if detected_equipment.get(EquipmentType.REACTOR):
            config['calculate_reactors'] = True
            config['reactors'] = []
            for equip in detected_equipment[EquipmentType.REACTOR]:
                config['reactors'].append({
                    'name': equip['name'],
                    'liquid_fill': 0.65,
                    'h_d_ratio': 3.0,
                    'material_factor': 2.1,
                    'density': 8000
                })
        
        # 펌프
        if detected_equipment.get(EquipmentType.PUMP):
            config['calculate_pumps'] = True
            config['no_pumps'] = len(detected_equipment[EquipmentType.PUMP])
            config['pump_names'] = [e['name'] for e in detected_equipment[EquipmentType.PUMP]]
        
        # 압축기
        if detected_equipment.get(EquipmentType.COMPRESSOR):
            config['calculate_compressors'] = True
            config['no_compressors'] = len(detected_equipment[EquipmentType.COMPRESSOR])
            config['compressor_names'] = [e['name'] for e in detected_equipment[EquipmentType.COMPRESSOR]]
        
        # 진공 시스템
        if detected_equipment.get(EquipmentType.VACUUM_SYSTEM):
            config['calculate_vacuum'] = True
            config['no_vacuum_systems'] = len(detected_equipment[EquipmentType.VACUUM_SYSTEM])
            config['vacuum_system_names'] = [e['name'] for e in detected_equipment[EquipmentType.VACUUM_SYSTEM]]
        
        # 증발기
        if detected_equipment.get(EquipmentType.EVAPORATOR):
            config['calculate_evaporators'] = True
            config['no_evaporators'] = len(detected_equipment[EquipmentType.EVAPORATOR])
            config['evaporator_names'] = [e['name'] for e in detected_equipment[EquipmentType.EVAPORATOR]]
        
        # 분리기
        if detected_equipment.get(EquipmentType.SEPARATOR):
            config['calculate_separators'] = True
            config['no_separators'] = len(detected_equipment[EquipmentType.SEPARATOR])
            config['separator_names'] = [e['name'] for e in detected_equipment[EquipmentType.SEPARATOR]]
        
        # 혼합기
        if detected_equipment.get(EquipmentType.MIXER):
            config['calculate_mixers'] = True
            config['no_mixers'] = len(detected_equipment[EquipmentType.MIXER])
            config['mixer_names'] = [e['name'] for e in detected_equipment[EquipmentType.MIXER]]
        
        # 분할기
        if detected_equipment.get(EquipmentType.SPLITTER):
            config['calculate_splitters'] = True
            config['no_splitters'] = len(detected_equipment[EquipmentType.SPLITTER])
            config['splitter_names'] = [e['name'] for e in detected_equipment[EquipmentType.SPLITTER]]
        
        # 기본값 설정
        config.update({
            'fouling_factor': 0.9,
            'tube_length_factor': 1.05,
            'material_factor_hx': 1.0,
            'material_factor_pumps': 2.0,
            'tray_spacing': 0.5,
            'top_space': 1.5,
            'bottom_space': 1.5,
            'reactor_liquid_fill': 0.65,
            'reactor_h_d_ratio': 3.0,
            'reactor_material_factor': 2.1,
            'reactor_density': 8000,
            'column_material_factor': 2.1,
            'column_density': 8000
        })
        
        return config
    
    def _detect_heat_exchangers(self) -> Dict[str, Any]:
        """열교환기 자동 감지"""
        try:
            heat_exchangers = []
            count = 0
            
            # 방법 1: E01, E02, E03... 형태로 명명된 열교환기 검색
            for i in range(1, 100):  # 최대 99개까지 검색
                try:
                    block_name = f"E{i:02d}"
                    # 블록이 존재하는지 확인
                    block_path = f"\\Data\\Blocks\\{block_name}"
                    block_node = self.Application.Tree.FindNode(block_path)
                    if block_node:
                        heat_exchangers.append(block_name)
                        count += 1
                except:
                    break
            
            # 방법 2: HEX가 포함된 블록 검색
            try:
                blocks_node = self.Application.Tree.FindNode("\\Data\\Blocks")
                if blocks_node:
                    for i in range(blocks_node.Count):
                        try:
                            block_name = blocks_node.Item(i).Name
                            # HEX가 포함된 블록 검색 (이미 찾은 E01, E02... 제외)
                            if 'HEX' in block_name.upper() and block_name not in heat_exchangers:
                                heat_exchangers.append(block_name)
                                count += 1
                        except:
                            continue
            except:
                pass
            
            return {
                'count': count,
                'names': heat_exchangers
            }
            
        except Exception as e:
            print(f"열교환기 감지 중 오류: {e}")
            return {'count': 0, 'names': []}
    
    def _detect_distillation_columns(self) -> Dict[str, Any]:
        """증류탑 자동 감지"""
        try:
            columns = []
            configs = []
            
            # RADFRAC 블록 검색
            try:
                blocks_node = self.Application.Tree.FindNode("\\Data\\Blocks")
                if blocks_node:
                    for i in range(blocks_node.Count):
                        try:
                            block_name = blocks_node.Item(i).Name
                            # RADFRAC, DIST, COLUMN, DISTIL로 시작하거나 포함된 블록 검색
                            if (block_name.startswith(('RADFRAC', 'DIST', 'COLUMN')) or 
                                'DISTIL' in block_name.upper() or
                                'DIST' in block_name.upper()):
                                columns.append(block_name)
                                configs.append({
                                    'name': block_name,
                                    'tray_spacing': 0.5,
                                    'top_space': 1.5,
                                    'bottom_space': 1.5,
                                    'density': 8000,
                                    'material_factor': 2.1
                                })
                        except:
                            continue
            except:
                pass
            
            return {
                'count': len(columns),
                'names': columns,
                'configs': configs
            }
            
        except Exception as e:
            print(f"증류탑 감지 중 오류: {e}")
            return {'count': 0, 'names': [], 'configs': []}
    
    def _detect_reactors(self) -> Dict[str, Any]:
        """반응기 자동 감지"""
        try:
            reactors = []
            configs = []
            
            # 반응기 블록 검색 (CSTR, R, REACTOR 등)
            try:
                blocks_node = self.Application.Tree.FindNode("\\Data\\Blocks")
                if blocks_node:
                    for i in range(blocks_node.Count):
                        try:
                            block_name = blocks_node.Item(i).Name
                            # 반응기 관련 블록 검색
                            if any(keyword in block_name.upper() for keyword in ['CSTR', 'R', 'REACTOR', 'RX', 'RE', 'COMB']):
                                reactors.append(block_name)
                                configs.append({
                                    'name': block_name,
                                    'liquid_fill': 0.65,
                                    'h_d_ratio': 3.0,
                                    'material_factor': 2.1,
                                    'density': 8000
                                })
                        except:
                            continue
            except:
                pass
            
            return {
                'count': len(reactors),
                'names': reactors,
                'configs': configs
            }
            
        except Exception as e:
            print(f"반응기 감지 중 오류: {e}")
            return {'count': 0, 'names': [], 'configs': []}
    
    def _detect_pumps(self) -> Dict[str, Any]:
        """펌프 자동 감지"""
        try:
            pumps = []
            count = 0
            
            # 방법 1: P01, P02, P03... 형태로 명명된 펌프 검색 (P로 시작하는 것만)
            for i in range(1, 100):  # 최대 99개까지 검색
                try:
                    block_name = f"P{i:02d}"
                    # 블록이 존재하는지 확인
                    block_path = f"\\Data\\Blocks\\{block_name}"
                    block_node = self.Application.Tree.FindNode(block_path)
                    if block_node:
                        pumps.append(block_name)
                        count += 1
                except:
                    break
            
            # 방법 2: PUMP가 포함된 블록 검색
            try:
                blocks_node = self.Application.Tree.FindNode("\\Data\\Blocks")
                if blocks_node:
                    for i in range(blocks_node.Count):
                        try:
                            block_name = blocks_node.Item(i).Name
                            # PUMP가 포함된 블록 검색 (이미 찾은 P01, P02... 제외)
                            if 'PUMP' in block_name.upper() and block_name not in pumps:
                                pumps.append(block_name)
                                count += 1
                        except:
                            continue
            except:
                pass
            
            return {
                'count': count,
                'names': pumps
            }
            
        except Exception as e:
            print(f"펌프 감지 중 오류: {e}")
            return {'count': 0, 'names': []}
    
    def _detect_compressors(self) -> Dict[str, Any]:
        """압축기 자동 감지"""
        try:
            compressors = []
            count = 0
            
            # 방법 1: C01, C02, C03... 형태로 명명된 압축기 검색 (C로 시작하는 것만)
            for i in range(1, 100):  # 최대 99개까지 검색
                try:
                    block_name = f"C{i:02d}"
                    # 블록이 존재하는지 확인
                    block_path = f"\\Data\\Blocks\\{block_name}"
                    block_node = self.Application.Tree.FindNode(block_path)
                    if block_node:
                        compressors.append(block_name)
                        count += 1
                except:
                    break
            
            # 방법 2: COMP가 포함된 블록 검색
            try:
                blocks_node = self.Application.Tree.FindNode("\\Data\\Blocks")
                if blocks_node:
                    for i in range(blocks_node.Count):
                        try:
                            block_name = blocks_node.Item(i).Name
                            # COMP가 포함된 블록 검색 (이미 찾은 C01, C02... 제외)
                            if 'COMP' in block_name.upper() and block_name not in compressors:
                                compressors.append(block_name)
                                count += 1
                        except:
                            continue
            except:
                pass
            
            return {
                'count': count,
                'names': compressors
            }
            
        except Exception as e:
            print(f"압축기 감지 중 오류: {e}")
            return {'count': 0, 'names': []}
    
    def generate_config_file(self, config: Dict[str, Any], filename: str = "auto_generated_config.py"):
        """감지된 설정을 Python 설정 파일로 생성"""
        try:
            config_content = f'''# -*- coding: utf-8 -*-
"""
자동 생성된 장비 설정 파일
생성일: {time.strftime("%Y-%m-%d %H:%M:%S")}
파일: {self.aspen_file_path}

이 파일은 TotalEquipmentCostCalculator.py의 auto_detect_equipment() 함수로 자동 생성되었습니다.
필요에 따라 값을 수정하여 사용하세요.
"""

equipment_config = {{
    # 계산할 장비 선택
    'calculate_heat_exchangers': {config.get('calculate_heat_exchangers', False)},
    'calculate_distillation': {config.get('calculate_distillation', False)},
    'calculate_reactors': {config.get('calculate_reactors', False)},
    'calculate_pumps': {config.get('calculate_pumps', False)},
    
    # 열교환기 설정
    'no_heat_exchangers': {config.get('no_heat_exchangers', 0)},
    'fouling_factor': {config.get('fouling_factor', 0.9)},
    'tube_length_factor': {config.get('tube_length_factor', 1.05)},
    'material_factor_hx': {config.get('material_factor_hx', 1.0)},
'''
            
            if config.get('calculate_distillation'):
                config_content += f'''    
    # 증류탑 설정
    'radfrac_columns': {config.get('radfrac_columns', [])},
'''
            
            if config.get('calculate_reactors'):
                config_content += f'''    
    # 반응기 설정
    'reactors': {config.get('reactors', [])},
'''
            
            if config.get('calculate_pumps'):
                config_content += f'''    
    # 펌프 설정
    'no_pumps': {config.get('no_pumps', 0)},
    'material_factor_pumps': {config.get('material_factor_pumps', 2.0)},
'''
            
            config_content += '''}
'''
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            print(f"\n설정 파일이 '{filename}'로 저장되었습니다.")
            print("이 파일을 수정하여 필요에 맞게 조정할 수 있습니다.")
            
        except Exception as e:
            print(f"설정 파일 생성 중 오류: {e}")
        
    def connect_to_aspen(self) -> bool:
        """Aspen Plus에 연결"""
        try:
            if not os.path.exists(self.aspen_file_path):
                print(f"ERROR: File not found: {self.aspen_file_path}")
                return False
            
            print(f"File found: {self.aspen_file_path}")
            
            # Aspen Plus 연결
            connect_spinner = Spinner('Connecting to Aspen Plus')
            connect_spinner.start()
            self.Application = win32.Dispatch('Apwn.Document')
            connect_spinner.stop('Aspen Plus COM object created successfully!')
            
            # 파일 열기
            open_spinner = Spinner('Opening Aspen backup file')
            open_spinner.start()
            self.Application.InitFromArchive2(self.aspen_file_path)
            open_spinner.stop('File opened successfully!')
            
            # Aspen Plus 화면 표시
            self.Application.visible = 1
            print('Aspen Plus is now visible')
            
            return True
            
        except Exception as e:
            print(f"ERROR connecting to Aspen Plus: {e}")
            return False
    
    def calculate_heat_exchangers(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """열교환기 비용 계산"""
        try:
            spinner = Spinner('Calculating Heat Exchanger costs')
            spinner.start()
            
            No_Heat_Exchanger = config.get('no_heat_exchangers', 0)
            if No_Heat_Exchanger == 0:
                spinner.stop('No heat exchangers found - skipped')
                return {'total_cost': 0, 'individual_costs': [], 'heat_duties': [], 'areas': []}
            
            fouling_factor = config.get('fouling_factor', 0.9)
            E_FL = np.ones(No_Heat_Exchanger) * config.get('tube_length_factor', 1.05)
            E_FM = np.ones(No_Heat_Exchanger) * config.get('material_factor_hx', 1.0)
            
            total_cost, individual_costs, heat_duties, areas = heatexchanger(
                self.Application, No_Heat_Exchanger, fouling_factor, E_FM, E_FL, self.cost_index
            )
            
            spinner.stop(f'Heat Exchanger calculation completed - ${total_cost:,.2f}')
            
            return {
                'total_cost': total_cost,
                'individual_costs': individual_costs,
                'heat_duties': heat_duties,
                'areas': areas
            }
            
        except Exception as e:
            spinner.stop(f'Heat Exchanger calculation failed: {e}')
            return {'total_cost': 0, 'individual_costs': [], 'heat_duties': [], 'areas': [], 'error': str(e)}
    
    def calculate_distillation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """증류탑 비용 계산"""
        try:
            spinner = Spinner('Calculating Distillation costs')
            spinner.start()
            
            total_cost = 0
            results = {}
            
            # RADFRAC 증류탑들
            radfrac_columns = config.get('radfrac_columns', [])
            for column_config in radfrac_columns:
                name = column_config['name']
                tray_spacing = column_config.get('tray_spacing', 0.5)
                top_space = column_config.get('top_space', 1.5)
                bottom_space = column_config.get('bottom_space', 1.5)
                d_rho = column_config.get('density', 8000)
                F_M = column_config.get('material_factor', 2.1)
                
                cost, diameter, volume = distillationRADFRAC(
                    self.Application, name, tray_spacing, top_space, bottom_space, 
                    d_rho, F_M, self.cost_index
                )
                
                results[f'radfrac_{name}'] = {
                    'cost': cost, 'diameter': diameter, 'volume': volume
                }
                total_cost += cost
            
            spinner.stop(f'Distillation calculation completed - ${total_cost:,.2f}')
            
            return {
                'total_cost': total_cost,
                'details': results
            }
            
        except Exception as e:
            spinner.stop(f'Distillation calculation failed: {e}')
            return {'total_cost': 0, 'details': {}, 'error': str(e)}
    
    def calculate_reactors(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """반응기 비용 계산"""
        try:
            spinner = Spinner('Calculating Reactor costs')
            spinner.start()
            
            total_cost = 0
            results = {}
            
            reactors = config.get('reactors', [])
            for reactor_config in reactors:
                name = reactor_config['name']
                liquid_fill = reactor_config.get('liquid_fill', 0.65)
                h_d_ratio = reactor_config.get('h_d_ratio', 3.0)
                F_M = reactor_config.get('material_factor', 2.1)
                rho = reactor_config.get('density', 8000)
                
                volume, cost = reactorCSTR(
                    self.Application, liquid_fill, h_d_ratio, F_M, rho, name, self.cost_index
                )
                
                results[f'reactor_{name}'] = {
                    'cost': cost, 'volume': volume
                }
                total_cost += cost
            
            spinner.stop(f'Reactor calculation completed - ${total_cost:,.2f}')
            
            return {
                'total_cost': total_cost,
                'details': results
            }
            
        except Exception as e:
            spinner.stop(f'Reactor calculation failed: {e}')
            return {'total_cost': 0, 'details': {}, 'error': str(e)}
    
    def calculate_pumps(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """펌프 비용 계산"""
        try:
            spinner = Spinner('Calculating Pump costs')
            spinner.start()
            
            No_pumps = config.get('no_pumps', 0)
            if No_pumps == 0:
                spinner.stop('No pumps found - skipped')
                return {'total_cost': 0, 'pump_costs': [], 'motor_costs': [], 'heads': [], 'flowrates': []}
            
            material_factor = config.get('material_factor_pumps', 2.0)
            
            total_cost, motor_costs, pump_costs, heads, flowrates = pumps(
                self.Application, No_pumps, material_factor, self.cost_index
            )
            
            spinner.stop(f'Pump calculation completed - ${total_cost:,.2f}')
            
            return {
                'total_cost': total_cost,
                'pump_costs': pump_costs,
                'motor_costs': motor_costs,
                'heads': heads,
                'flowrates': flowrates
            }
            
        except Exception as e:
            spinner.stop(f'Pump calculation failed: {e}')
            return {'total_cost': 0, 'pump_costs': [], 'motor_costs': [], 'heads': [], 'flowrates': [], 'error': str(e)}
    
    def calculate_all_equipment(self, equipment_config: Dict[str, Any]) -> Dict[str, Any]:
        """모든 장비 비용 계산"""
        print("\n" + "="*60)
        print("         전체 장비 비용 계산 시작")
        print("="*60)
        
        all_results = {}
        total_plant_cost = 0
        
        # 1. 열교환기
        if equipment_config.get('calculate_heat_exchangers', True):
            hx_results = self.calculate_heat_exchangers(equipment_config)
            all_results['heat_exchangers'] = hx_results
            total_plant_cost += hx_results['total_cost']
        
        # 2. 증류탑
        if equipment_config.get('calculate_distillation', True):
            dist_results = self.calculate_distillation(equipment_config)
            all_results['distillation'] = dist_results
            total_plant_cost += dist_results['total_cost']
        
        # 3. 반응기
        if equipment_config.get('calculate_reactors', True):
            reactor_results = self.calculate_reactors(equipment_config)
            all_results['reactors'] = reactor_results
            total_plant_cost += reactor_results['total_cost']
        
        # 4. 펌프
        if equipment_config.get('calculate_pumps', True):
            pump_results = self.calculate_pumps(equipment_config)
            all_results['pumps'] = pump_results
            total_plant_cost += pump_results['total_cost']
        
        all_results['total_plant_cost'] = total_plant_cost
        
        return all_results
    
    def print_summary_report(self, results: Dict[str, Any]):
        """결과 요약 보고서 출력"""
        print("\n" + "="*60)
        print("              장비 비용 계산 결과 요약")
        print("="*60)
        
        # 열교환기
        if 'heat_exchangers' in results:
            hx = results['heat_exchangers']
            print(f"열교환기 총 비용:        ${hx['total_cost']:>15,.2f}")
            if len(hx['individual_costs']) > 0:
                print(f"  - 개수: {len(hx['individual_costs'])}개")
        
        # 증류탑
        if 'distillation' in results:
            dist = results['distillation']
            print(f"증류탑 총 비용:          ${dist['total_cost']:>15,.2f}")
            if 'details' in dist:
                print(f"  - 개수: {len(dist['details'])}개")
        
        # 반응기
        if 'reactors' in results:
            reactor = results['reactors']
            print(f"반응기 총 비용:          ${reactor['total_cost']:>15,.2f}")
            if 'details' in reactor:
                print(f"  - 개수: {len(reactor['details'])}개")
        
        # 펌프
        if 'pumps' in results:
            pump = results['pumps']
            print(f"펌프 총 비용:            ${pump['total_cost']:>15,.2f}")
            if len(pump['pump_costs']) > 0:
                print(f"  - 개수: {len(pump['pump_costs'])}개")
        
        print("-" * 60)
        print(f"전체 장비 총 비용:       ${results['total_plant_cost']:>15,.2f}")
        print("=" * 60)
        
        # 에러 체크
        errors = []
        for equipment_type, equipment_results in results.items():
            if isinstance(equipment_results, dict) and 'error' in equipment_results:
                errors.append(f"{equipment_type}: {equipment_results['error']}")
        
        if errors:
            print("\n주의: 다음 계산에서 오류가 발생했습니다:")
            for error in errors:
                print(f"  - {error}")

def get_manual_config() -> Dict[str, Any]:
    """수동으로 장비 설정을 입력받는 함수"""
    print("\n" + "="*60)
    print("         수동 장비 설정")
    print("="*60)
    
    config = {}
    
    # 열교환기 설정
    print("\n--- 열교환기 설정 ---")
    config['calculate_heat_exchangers'] = input("열교환기 비용을 계산하시겠습니까? (y/n): ").lower().strip() in ['y', 'yes', '예']
    
    if config['calculate_heat_exchangers']:
        config['no_heat_exchangers'] = int(input("열교환기 개수를 입력하세요 (예: 8): "))
        config['fouling_factor'] = float(input("오염계수를 입력하세요 (기본값: 0.9): ") or "0.9")
        config['tube_length_factor'] = float(input("튜브 길이 보정계수를 입력하세요 (기본값: 1.05): ") or "1.05")
        config['material_factor_hx'] = float(input("재질계수를 입력하세요 (탄소강=1.0, 스테인리스강=1.75): ") or "1.0")
    
    # 증류탑 설정
    print("\n--- 증류탑 설정 ---")
    config['calculate_distillation'] = input("증류탑 비용을 계산하시겠습니까? (y/n): ").lower().strip() in ['y', 'yes', '예']
    
    if config['calculate_distillation']:
        num_columns = int(input("증류탑 개수를 입력하세요: "))
        config['radfrac_columns'] = []
        
        for i in range(num_columns):
            print(f"\n증류탑 {i+1} 설정:")
            column_config = {
                'name': input(f"블록 이름을 입력하세요: "),
                'tray_spacing': float(input("트레이 간격 (미터, 기본값: 0.5): ") or "0.5"),
                'top_space': float(input("상단 여유 공간 (미터, 기본값: 1.5): ") or "1.5"),
                'bottom_space': float(input("하단 여유 공간 (미터, 기본값: 1.5): ") or "1.5"),
                'density': float(input("재질 밀도 (kg/m³, 기본값: 8000): ") or "8000"),
                'material_factor': float(input("재질계수 (기본값: 2.1): ") or "2.1")
            }
            config['radfrac_columns'].append(column_config)
    
    # 반응기 설정
    print("\n--- 반응기 설정 ---")
    config['calculate_reactors'] = input("반응기 비용을 계산하시겠습니까? (y/n): ").lower().strip() in ['y', 'yes', '예']
    
    if config['calculate_reactors']:
        num_reactors = int(input("반응기 개수를 입력하세요: "))
        config['reactors'] = []
        
        for i in range(num_reactors):
            print(f"\n반응기 {i+1} 설정:")
            reactor_config = {
                'name': input(f"블록 이름을 입력하세요: "),
                'liquid_fill': float(input("액체 충전률 (기본값: 0.65): ") or "0.65"),
                'h_d_ratio': float(input("높이/직경 비 (기본값: 3.0): ") or "3.0"),
                'material_factor': float(input("재질계수 (기본값: 2.1): ") or "2.1"),
                'density': float(input("재질 밀도 (kg/m³, 기본값: 8000): ") or "8000")
            }
            config['reactors'].append(reactor_config)
    
    # 펌프 설정
    print("\n--- 펌프 설정 ---")
    config['calculate_pumps'] = input("펌프 비용을 계산하시겠습니까? (y/n): ").lower().strip() in ['y', 'yes', '예']
    
    if config['calculate_pumps']:
        config['no_pumps'] = int(input("펌프 개수를 입력하세요 (예: 3): "))
        config['material_factor_pumps'] = float(input("재질계수를 입력하세요 (기본값: 2.0): ") or "2.0")
    
    return config

def main():
    """메인 실행 함수"""
    
    print("="*60)
    print("    전체 장비 비용 계산기 (Total Equipment Cost Calculator)")
    print("="*60)
    
    # Aspen Plus 파일 경로 (사용자가 수정해야 함)
    aspen_file = os.path.join(current_dir, 'MIX_HEFA_20250716_after_HI_v1.bkp')
    
    # 파일 존재 여부 확인
    if not os.path.exists(aspen_file):
        print(f"❌ 파일을 찾을 수 없습니다: {aspen_file}")
        print("현재 폴더에 MIX_HEFA_20250716_after_HI_v1.bkp 파일이 있는지 확인하세요.")
        return
    
    print(f"✓ 파일 경로 확인됨: {aspen_file}")
    
    # 비용 지수 (연도별로 조정)
    cost_index_2019 = 607.5
    
    # 계산기 초기화
    calculator = TotalEquipmentCostCalculator(aspen_file, cost_index_2019)
    
    # Aspen Plus 연결
    if not calculator.connect_to_aspen():
        print("Aspen Plus 연결에 실패했습니다.")
        return
    
    # 장비 탐지 방식 선택
    print("\n장비 탐지 방식을 선택하세요:")
    print("1. 스마트 탐지 (권장) - 다양한 명명법 자동 인식")
    print("2. 기본 탐지 - 기존 패턴 기반 탐지")
    print("3. 수동 설정 - 사용자가 직접 입력")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    if choice == '1':
        # 스마트 탐지 실행
        equipment_config = calculator.smart_detect_equipment()
        
        if equipment_config:
            # 감지된 설정을 파일로 저장
            calculator.generate_config_file(equipment_config)
            
            print("\n스마트 탐지된 설정으로 계산을 진행하시겠습니까? (y/n): ", end="")
            use_smart_config = input().lower().strip()
            
            if use_smart_config not in ['y', 'yes', '예']:
                print("수동 설정을 사용합니다.")
                equipment_config = get_manual_config()
        else:
            print("스마트 탐지에 실패했습니다. 기본 탐지를 시도합니다.")
            equipment_config = calculator.auto_detect_equipment()
            
            if not equipment_config:
                print("기본 탐지도 실패했습니다. 수동 설정을 사용합니다.")
                equipment_config = get_manual_config()
    
    elif choice == '2':
        # 기본 자동 감지 실행
        equipment_config = calculator.auto_detect_equipment()
        
        if equipment_config:
            # 감지된 설정을 파일로 저장
            calculator.generate_config_file(equipment_config)
            
            print("\n기본 탐지된 설정으로 계산을 진행하시겠습니까? (y/n): ", end="")
            use_auto_config = input().lower().strip()
            
            if use_auto_config not in ['y', 'yes', '예']:
                print("수동 설정을 사용합니다.")
                equipment_config = get_manual_config()
        else:
            print("기본 탐지에 실패했습니다. 수동 설정을 사용합니다.")
            equipment_config = get_manual_config()
    
    else:
        # 수동 설정 사용
        equipment_config = get_manual_config()
    
    # 모든 장비 비용 계산
    results = calculator.calculate_all_equipment(equipment_config)
    
    # 결과 출력
    calculator.print_summary_report(results)
    
    # 결과를 파일로 저장 (선택사항)
    import json
    with open('equipment_cost_results.json', 'w', encoding='utf-8') as f:
        # numpy 배열을 리스트로 변환
        json_results = {}
        for key, value in results.items():
            if isinstance(value, dict):
                json_value = {}
                for k, v in value.items():
                    if isinstance(v, np.ndarray):
                        json_value[k] = v.tolist()
                    else:
                        json_value[k] = v
                json_results[key] = json_value
            else:
                json_results[key] = value
        
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과가 'equipment_cost_results.json' 파일로 저장되었습니다.")

if __name__ == "__main__":
    main()
