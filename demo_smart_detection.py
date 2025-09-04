# -*- coding: utf-8 -*-
"""
스마트 장비 탐지 시스템 데모
여러 사용자의 다양한 명명법을 자동으로 인식하는 기능을 시연합니다.

@author: Assistant
@created: 2025-01-22
"""

from SmartEquipmentDetector import SmartEquipmentDetector

def main():
    """메인 함수"""
    print("=" * 60)
    print("         스마트 장비 탐지 시스템 데모")
    print("=" * 60)
    
    # 탐지기 초기화
    detector = SmartEquipmentDetector()
    
    # 시나리오 1: 표준 명명법 사용자
    print("\n📋 시나리오 1: 표준 명명법 사용자")
    print("-" * 40)
    standard_blocks = [
        "E01", "E02", "E03", "E04",
        "RADFRAC1", "RADFRAC2", "RADFRAC3",
        "R1", "R2",
        "P1", "P2", "P3",
        "C1", "C2"
    ]
    
    detected_standard = detector.detect_equipment(standard_blocks)
    print(detector.generate_detection_report(detected_standard))
    
    # 시나리오 2: 기술적 명명법 사용자
    print("\n📋 시나리오 2: 기술적 명명법 사용자")
    print("-" * 40)
    technical_blocks = [
        "HEX1", "HEX2", "COOLER1", "HEATER1", "CONDENSER1", "REBOILER1",
        "DIST1", "COLUMN1", "TOWER1", "FRACTIONATOR1",
        "CSTR1", "PFR1", "REACTOR1", "BATCH_REACTOR1",
        "PUMP1", "CENTRIFUGAL_PUMP1", "RECIPROCATING_PUMP1",
        "COMP1", "TURBO_COMPRESSOR1", "RECIPROCATING_COMPRESSOR1",
        "VAC1", "STEAM_JET_EJECTOR1", "LIQUID_RING_PUMP1",
        "EVAP1", "FLASH1", "CRYSTALLIZER1",
        "SEP1", "DECANTER1", "FILTER1", "CENTRIFUGE1",
        "MIX1", "BLENDER1", "AGITATOR1",
        "SPLIT1", "DIVIDER1", "MANIFOLD1"
    ]
    
    detected_technical = detector.detect_equipment(technical_blocks)
    print(detector.generate_detection_report(detected_technical))
    
    # 시나리오 3: 혼합 명명법 사용자 (가장 현실적)
    print("\n📋 시나리오 3: 혼합 명명법 사용자 (현실적)")
    print("-" * 40)
    mixed_blocks = [
        "E01", "HEX2", "COOLER3", "HEATER4",
        "RADFRAC1", "DIST2", "COLUMN3",
        "R1", "RX2", "CSTR3", "REACTOR4",
        "P1", "PUMP2", "PMP3",
        "C1", "COMP2", "COMPRESSOR3",
        "VAC1", "EJECTOR2", "VACUUM3",
        "EVAP1", "FLASH2", "EVAPORATOR3",
        "SEP1", "DECANTER2", "FILTER3",
        "MIX1", "BLENDER2", "AGITATOR3",
        "SPLIT1", "DIVIDER2", "MANIFOLD3"
    ]
    
    detected_mixed = detector.detect_equipment(mixed_blocks)
    print(detector.generate_detection_report(detected_mixed))
    
    # 시나리오 4: 완전히 자유로운 명명법 사용자
    print("\n📋 시나리오 4: 자유로운 명명법 사용자")
    print("-" * 40)
    free_blocks = [
        "HEAT_EXCHANGER_001", "COOLING_UNIT_002", "STEAM_HEATER_003",
        "DISTILLATION_TOWER_001", "SEPARATION_COLUMN_002", "FRACTIONATION_UNIT_003",
        "CONTINUOUS_STIRRED_TANK_001", "PLUG_FLOW_REACTOR_002", "CATALYTIC_REACTOR_003",
        "LIQUID_PUMP_001", "HIGH_PRESSURE_PUMP_002", "FEED_PUMP_003",
        "AIR_COMPRESSOR_001", "GAS_COMPRESSOR_002", "RECYCLE_COMPRESSOR_003",
        "VACUUM_EJECTOR_001", "STEAM_JET_SYSTEM_002", "ROOTS_BLOWER_003",
        "EVAPORATION_UNIT_001", "FLASH_DRUM_002", "CONCENTRATION_UNIT_003",
        "LIQUID_SEPARATOR_001", "GRAVITY_SETTLER_002", "HYDROCYCLONE_003",
        "FLUID_MIXER_001", "SOLID_BLENDER_002", "EMULSION_AGITATOR_003",
        "STREAM_SPLITTER_001", "FLOW_DIVIDER_002", "DISTRIBUTION_MANIFOLD_003"
    ]
    
    detected_free = detector.detect_equipment(free_blocks)
    print(detector.generate_detection_report(detected_free))
    
    # 명명법 개선 제안
    print("\n🔧 명명법 개선 제안")
    print("=" * 60)
    
    all_blocks = standard_blocks + technical_blocks + mixed_blocks + free_blocks
    detected_all = detector.detect_equipment(all_blocks)
    
    print(detector.suggest_naming_conventions(detected_all))
    
    # 성능 분석
    print("\n📊 탐지 성능 분석")
    print("=" * 60)
    
    total_blocks = len(all_blocks)
    detected_blocks = sum(len(equipments) for equipments in detected_all.values())
    
    print(f"총 블록 수: {total_blocks}")
    print(f"탐지된 장비 수: {detected_blocks}")
    print(f"탐지율: {detected_blocks/total_blocks*100:.1f}%")
    
    # 장비 타입별 탐지율
    for equip_type, equipments in detected_all.items():
        if equipments:
            avg_confidence = sum(e['confidence'] for e in equipments) / len(equipments)
            pattern_matches = sum(1 for e in equipments if e['detection_method'] == 'pattern')
            print(f"\n{equip_type.value.replace('_', ' ').title()}:")
            print(f"  탐지된 장비 수: {len(equipments)}")
            print(f"  평균 신뢰도: {avg_confidence:.3f}")
            print(f"  패턴 매칭: {pattern_matches}/{len(equipments)}")
    
    print("\n" + "=" * 60)
    print("         데모 완료")
    print("=" * 60)

if __name__ == "__main__":
    main()
