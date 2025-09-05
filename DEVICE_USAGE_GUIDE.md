# 장치 카테고리별 불러오기 사용법

## 개요
`TEA_machine.py`에서 Aspen Plus 모델의 장치들을 카테고리별로 분류하고 불러오는 기능을 구현했습니다.

## 주요 기능

### 1. 장치 분류
- **열교환기** (HeatX, Heater, Cooler, Condenser)
- **증류탑** (RadFrac, Distl, DWSTU)
- **반응기** (RStoic, RCSTR, RPlug, RBatch, REquil, RYield)
- **펌프/압축기** (Pump, Compr, MCompr)
- **용기** (Vacuum, Flash, Sep)
- **무시할 장치** (Mixer, FSplit, Valve)
- **기타 장치**

### 2. 카테고리별 장치 불러오기 함수

```python
# 열교환기만 가져오기
heat_exchangers = get_heat_exchangers(devices_by_category)

# 증류탑만 가져오기
distillation_columns = get_distillation_columns(devices_by_category)

# 반응기만 가져오기
reactors = get_reactors(devices_by_category)

# 펌프와 압축기만 가져오기
pumps_compressors = get_pumps_and_compressors(devices_by_category)

# 용기만 가져오기
vessels = get_vessels(devices_by_category)

# 무시할 장치들만 가져오기
ignored_devices = get_ignored_devices(devices_by_category)

# 기타 장치들만 가져오기
other_devices = get_other_devices(devices_by_category)
```

### 3. 장치 검색 함수

```python
# 장치 이름으로 찾기
device, category = get_device_by_name(devices_by_category, "E-101")

# 장치 타입으로 찾기
heatx_devices = get_devices_by_type(devices_by_category, "HeatX")
```

### 4. 장치 분석 함수

```python
# 열교환기 분석
analyze_heat_exchangers(devices_by_category)

# 증류탑 분석
analyze_distillation_columns(devices_by_category)

# 반응기 분석
analyze_reactors(devices_by_category)
```

## 사용 예시

### 예시 1: 열교환기만 처리하기
```python
# 열교환기들 가져오기
heat_exchangers = get_heat_exchangers(devices_by_category)

# 각 열교환기에 대해 작업 수행
for he in heat_exchangers:
    print(f"Processing {he['name']} ({he['type']})")
    
    # 온도 정보가 있으면 출력
    if 'temperature' in he['properties']:
        print(f"  Temperature: {he['properties']['temperature']} °C")
    
    # 여기에 열교환기 특화 분석 로직 추가
    # 예: 효율성 계산, 열전달 계수 등
```

### 예시 2: 특정 장치 찾기
```python
# 특정 장치 찾기
device, category = get_device_by_name(devices_by_category, "E-101")

if device:
    print(f"Found device: {device['name']}")
    print(f"Category: {category}")
    print(f"Type: {device['type']}")
    print(f"Properties: {device['properties']}")
```

### 예시 3: 특정 타입의 모든 장치 찾기
```python
# 모든 HeatX 타입 장치 찾기
heatx_devices = get_devices_by_type(devices_by_category, "HeatX")

print(f"Found {len(heatx_devices)} HeatX devices:")
for device, category in heatx_devices:
    print(f"  - {device['name']} in {category}")
```

### 예시 4: 카테고리별 통계
```python
# 각 카테고리별 장치 수 출력
for category, devices in devices_by_category.items():
    if devices:
        print(f"{category}: {len(devices)} devices")
        for device in devices:
            print(f"  - {device['name']} ({device['type']})")
```

## 장치 정보 구조

각 장치는 다음과 같은 구조를 가집니다:

```python
device = {
    'name': 'E-101',           # 장치 이름
    'type': 'HeatX',          # 장치 타입
    'properties': {            # 장치 속성
        'temperature': 150.0,  # 온도 (°C)
        'pressure': 5.0,       # 압력 (bar)
        'flow': 1000.0        # 유량 (kg/h)
    },
    'connections': {}         # 연결 정보 (향후 확장)
}
```

## 실행 방법

1. **가상환경 활성화**:
   ```bash
   conda activate aspen_env
   ```

2. **코드 실행**:
   ```bash
   python TEA_machine.py
   ```

3. **결과 확인**: 콘솔에서 카테고리별 장치 분류 및 분석 결과를 확인할 수 있습니다.

## 확장 가능성

이 구조를 기반으로 다음과 같은 기능들을 추가할 수 있습니다:

- 장치별 효율성 계산
- 열교환기 네트워크 분석
- 증류탑 분리 효율 계산
- 반응기 전환율 분석
- 장치 간 연결 관계 분석
- 경제성 분석 (TEA) 통합
