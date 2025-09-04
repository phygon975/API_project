# -*- coding: utf-8 -*-
"""
블록 이름 감지기 사용 예시

이 파일은 block_name_detector.py 모듈의 사용법을 보여줍니다.
"""

from block_name_detector import detect_all_block_names, get_block_info, print_block_summary

def example_usage():
    """
    블록 이름 감지기 사용 예시
    """
    print("=== 블록 이름 감지기 사용 예시 ===\n")
    
    # Aspen Plus 연결 예시 (실제 사용 시에는 실제 연결 필요)
    try:
        # Aspen Plus 연결
        # Application = AspenPlus.Application()
        
        print("1. 모든 블록 이름 감지:")
        print("   block_categories = detect_all_block_names(Application)")
        print("   이 함수는 다음과 같은 구조를 반환합니다:")
        print("   {")
        print("       'heat_exchangers': ['E01', 'E02', ...],")
        print("       'distillation_columns': ['DIST1', 'DIST2', ...],")
        print("       'reactors': ['CSTR1', 'CSTR2', ...],")
        print("       'pumps': ['P01', 'P02', ...],")
        print("       'vacuum_systems': ['VAC1', 'VAC2', ...],")
        print("       'evaporators': ['EVAP1', 'EVAP2', ...],")
        print("       'other_blocks': ['BLOCK1', 'BLOCK2', ...]")
        print("   }")
        
        print("\n2. 특정 블록 정보 가져오기:")
        print("   block_info = get_block_info(Application, 'E01')")
        print("   반환되는 정보:")
        print("   {")
        print("       'name': 'E01',")
        print("       'type': 'heat_exchanger',")
        print("       'temperature': 298.15,")
        print("       'pressure': 101325.0,")
        print("       'duty': 1000000.0,")
        print("       'volume': None,")
        print("       'area': 50.0")
        print("   }")
        
        print("\n3. 전체 요약 정보 출력:")
        print("   print_block_summary(Application)")
        print("   이 함수는 모든 블록의 상세 정보를 콘솔에 출력합니다.")
        
        print("\n=== 실제 사용 코드 예시 ===")
        print("""
# Aspen Plus 연결
import AspenPlus
Application = AspenPlus.Application()

# 모든 블록 이름 감지
block_categories = detect_all_block_names(Application)

# 열교환기만 가져오기
heat_exchangers = block_categories['heat_exchangers']
print(f"발견된 열교환기: {heat_exchangers}")

# 특정 블록의 상세 정보
if heat_exchangers:
    first_he = get_block_info(Application, heat_exchangers[0])
    print(f"첫 번째 열교환기 정보: {first_he}")

# 전체 요약 출력
print_block_summary(Application)
        """)
        
    except Exception as e:
        print(f"예시 실행 중 오류 발생: {str(e)}")
        print("실제 사용 시에는 Aspen Plus가 실행 중이어야 합니다.")

def supported_block_patterns():
    """
    지원되는 블록 이름 패턴들을 보여줍니다.
    """
    print("\n=== 지원되는 블록 이름 패턴 ===")
    
    patterns = {
        '열교환기 (Heat Exchangers)': ['E01', 'E02', 'E03', 'HEAT1', 'HEAT2'],
        '증류탑 (Distillation Columns)': ['DIST1', 'DIST2', 'COL1', 'COL2'],
        '반응기 (Reactors)': ['CSTR1', 'CSTR2', 'REACTOR1', 'REACTOR2'],
        '펌프 (Pumps)': ['P01', 'P02', 'P03', 'PUMP1', 'PUMP2'],
        '진공 시스템 (Vacuum Systems)': ['VAC1', 'VAC2', 'STEAMJET1', 'STEAMJET2'],
        '증발기 (Evaporators)': ['EVAP1', 'EVAP2', 'EVAP3']
    }
    
    for category, examples in patterns.items():
        print(f"\n{category}:")
        for example in examples:
            print(f"  - {example}")

if __name__ == "__main__":
    example_usage()
    supported_block_patterns()
