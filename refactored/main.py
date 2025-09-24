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

            size_val = dev.get("size_value")
            size_unit = dev.get("size_unit")
            mat = dev.get("material")
            sub = dev.get("selected_subtype")
            
            size_str = f"{size_val:,.2f} {size_unit}" if size_val is not None else "NA"
            
            details = [f"Size={size_str}", f"Mat={mat}", f"Type={sub}"]

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

    # 3. 데이터 추출 및 프리뷰
    spinner = Spinner("데이터를 추출하는 중입니다...")
    spinner.start()
    try:
        all_devices_base = data_manager.extract_all_device_data(Application, block_info, current_unit_set)
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

    # 4. 사용자 오버라이드
    while True:
        print("\n" + "="*80)
        print("EQUIPMENT DESIGN OVERRIDES")
        print("="*80)
        
        print("사용 가능한 장치 목록:")
        for i, device in enumerate(all_devices_preview, 1):
            name = device.get('name', 'Unknown')
            cat = device.get('category', 'Unknown')
            mat = device.get('material', 'Unknown')
            sub = device.get('selected_subtype', 'Unknown')
            print(f"  {i:2d}. {name:<20} | Category: {cat:<10} | Current Mat: {mat:<10} | Current Type: {sub:<20}")

        ans = input("\n변경할 장치 이름을 입력하세요 (없으면 엔터): ").strip()
        if not ans:
            break
        
        device_info = next((d for d in all_devices_preview if d['name'] == ans), None)
        if not device_info:
            print(f"장치 '{ans}'를 찾을 수 없습니다.")
            continue
        
        # 재질 변경 로직
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
        
        # 기본 재질들 추가
        valid_materials_set.update(['CS', 'SS', 'Ni', 'Cu', 'Cl', 'Ti', 'Fiberglass'])
        
        while True:
            mat_input = input(f"현재 재질: {device_info['material']}. 변경할 재질을 입력하세요 (가능: {', '.join(sorted(valid_materials_set))}, 없으면 엔터): ").strip()
            if not mat_input:
                break
            elif mat_input in valid_materials_set:
                device_info['material'] = mat_input
                print(f"✅ {ans}의 재질이 {mat_input}로 변경되었습니다.")
                break
            else:
                print("잘못된 재질입니다. 다시 입력해주세요.")

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
    cost_results = cost_calculator.calculate_all_costs_with_data(final_devices_to_calc, cepci_options)

    # 6. 결과 출력
    print("\n" + "=" * 80)
    print("CALCULATED EQUIPMENT COSTS")
    print("=" * 80)
    for res in cost_results["results"]:
        name = res.get("name")
        cost = res.get("bare_module_cost")
        if cost is not None:
            print(f"  - {name:<20} | Bare Module Cost: ${cost:,.2f}")
        else:
            print(f"  - {name:<20} | ERROR: {res.get('error', 'Unknown Error')}")
    print("-" * 80)
    total = cost_results["total_bare_module_cost"]
    print(f"TOTAL BARE MODULE COST: ${total:,.2f}")
    print("=" * 80)

if __name__ == "__main__":
    main()