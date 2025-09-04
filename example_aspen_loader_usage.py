# -*- coding: utf-8 -*-
"""
아스펜 파일 로더 사용 예시

이 스크립트는 aspen_file_loader.py 모듈의 실제 사용법을 보여줍니다.
"""

import os
from aspen_file_loader import (
    analyze_aspen_simulation, 
    load_aspen_file_and_detect_blocks,
    get_equipment_costs,
    save_analysis_results
)

def example_usage():
    """
    아스펜 파일 로더 사용 예시
    """
    print("=== 아스펜 파일 로더 사용 예시 ===\n")
    
    # 현재 디렉토리의 아스펜 파일들 찾기
    aspen_files = []
    for file in os.listdir('.'):
        if file.endswith(('.apw', '.bkp', '.apwz')):
            aspen_files.append(file)
    
    if not aspen_files:
        print("현재 디렉토리에 아스펜 파일이 없습니다.")
        print("사용 가능한 파일들:")
        print("- .apw (Aspen Plus 프로젝트 파일)")
        print("- .bkp (Aspen Plus 백업 파일)")
        print("- .apwz (Aspen Plus 압축 프로젝트 파일)")
        return
    
    print(f"발견된 아스펜 파일들: {aspen_files}")
    
    # 첫 번째 파일로 예시 실행
    example_file = aspen_files[0]
    print(f"\n예시 파일: {example_file}")
    
    try:
        # 방법 1: 완전한 분석 (권장)
        print("\n1. 완전한 분석 실행:")
        analysis_result = analyze_aspen_simulation(
            file_path=example_file,
            file_type="auto",  # 자동 감지
            run_simulation=True,
            print_summary=True
        )
        
        # 방법 2: 파일 로드 및 블록 감지만
        print("\n2. 파일 로드 및 블록 감지:")
        Application, block_categories = load_aspen_file_and_detect_blocks(
            file_path=example_file,
            file_type="auto"
        )
        
        print(f"발견된 블록 카테고리:")
        for category, blocks in block_categories.items():
            if blocks:
                print(f"  {category}: {blocks}")
        
        # 방법 3: 장비 비용 계산
        print("\n3. 장비 비용 계산:")
        cost_results = get_equipment_costs(analysis_result, current_cost_index=600.0)
        
        # 방법 4: 결과 저장
        print("\n4. 결과 저장:")
        output_filename = f"{os.path.splitext(example_file)[0]}_analysis.json"
        save_analysis_results(analysis_result, output_filename)
        
        print(f"\n분석이 완료되었습니다!")
        print(f"결과 파일: {output_filename}")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        print("Aspen Plus가 실행 중이고 파일이 올바른지 확인하세요.")

def batch_analysis():
    """
    여러 아스펜 파일을 일괄 분석하는 예시
    """
    print("\n=== 일괄 분석 예시 ===\n")
    
    # 현재 디렉토리의 모든 아스펜 파일 찾기
    aspen_files = []
    for file in os.listdir('.'):
        if file.endswith(('.apw', '.bkp', '.apwz')):
            aspen_files.append(file)
    
    if not aspen_files:
        print("분석할 아스펜 파일이 없습니다.")
        return
    
    print(f"일괄 분석할 파일들: {aspen_files}")
    
    all_results = {}
    
    for file_path in aspen_files:
        try:
            print(f"\n{'='*50}")
            print(f"분석 중: {file_path}")
            print(f"{'='*50}")
            
            # 파일 분석
            analysis_result = analyze_aspen_simulation(
                file_path=file_path,
                file_type="auto",
                run_simulation=True,
                print_summary=False  # 일괄 처리 시 출력 최소화
            )
            
            # 비용 계산
            cost_results = get_equipment_costs(analysis_result)
            
            # 결과 저장
            all_results[file_path] = {
                'analysis': analysis_result,
                'costs': cost_results
            }
            
            # 개별 파일로 저장
            output_filename = f"{os.path.splitext(file_path)[0]}_analysis.json"
            save_analysis_results(analysis_result, output_filename)
            
            print(f"✓ {file_path} 분석 완료")
            
        except Exception as e:
            print(f"✗ {file_path} 분석 실패: {str(e)}")
    
    # 전체 결과 요약
    print(f"\n{'='*60}")
    print("일괄 분석 완료 요약")
    print(f"{'='*60}")
    
    for file_path, results in all_results.items():
        total_cost = results['costs']['total_cost']
        total_blocks = results['analysis']['total_blocks']
        print(f"{file_path}:")
        print(f"  - 총 블록 수: {total_blocks}")
        print(f"  - 총 장비 비용: ${total_cost:,.2f}")
    
    # 전체 결과를 하나의 파일로 저장
    import json
    summary_data = {}
    for file_path, results in all_results.items():
        summary_data[file_path] = {
            'total_blocks': results['analysis']['total_blocks'],
            'total_cost': results['costs']['total_cost'],
            'block_categories': results['analysis']['block_categories']
        }
    
    with open('batch_analysis_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n일괄 분석 요약이 저장되었습니다: batch_analysis_summary.json")

if __name__ == "__main__":
    print("아스펜 파일 로더 사용 예시")
    print("=" * 50)
    
    # 단일 파일 분석 예시
    example_usage()
    
    # 일괄 분석 예시 (선택적)
    print("\n" + "="*50)
    response = input("일괄 분석을 실행하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        batch_analysis()
    
    print("\n예시 실행이 완료되었습니다.")
