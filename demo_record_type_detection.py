# -*- coding: utf-8 -*-
"""
스마트 장비 탐지 시스템 (Smart Equipment Detector)
Aspen Plus의 Record Type을 직접 확인하여 장비를 정확하게 분류합니다.

@author: Assistant
@created: 2025-01-22
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class EquipmentType(Enum):
    """장비 타입 열거형"""
    HEAT_EXCHANGER = "heat_exchanger"
    DISTILLATION_COLUMN = "distillation_column"
    REACTOR = "reactor"
    PUMP = "pump"
    COMPRESSOR = "compressor"
    VACUUM_SYSTEM = "vacuum_system"
    EVAPORATOR = "evaporator"
    SEPARATOR = "separator"
    MIXER = "mixer"
    SPLITTER = "splitter"
    FLASH = "flash"
    VALVE = "valve"
    STREAM = "stream"
    UTILITY = "utility"
    UNKNOWN = "unknown"

@dataclass
class RecordTypeMapping:
    """Record Type과 장비 타입 매핑"""
    type: EquipmentType
    record_types: List[str]
    description: str
    priority: int  # 높을수록 우선순위가 높음

class SmartEquipmentDetector:
    """Record Type 기반 스마트 장비 탐지기"""
    
    def __init__(self):
        """초기화"""
        self.record_type_mappings = self._initialize_record_type_mappings()
        
    def _initialize_record_type_mappings(self) -> List[RecordTypeMapping]:
        """Record Type 매핑 초기화"""
        return [
            # 열교환기 - 가장 다양한 Record Type을 가짐
            RecordTypeMapping(
                type=EquipmentType.HEAT_EXCHANGER,
                record_types=[
                    'HeatX', 'Heater', 'Cooler', 'Condenser', 'Reboiler',
                    'HeatX-1', 'HeatX-2', 'Heater-1', 'Cooler-1', 'Condenser-1'
                ],
                description="열교환기, 가열기, 냉각기, 응축기, 리보일러",
                priority=10
            ),
            
            # 증류탑
            RecordTypeMapping(
                type=EquipmentType.DISTILLATION_COLUMN,
                record_types=[
                    'RadFrac', 'Distl', 'DWSTU', 'Column', 'Tower',
                    'RadFrac-1', 'Distl-1', 'DWSTU-1', 'Column-1'
                ],
                description="증류탑, 분리탑, 정류탑",
                priority=9
            ),
            
            # 반응기
            RecordTypeMapping(
                type=EquipmentType.REACTOR,
                record_types=[
                    'RStoic', 'RPlug', 'RCSTR', 'RBatch', 'REquil',
                    'RStoic-1', 'RPlug-1', 'RCSTR-1', 'RBatch-1', 'REquil-1'
                ],
                description="화학반응기, 정량반응기, 플러그플로우, CSTR, 배치반응기",
                priority=8
            ),
            
            # 펌프
            RecordTypeMapping(
                type=EquipmentType.PUMP,
                record_types=[
                    'Pump', 'Compr', 'MCompr', 'Valve', 'Pump-1', 'Compr-1'
                ],
                description="펌프, 압축기, 밸브",
                priority=7
            ),
            
            # 압축기
            RecordTypeMapping(
                type=EquipmentType.COMPRESSOR,
                record_types=[
                    'Compr', 'MCompr', 'Compr-1', 'MCompr-1'
                ],
                description="압축기, 다단압축기",
                priority=6
            ),
            
            # 진공 시스템
            RecordTypeMapping(
                type=EquipmentType.VACUUM_SYSTEM,
                record_types=[
                    'Vacuum', 'Ejector', 'Vacuum-1', 'Ejector-1'
                ],
                description="진공 시스템, 이젝터",
                priority=5
            ),
            
            # 증발기
            RecordTypeMapping(
                type=EquipmentType.EVAPORATOR,
                record_types=[
                    'Flash', 'Flash2', 'Flash3', 'Evaporator',
                    'Flash-1', 'Flash2-1', 'Flash3-1', 'Evaporator-1'
                ],
                description="플래시 드럼, 증발기, 결정화기",
                priority=4
            ),
            
            # 분리기
            RecordTypeMapping(
                type=EquipmentType.SEPARATOR,
                record_types=[
                    'Sep', 'Decanter', 'Filter', 'Centrifuge',
                    'Sep-1', 'Decanter-1', 'Filter-1', 'Centrifuge-1'
                ],
                description="분리기, 디캔터, 필터, 원심분리기",
                priority=3
            ),
            
            # 혼합기
            RecordTypeMapping(
                type=EquipmentType.MIXER,
                record_types=[
                    'Mixer', 'Blender', 'Agitator', 'Mixer-1', 'Blender-1'
                ],
                description="혼합기, 블렌더, 교반기",
                priority=2
            ),
            
            # 분할기
            RecordTypeMapping(
                type=EquipmentType.SPLITTER,
                record_types=[
                    'Splitter', 'Divider', 'Manifold', 'Splitter-1', 'Divider-1'
                ],
                description="분할기, 분배기, 매니폴드",
                priority=1
            ),
            
            # 밸브
            RecordTypeMapping(
                type=EquipmentType.VALVE,
                record_types=[
                    'Valve', 'Valve-1', 'Valve-2'
                ],
                description="밸브, 제어밸브",
                priority=1
            ),
            
            # 유틸리티
            RecordTypeMapping(
                type=EquipmentType.UTILITY,
                record_types=[
                    'Utility', 'Utility-1', 'Utility-2'
                ],
                description="유틸리티, 보조설비",
                priority=1
            )
        ]
    
    def detect_equipment_from_aspen(self, aspen_application) -> Dict[EquipmentType, List[Dict[str, Any]]]:
        """
        Aspen Plus 애플리케이션에서 직접 장비를 탐지
        
        Args:
            aspen_application: Aspen Plus COM 객체
            
        Returns:
            장비 타입별로 분류된 장비 정보 딕셔너리
        """
        try:
            detected_equipment = {equip_type: [] for equip_type in EquipmentType}
            
            # Blocks 노드에서 모든 블록 정보 가져오기
            blocks_node = aspen_application.Tree.FindNode("\\Data\\Blocks")
            if not blocks_node:
                print("ERROR: Blocks 노드를 찾을 수 없습니다.")
                return detected_equipment
            
            print(f"총 {blocks_node.Count}개의 블록을 발견했습니다.")
            
            for i in range(blocks_node.Count):
                try:
                    block_node = blocks_node.Item(i)
                    block_name = block_node.Name
                    
                    # Record Type 확인
                    record_type = self._get_record_type(aspen_application, block_name)
                    
                    if record_type:
                        # Record Type을 기반으로 장비 분류
                        equipment_info = self._classify_by_record_type(block_name, record_type)
                        if equipment_info:
                            detected_equipment[equipment_info['type']].append(equipment_info)
                            print(f"✓ {block_name} -> {record_type} -> {equipment_info['type'].value}")
                        else:
                            # 분류되지 않은 장비는 UNKNOWN으로 분류
                            unknown_info = {
                                'type': EquipmentType.UNKNOWN,
                                'name': block_name,
                                'record_type': record_type,
                                'detection_method': 'record_type',
                                'confidence': 0.5,
                                'config': {}
                            }
                            detected_equipment[EquipmentType.UNKNOWN].append(unknown_info)
                            print(f"? {block_name} -> {record_type} -> UNKNOWN")
                    else:
                        print(f"⚠ {block_name} -> Record Type 확인 불가")
                        
                except Exception as e:
                    print(f"⚠ 블록 {i} 처리 중 오류: {e}")
                    continue
            
            return detected_equipment
            
        except Exception as e:
            print(f"ERROR during Aspen Plus detection: {e}")
            return {equip_type: [] for equip_type in EquipmentType}
    
    def _get_record_type(self, aspen_application, block_name: str) -> str:
        """
        특정 블록의 Record Type 가져오기
        
        Args:
            aspen_application: Aspen Plus COM 객체
            block_name: 블록명
            
        Returns:
            Record Type 문자열 또는 None
        """
        try:
            # 방법 1: 직접 Record Type 노드 확인
            record_type_path = f"\\Data\\Blocks\\{block_name}\\Input\\RECORD_TYPE"
            record_type_node = aspen_application.Tree.FindNode(record_type_path)
            if record_type_node:
                return record_type_node.Value
            
            # 방법 2: 블록 타입 확인
            block_type_path = f"\\Data\\Blocks\\{block_name}\\Input\\BLOCK_TYPE"
            block_type_node = aspen_application.Tree.FindNode(block_type_path)
            if block_type_node:
                return block_type_node.Value
            
            # 방법 3: 블록 속성에서 확인
            try:
                block_node = aspen_application.Tree.FindNode(f"\\Data\\Blocks\\{block_name}")
                if hasattr(block_node, 'BlockType'):
                    return block_node.BlockType
            except:
                pass
            
            return None
            
        except Exception as e:
            print(f"Record Type 확인 중 오류 ({block_name}): {e}")
            return None
    
    def _classify_by_record_type(self, block_name: str, record_type: str) -> Dict[str, Any]:
        """
        Record Type을 기반으로 장비 분류
        
        Args:
            block_name: 블록명
            record_type: Record Type
            
        Returns:
            장비 정보 딕셔너리 또는 None
        """
        record_type_upper = record_type.upper()
        
        # 우선순위가 높은 순서대로 매핑 확인
        for mapping in sorted(self.record_type_mappings, key=lambda x: x.priority, reverse=True):
            for rt in mapping.record_types:
                if rt.upper() in record_type_upper or record_type_upper in rt.upper():
                    return self._create_equipment_info(
                        mapping.type, 
                        block_name, 
                        'record_type', 
                        record_type,
                        mapping.description
                    )
        
        return None
    
    def _create_equipment_info(self, equip_type: EquipmentType, block_name: str, 
                              detection_method: str, record_type: str, description: str) -> Dict[str, Any]:
        """
        장비 정보 딕셔너리 생성
        
        Args:
            equip_type: 장비 타입
            block_name: 블록명
            detection_method: 탐지 방법
            record_type: Record Type
            description: 장비 설명
            
        Returns:
            장비 정보 딕셔너리
        """
        return {
            'type': equip_type,
            'name': block_name,
            'record_type': record_type,
            'description': description,
            'detection_method': detection_method,
            'confidence': self._calculate_confidence(equip_type, detection_method),
            'config': self._get_default_config(equip_type)
        }
    
    def _calculate_confidence(self, equip_type: EquipmentType, detection_method: str) -> float:
        """
        탐지 신뢰도 계산
        
        Args:
            equip_type: 장비 타입
            detection_method: 탐지 방법
            
        Returns:
            신뢰도 (0.0 ~ 1.0)
        """
        base_confidence = 0.9  # Record Type 기반이므로 기본 신뢰도 높음
        
        # 장비 타입별 신뢰도 조정
        if equip_type == EquipmentType.HEAT_EXCHANGER:
            base_confidence += 0.05  # 가장 명확한 분류
        elif equip_type == EquipmentType.UNKNOWN:
            base_confidence = 0.3  # 미분류는 신뢰도 낮음
        
        return min(base_confidence, 1.0)
    
    def _get_default_config(self, equip_type: EquipmentType) -> Dict[str, Any]:
        """
        장비 타입별 기본 설정 반환
        
        Args:
            equip_type: 장비 타입
            
        Returns:
            기본 설정 딕셔너리
        """
        configs = {
            EquipmentType.HEAT_EXCHANGER: {
                'fouling_factor': 0.9,
                'material_factor': 1.0,
                'tube_length_factor': 1.05
            },
            EquipmentType.DISTILLATION_COLUMN: {
                'tray_spacing': 0.5,
                'top_space': 1.5,
                'bottom_space': 1.5,
                'density': 8000,
                'material_factor': 2.1
            },
            EquipmentType.REACTOR: {
                'liquid_fill': 0.65,
                'h_d_ratio': 3.0,
                'material_factor': 2.1,
                'density': 8000
            },
            EquipmentType.PUMP: {
                'material_factor': 2.0
            },
            EquipmentType.COMPRESSOR: {
                'material_factor': 2.5
            },
            EquipmentType.VACUUM_SYSTEM: {
                'material_factor': 1.5
            },
            EquipmentType.EVAPORATOR: {
                'material_factor': 1.8
            },
            EquipmentType.SEPARATOR: {
                'material_factor': 1.2
            },
            EquipmentType.MIXER: {
                'material_factor': 1.0
            },
            EquipmentType.SPLITTER: {
                'material_factor': 1.0
            },
            EquipmentType.FLASH: {
                'material_factor': 1.5
            },
            EquipmentType.VALVE: {
                'material_factor': 1.0
            },
            EquipmentType.UTILITY: {
                'material_factor': 1.0
            },
            EquipmentType.UNKNOWN: {
                'material_factor': 1.0
            }
        }
        
        return configs.get(equip_type, {})
    
    def generate_detection_report(self, detected_equipment: Dict[EquipmentType, List[Dict[str, Any]]]) -> str:
        """
        탐지 결과 리포트 생성
        
        Args:
            detected_equipment: 탐지된 장비 정보
            
        Returns:
            리포트 문자열
        """
        report = "=" * 60 + "\n"
        report += "         Record Type 기반 장비 탐지 결과 리포트\n"
        report += "=" * 60 + "\n\n"
        
        total_equipment = 0
        
        for equip_type, equipments in detected_equipment.items():
            if equipments:
                report += f"📋 {equip_type.value.replace('_', ' ').title()}:\n"
                report += f"   발견된 장비 수: {len(equipments)}\n"
                
                for equip in equipments:
                    confidence_pct = equip['confidence'] * 100
                    record_type = equip.get('record_type', 'N/A')
                    description = equip.get('description', '')
                    report += f"   🎯 {equip['name']} (Record Type: {record_type})\n"
                    if description:
                        report += f"      설명: {description}\n"
                    report += f"      신뢰도: {confidence_pct:.1f}%\n"
                
                report += "\n"
                total_equipment += len(equipments)
        
        report += f"\n총 발견된 장비 수: {total_equipment}\n"
        report += "=" * 60
        
        return report
    
    def suggest_naming_conventions(self, detected_equipment: Dict[EquipmentType, List[Dict[str, Any]]]) -> str:
        """
        명명법 개선 제안 (Record Type 기반)
        
        Args:
            detected_equipment: 탐지된 장비 정보
            
        Returns:
            개선 제안 문자열
        """
        suggestions = "=" * 60 + "\n"
        suggestions += "         Record Type 기반 명명법 개선 제안\n"
        suggestions += "=" * 60 + "\n\n"
        
        for equip_type, equipments in detected_equipment.items():
            if equipments and equip_type != EquipmentType.UNKNOWN:
                suggestions += f"🔧 {equip_type.value.replace('_', ' ').title()}:\n"
                
                # 현재 명명법 분석
                current_names = [e['name'] for e in equipments]
                record_types = [e.get('record_type', 'N/A') for e in equipments]
                suggestions += f"   현재 명명법: {', '.join(current_names)}\n"
                suggestions += f"   Record Type: {', '.join(set(record_types))}\n"
                
                # 표준 명명법 제안
                standard_names = self._get_standard_naming(equip_type, len(equipments))
                suggestions += f"   권장 명명법: {', '.join(standard_names)}\n"
                
                # 개선 효과
                improvements = self._analyze_naming_improvements(equipments)
                if improvements:
                    suggestions += f"   개선 효과: {improvements}\n"
                
                suggestions += "\n"
        
        # 미분류 장비 분석
        if detected_equipment.get(EquipmentType.UNKNOWN):
            suggestions += f"⚠️  미분류 장비:\n"
            for equip in detected_equipment[EquipmentType.UNKNOWN]:
                suggestions += f"   - {equip['name']} (Record Type: {equip.get('record_type', 'N/A')})\n"
            suggestions += "\n"
        
        return suggestions
    
    def _get_standard_naming(self, equip_type: EquipmentType, count: int) -> List[str]:
        """표준 명명법 반환"""
        prefixes = {
            EquipmentType.HEAT_EXCHANGER: 'E',
            EquipmentType.DISTILLATION_COLUMN: 'COL',
            EquipmentType.REACTOR: 'R',
            EquipmentType.PUMP: 'P',
            EquipmentType.COMPRESSOR: 'C',
            EquipmentType.VACUUM_SYSTEM: 'VAC',
            EquipmentType.EVAPORATOR: 'EVAP',
            EquipmentType.SEPARATOR: 'SEP',
            EquipmentType.MIXER: 'MIX',
            EquipmentType.SPLITTER: 'SPLIT',
            EquipmentType.FLASH: 'FLASH',
            EquipmentType.VALVE: 'V',
            EquipmentType.UTILITY: 'UTIL'
        }
        
        prefix = prefixes.get(equip_type, 'EQ')
        return [f"{prefix}{i:02d}" for i in range(1, count + 1)]
    
    def _analyze_naming_improvements(self, equipments: List[Dict[str, Any]]) -> str:
        """명명법 개선 효과 분석"""
        improvements = []
        
        # 신뢰도 분석
        avg_confidence = sum(e['confidence'] for e in equipments) / len(equipments)
        if avg_confidence < 0.9:
            improvements.append(f"평균 신뢰도 {avg_confidence:.1f}")
        
        # Record Type 일관성 분석
        record_types = [e.get('record_type', 'N/A') for e in equipments]
        unique_record_types = set(record_types)
        if len(unique_record_types) > 1:
            improvements.append(f"Record Type 다양성: {len(unique_record_types)}개")
        
        return "; ".join(improvements) if improvements else "이미 최적화됨"
    
    def get_equipment_statistics(self, detected_equipment: Dict[EquipmentType, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        장비 탐지 통계 정보 반환
        
        Args:
            detected_equipment: 탐지된 장비 정보
            
        Returns:
            통계 정보 딕셔너리
        """
        stats = {
            'total_equipment': 0,
            'classified_equipment': 0,
            'unknown_equipment': 0,
            'equipment_by_type': {},
            'record_type_distribution': {},
            'confidence_stats': {
                'min': 1.0,
                'max': 0.0,
                'average': 0.0
            }
        }
        
        all_confidences = []
        
        for equip_type, equipments in detected_equipment.items():
            if equipments:
                stats['total_equipment'] += len(equipments)
                stats['equipment_by_type'][equip_type.value] = len(equipments)
                
                if equip_type == EquipmentType.UNKNOWN:
                    stats['unknown_equipment'] += len(equipments)
                else:
                    stats['classified_equipment'] += len(equipments)
                
                for equip in equipments:
                    # Record Type 분포
                    record_type = equip.get('record_type', 'N/A')
                    stats['record_type_distribution'][record_type] = stats['record_type_distribution'].get(record_type, 0) + 1
                    
                    # 신뢰도 통계
                    confidence = equip['confidence']
                    all_confidences.append(confidence)
                    stats['confidence_stats']['min'] = min(stats['confidence_stats']['min'], confidence)
                    stats['confidence_stats']['max'] = max(stats['confidence_stats']['max'], confidence)
        
        if all_confidences:
            stats['confidence_stats']['average'] = sum(all_confidences) / len(all_confidences)
        
        return stats


# 사용 예시
if __name__ == "__main__":
    # 탐지기 초기화
    detector = SmartEquipmentDetector()
    
    print("Record Type 기반 스마트 장비 탐지기 초기화 완료")
    print("Aspen Plus 애플리케이션과 연결하여 사용하세요.")
    print("\n사용법:")
    print("detector.detect_equipment_from_aspen(aspen_app)")