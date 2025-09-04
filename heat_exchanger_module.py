"""
Create on Sep 3, 2025

@author: Pyeong-Gon Jung
"""

import os
import win32com.client as win32
import numpy as np
import sys
import time
from threading import Thread
from typing import Optional

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


# #Unit calculations
# m_to_inch = 39.3701
# m_to_ft = 3.28084
# m2_to_ft2 = 10.7639
# m3_to_ft3 = 35.3147
# kPa_to_psig = 0.145038
# kPa_to_Torr = 7.50062
# kg_to_lb = 2.20462
# W_to_Btu_hr = 3.41
# gal_to_m3 = 0.00378541
# BTU_to_J = 1055.06
# HP_to_W = 745.7
# m3_s_to_gpm = 15850.3
# kg_m3_to_lb_gal = 0.0083454
# t_to_kg = 1000
# HP_per_1000_Gal = 10
# N_m2_to_psig = 0.000145038

# #Operating year
# hr_per_day = 24
# day_per_year = 365
# operating_hr_per_year = 8000

#cost factors of equations from Seider et al. 2006
cost_index_2006 = 500

file = 'MIX_HEFA_20250716_after_HI_v1.bkp'  #아스펜 파일이 바뀔 시 여기를 수정해야 함
    
    # 2. Get absolute path to Aspen Plus file
current_dir = os.path.dirname(os.path.abspath(__file__))
aspen_Path = os.path.join(current_dir, file)
print(f"Looking for file: {aspen_Path}")

try:
    # 4. Initiate Aspen Plus application
    print('\nConnecting to Aspen Plus... Please wait...')
    connect_spinner = Spinner('Connecting to Aspen Plus')
    connect_spinner.start()
    Application = win32.Dispatch('Apwn.Document') # Registered name of Aspen Plus
    connect_spinner.stop('Aspen Plus COM object created successfully!')
    
    # 5. Try to open the file
    print(f'Attempting to open file: {aspen_Path}')
    open_spinner = Spinner('Opening Aspen backup')
    open_spinner.start()
    Application.InitFromArchive2(aspen_Path)    
    open_spinner.stop('File opened successfully!')
    
    # 6. Make the files visible
    Application.visible = 1   
    print('Aspen Plus is now visible')

except Exception as e:
    print(f"ERROR connecting to Aspen Plus: {e}")
    print("\nPossible solutions:")
    print("1. Make sure Aspen Plus is installed on your computer")
    print("2. Make sure Aspen Plus is properly licensed")
    print("3. Try running Aspen Plus manually first to ensure it works")
    print("4. Check if the .bkp file is compatible with your Aspen Plus version")
    exit()

block_names = ['03HEX', '04HEX', '06HEX', '12HEX']
fouling_factor = 0.9
E_FM = np.ones(len(block_names)) * 1.0
E_FL = np.ones(len(block_names)) * 1.05
current_cost_index = 600


def heatexchanger(Application, name_heat_exchanger, fouling_factor, E_FM, E_FL, current_cost_index):

        #For storing the results in a vector
    E_T = np.zeros(len(name_heat_exchanger))
    E_T_unit = np.zeros(len(name_heat_exchanger))
    E_Q = np.zeros((len(name_heat_exchanger)))
    E_U = np.zeros(len(name_heat_exchanger))
    E_area = np.zeros((len(name_heat_exchanger)))
    E_LMTD = np.zeros(len(name_heat_exchanger))
    E_pressure = np.zeros(len(name_heat_exchanger))
    E_FP = np.zeros(len(name_heat_exchanger))
    E_base_costs = np.zeros(len(name_heat_exchanger))
    E_purchase_costs = np.zeros(len(name_heat_exchanger))
    E_purchase_costs_current = np.zeros(len(name_heat_exchanger))
    E_Q_BTU = np.zeros(len(name_heat_exchanger))

    #For loop for all heat exchangers in the simulation
    for i in range(len(name_heat_exchanger)):
        #one of the following two commands for computing the temperature E_T will work, try function is required because
        #depending on the type of heat exchanger, the path in aspen plus is called differently
        heat_exchanger = name_heat_exchanger[i]    
        try: 
            E_T[i] = Application.Tree.FindNode(f"\Data\Blocks\{heat_exchanger}\Output\B_TEMP").Value
        except: 
            print()

        try:
            E_T_unit[i] = Application.Tree.FindNode("\\Unit Table\\TEMPERATURE\\C").Value
        except:
            print()

        print(f"Heat exchanger {heat_exchanger} temperature: {E_T[i]} {E_T_unit[i]}")

    return E_T, E_T_unit
        # if E_T[i] < 252+273.15 :      #For this temperature, either double pipe or shell and tube heat exchangers are used  
        #     #for area calculation:
        #     E_Q[i] = Application.Tree.FindNode(f"\\Data\\Blocks\\{heat_exchanger}\\Output\\HX_DUTY").Value
        #     E_U[i] = Application.Tree.FindNode(f"\\Data\\Blocks\\{heat_exchanger}\\Input\\U").Value    #W/m2/C
        #     E_LMTD[i] = Application.Tree.FindNode(f"\\Data\\Blocks\\{heat_exchanger}\\Output\\HX_DTLM").Value   #K
        #     E_area[i] = E_Q[i] / (E_U[i] * E_LMTD[i] * fouling_factor) * m2_to_ft2      #in ft2

        # else:       #Shell and Tube HE is taken for areas above 150 ft2 
        #     #for pressure factor calculation:
        #     E_pressure[i] = Application.Tree.FindNode(f"\\Data\\Blocks\\{heat_exchanger}\\Output\\COLDINP").Value * N_m2_to_psig    #Aspen in N/m2


E_T, E_T_unit = heatexchanger(Application, block_names, fouling_factor, E_FM, E_FL, current_cost_index)

blocks_node = Application.Tree.FindNode("\\Data\\Blocks")
print(hasattr(blocks_node, 'Elements'))

for element in blocks_node.Elements:
    try:
        block_names.append(element.Name)
    except:
        print()

print(block_names)
