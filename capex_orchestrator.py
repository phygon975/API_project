"""
Create on Sep 2, 2025

Total CAPEX orchestrator: 
- Open a .bkp with Aspen Plus (COM)
- Detect block names from Aspen
- Classify categories from BKP (next-4-lines rule)
- Route each category to cost modules when naming/inputs allow

Notes:
- Heat exchangers: requires E01, E02 ... naming (E0{i}) for 0Heat-Exchanger.Heatexchanger
- Pumps: requires P01, P02 ... naming (P0{i}) for 3Pumps.pumps
- Distillation RADFRAC: uses block name directly for 1Distillation.distillationRADFRAC
- DWSTU, Vacuum, Reactors: need extra inputs; skipped unless data available
- Evaporators: requires EVAP1, EVAP2 ... naming for 5Evaporator.verticalEVAPORATORS
"""

import os
import sys
from typing import Dict, Any, List, Tuple

import win32com.client as win32
import importlib.util

# Ensure local imports resolve
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from block_classifier import (
    get_block_names,
    classify_blocks_from_bkp,
)

# Cost modules
def _load_module(module_name: str, file_path: str):
    try:
        if not os.path.exists(file_path):
            return None
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


# Load cost modules by file path (folders contain hyphens/numbers, so normal import won't work)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HeatExchanger = _load_module(
    "HeatExchanger",
    os.path.join(BASE_DIR, "0Heat-Exchanger", "HeatExchanger.py"),
)
Pumps = _load_module(
    "pumps",
    os.path.join(BASE_DIR, "3Pumps", "pumps.py"),
)
Distillation = _load_module(
    "Distillation",
    os.path.join(BASE_DIR, "1Distillation", "Distillation.py"),
)
Evaporator = _load_module(
    "Evaporator",
    os.path.join(BASE_DIR, "5Evaporator", "Evaporator.py"),
)


def _safe_imports():
    modules = {
        "HeatExchanger": HeatExchanger,
        "Pumps": Pumps,
        "Distillation": Distillation,
        "Evaporator": Evaporator,
    }
    return modules


def _filter_names(names: List[str], prefix: str) -> List[str]:
    return [n for n in names if n.upper().startswith(prefix.upper())]


def calculate_costs(
    Application,
    aspen_bkp_path: str,
    current_cost_index: float = 600.0,
) -> Dict[str, Any]:
    # 1) Detect block names from Aspen
    block_names = get_block_names(Application)

    # 2) Classify categories from BKP using detected names
    block_categories, block_info = classify_blocks_from_bkp(aspen_bkp_path, block_names)

    results: Dict[str, Any] = {
        "block_names": block_names,
        "block_info": block_info,
        "categories": block_categories,
        "costs": {},
        "notes": [],
    }

    modules = _safe_imports()

    # Heat Exchangers (require E0{i})
    hx_names = _filter_names(block_categories.get("heat_exchangers", []), "E0")
    if HeatExchanger and len(hx_names) > 0:
        try:
            no_hex = len(hx_names)
            fouling_factor = 0.9
            # Material factor (E_FM) and tube-length correction factor (E_FL)
            E_FM = [1.0] * no_hex
            E_FL = [1.05] * no_hex
            (
                total_cost,
                purchase_costs_current,
                duties,
                areas,
            ) = HeatExchanger.heatexchanger(
                Application,
                no_hex,
                fouling_factor,
                E_FM,
                E_FL,
                current_cost_index,
            )
            results["costs"]["heat_exchangers"] = {
                "total_cost": float(total_cost),
                "purchase_costs_current": [float(x) for x in purchase_costs_current],
                "duties_W": [float(x) for x in duties],
                "areas_m2": [float(x) for x in areas],
                "names_used": hx_names,
            }
        except Exception as e:
            results["notes"].append(f"Heat exchanger cost evaluation skipped: {e}")
    else:
        results["notes"].append("HeatExchanger module missing or no E0* blocks detected.")

    # Pumps (require P0{i})
    pump_names = _filter_names(block_categories.get("pumps", []), "P0")
    if Pumps and len(pump_names) > 0:
        try:
            no_pumps = len(pump_names)
            pump_material_factor = 2.0
            (
                pump_total_costs,
                motor_costs,
                pump_costs,
                pump_head_m,
                pump_flow_m3s,
            ) = Pumps.pumps(
                Application,
                no_pumps,
                pump_material_factor,
                current_cost_index,
            )
            results["costs"]["pumps"] = {
                "total_cost": float(pump_total_costs),
                "motor_costs": [float(x) for x in motor_costs],
                "pump_costs": [float(x) for x in pump_costs],
                "head_m": [float(x) for x in pump_head_m],
                "flow_m3s": [float(x) for x in pump_flow_m3s],
                "names_used": pump_names,
            }
        except Exception as e:
            results["notes"].append(f"Pump cost evaluation skipped: {e}")
    else:
        results["notes"].append("Pumps module missing or no P0* blocks detected.")

    # Distillation (RADFRAC only; DWSTU requires extra stream names)
    if Distillation:
        radfrac_names = [
            b for b in block_names if block_info.get(b, "").lower() == "radfrac"
        ]
        radfrac_details = []
        for name in radfrac_names:
            try:
                tray_spacing = 0.5
                top_space = 1.5
                bottom_space = 1.5
                rho = 8000.0
                F_M = 2.1
                (
                    column_cost,
                    diameter_m,
                    volume_m3,
                ) = Distillation.distillationRADFRAC(
                    Application,
                    name,
                    tray_spacing,
                    top_space,
                    bottom_space,
                    rho,
                    F_M,
                    current_cost_index,
                )
                radfrac_details.append(
                    {
                        "name": name,
                        "purchase_cost_current": float(column_cost),
                        "diameter_m": float(diameter_m),
                        "volume_m3": float(volume_m3),
                    }
                )
            except Exception as e:
                results["notes"].append(f"RADFRAC {name} skipped: {e}")
        if radfrac_details:
            results["costs"]["distillation_radfrac"] = {
                "items": radfrac_details,
                "total_cost": float(sum(x["purchase_cost_current"] for x in radfrac_details)),
            }
        else:
            results["notes"].append("No RADFRAC costs computed.")
    else:
        results["notes"].append("Distillation module not available.")

    # Evaporators (require EVAP{i})
    evap_names = _filter_names(block_names, "EVAP")
    if Evaporator and len(evap_names) > 0:
        try:
            No_Evaporators = len(evap_names)
            souders_brown_param = 0.107
            L_D_ratio = 3.0
            evap_U = 1140.0
            fouling_factor = 0.9
            evap_hotutility_temperature = [412.0] * No_Evaporators
            (
                evap_volume,
                evap_Q,
                evap_area,
                evap_purchase_costs_current,
                evap_total_costs,
            ) = Evaporator.verticalEVAPORATORS(
                Application,
                No_Evaporators,
                souders_brown_param,
                L_D_ratio,
                evap_U,
                evap_hotutility_temperature,
                fouling_factor,
                current_cost_index,
            )
            results["costs"]["evaporators"] = {
                "total_cost": float(evap_total_costs),
                "purchase_costs_current": [float(x) for x in evap_purchase_costs_current],
                "duties_W": [float(x) for x in evap_Q],
                "areas_ft2": [float(x) for x in evap_area],
                "volume_m3": [float(x) for x in evap_volume],
                "names_used": evap_names,
            }
        except Exception as e:
            results["notes"].append(f"Evaporator cost evaluation skipped: {e}")
    else:
        results["notes"].append("Evaporator module missing or no EVAP* blocks detected.")

    # Reactors, Vacuum systems: require additional inputs → skipped by default
    results["notes"].append(
        "Reactors/Vacuum costs require additional inputs; extend orchestrator if needed."
    )

    # Grand total
    grand_total = 0.0
    for key, val in results["costs"].items():
        if isinstance(val, dict):
            if "total_cost" in val:
                try:
                    grand_total += float(val["total_cost"])
                except Exception:
                    pass
            elif "items" in val:
                try:
                    grand_total += float(sum(x.get("purchase_cost_current", 0.0) for x in val["items"]))
                except Exception:
                    pass
    results["grand_total_cost"] = grand_total

    return results


def run(aspen_bkp_filename: str) -> Dict[str, Any]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    aspen_path = os.path.join(current_dir, aspen_bkp_filename)
    if not os.path.exists(aspen_path):
        raise FileNotFoundError(f"BKP file not found: {aspen_path}")

    # Open Aspen
    Application = win32.Dispatch('Apwn.Document')
    Application.InitFromArchive2(aspen_path)
    Application.Visible = 0

    try:
        results = calculate_costs(Application, aspen_path)
    finally:
        try:
            Application.Close(False)
        except Exception:
            pass

    return results


if __name__ == "__main__":
    # Example usage
    filename = sys.argv[1] if len(sys.argv) > 1 else "MIX_HEFA_20250716_after_HI_v1.bkp"
    out = run(filename)
    # Minimal console print
    print("Grand total cost:", out.get("grand_total_cost"))
    print("Notes:")
    for n in out.get("notes", []):
        print(" -", n)


