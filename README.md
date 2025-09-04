# TEA Machine - Aspen Plus 연동 장비 비용 계산기

Aspen Plus 시뮬레이션 파일을 분석하여 장비 비용을 자동으로 계산하는 Python 도구입니다.

## 주요 기능

- **Aspen Plus 파일 분석**: .bkp 파일을 직접 읽어서 장비 정보 추출
- **장비 자동 분류**: 열교환기, 증류탑, 반응기, 펌프, 진공 시스템, 증발기 등 자동 분류
- **비용 계산**: 각 장비별 상세 비용 계산
- **결과 출력**: JSON 형식으로 결과 저장

## 파일 구조

```
├── TEA_machine.py                          # 메인 프로그램
├── MIX_HEFA_20250716_after_HI_v1.bkp      # Aspen Plus 시뮬레이션 파일
├── README.md                               # 프로젝트 설명서
└── .gitignore                              # Git 설정 파일
```

## 설치 및 요구사항

### 필수 요구사항
- Python 3.6 이상
- Aspen Plus가 설치되어 있어야 함
- Aspen Plus Python 연결이 설정되어 있어야 함

### 설치 방법
1. 프로젝트 파일들을 다운로드
2. Aspen Plus를 실행
3. Python에서 TEA_machine.py를 실행

## 사용법

### 기본 실행
```bash
python TEA_machine.py
```

### Python 스크립트에서 사용
```python
from TEA_machine import analyze_equipment_costs

# Aspen Plus 파일 분석
results = analyze_equipment_costs('MIX_HEFA_20250716_after_HI_v1.bkp')
print(results)
```

## 지원되는 장비 타입

- **열교환기 (Heat Exchangers)**: E01, E02, E03, ...
- **증류탑 (Distillation Columns)**: DIST1, DIST2, ...
- **반응기 (Reactors)**: CSTR1, CSTR2, ...
- **펌프 (Pumps)**: P01, P02, P03, ...
- **진공 시스템 (Vacuum Systems)**: VAC1, VAC2, ...
- **증발기 (Evaporators)**: EVAP1, EVAP2, EVAP3, ...

## 출력 형식

### JSON 결과 파일 예시
```json
{
  "file_path": "MIX_HEFA_20250716_after_HI_v1.bkp",
  "total_equipment": 8,
  "equipment_categories": {
    "heat_exchangers": ["E01", "E02"],
    "distillation_columns": ["DIST1"],
    "reactors": ["CSTR1"],
    "pumps": ["P01", "P02"],
    "vacuum_systems": [],
    "evaporators": ["EVAP1"]
  },
  "cost_analysis": {
    "total_cost": 1250000.0,
    "heat_exchangers_cost": 250000.0,
    "distillation_cost": 500000.0,
    "reactors_cost": 300000.0,
    "pumps_cost": 100000.0,
    "evaporators_cost": 100000.0
  }
}
```

## 오류 처리

### 일반적인 오류와 해결 방법

1. **Aspen Plus 연결 오류**
   - Aspen Plus가 실행 중인지 확인
   - Python 환경에서 Aspen Plus 연결이 설정되어 있는지 확인

2. **파일을 찾을 수 없음**
   - 파일 경로가 올바른지 확인
   - 파일이 존재하는지 확인

3. **장비 분류 오류**
   - 장비 이름이 표준 패턴을 따르는지 확인
   - TEA_machine.py의 분류 로직을 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

버그 리포트, 기능 요청, 코드 기여를 환영합니다. 이슈를 등록하거나 풀 리퀘스트를 보내주세요.

## 연락처

문의사항이나 지원이 필요한 경우 [이슈](https://github.com/phygon975/API_project/issues)를 등록해주세요.
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
