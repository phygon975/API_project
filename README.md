# Python-Aspen-Plus-Connected-Model

Aspen Plus 시뮬레이션 파일을 자동으로 분석하고 장비 비용을 계산하는 통합 도구입니다. Record Type 기반 스마트 장비 탐지 시스템을 통해 정확한 장비 분류와 비용 계산을 제공합니다.

## 주요 기능

- **스마트 장비 탐지**: Record Type 기반 자동 장비 분류 시스템
- **자동 파일 로드**: .apw, .bkp, .apwz 파일 자동 감지 및 로드
- **블록 자동 감지**: 시뮬레이션의 모든 장비 블록을 자동으로 찾아서 분류
- **상세 정보 추출**: 각 블록의 온도, 압력, 열부하, 부피, 면적 등의 정보 자동 추출
- **장비 비용 계산**: 열교환기, 증류탑, 반응기, 펌프, 압축기, 진공 시스템 등의 장비 비용 자동 계산
- **결과 저장**: 분석 결과를 JSON 형식으로 저장
- **일괄 처리**: 여러 파일을 한 번에 분석 가능

## 프로젝트 구조

```
├── TotalEquipmentCostCalculator.py    # 전체 장비 비용 계산기 (메인)
├── SmartEquipmentDetector.py          # 스마트 장비 탐지 시스템
├── 0Heat-Exchanger/                   # 열교환기 모듈
│   ├── HeatExchanger.py
│   └── README.md
├── 1Distillation/                     # 증류탑 모듈
│   ├── Distillation.py
│   └── README.md
├── 2Reactor/                          # 반응기 모듈
│   ├── Reactor.py
│   └── README.md
├── 3Pumps/                            # 펌프 모듈
│   ├── pumps.py
│   └── README.md
├── 4Vacuum-System/                    # 진공 시스템 모듈
│   ├── vacuumoperation.py
│   └── README.md
├── 5Evaporator/                       # 증발기 모듈
│   ├── Evaporator.py
│   └── README.md
├── Pictures/                          # 예시 이미지들
├── test_smart_detector.py             # 스마트 탐지기 테스트
└── README.md                          # 프로젝트 설명서
```

## 설치 및 요구사항

### 필수 요구사항
- Python 3.6 이상
- Aspen Plus가 설치되어 있어야 함
- Aspen Plus Python 연결이 설정되어 있어야 함

### 설치 방법
1. 모든 Python 파일을 프로젝트 폴더에 저장
2. Aspen Plus를 실행
3. Python에서 모듈을 import하여 사용

## 사용법

### 1. 메인 계산기 실행 (권장)

```bash
# 기본 사용법
python TotalEquipmentCostCalculator.py

# 또는 직접 실행
python -c "
from TotalEquipmentCostCalculator import main
main()
"
```

### 2. 스마트 장비 탐지 테스트

```bash
# 스마트 탐지기 테스트
python test_smart_detector.py
```

### 3. Python 스크립트에서 사용

```python
from TotalEquipmentCostCalculator import TotalEquipmentCostCalculator

# 계산기 초기화
calculator = TotalEquipmentCostCalculator('MIX_HEFA_20250716_after_HI_v1.bkp')

# Aspen Plus 연결
if calculator.connect_to_aspen():
    # 스마트 탐지 실행
    equipment_config = calculator.smart_detect_equipment()
    
    # 모든 장비 비용 계산
    results = calculator.calculate_all_equipment(equipment_config)
    
    # 결과 출력
    calculator.print_summary_report(results)
```

### 4. 개별 모듈 사용

```python
# 열교환기 모듈
from HeatExchanger import heatexchanger
total_cost, individual_costs, heat_duties, areas = heatexchanger(
    Application, No_Heat_Exchanger, fouling_factor, E_FM, E_FL, cost_index
)

# 증류탑 모듈
from Distillation import distillationRADFRAC
cost, diameter, volume = distillationRADFRAC(
    Application, column_name, tray_spacing, top_space, bottom_space, 
    density, material_factor, cost_index
)

# 반응기 모듈
from Reactor import reactorCSTR
volume, cost = reactorCSTR(
    Application, liquid_fill, h_d_ratio, material_factor, 
    density, reactor_name, cost_index
)
```

## 지원되는 파일 형식

- **.apw**: Aspen Plus 프로젝트 파일
- **.bkp**: Aspen Plus 백업 파일  
- **.apwz**: Aspen Plus 압축 프로젝트 파일

## 기여하기

이 프로젝트에 기여하고 싶으시다면:

1. 이 저장소를 포크하세요
2. 새로운 기능 브랜치를 만드세요 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋하세요 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시하세요 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성하세요

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 연락처

프로젝트에 대한 질문이나 제안사항이 있으시면 [이슈](https://github.com/phygon975/API_project/issues)를 생성해주세요.
# 열교환기 모듈
from HeatExchanger import heatexchanger
total_cost, individual_costs, heat_duties, areas = heatexchanger(
    Application, No_Heat_Exchanger, fouling_factor, E_FM, E_FL, cost_index
)

# 증류탑 모듈
from Distillation import distillationRADFRAC
cost, diameter, volume = distillationRADFRAC(
    Application, column_name, tray_spacing, top_space, bottom_space, 
    density, material_factor, cost_index
)

# 반응기 모듈
from Reactor import reactorCSTR
volume, cost = reactorCSTR(
    Application, liquid_fill, h_d_ratio, material_factor, 
    density, reactor_name, cost_index
)
```

## 지원되는 파일 형식

- **.apw**: Aspen Plus 프로젝트 파일
- **.bkp**: Aspen Plus 백업 파일  
- **.apwz**: Aspen Plus 압축 프로젝트 파일

## 지원되는 블록 타입

### 열교환기 (Heat Exchangers)
- 패턴: `E01`, `E02`, `E03`, ... 또는 `HEAT1`, `HEAT2`, ...
- 정보: 열부하, 면적, 온도, 압력

### 증류탑 (Distillation Columns)
- 패턴: `DIST1`, `DIST2`, ... 또는 `COL1`, `COL2`, ...
- 정보: 온도, 압력, 단수

### 반응기 (Reactors)
- 패턴: `CSTR1`, `CSTR2`, ... 또는 `REACTOR1`, `REACTOR2`, ...
- 정보: 온도, 압력, 부피

### 펌프 (Pumps)
- 패턴: `P01`, `P02`, `P03`, ... 또는 `PUMP1`, `PUMP2`, ...
- 정보: 전력, 헤드, 유량

### 진공 시스템 (Vacuum Systems)
- 패턴: `VAC1`, `VAC2`, ... 또는 `STEAMJET1`, `STEAMJET2`, ...
- 정보: 압력, 유량

### 증발기 (Evaporators)
- 패턴: `EVAP1`, `EVAP2`, `EVAP3`, ...
- 정보: 열부하, 부피, 면적

## 출력 형식

### JSON 결과 파일 예시
```json
{
  "file_path": "CumenePlant4.bkp",
  "file_type": "bkp",
  "total_blocks": 8,
  "block_categories": {
    "heat_exchangers": ["E01", "E02"],
    "distillation_columns": ["DIST1"],
    "reactors": ["CSTR1"],
    "pumps": ["P01", "P02"],
    "vacuum_systems": [],
    "evaporators": ["EVAP1"],
    "other_blocks": ["BLOCK1"]
  },
  "block_details": {
    "heat_exchangers": {
      "E01": {
        "name": "E01",
        "type": "heat_exchanger",
        "temperature": 298.15,
        "pressure": 101325.0,
        "duty": 1000000.0,
        "area": 50.0
      }
    }
  },
  "cost_analysis": {
    "total_cost": 1250000.0,
    "heat_exchangers": {
      "E01": {
        "cost": 250000.0,
        "duty": 1000000.0,
        "area": 50.0
      }
    }
  }
}
```

## 오류 처리

### 일반적인 오류와 해결 방법

1. **AspenPlus 모듈을 찾을 수 없음**
   - Aspen Plus가 설치되어 있는지 확인
   - Python 환경에서 Aspen Plus 연결이 설정되어 있는지 확인

2. **파일을 찾을 수 없음**
   - 파일 경로가 올바른지 확인
   - 파일이 존재하는지 확인

3. **시뮬레이션 실행 오류**
   - `--no-simulation` 옵션을 사용하여 기존 결과 사용
   - Aspen Plus에서 시뮬레이션을 수동으로 실행

4. **비용 계산 모듈을 찾을 수 없음**
   - 해당 장비 모듈이 프로젝트 폴더에 있는지 확인
   - 모듈 경로가 올바른지 확인

## 고급 사용법

### 일괄 분석
```python
from example_aspen_loader_usage import batch_analysis
batch_analysis()
```

### 사용자 정의 비용 계산
```python
# 비용 지수 변경
cost_results = get_equipment_costs(analysis_result, current_cost_index=650.0)

# 특정 장비만 계산
if 'heat_exchangers' in analysis_result['block_categories']:
    # 열교환기 비용만 계산
    pass
```

## 확장 가능성

### 새로운 블록 타입 추가
`block_name_detector.py`의 `detect_all_block_names` 함수에서 패턴 매칭 부분을 수정:

```python
# 새로운 블록 타입 추가 예시
elif re.match(r'^NEW\d+$', block_name):
    block_categories['new_blocks'].append(block_name)
    categorized = True
```

### 새로운 비용 계산 모듈 추가
`aspen_file_loader.py`의 `get_equipment_costs` 함수에 새로운 장비 타입 추가:

```python
# 새로운 장비 비용 계산 예시
if block_categories['new_equipment']:
    try:
        from NewEquipment import calculate_costs
        # 비용 계산 로직
    except ImportError:
        print("경고: NewEquipment 모듈을 찾을 수 없습니다.")
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

버그 리포트, 기능 요청, 코드 기여를 환영합니다. 이슈를 등록하거나 풀 리퀘스트를 보내주세요.

## 연락처

문의사항이나 지원이 필요한 경우 이슈를 등록해주세요.
=======
# API_project
>>>>>>> ba196a8374708717c207e21ce58f6f8f529b900c
