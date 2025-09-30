"""
메인 실행 파일
이 모듈은 전체 프로그램의 워크플로우를 제어합니다.
"""

import os
import sys
import time
from threading import Thread
import pickle
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import win32com.client as win32
import math

import config
import unit_converter
import data_manager
import cost_calculator
import logger

# =============================================================================
# 스피너 클래스 (시각적 피드백 제공)
# =============================================================================

class Spinner:
    """Simple CLI spinner to indicate progress during long-running tasks."""
    def __init__(self, message: str) -> None:
        self.message = message
        self._running = False
        self._thread = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        frames = ['|', '/', '-', '\\']
        idx = 0
        while self._running:
            sys.stdout.write(f"\r{self.message} {frames[idx % len(frames)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            idx += 1

    def stop(self, done_message: Optional[str] = None) -> None:
        if not self._running:
            return
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        sys.stdout.write('\r')
        if done_message:
            print(done_message)
        else:
            print('')

# =============================================================================
# 세션 컨테이너 (사용자 오버라이드 저장/복원)
# =============================================================================

@dataclass
class PreviewSession:
    """프리뷰 결과와 사용자 오버라이드를 한 번에 저장/복원하는 세션 컨테이너"""
    aspen_file: str
    current_unit_set: Optional[str]
    block_info: Dict[str, str]
    all_devices: List[Dict[str, Any]]
    material_overrides: Dict[str, str] = field(default_factory=dict)
    type_overrides: Dict[str, str] = field(default_factory=dict)
    subtype_overrides: Dict[str, str] = field(default_factory=dict)

    def apply_overrides(self) -> List[Dict[str, Any]]:
        """저장된 오버라이드를 장치 데이터에 적용합니다."""
        updated_devices = []
        for device in self.all_devices:
            up = device.copy()
            name = device.get('name')
            if name in self.material_overrides:
                up['material'] = self.material_overrides[name]
            if name in self.type_overrides:
                up['selected_type'] = self.type_overrides[name]
            if name in self.subtype_overrides:
                up['selected_subtype'] = self.subtype_overrides[name]
            updated_devices.append(up)
        return updated_devices

    def save(self, path: str) -> None:
        with open(path, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "PreviewSession":
        with open(path, 'rb') as f:
            return pickle.load(f)

# =============================================================================
# 메인 실행 로직
# =============================================================================

def print_all_previews(all_devices: List[Dict]):
    """모든 장치의 데이터를 보기 좋게 출력합니다."""
    print("=" * 80)
    print("PREVIEW: ALL EQUIPMENT (extracted data and overrides)")
    print("=" * 80)

def print_detailed_analysis(all_devices: List[Dict]):
    """계산 결과/과정 상세 출력 (verbosity에 따라 단계적 출력)."""
    from logger import get_verbosity
    v = get_verbosity()
    if v <= 0:
        return

    print("\n" + "=" * 80)
    print(f"DETAILED CALCULATION SUMMARY (verbosity={v})")
    print("=" * 80)

    for dev in all_devices:
        name = dev.get('name', 'Unknown')
        eq_type = dev.get('selected_type', 'Unknown')
        sub = dev.get('selected_subtype', 'Unknown')
        cat = dev.get('category', 'Unknown')
        err = dev.get('error')
        if err:
            if v >= 1:
                print(f"  - {name:<20} | ERROR: {err}")
            continue

        # v>=1: 핵심 입력값 요약
        if v >= 1:
            basics = [f"Type={eq_type}/{sub}"]
            if dev.get('power_value') is not None:
                basics.append(f"Power={dev['power_value']} {dev.get('power_unit','')}")
            if dev.get('heat_duty_value') is not None:
                basics.append(f"Q={dev['heat_duty_value']} {dev.get('heat_duty_unit','')}")
            if dev.get('volume_value') is not None:
                basics.append(f"Vol={dev['volume_value']} {dev.get('volume_unit','')}")
            print(f"  - {name:<20} | " + " | ".join(basics))

        # v>=2: 중간 계산 변수/단위 타입
        if v >= 2:
            mid = []
            if dev.get('heat_transfer_coefficient_value') is not None:
                mid.append(f"U={dev['heat_transfer_coefficient_value']} {dev.get('heat_transfer_coefficient_unit','')}")
            if dev.get('log_mean_temp_difference_value') is not None:
                lmtd_unit = dev.get('log_mean_temp_difference_unit','')
                lmtd_utype = dev.get('log_mean_temp_difference_unit_type','')
                if lmtd_utype:
                    mid.append(f"LMTD={dev['log_mean_temp_difference_value']} {lmtd_unit} [{lmtd_utype}]")
                else:
                    mid.append(f"LMTD={dev['log_mean_temp_difference_value']} {lmtd_unit}")
            if mid:
                print(f"    · Vars: " + ", ".join(mid))

        # v>=3: 계산 과정 (핵심 수식과 수치 대입)
        if v >= 3 and eq_type == 'heat_exchanger':
            q_val = dev.get('heat_duty_value')
            q_unit = dev.get('heat_duty_unit')
            u_val = dev.get('heat_transfer_coefficient_value')
            u_unit = dev.get('heat_transfer_coefficient_unit')
            lmtd_val = dev.get('log_mean_temp_difference_value')
            lmtd_unit = dev.get('log_mean_temp_difference_unit')
            lmtd_utype = dev.get('log_mean_temp_difference_unit_type', 'DELTA-T')

            q_w = unit_converter.convert_units(q_val, q_unit, 'Watt', 'ENTHALPY-FLO') if q_val is not None and q_unit else None
            u_si = unit_converter.convert_units(u_val, u_unit, 'Watt/sqm-K', 'HEAT-TRANS-C') if u_val is not None and u_unit else None
            dt_k = unit_converter.convert_units(lmtd_val, lmtd_unit, 'K', lmtd_utype) if lmtd_val is not None and lmtd_unit else None

            steps = [
                "A = Q / (U · ΔT_lm)",
            ]
            if q_val is not None and q_unit:
                steps.append(f"  Q = {q_val} {q_unit} → {q_w} Watt")
            if u_val is not None and u_unit:
                steps.append(f"  U = {u_val} {u_unit} → {u_si} Watt/sqm-K")
            if lmtd_val is not None and lmtd_unit:
                steps.append(f"  ΔT_lm = {lmtd_val} {lmtd_unit} → {dt_k} K")

            area = None
            if q_w is not None and u_si not in (None, 0) and dt_k not in (None, 0):
                area = q_w / (u_si * dt_k)
                steps.append(f"  A = {q_w} / ({u_si} · {dt_k}) = {area:.4f} m²")
            else:
                steps.append("  A 계산 불가 (입력 부족 또는 0)")

            for s in steps:
                print("    · " + s)

    grouped_devices = {}
    for device in all_devices:
        cat = device.get("category", "Unknown")
        if cat not in grouped_devices:
            grouped_devices[cat] = []
        grouped_devices[cat].append(device)

    for cat in sorted(grouped_devices.keys()):
        print(f"\n[{cat.upper()} DEVICES] ({len(grouped_devices[cat])} devices)")
        print("-" * 80)
        
        for dev in grouped_devices[cat]:
            name = dev.get("name")
            error_msg = dev.get("error")
            if error_msg:
                print(f"  - {name:<20} | ERROR: {error_msg}")
                continue

            # 재질 정보 판별 (열교환기인 경우 Shell/Tube 분리 표시)
            if dev.get("selected_type") == "heat_exchanger":
                shell_mat = dev.get("shell_material", "Unknown")
                tube_mat = dev.get("tube_material", "Unknown")
                mat_display = f"{shell_mat}/{tube_mat}"
            else:
                mat_display = dev.get("material", "Unknown")
            
            sub = dev.get("selected_subtype")
            
            # 장치별 주요 사이징 파라미터 표시
            size_info = []
            if dev.get("power_value") is not None:
                size_info.append(f"Power={dev['power_value']} {dev.get('power_unit', 'kW')}")
            elif dev.get("volume_value") is not None:
                size_info.append(f"Volume={dev['volume_value']} {dev.get('volume_unit', 'm³')}")
            elif dev.get("heat_duty_value") is not None:
                size_info.append(f"Heat={dev['heat_duty_value']} {dev.get('heat_duty_unit', 'W')}")
            
            size_str = ", ".join(size_info) if size_info else "N/A"
            
            details = [f"Design={size_str}", f"Mat={mat_display}", f"Type={sub}"]

            if "power_kilowatt" in dev:
                power_kw = dev.get("power_kilowatt")
                power_str = f"{power_kw:,.2f} kW" if power_kw is not None else "NA"
                details[0] = f"Power={power_str}"

            if "inlet_bar" in dev and "outlet_bar" in dev:
                in_pres = dev.get("inlet_bar")
                out_pres = dev.get("outlet_bar")
                in_str = f"{in_pres:,.2f}" if in_pres is not None else "NA"
                out_str = f"{out_pres:,.2f}" if out_pres is not None else "NA"
                details.append(f"Pressure={in_str} -> {out_str} bar")
            
            if "volumetric_flow_m3_s" in dev:
                flow_val = dev.get("volumetric_flow_m3_s")
                flow_str = f"{flow_val:,.2f} m³/s" if flow_val is not None else "NA"
                details.append(f"Flow={flow_str}")
            
            print(f"  - {name:<20} | {' | '.join(details)}")
    print("=" * 80)

def print_utility_info(utilities_data: List[Dict]):
    """유틸리티 정보를 별도로 표시합니다."""
    if not utilities_data:
        return
    
    print("\n" + "=" * 80)
    print("UTILITY INFORMATION")
    print("=" * 80)
    
    for utility in utilities_data:
        utility_data = utility.get("utility_data", {})
        utility_name = utility_data.get("name", "Unknown")
        inlet_temp_val = utility_data.get("inlet_temperature_value")
        outlet_temp_val = utility_data.get("outlet_temperature_value")
        
        details = []
        if inlet_temp_val is not None or outlet_temp_val is not None:
            temp_unit = utility_data.get("temperature_unit", "°C")
            if inlet_temp_val is not None and outlet_temp_val is not None:
                details.append(f"Temp={inlet_temp_val}->{outlet_temp_val} {temp_unit}")
            elif inlet_temp_val is not None:
                details.append(f"Inlet Temp={inlet_temp_val} {temp_unit}")
            elif outlet_temp_val is not None:
                details.append(f"Outlet Temp={outlet_temp_val} {temp_unit}")
        
        details_str = " | ".join(details) if details else "No data"
        print(f"  - {utility_name:<20} | {details_str}")
    
    print("=" * 80)

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. 파일 선택 및 Aspen Plus 연결
    file_path = data_manager.find_aspen_file(current_dir)
    if not file_path:
        sys.exit("파일을 선택하지 않았거나 찾을 수 없습니다.")

    Application = data_manager.connect_to_aspen(file_path)

    # 2. 장치 분류 및 단위 세트 추출
    block_names = data_manager.get_block_names(Application)
    block_info = data_manager.parse_bkp_file_for_blocks(file_path, block_names)
    current_unit_set = data_manager.get_current_unit_set(Application)

    # 2.5. Verbosity 설정 (사용자 입력, 기본값은 config.DEFAULT_VERBOSITY)
    try:
        v_in = input(f"로그 상세 레벨을 설정하세요 (0-3, 기본 {config.DEFAULT_VERBOSITY}): ").strip()
        if v_in != '':
            logger.set_verbosity(int(v_in))
    except Exception:
        pass

    # 3. 데이터 추출 및 프리뷰
    spinner = Spinner("데이터를 추출하는 중입니다...")
    spinner.start()
    try:
        all_devices_base = data_manager.extract_all_device_data(Application, block_info, current_unit_set)
        utilities_data = data_manager.extract_all_utility_data(Application)
    finally:
        spinner.stop("데이터 추출 완료!")

    session: Optional[PreviewSession] = None
    
    # 세션 불러오기 옵션
    load_choice = input("기존 세션을 불러오시겠습니까? (y/n): ").strip().lower()
    if load_choice == 'y':
        try:
            session_files_all = [f for f in os.listdir(current_dir) if f.lower().endswith('.pkl')]
            session_files = sorted(session_files_all, key=lambda f: os.path.getmtime(os.path.join(current_dir, f)), reverse=True)
            if not session_files:
                print("불러올 .pkl 세션이 없습니다.")
            else:
                print("\n감지된 세션(.pkl) 목록:")
                for i, fname in enumerate(session_files, 1):
                    print(f"  {i}. {fname}")
                while True:
                    try:
                        choice = int(input("불러올 세션 번호를 선택하세요: ").strip())
                        if 1 <= choice <= len(session_files):
                            load_path = os.path.join(current_dir, session_files[choice - 1])
                            session = PreviewSession.load(load_path)
                            print(f"✅ 세션을 불러왔습니다: {session_files[choice - 1]}")
                            break
                        else:
                            print("잘못된 번호입니다. 다시 입력해주세요.")
                    except ValueError:
                        print("숫자를 입력해주세요.")
        except Exception as e:
            print(f"세션 불러오기 실패: {e}")
            session = None

    all_devices_preview = session.apply_overrides() if session else all_devices_base
    print_all_previews(all_devices_preview)
    
    # 유틸리티 정보 표시
    if utilities_data:
        print_utility_info(utilities_data)

    # 4. 사용자 오버라이드
    while True:
        print("\n" + "="*80)
        print("EQUIPMENT DESIGN OVERRIDES")
        print("="*80)
        
        print("사용 가능한 장치 목록:")
        for i, device in enumerate(all_devices_preview, 1):
            name = device.get('name', 'Unknown')
            cat = device.get('category', 'Unknown')
            eq_type = device.get('selected_type', 'Unknown')
            sub = device.get('selected_subtype', 'Unknown')
            
            # 재질 정보 판별 (열교환기인 경우 Shell/Tube 분리 표시)
            if eq_type == "heat_exchanger":
                shell_mat = device.get("shell_material", "Unknown")
                tube_mat = device.get("tube_material", "Unknown")
                mat_display = f"{shell_mat}/{tube_mat}"
            else:
                mat_display = device.get("material", 'Unknown')
            
            print(f"  {i:2d}. {name:<20} | Category: {cat:<10} | Current Mat: {mat_display:<12} | Current Type: {eq_type}/{sub}")

        ans = input("\n변경할 장치 이름을 입력하세요 (없으면 엔터): ").strip()
        if not ans:
            break
        
        device_info = next((d for d in all_devices_preview if d['name'] == ans), None)
        if not device_info:
            print(f"장치 '{ans}'를 찾을 수 없습니다.")
            continue
        
        # 장치 타입 및 서브타입 변경 옵션
        current_eq_type = device_info.get('selected_type', 'Unknown')
        current_subtype = device_info.get('selected_subtype', 'Unknown')
        
        print(f"\n현재 장치 설정: {current_eq_type}/{current_subtype}")
        type_change = input("장치 타입을 변경하시겠습니까? (y/n): ").strip().lower()
        
        if type_change == 'y':
            # 블록 카테고리에 따라 가능한 장치 타입만 표시
            def allowed_types_for_category(cat: str) -> List[str]:
                # config.EQUIPMENT_SETTINGS 키들 중 합리적인 후보만 노출
                all_types = set(config.EQUIPMENT_SETTINGS.keys())
                if cat == 'Pump':
                    return [t for t in ['pump'] if t in all_types]
                if cat == 'Compr':
                    return [t for t in ['compressor', 'fan', 'turbine'] if t in all_types]
                if cat == 'MCompr':
                    return [t for t in ['compressor'] if t in all_types]
                if cat in ('Heater', 'HeatX', 'Condenser'):
                    return [t for t in ['heat_exchanger'] if t in all_types]
                if cat in ('RStoic', 'RCSTR', 'RPlug', 'RBatch', 'REquil', 'RYield'):
                    return [t for t in ['reactor'] if t in all_types]
                if cat in ('Flash', 'Sep'):
                    return [t for t in ['vessel'] if t in all_types]
                if cat in ('RadFrac', 'Distl', 'DWSTU'):
                    # 탑/트레이/패킹 범주만 노출
                    return [t for t in ['tower', 'tray', 'packing'] if t in all_types]
                return []

            available_types = allowed_types_for_category(cat)
            if not available_types:
                print("이 블록 카테고리에서 변경 가능한 장치 타입이 없습니다.")
            else:
                print(f"가능한 장치 타입들: {', '.join(available_types)}")
            
            new_type = input(f"새로운 장치 타입을 입력하세요 (현재: {current_eq_type}): ").strip()
            if new_type in available_types:
                # 서브타입 선택 (번호 입력)
                available_subtypes = list(config.EQUIPMENT_SETTINGS[new_type].keys())
                print("\n가능한 서브타입들:")
                for idx, st in enumerate(available_subtypes, 1):
                    print(f"  {idx:2d}. {st}")
                sel = input(f"서브타입 번호를 선택하세요 (현재: {current_subtype}): ").strip()
                try:
                    sel_idx = int(sel) if sel else 0
                except ValueError:
                    sel_idx = 0
                if 1 <= sel_idx <= len(available_subtypes):
                    new_subtype = available_subtypes[sel_idx - 1]
                    device_info['selected_type'] = new_type
                    device_info['selected_subtype'] = new_subtype
                    print(f"✅ {ans}의 장치 타입이 {new_type}/{new_subtype}로 변경되었습니다.")
                    
                    # 재질 유효성 검사 및 기본값 재설정 (새 타입에 맞는 재질로)
                    new_settings = config.get_equipment_setting(new_type, new_subtype)
                    new_valid_materials = set()

                    # 열교환기 재질 매트릭스 구조 판별
                    def _hx_mode(settings: dict) -> str:
                        matrix = settings.get("material_factors_matrix")
                        if isinstance(matrix, dict) and matrix:
                            sample_val = next(iter(matrix.values()))
                            return "dual" if isinstance(sample_val, dict) else "single"
                        return "single"
                    
                    if "material_factors" in new_settings:
                        new_valid_materials.update(new_settings["material_factors"].keys())
                    if "material_factors_matrix" in new_settings:
                        matrix = new_settings["material_factors_matrix"]
                        if isinstance(matrix, dict):
                            if new_type == 'heat_exchanger':  # 열교환기
                                mode = _hx_mode(new_settings)
                                if mode == 'dual':
                                    # 첫 번째 사용 가능한 조합으로 기본값 설정
                                    first_shell = list(matrix.keys())[0]
                                    first_tube = list(matrix[first_shell].keys())[0]
                                    old_mat = device_info.get('material')
                                    old_shell = device_info.get('shell_material')
                                    old_tube = device_info.get('tube_material')
                                    device_info['material'] = first_shell  # 기본값은 shell material 사용
                                    device_info['shell_material'] = first_shell
                                    device_info['tube_material'] = first_tube
                                    if old_shell != first_shell or old_tube != first_tube:
                                        print(f"ℹ️  열교환기 재질 기본값 적용: Shell {old_shell} -> {first_shell}, Tube {old_tube} -> {first_tube}")
                                    if old_mat != first_shell:
                                        print(f"ℹ️  기본 재질(material) {old_mat} -> {first_shell}")
                                    new_valid_materials.update(matrix.keys())  # shell materials만 추가
                                else:  # single (평면형, 혹은 단일 측만 선택)
                                    first_mat = list(matrix.keys())[0]
                                    old_mat = device_info.get('material')
                                    old_shell = device_info.get('shell_material')
                                    old_tube = device_info.get('tube_material')
                                    device_info['material'] = first_mat
                                    device_info['shell_material'] = first_mat
                                    device_info['tube_material'] = first_mat
                                    if old_shell != first_mat:
                                        print(f"ℹ️  Shell 재질 변경: {old_shell} -> {first_mat}")
                                    if old_tube != first_mat:
                                        print(f"ℹ️  Tube 재질 변경: {old_tube} -> {first_mat}")
                                    if old_mat != first_mat:
                                        print(f"ℹ️  기본 재질(material) {old_mat} -> {first_mat}")
                                    new_valid_materials.update(matrix.keys())
                            else:
                                for key, value in matrix.items():
                                    if isinstance(value, dict):
                                        new_valid_materials.update(value.keys())
                                    else:
                                        new_valid_materials.add(key)
                    
                    if not new_valid_materials:
                        new_valid_materials = {'CS', 'SS', 'Ni', 'Cu', 'Cl', 'Ti'}  # 기본값들
                    
                    if device_info['material'] not in new_valid_materials:
                        print(f"⚠️  장치 타입 변경으로 재질 후보에 '{device_info['material']}'가 없어 기본 재질로 재설정합니다.")
                        if new_type == 'heat_exchanger':
                            print(f"열교환기: Shell={device_info['shell_material']}, Tube={device_info['tube_material']}")
                else:
                    print("유효하지 않은 서브타입 번호입니다.")
            else:
                print("유효하지 않은 장치 타입입니다.")

        # 재질 변경 로직 (최신 설정 기반)
        equipment_settings = config.get_equipment_setting(device_info['selected_type'], device_info['selected_subtype'])
        valid_materials_set = set()
        
        # material_factors에서 재질 목록 추출
        if "material_factors" in equipment_settings:
            valid_materials_set.update(equipment_settings["material_factors"].keys())
        
        # material_factors_matrix에서 재질 목록 추출
        if "material_factors_matrix" in equipment_settings:
            matrix = equipment_settings["material_factors_matrix"]
            if isinstance(matrix, dict):
                for key, value in matrix.items():
                    if isinstance(value, dict):
                        valid_materials_set.update(value.keys())
                    else:
                        valid_materials_set.add(key)
        
        # 열교환기의 경우 매트릭스 구조에 따라 동기화 정책 적용
        if device_info['selected_type'] == 'heat_exchanger':
            eq_settings = config.get_equipment_setting(device_info['selected_type'], device_info['selected_subtype'])
            matrix = eq_settings.get('material_factors_matrix')
            if isinstance(matrix, dict) and matrix:
                sample_val = next(iter(matrix.values()))
                if isinstance(sample_val, dict):
                    # dual: shell/tube 분리 유지, material은 shell과 동기화
                    device_info['shell_material'] = device_info.get('shell_material', device_info['material'])
                    device_info['tube_material'] = device_info.get('tube_material', device_info['material'])
                    device_info['material'] = device_info['shell_material']
                else:
                    # single: 모두 동일 재질로 동기화
                    device_info['shell_material'] = device_info['material']
                    device_info['tube_material'] = device_info['material']
        
        # 현재 재질 정보 표시 개선
        if device_info['selected_type'] == 'heat_exchanger':
            current_mat_display = f"Shell: {device_info.get('shell_material', 'Unknown')}/{device_info.get('tube_material', 'Unknown')}"
        else:
            current_mat_display = f"Material: {device_info.get('material', 'Unknown')}"
            
        print(f"\n현재 재질: {current_mat_display}")
        print(f"가능한 재질들: {', '.join(sorted(valid_materials_set))}")
        # y/n 없이 재질을 직접 입력 받아 오버라이드
        if device_info['selected_type'] == 'heat_exchanger':
            # 열교환기의 경우 shell과 tube 재질을 분리해서 선택 가능
            print(f"\n열교환기 재질 설정:")
            print(f"현재 Shell: {device_info.get('shell_material', 'CS')}, Tube: {device_info.get('tube_material', 'CS')}")
            print(f"가능한 Shell 재질들: {', '.join(sorted(valid_materials_set))}")
            
            # 먼저 전체 조합 매트릭스 확인
            equipment_settings = config.get_equipment_setting(device_info['selected_type'], device_info['selected_subtype'])
            if "material_factors_matrix" in equipment_settings:
                matrix = equipment_settings["material_factors_matrix"]
                print("\n사용 가능한 Shell/Tube 조합:")
                for shell_mat, tube_dict in matrix.items():
                    if isinstance(tube_dict, dict):
                        tube_materials = ', '.join(list(tube_dict.keys()))
                        print(f"  Shell: {shell_mat} -> Tube: {tube_materials}")
            
            # Shell 입력: 대소문자 구분 없이 허용
            shell_input = input(f"Shell 재질을 입력하세요 (없으면 유지): ").strip()
            if shell_input:
                canon_shell_map = {m.upper(): m for m in valid_materials_set}
                shell_canon = canon_shell_map.get(shell_input.upper())
                if shell_canon:
                    if shell_input != shell_canon:
                        print(f"ℹ️  입력 '{shell_input}'을(를) '{shell_canon}'로 인식했습니다.")
                    prev_shell = device_info.get('shell_material')
                    device_info['shell_material'] = shell_canon
                    if prev_shell != shell_canon:
                        print(f"ℹ️  Shell 재질 변경: {prev_shell} -> {shell_canon}")
                else:
                    print("유효하지 않은 shell 재질입니다.")
            
            # Tube 입력 처리
            equipment_settings = config.get_equipment_setting(device_info['selected_type'], device_info['selected_subtype'])
            if "material_factors_matrix" in equipment_settings:
                matrix = equipment_settings["material_factors_matrix"]
                current_shell = device_info.get('shell_material')
                available_tubes = list(matrix.get(current_shell, {}).keys()) if isinstance(matrix.get(current_shell), dict) else []
                if available_tubes:
                    print(f"가능한 Tube 재질들: {', '.join(available_tubes)}")
                tube_input = input(f"Tube 재질을 입력하세요 (없으면 유지): ").strip()
                if tube_input:
                    canon_tube_map = {m.upper(): m for m in available_tubes}
                    tube_canon = canon_tube_map.get(tube_input.upper())
                    if tube_canon:
                        if tube_input != tube_canon:
                            print(f"ℹ️  입력 '{tube_input}'을(를) '{tube_canon}'로 인식했습니다.")
                        prev_tube = device_info.get('tube_material')
                        device_info['tube_material'] = tube_canon
                        if prev_tube != tube_canon:
                            print(f"ℹ️  Tube 재질 변경: {prev_tube} -> {tube_canon}")
                        prev_mat = device_info.get('material')
                        device_info['material'] = device_info.get('shell_material', prev_mat)
                        if prev_mat != device_info['material']:
                            print(f"ℹ️  material 동기화: {prev_mat} -> {device_info['material']}")
                        print(f"✅ Shell: {device_info['shell_material']}, Tube: {device_info['tube_material']}")
                    else:
                        print("유효하지 않은 tube 재질입니다.")
        else:
            # 일반 장치의 재질 변경: 바로 입력 받아 적용
            mat_input = input(f"변경할 재질을 입력하세요 (없으면 유지): ").strip()
            if mat_input:
                canon_map = {m.upper(): m for m in valid_materials_set}
                mat_canon = canon_map.get(mat_input.upper())
                if mat_canon:
                    if mat_input != mat_canon:
                        print(f"ℹ️  입력 '{mat_input}'을(를) '{mat_canon}'로 인식했습니다.")
                    old_mat = device_info.get('material')
                    device_info['material'] = mat_canon
                    if old_mat != mat_canon:
                        print(f"ℹ️  Material 변경: {old_mat} -> {mat_canon}")
                    print(f"✅ {ans}의 재질이 {mat_canon}로 변경되었습니다.")
            else:
                    print("잘못된 재질입니다. 목록 중 하나를 입력해주세요.")

        print_all_previews(all_devices_preview)
        
    save_choice = input("현재 세션을 저장하시겠습니까? (y/n): ").strip().lower()
    if save_choice == 'y':
        try:
            save_path = input("저장할 파일 경로(기본 .pkl): ").strip() or f"{os.path.splitext(os.path.basename(file_path))[0]}_session.pkl"
            session_to_save = PreviewSession(
                aspen_file=file_path,
                current_unit_set=current_unit_set,
                block_info=block_info,
                all_devices=all_devices_base,
                material_overrides={d['name']: d['material'] for d in all_devices_preview},
                type_overrides={d['name']: d['selected_type'] for d in all_devices_preview},
                subtype_overrides={d['name']: d['selected_subtype'] for d in all_devices_preview}
            )
            session_to_save.save(save_path)
            print(f"✅ 세션이 저장되었습니다: {save_path}")
        except Exception as e:
            print(f"세션 저장 실패: {e}")

    # 5. 최종 계산
    confirm = input("\n위 데이터로 비용 계산을 진행할까요? (y/n): ").strip().lower()
    if confirm != 'y':
        sys.exit("사용자에 의해 계산이 취소되었습니다.")
        
    cepci_options = cost_calculator.CEPCIOptions(
        target_index=config.CEPCI_BY_YEAR.get(config.DEFAULT_TARGET_YEAR)
    )
    
    final_devices_to_calc = all_devices_preview
    # 비용 계산 실행 (상세 출력은 결과 생성 후 별도 섹션에서 표시)
    cost_results = cost_calculator.calculate_all_costs_with_data(final_devices_to_calc, cepci_options)

    # verbosity에 따른 상세 계산 결과(장치비 계산 과정 포함)를 먼저 표시
    def print_verbose_cost_details(cost_results: Dict[str, Any]):
        from logger import get_verbosity
        v = get_verbosity()
        if v <= 0:
            return
        results = cost_results.get("results", [])
        print("\n" + "=" * 80)
        print(f"DETAILED COST CALCULATION (verbosity={v})")
        print("=" * 80)
        for res in results:
            name = res.get("name", "Unknown")
            # final_devices_to_calc는 외부 스코프 변수이므로 참조
            eq_type = next((d.get('selected_type') for d in final_devices_to_calc if d.get('name') == name), None)
            sub = next((d.get('selected_subtype') for d in final_devices_to_calc if d.get('name') == name), None)
            info_msg = res.get("info")
            err = res.get("error")
            if info_msg:
                if v >= 1:
                    print(f"  - {name} ({eq_type}/{sub}) | {info_msg}")
                continue
            if err:
                if v >= 1:
                    print(f"  - {name} ({eq_type}/{sub}) | ERROR: {err}")
                continue
            if v >= 1:
                print(f"  - {name} ({eq_type}/{sub})")
            if v >= 3:
                steps = res.get("debug_steps") or []
                for s in steps:
                    print(f"      · {s}")

    print_verbose_cost_details(cost_results)

    # 6. 결과 출력
    print("\n" + "=" * 80)
    print("CALCULATED EQUIPMENT COSTS")
    print("=" * 80)
    for res in cost_results["results"]:
        name = res.get("name")
        cost = res.get("bare_module_cost")
        # 장치 카테고리 정보 가져오기
        eq_type = next((d.get('selected_type') for d in final_devices_to_calc if d.get('name') == name), None)
        info_msg = res.get("info")
        if info_msg is not None:
            if eq_type:
                print(f"  - {name:<20} | {info_msg} ({eq_type})")
            else:
                print(f"  - {name:<20} | {info_msg}")
        elif cost is not None:
            if eq_type:
                print(f"  - {name:<20} | Bare Module Cost: ${cost:,.2f} ({eq_type})")
            else:
                print(f"  - {name:<20} | Bare Module Cost: ${cost:,.2f}")
        else:
            if eq_type:
                print(f"  - {name:<20} | ERROR: {res.get('error', 'Unknown Error')} ({eq_type})")
            else:
                print(f"  - {name:<20} | ERROR: {res.get('error', 'Unknown Error')}")
    print("-" * 80)
    total = cost_results["total_bare_module_cost"]
    print(f"TOTAL BARE MODULE COST: ${total:,.2f}")
    print("=" * 80)

if __name__ == "__main__":
    main()