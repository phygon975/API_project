# -*- coding: utf-8 -*-
"""
Created on Mon May 30 17:23:28 2022
Modified for better error handling

@author: Ann-Joelle
"""

import os                          # Import operating system interface
import win32com.client as win32    # Import COM
import numpy as np
import sys
import time
from threading import Thread
from typing import Optional

# Add current directory to path to import HeatExchanger module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

try:
    from HeatExchanger import heatexchanger
    print("HeatExchanger module imported successfully!")
except ImportError as e:
    print(f"Error importing HeatExchanger module: {e}")
    print("Make sure HeatExchanger.py is in the same directory")
    sys.exit(1)

def main():
    #%% Aspen Plus Connection
    
    # 1. Specify file name
    file = 'CumenePlant4.bkp'  
    
    # 2. Get absolute path to Aspen Plus file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    aspen_Path = os.path.join(current_dir, file)
    print(f"Looking for file: {aspen_Path}")
    
    # 3. Check if file exists
    if not os.path.exists(aspen_Path):
        print(f"ERROR: File not found: {aspen_Path}")
        print("Please make sure CumenePlant4.bkp is in the same directory as this script")
        return
    
    print(f"File found: {aspen_Path}")
    
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
        return
    
    #%% Constants and Inputs
    
    #cost factors 
    cost_index_2019 = 607.5
    cost_index_2006 = 500
    
    #number of heat exchangers
    No_Heat_Exchanger = 8
    
    #constants
    fouling_factor = 0.9
    E_FL = np.ones(No_Heat_Exchanger) * 1.05     #Tube length correction factor for shell and tube heat exchanger according to Seider (2008)
    E_FM = np.ones(No_Heat_Exchanger)  #only carbon steel chosen
    
    #%% Function Call
    
    try:
        print("\nCalculating heat exchanger costs...")
        calc_spinner = Spinner('Calculating costs')
        calc_spinner.start()
        E_totalcosts, E_purchase_costs2019, E_Q, E_area = heatexchanger(Application, No_Heat_Exchanger, fouling_factor, E_FM, E_FL, cost_index_2019)
        calc_spinner.stop('Calculation finished.')
        
        print("\n=== RESULTS ===")
        print(f"Total Heat Exchanger Costs: ${E_totalcosts:,.2f}")
        print(f"Individual Heat Exchanger Costs: {E_purchase_costs2019}")
        print(f"Heat Duties (W): {E_Q}")
        print(f"Areas (m²): {E_area}")
        
    except Exception as e:
        print(f"ERROR during calculation: {e}")
        print("This might be due to:")
        print("1. Aspen Plus simulation not being properly set up")
        print("2. Heat exchangers not named correctly (should be E01, E02, etc.)")
        print("3. Missing data in the simulation")

if __name__ == "__main__":
    main()
