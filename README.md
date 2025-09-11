# 장비 비용 계산기

Aspen Plus 시뮬레이션 파일을 분석하여 장비 비용을 계산하는 Python 도구입니다.

**현재 코드 개발 중입니다.**

## 파일 구조

```
├── TEA_machine.py                          # 메인 프로그램
├── Equipment_cost_estimation_aspen.bkp     # Aspen Plus 시뮬레이션 파일
├── README.md                               # 프로젝트 설명서
└── .gitignore                              # Git 설정 파일
```

## 사용법

```bash
python TEA_machine.py
```
## 현재까지 진행 상황

코드 실행 결과

Looking for file: c:\Users\###\###\###\####\Equipment_cost_estimation_aspen.bkp

Connecting to Aspen Plus... Please wait...
Aspen Plus COM object created successfully!
Attempting to open file: c:\Users\###\###\###\####\Equipment_cost_estimation_aspen.bkp
File opened successfully!
Aspen Plus is now visible
## 장비 탐지
['01PUMP', '02HEX', '02HEX-1', '03HEX', '03HEX-1', '04HEX', '05HDO-RE', '06REQUIL', '07SPLIT', '08MIXER', '09HEX', '09HEX-1', '10HEX', '10HEX-1', '11HEX', '12VALVE', '13SEP', '14HEX', '14HEX-1', '15ABS', '16HEX', '16HEX-1', '17HCC-RE', '18HEX', '18HEX-1', '19HEX', '19HEX-1', '20HEX', '21HEX', '22HEX', '23SEP', '24VALVE', '25PSA', '26DISTIL', '27DISTIL', '28COMP', '29MIXER', '30SPLIT', '31COMP', '32VALVE', '33MIXER', '34COMB', '35HEX', '36SPLIT', 'B1', 'B3', 'B4', 'B5']

## 장비 분류
============================================================
DEVICE CATEGORIES
============================================================

Heat Exchangers (24 devices):
  - 02HEX
  - 02HEX-1
  - 03HEX
  - 03HEX-1
  - 04HEX
  - 09HEX
  - 09HEX-1
  - 10HEX
  - 10HEX-1
  - 11HEX
  - 14HEX
  - 14HEX-1
  - 16HEX
  - 16HEX-1
  - 18HEX
  - 18HEX-1
  - 19HEX
  - 19HEX-1
  - 20HEX
  - 21HEX
  - 22HEX
  - 35HEX
  - B1
  - B5

Distillation Columns (2 devices):
  - 26DISTIL
  - 27DISTIL

Reactors (4 devices):
  - 05HDO-RE
  - 06REQUIL
  - 17HCC-RE
  - 34COMB

Pumps and Compressors (5 devices):
  - 01PUMP
  - 28COMP
  - 31COMP
  - B3
  - B4

Vessels (4 devices):
  - 13SEP
  - 15ABS
  - 23SEP
  - 25PSA

Ignored Devices (9 devices):
  - 07SPLIT
  - 08MIXER
  - 12VALVE
  - 24VALVE
  - 29MIXER
  - 30SPLIT
  - 32VALVE
  - 33MIXER
  - 36SPLIT

Other Devices (0 devices):

============================================================
DEVICE LOADING COMPLETED
============================================================

## 아스펜 내부에서 사용 중인 Units-sets 탐지
Unit sets detected successfully!

============================================================
UNITS SETS SUMMARY
============================================================
Total unit sets found: 9

Unit sets:
   1. ENG
   2. FORHI
   3. MET
   4. METCBAR
   5. METCKGCM
   6. SI
   7. SI-CBAR
   8. T-D
   9. US-1

## 현재 Simulation sheet에서 활성화 중인 Units set 감지
============================================================
Current unit set: FORHI

## 장치비 계산 전 재질 및 장비 타입 검토 및 변경 예시
============================================================
PREVIEW: PRESSURE-DRIVEN DEVICES (extracted data)
============================================================
01PUMP               | Pump         | P=135.53874299999998 kW | Pin=1.01325 bar | Pout=92.0 bar | Material=CS | Type=pump | Subtype=centrifugal
28COMP               | MCompr       | P=2164.4786 kW | Stages=3 | Pout_final=NA bar | Material=CS | Type=multi-stage compressor | Subtype=centrifugal
31COMP               | Compr        | P=535.8173 kW | Pin=35.4870365 bar | Pout=92.0 bar | Material=CS | Type=compressor | Subtype=centrifugal
B3                   | Compr        | Q=0.009809 m3/s | Pin=1.01325 bar | Pout=1.15 bar | Material=CS | Type=fan | Subtype=centrifugal_radial
B4                   | Compr        | P=-801.822175 kW | Pin=15.0 bar | Pout=3.0 bar | Material=CS | Type=turbine | Subtype=axial

설계 조건을 변경할 장치 이름을 입력하세요 (없으면 엔터): 01PUMP

선택된 장치: 01PUMP (Pump)
현재 타입: pump
현재 세부 타입: centrifugal

사용 가능한 타입과 세부 타입:
  pump: centrifugal, reciprocating

타입을 변경하시겠습니까? (y/n): y

사용 가능한 타입:
  1. pump
타입 번호를 선택하세요: 1
01PUMP의 타입이 pump로 변경되었습니다.

사용 가능한 세부 타입:
  1. centrifugal
  2. reciprocating
세부 타입 번호를 선택하세요: 2
01PUMP의 세부 타입이 reciprocating로 변경되었습니다.
변경할 재질을 입력하세요 (예: CS, SS, Ni, Cl, Ti, Fiberglass, 없으면 엔터): SS
01PUMP의 재질이 SS로 변경되었습니다.

============================================================
UPDATED PREVIEW: PRESSURE-DRIVEN DEVICES
============================================================

============================================================
PREVIEW: PRESSURE-DRIVEN DEVICES (extracted data)
============================================================
01PUMP               | Pump         | P=135.53874299999998 kW | Pin=1.01325 bar | Pout=92.0 bar | Material=SS | Type=pump | Subtype=reciprocating
28COMP               | MCompr       | P=2164.4786 kW | Stages=3 | Pout_final=NA bar | Material=CS | Type=multi-stage compressor | Subtype=centrifugal
31COMP               | Compr        | P=535.8173 kW | Pin=35.4870365 bar | Pout=92.0 bar | Material=CS | Type=compressor | Subtype=centrifugal
B3                   | Compr        | Q=0.009809 m3/s | Pin=1.01325 bar | Pout=1.15 bar | Material=CS | Type=fan | Subtype=centrifugal_radial
B4                   | Compr        | P=-801.822175 kW | Pin=15.0 bar | Pout=3.0 bar | Material=CS | Type=turbine | Subtype=axial

설계 조건을 변경할 장치 이름을 입력하세요 (없으면 엔터): 31COMP

선택된 장치: 31COMP (Compr)
현재 타입: compressor
현재 세부 타입: centrifugal

사용 가능한 타입과 세부 타입:
  fan: centrifugal_radial, centrifugal_backward, centrifugal_forward, axial
  compressor: centrifugal, axial, reciprocating
  turbine: axial, radial

타입을 변경하시겠습니까? (y/n): y

사용 가능한 타입:
  1. fan
  2. compressor
  3. turbine
타입 번호를 선택하세요: 2
31COMP의 타입이 compressor로 변경되었습니다.

사용 가능한 세부 타입:
  1. centrifugal
  2. axial
  3. reciprocating
세부 타입 번호를 선택하세요: 2
31COMP의 세부 타입이 axial로 변경되었습니다.
변경할 재질을 입력하세요 (예: CS, SS, Ni, Cl, Ti, Fiberglass, 없으면 엔터): Ni
31COMP의 재질이 Ni로 변경되었습니다.

============================================================
UPDATED PREVIEW: PRESSURE-DRIVEN DEVICES
============================================================

============================================================
PREVIEW: PRESSURE-DRIVEN DEVICES (extracted data)
============================================================
01PUMP               | Pump         | P=135.53874299999998 kW | Pin=90.98675 bar | Pout=92.0 bar | Material=SS | Type=pump | Subtype=reciprocating
28COMP               | MCompr       | P=2164.4786 kW | Stages=3 | Pout_final=NA bar | Material=CS | Type=multi-stage compressor | Subtype=centrifugal
31COMP               | Compr        | P=535.8173 kW | Pin=35.4870365 bar | Pout=92.0 bar | Material=Ni | Type=compressor | Subtype=axial
B3                   | Compr        | Q=0.009809 m3/s | Pin=1.01325 bar | Pout=1.15 bar | Material=CS | Type=fan | Subtype=centrifugal_radial
B4                   | Compr        | P=-801.822175 kW | Pin=15.0 bar | Pout=3.0 bar | Material=CS | Type=turbine | Subtype=axial

설계 조건을 변경할 장치 이름을 입력하세요 (없으면 엔터): 30PUMP
장치 '30PUMP'를 찾을 수 없습니다.

설계 조건을 변경할 장치 이름을 입력하세요 (없으면 엔터):

위 데이터/재질로 비용 계산을 진행할까요? (y/n): y
## 장치비 산정 과정 디버깅용 추후 verbose 옵션을 통해 계산 내역 출력 디테일 정도를 조절하는 옵션 추가
```
PUMP RECIPROCATING: Input power = 135.5387 kW
Unit conversion: 135.5387 kW -> 135.5387 kW
PUMP RECIPROCATING: logS = math.log10(135.5387(kW))
logC = 3.8696 + 0.3161 * logS + 0.1220 * logS**2
logC = 3.8696 + 0.3161 * 2.1321 + 0.1220 * 4.5457
logC = 5.0981
log_quadratic_cost = 10 ** 5.0981 = 125348.75
Base purchased cost = 125348.75 USD
PUMP RECIPROCATING: Material & Pressure factors applied
  Base cost: 125348.75 USD
  Material factor (F_M): 2.400
  Pressure factor (F_P): 1.000
  Adjusted cost: 125348.75 * 2.400 * 1.000 = 300836.99 USD
PUMP RECIPROCATING: CEPCI index adjustment
  Cost at base index: 300836.99 USD
  Base CEPCI index: 567.5
  Target CEPCI index: 800.0
  Adjustment factor: 800.0 / 567.5 = 1.4097
  Adjusted cost: 300836.99 * 1.4097 = 424087.39 USD
PUMP RECIPROCATING: BM calculation (B1 + B2 * Fm)
  B1 = 1.890, B2 = 1.350, Fm = 2.400
  Effective BM = 1.890 + 1.350 * 2.400 = 5.130
PUMP RECIPROCATING: Bare Module cost calculation
  Purchased cost: 424087.39 USD
  BM factor: 5.130
  Bare module cost: 424087.39 * 5.130 = 2175568.31 USD
COMPRESSOR CENTRIFUGAL: Input power = 693.0352 kW
Unit conversion: 693.0352 kW -> 693.0352 kW
COMPRESSOR CENTRIFUGAL: logS = math.log10(693.0352(kW))
logC = 2.2891 + 1.3604 * logS + -0.1027 * logS**2
logC = 2.2891 + 1.3604 * 2.8408 + -0.1027 * 8.0699
logC = 5.3249
log_quadratic_cost = 10 ** 5.3249 = 211293.31
Base purchased cost = 211293.31 USD
COMPRESSOR CENTRIFUGAL: Material & Pressure factors applied
  Base cost: 211293.31 USD
  Material factor (F_M): 1.000
  Pressure factor (F_P): 1.000
  Adjusted cost: 211293.31 * 1.000 * 1.000 = 211293.31 USD
COMPRESSOR CENTRIFUGAL: CEPCI index adjustment
  Cost at base index: 211293.31 USD
  Base CEPCI index: 567.5
  Target CEPCI index: 800.0
  Adjustment factor: 800.0 / 567.5 = 1.4097
  Adjusted cost: 211293.31 * 1.4097 = 297858.42 USD
COMPRESSOR CENTRIFUGAL: Using BM factor from table = 2.700
COMPRESSOR CENTRIFUGAL: Bare Module cost calculation
  Purchased cost: 297858.42 USD
  BM factor: 2.700
  Bare module cost: 297858.42 * 2.700 = 804217.72 USD
COMPRESSOR CENTRIFUGAL: Input power = 733.5077 kW
Unit conversion: 733.5077 kW -> 733.5077 kW
COMPRESSOR CENTRIFUGAL: logS = math.log10(733.5077(kW))
logC = 2.2891 + 1.3604 * logS + -0.1027 * logS**2
logC = 2.2891 + 1.3604 * 2.8654 + -0.1027 * 8.2105
logC = 5.3440
log_quadratic_cost = 10 ** 5.3440 = 220787.07
Base purchased cost = 220787.07 USD
COMPRESSOR CENTRIFUGAL: Material & Pressure factors applied
  Base cost: 220787.07 USD
  Material factor (F_M): 1.000
  Pressure factor (F_P): 1.000
  Adjusted cost: 220787.07 * 1.000 * 1.000 = 220787.07 USD
COMPRESSOR CENTRIFUGAL: CEPCI index adjustment
  Cost at base index: 220787.07 USD
  Base CEPCI index: 567.5
  Target CEPCI index: 800.0
  Adjustment factor: 800.0 / 567.5 = 1.4097
  Adjusted cost: 220787.07 * 1.4097 = 311241.68 USD
COMPRESSOR CENTRIFUGAL: Using BM factor from table = 2.700
COMPRESSOR CENTRIFUGAL: Bare Module cost calculation
  Purchased cost: 311241.68 USD
  BM factor: 2.700
  Bare module cost: 311241.68 * 2.700 = 840352.55 USD
COMPRESSOR CENTRIFUGAL: Input power = 737.9357 kW
Unit conversion: 737.9357 kW -> 737.9357 kW
COMPRESSOR CENTRIFUGAL: logS = math.log10(737.9357(kW))
logC = 2.2891 + 1.3604 * logS + -0.1027 * logS**2
logC = 2.2891 + 1.3604 * 2.8680 + -0.1027 * 8.2255
logC = 5.3460
log_quadratic_cost = 10 ** 5.3460 = 221814.76
Base purchased cost = 221814.76 USD
COMPRESSOR CENTRIFUGAL: Material & Pressure factors applied
  Base cost: 221814.76 USD
  Material factor (F_M): 1.000
  Pressure factor (F_P): 1.000
  Adjusted cost: 221814.76 * 1.000 * 1.000 = 221814.76 USD
COMPRESSOR CENTRIFUGAL: CEPCI index adjustment
  Cost at base index: 221814.76 USD
  Base CEPCI index: 567.5
  Target CEPCI index: 800.0
  Adjustment factor: 800.0 / 567.5 = 1.4097
  Adjusted cost: 221814.76 * 1.4097 = 312690.41 USD
COMPRESSOR CENTRIFUGAL: Using BM factor from table = 2.700
COMPRESSOR CENTRIFUGAL: Bare Module cost calculation
  Purchased cost: 312690.41 USD
  BM factor: 2.700
  Bare module cost: 312690.41 * 2.700 = 844264.11 USD
COMPRESSOR AXIAL: Input power = 535.8173 kW
Unit conversion: 535.8173 kW -> 535.8173 kW
COMPRESSOR AXIAL: logS = math.log10(535.8173(kW))
logC = 2.2891 + 1.3604 * logS + -0.1027 * logS**2
logC = 2.2891 + 1.3604 * 2.7290 + -0.1027 * 7.4475
logC = 5.2368
log_quadratic_cost = 10 ** 5.2368 = 172501.47
Base purchased cost = 172501.47 USD
COMPRESSOR AXIAL: Material & Pressure factors applied
  Base cost: 172501.47 USD
  Material factor (F_M): 1.000
  Pressure factor (F_P): 1.000
  Adjusted cost: 172501.47 * 1.000 * 1.000 = 172501.47 USD
COMPRESSOR AXIAL: CEPCI index adjustment
  Cost at base index: 172501.47 USD
  Base CEPCI index: 567.5
  Target CEPCI index: 800.0
  Adjustment factor: 800.0 / 567.5 = 1.4097
  Adjusted cost: 172501.47 * 1.4097 = 243173.87 USD
COMPRESSOR AXIAL: Using BM factor from table = 15.900
COMPRESSOR AXIAL: Bare Module cost calculation
  Purchased cost: 243173.87 USD
  BM factor: 15.900
  Bare module cost: 243173.87 * 15.900 = 3866464.60 USD
TURBINE AXIAL: Input power = 801.8222 kW
Unit conversion: 801.8222 kW -> 801.8222 kW
TURBINE AXIAL: logS = math.log10(801.8222(kW))
logC = 2.7051 + 1.4398 * logS + -0.1776 * logS**2
logC = 2.7051 + 1.4398 * 2.9041 + -0.1776 * 8.4337
logC = 5.3886
log_quadratic_cost = 10 ** 5.3886 = 244665.04
Base purchased cost = 244665.04 USD
TURBINE AXIAL: Material & Pressure factors applied
  Base cost: 244665.04 USD
  Material factor (F_M): 1.000
  Pressure factor (F_P): 1.000
  Adjusted cost: 244665.04 * 1.000 * 1.000 = 244665.04 USD
TURBINE AXIAL: CEPCI index adjustment
  Cost at base index: 244665.04 USD
  Base CEPCI index: 567.5
  Target CEPCI index: 800.0
  Adjustment factor: 800.0 / 567.5 = 1.4097
  Adjusted cost: 244665.04 * 1.4097 = 344902.25 USD
TURBINE AXIAL: Using BM factor from table = 3.500
TURBINE AXIAL: Bare Module cost calculation
  Purchased cost: 344902.25 USD
  BM factor: 3.500
  Bare module cost: 344902.25 * 3.500 = 1207157.89 USD
```
## 최종 계산 및 오류(발생 시) 원인 출력
============================================================
CALCULATED PRESSURE DEVICE COSTS
============================================================
01PUMP (pump): Bare Module Cost = 2,175,568.31 USD
28COMP (multi-stage compressor (stage-by-stage)): Bare Module Cost = 2,544,007.66 USD
31COMP (compressor): Bare Module Cost = 3,866,464.60 USD
B3 (compr(under limit)): Bare Module Cost = 0.00 USD
B4 (turbine): Bare Module Cost = 1,207,157.89 USD

Total Bare Module Cost for Pressure Devices: 9,793,198.45 USD
Note: Bare Module Cost includes installation costs
============================================================
