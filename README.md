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
# 현재까지 진행 상황

## 코드 실행 결과
```
Looking for file: c:\Users\###\###\###\####\Equipment_cost_estimation_aspen.bkp

Connecting to Aspen Plus... Please wait...
Aspen Plus COM object created successfully!
Attempting to open file: c:\Users\###\###\###\####\Equipment_cost_estimation_aspen.bkp
File opened successfully!
Aspen Plus is now visible
```
## 장비 탐지
```
['01PUMP', '02HEX', '02HEX-1', '03HEX', '03HEX-1', '04HEX', '05HDO-RE', '06REQUIL', '07SPLIT', '08MIXER', '09HEX', '09HEX-1', '10HEX', '10HEX-1', '11HEX', '12VALVE', '13SEP', '14HEX', '14HEX-1', '15ABS', '16HEX', '16HEX-1', '17HCC-RE', '18HEX', '18HEX-1', '19HEX', '19HEX-1', '20HEX', '21HEX', '22HEX', '23SEP', '24VALVE', '25PSA', '26DISTIL', '27DISTIL', '28COMP', '29MIXER', '30SPLIT', '31COMP', '32VALVE', '33MIXER', '34COMB', '35HEX', '36SPLIT', 'B1', 'B3', 'B4', 'B5']
```
## 장비 분류
```
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
```
## 아스펜 내부에서 사용 중인 Units-sets 탐지
```
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
```
## 현재 Simulation sheet에서 활성화 중인 Units set 감지
```
============================================================
Current unit set: FORHI
```
## 탐지된 unit set을 통해 얻은 단위들을 기반으로 코드 내에서 필요환산 인자 판별
```python
#======================================================================
# Hardcoded Unit Data (for CSV-free operation)
#======================================================================

def get_hardcoded_unit_table():
    """
    CSV 파일 없이도 작동하도록 하드코딩된 단위 테이블을 반환하는 함수
    Unit_table.csv의 내용을 기반으로 함
    """
    # CSV 열 순서에 따른 unit_type 매핑 (1부터 시작)
    csv_column_to_unit_type = {
        1: 'AREA',           # sqm
        2: 'COMPOSITION',    # mol-fr
        3: 'DENSITY',        # kg/cum
        4: 'ENERGY',         # J
        5: 'FLOW',           # kg/sec
        6: 'MASS-FLOW',      # kg/sec
        7: 'MOLE-FLOW',      # kmol/sec
        8: 'VOLUME-FLOW',    # cum/sec
        9: 'MASS',           # kg
        10: 'POWER',         # Watt
        11: 'PRESSURE',      # N/sqm
        12: 'TEMPERATURE',   # K
        13: 'TIME',          # sec
        14: 'VELOCITY',      # m/sec
        15: 'VOLUME',        # cum
        16: 'MOLE-DENSITY',  # kmol/cum
        17: 'MASS-DENSITY',  # kg/cum
        18: 'MOLE-VOLUME',   # cum/kmol
        19: 'ELEC-POWER',    # Watt
        20: 'UA',            # J/sec-K
        21: 'WORK',          # J
        22: 'HEAT'           # J
    }
    
    # 하드코딩된 단위 데이터 (Unit_table.csv의 전체 내용)
    hardcoded_units = {
        1: {1: 'sqm', 2: 'sqft', 3: 'sqm', 4: 'sqcm', 5: 'sqin', 6: 'sqmile', 7: 'sqmm', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # AREA
        2: {1: 'mol-fr', 2: 'mol-fr', 3: 'mol-fr', 4: 'mass-fr', 5: '', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # COMPOSITION
        3: {1: 'kg/cum', 2: 'lb/cuft', 3: 'gm/cc', 4: 'lb/gal', 5: 'gm/cum', 6: 'gm/ml', 7: 'lb/bbl', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # DENSITY
        4: {1: 'J', 2: 'Btu', 3: 'cal', 4: 'kcal', 5: 'kWhr', 6: 'ft-lbf', 7: 'GJ', 8: 'kJ', 9: 'N-m', 10: 'MJ', 11: 'Mcal', 12: 'Gcal', 13: 'Mbtu', 14: 'MMBtu', 15: 'hp-hr', 16: 'MMkcal', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # ENERGY
        5: {1: 'kg/sec', 2: 'lb/hr', 3: 'kg/hr', 4: 'lb/sec', 5: 'Mlb/hr', 6: 'tons/day', 7: 'Mcfh', 8: 'tonne/hr', 9: 'lb/day', 10: 'kg/day', 11: 'tons/hr', 12: 'kg/min', 13: 'kg/year', 14: 'gm/min', 15: 'gm/hr', 16: 'gm/day', 17: 'Mgm/hr', 18: 'Ggm/hr', 19: 'Mgm/day', 20: 'Ggm/day', 21: 'lb/min', 22: 'MMlb/hr', 23: 'Mlb/day', 24: 'MMlb/day', 25: 'lb/year', 26: 'Mlb/year', 27: 'MMIb/year', 28: 'tons/min', 29: 'Mtons/year', 30: 'MMtons/year', 31: 'L-tons/min', 32: 'L-tons/hr', 33: 'L-tons/day', 34: 'ML-tons/year', 35: 'MML-tons/year', 36: 'ktonne/year', 37: 'kg/oper-year', 38: 'lb/oper-year', 39: 'Mlb/oper-year', 40: 'MIMIb/oper-year', 41: 'Mtons/oper-year', 42: 'MMtons/oper-year', 43: 'ML-tons/oper-year', 44: 'MML-tons/oper-year', 45: 'ktonne/oper-year', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # FLOW
        6: {1: 'kg/sec', 2: 'lb/hr', 3: 'kg/hr', 4: 'lb/sec', 5: 'Mlb/hr', 6: 'tons/day', 7: 'gm/sec', 8: 'tonne/hr', 9: 'lb/day', 10: 'kg/day', 11: 'tons/year', 12: 'tons/hr', 13: 'tonne/day', 14: 'tonne/year', 15: 'kg/min', 16: 'kg/year', 17: 'gm/min', 18: 'gm/hr', 19: 'gm/day', 20: 'Mgm/hr', 21: 'Ggm/hr', 22: 'Mgm/day', 23: 'Ggm/day', 24: 'lb/min', 25: 'MMlb/hr', 26: 'Mlb/day', 27: 'MMlb/day', 28: 'lb/year', 29: 'Mlb/year', 30: 'MMlb/year', 31: 'tons/min', 32: 'Mtons/year', 33: 'MMtons/year', 34: 'L-tons/min', 35: 'L-tons/hr', 36: 'L-tons/day', 37: 'ML-tons/year', 38: 'MML-tons/year', 39: 'ktonne/year', 40: 'tons/oper-year', 41: 'tonne/oper-year', 42: 'kg/oper-year', 43: 'lb/oper-year', 44: 'Mlb/oper-year', 45: 'MMlb/oper-year', 46: 'Mtons/oper-year', 47: 'MMtons/oper-year', 48: 'ML-tons/oper-year', 49: 'MML-tons/oper-year', 50: 'ktonne/oper-year', 51: ''},  # MASS-FLOW
        7: {1: 'kmol/sec', 2: 'lbmol/hr', 3: 'kmol/hr', 4: 'MMscfh', 5: 'MMscmh', 6: 'mol/sec', 7: 'lbmol/sec', 8: 'scmh', 9: 'bmol/day', 10: 'kmol/day', 11: 'MMscfd', 12: 'Mlscfd', 13: 'scfm', 14: 'mol/min', 15: 'kmol/khr', 16: 'kmol/Mhr', 17: 'mol/hr', 18: 'Mmol/hr', 19: 'Mlbmol/hr', 20: 'lbmol/Mhr', 21: 'lbmol/MMhr', 22: 'Mscfm', 23: 'scfh', 24: 'scfd', 25: 'ncmh', 26: 'ncmd', 27: 'ACFM', 28: 'kmol/min', 29: 'kmol/week', 30: 'kmol/month', 31: 'kmol/year', 32: 'kmol/oper-year', 33: 'lbmol/min', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MOLE-FLOW
        8: {1: 'cum/sec', 2: 'cuft/hr', 3: 'l/min', 4: 'gal/min', 5: 'gal/hr', 6: 'bbl/day', 7: 'cum/hr', 8: 'cuft/min', 9: 'bbl/hr', 10: 'cuft/sec', 11: 'cum/day', 12: 'cum/year', 13: 'l/hr', 14: 'kbbl/day', 15: 'MMcuft/hr', 16: 'MMcuft/day', 17: 'Mcuft/day', 18: 'l/sec', 19: 'l/day', 20: 'cum/min', 21: 'kcum/sec', 22: 'kcum/hr', 23: 'kcum/day', 24: 'Mcum/sec', 25: 'Mcum/hr', 26: 'Mcum/day', 27: 'ACFM', 28: 'cuft/day', 29: 'Mcuft/min', 30: 'Mcuft/hr', 31: 'MMcuft/hr', 32: 'Mgal/min', 33: 'MMgal/min', 34: 'Mgal/hr', 35: 'MMgal/hr', 36: 'Mbbl/hr', 37: 'MMbbl/hr', 38: 'Mbbl/day', 39: 'MMbbl/day', 40: 'cum/oper-year', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # VOLUME-FLOW
        9: {1: 'kg', 2: 'lb', 3: 'kg', 4: 'gm', 5: 'ton', 6: 'Mlb', 7: 'tonne', 8: 'L-ton', 9: 'MMlb', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MASS
        10: {1: 'Watt', 2: 'hp', 3: 'kW', 4: 'Btu/hr', 5: 'cal/sec', 6: 'ft-lbf/sec', 7: 'MIW', 8: 'GW', 9: 'MJ/hr', 10: 'kcal/hr', 11: 'Gcal/hr', 12: 'MMBtu/hr', 13: 'MBtu/hr', 14: 'Mhp', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # POWER
        11: {1: 'N/sqm', 2: 'PsIa', 3: 'atm', 4: 'lbf/sqft', 5: 'bar', 6: 'torr', 7: 'in-water', 8: 'kg/sqcm', 9: 'mmHg', 10: 'kPa', 11: 'mm-water', 12: 'mbar', 13: 'psig', 14: 'atmg', 15: 'barg', 16: 'kg/sqcmg', 17: 'lb/ft-sqsec', 18: 'kg/m-sqsec', 19: 'pa', 20: 'MiPa', 21: 'Pag', 22: 'kPag', 23: 'MPag', 24: 'mbarg', 25: 'in-Hg', 26: 'mmHg-vac', 27: 'in-Hg-vac', 28: 'in-water-60F', 29: 'in-water-vac', 30: 'in-water-60F-vac', 31: 'in-water-g', 32: 'in-water-60F-g', 33: 'mm-water-g', 34: 'mm-water-60F-g', 35: 'psi', 36: 'mm-water-60F', 37: 'bara', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # PRESSURE
        12: {1: 'K', 2: 'F', 3: 'K', 4: 'C', 5: 'R', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # TEMPERATURE
        13: {1: 'sec', 2: 'hr', 3: 'hr', 4: 'day', 5: 'min', 6: 'year', 7: 'month', 8: 'week', 9: 'nsec', 10: 'oper-year', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # TIME
        14: {1: 'm/sec', 2: 'ft/sec', 3: 'm/sec', 4: 'mile/hr', 5: 'km/hr', 6: 'ft/min', 7: 'mm/day', 8: 'mm/hr', 9: 'mm/day30', 10: 'in/day', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # VELOCITY
        15: {1: 'cum', 2: 'cuft', 3: 'l', 4: 'cuin', 5: 'gal', 6: 'bbl', 7: 'cc', 8: 'kcum', 9: 'Mcum', 10: 'Mcuft', 11: 'MMcuft', 12: 'ml', 13: 'kl', 14: 'MMl', 15: 'Mgal', 16: 'MMgal', 17: 'UKgal', 18: 'MUKgal', 19: 'MMUKgal', 20: 'Mbbl', 21: 'MMbbl', 22: 'kbbl', 23: 'cuyd', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # VOLUME
        16: {1: 'kmol/cum', 2: 'lbmol/cuft', 3: 'mol/cc', 4: 'lbmol/gal', 5: 'mol/l', 6: 'mmol/cc', 7: 'mmol/l', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MOLE-DENSITY
        17: {1: 'kg/cum', 2: 'lb/cuft', 3: 'gm/cc', 4: 'lb/gal', 5: 'gm/cum', 6: 'gm/ml', 7: 'gm/l', 8: 'mg/l', 9: 'mg/cc', 10: 'mg/cum', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MASS-DENSITY
        18: {1: 'cum/kmol', 2: 'cuft/lbmol', 3: 'cc/mol', 4: 'ml/mol', 5: 'bbl/mscf', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # MOLE-VOLUME
        19: {1: 'Watt', 2: 'kW', 3: 'kW', 4: 'MW', 5: 'GW', 6: '', 7: '', 8: '', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # ELEC-POWER
        20: {1: 'J/sec-K', 2: 'Btu/hr-R', 3: 'cal/sec-K', 4: 'kJ/sec-K', 5: 'kcal/sec-K', 6: 'kcal/hr-K', 7: 'Btu/hr-F', 8: 'kW/k', 9: '', 10: '', 11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # UA
        21: {1: 'J', 2: 'hp-hr', 3: 'kW-hr', 4: 'ft-lbf', 5: 'kJ', 6: 'N-m', 7: 'MJ', 8: 'Mbtu', 9: 'MMBtu', 10: 'Mcal', 11: 'Gcal', 12: '', 13: '', 14: '', 15: '', 16: '', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''},  # WORK
        22: {1: 'J', 2: 'Btu', 3: 'cal', 4: 'kcal', 5: 'Mmkcal', 6: 'MMBtu', 7: 'Pcu', 8: 'MMPcu', 9: 'kJ', 10: 'GJ', 11: 'N-m', 12: 'MJ', 13: 'Mcal', 14: 'Gcal', 15: 'Mbtu', 16: 'kW-hr', 17: '', 18: '', 19: '', 20: '', 21: '', 22: '', 23: '', 24: '', 25: '', 26: '', 27: '', 28: '', 29: '', 30: '', 31: '', 32: '', 33: '', 34: '', 35: '', 36: '', 37: '', 38: '', 39: '', 40: '', 41: '', 42: '', 43: '', 44: '', 45: '', 46: '', 47: '', 48: '', 49: '', 50: '', 51: ''}  # HEAT
    }
    
    # unit_table 형태로 변환
    unit_table = {}
    for csv_col_idx, unit_type_name in csv_column_to_unit_type.items():
        if csv_col_idx in hardcoded_units:
            unit_table[csv_col_idx] = {
                'unit_type': unit_type_name,
                'units': {idx: unit for idx, unit in hardcoded_units[csv_col_idx].items() if unit.strip()}
            }
    
    return unit_table
```
## 장치비 계산 전 재질 및 장비 타입 검토 및 변경 예시
```
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
```
## 장치비 산정 과정 (디버깅용) 추후 verbose 옵션을 통해 계산 내역 출력 디테일 정도를 조절하는 옵션 추가
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
```
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
```
