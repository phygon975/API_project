# 블록 이름 감지기 (Block Name Detector)

Aspen Plus 시뮬레이션에서 모든 장비 블록의 이름을 자동으로 감지하고 분류하는 Python 모듈입니다.

## 기능

- **자동 블록 감지**: Aspen Plus 시뮬레이션의 모든 블록을 자동으로 찾아서 분류
- **카테고리별 분류**: 열교환기, 증류탑, 반응기, 펌프, 진공 시스템, 증발기 등으로 자동 분류
- **상세 정보 추출**: 각 블록의 온도, 압력, 열부하, 부피, 면적 등의 정보 자동 추출
- **요약 정보 출력**: 전체 시뮬레이션의 블록 요약 정보를 콘솔에 출력

## 지원되는 블록 패턴

### 열교환기 (Heat Exchangers)
- `E01`, `E02`, `E03`, ... (기본 패턴)
- `HEAT1`, `HEAT2`, `HEAT3`, ... (대안 패턴)

### 증류탑 (Distillation Columns)
- `DIST1`, `DIST2`, `DIST3`, ... (기본 패턴)
- `COL1`, `COL2`, `COL3`, ... (대안 패턴)

### 반응기 (Reactors)
- `CSTR1`, `CSTR2`, `CSTR3`, ... (기본 패턴)
- `REACTOR1`, `REACTOR2`, `REACTOR3`, ... (대안 패턴)

### 펌프 (Pumps)
- `P01`, `P02`, `P03`, ... (기본 패턴)
- `PUMP1`, `PUMP2`, `PUMP3`, ... (대안 패턴)

### 진공 시스템 (Vacuum Systems)
- `VAC1`, `VAC2`, `VAC3`, ... (기본 패턴)
- `STEAMJET1`, `STEAMJET2`, `STEAMJET3`, ... (대안 패턴)

### 증발기 (Evaporators)
- `EVAP1`, `EVAP2`, `EVAP3`, ... (기본 패턴)

## 사용법

### 1. 기본 사용법

```python
import AspenPlus
from block_name_detector import detect_all_block_names, get_block_info, print_block_summary

# Aspen Plus 연결
Application = AspenPlus.Application()

# 모든 블록 이름 감지
block_categories = detect_all_block_names(Application)

# 결과 확인
print(block_categories)
```

### 2. 특정 카테고리의 블록만 가져오기

```python
# 열교환기만 가져오기
heat_exchangers = block_categories['heat_exchangers']
print(f"발견된 열교환기: {heat_exchangers}")

# 펌프만 가져오기
pumps = block_categories['pumps']
print(f"발견된 펌프: {pumps}")
```

### 3. 특정 블록의 상세 정보 가져오기

```python
# 특정 블록의 상세 정보
block_info = get_block_info(Application, 'E01')
print(block_info)

# 반환되는 정보:
# {
#     'name': 'E01',
#     'type': 'heat_exchanger',
#     'temperature': 298.15,
#     'pressure': 101325.0,
#     'duty': 1000000.0,
#     'volume': None,
#     'area': 50.0
# }
```

### 4. 전체 요약 정보 출력

```python
# 모든 블록의 요약 정보를 콘솔에 출력
print_block_summary(Application)
```

## 함수 설명

### `detect_all_block_names(Application)`
- **기능**: 모든 블록의 이름을 감지하고 카테고리별로 분류
- **반환값**: 장비 타입별로 분류된 블록 이름들의 딕셔너리
- **예시**:
```python
{
    'heat_exchangers': ['E01', 'E02'],
    'distillation_columns': ['DIST1'],
    'reactors': ['CSTR1'],
    'pumps': ['P01', 'P02'],
    'vacuum_systems': [],
    'evaporators': ['EVAP1'],
    'other_blocks': ['BLOCK1']
}
```

### `get_block_info(Application, block_name)`
- **기능**: 특정 블록의 상세 정보를 가져옴
- **매개변수**: 
  - `Application`: Aspen Plus 애플리케이션 객체
  - `block_name`: 블록 이름 (문자열)
- **반환값**: 블록의 상세 정보 딕셔너리

### `print_block_summary(Application)`
- **기능**: 모든 블록의 요약 정보를 콘솔에 출력
- **매개변수**: `Application`: Aspen Plus 애플리케이션 객체

## 요구사항

- Python 3.6 이상
- Aspen Plus가 실행 중이어야 함
- Aspen Plus Python 연결이 설정되어 있어야 함

## 설치 및 실행

1. `block_name_detector.py` 파일을 프로젝트 폴더에 저장
2. Aspen Plus를 실행하고 시뮬레이션 파일을 로드
3. Python에서 모듈을 import하여 사용

```python
# 예시 실행
python example_block_detector_usage.py
```

## 주의사항

- 블록 이름이 지원되는 패턴을 따라야 자동 분류가 가능합니다
- 지원되지 않는 패턴의 블록은 `other_blocks` 카테고리에 포함됩니다
- Aspen Plus 시뮬레이션이 실행 완료된 상태에서 사용해야 정확한 정보를 얻을 수 있습니다

## 확장 가능성

새로운 블록 타입을 추가하려면 `detect_all_block_names` 함수의 패턴 매칭 부분을 수정하면 됩니다:

```python
# 새로운 블록 타입 추가 예시
elif re.match(r'^NEW\d+$', block_name):
    block_categories['new_blocks'].append(block_name)
    categorized = True
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
