# -*- coding: utf-8 -*-
"""
Created on Mon May 30 17:23:28 2022

@author: Ann-Joelle
"""

import os                          # Import operating system interface
import win32com.client as win32    # Import COM
import numpy as np


from HeatExchanger import  heatexchanger
 

#%% Aspen Plus Connection

# 1. Specify file name
file = 'CumenePlant4.bkp'  

# 2. Get path to Aspen Plus file
aspen_Path = os.path.abspath(file)
print(aspen_Path)
 

# 3 Initiate Aspen Plus application
print('\n Connecting to the Aspen Plus... Please wait ')
Application = win32.Dispatch('Apwn.Document') # Registered name of Aspen Plus
print('Connected!')

# 4. Initiate Aspen Plus file
Application.InitFromArchive2(aspen_Path)    

# 5. Make the files visible
Application.visible = 1   

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

E_totalcosts, E_purchase_costs2019, E_Q, E_area = heatexchanger(Application, No_Heat_Exchanger, fouling_factor, E_FM, E_FL, cost_index_2019)

#%% Reporting: 장치별 비용 및 계산 과정 요약 출력
print('\n================ 장치 비용 계산 결과 ================')
print(f"분석 파일: {aspen_Path}")
print(f"열교환기 개수: {No_Heat_Exchanger}")
print(f"적용 비용 지수(2019): {cost_index_2019}")
print(f"오염계수(fouling_factor): {fouling_factor}")
print(f"튜브 길이 보정계수 E_FL (예: 첫 번째 값): {E_FL[0] if len(E_FL)>0 else 'N/A'}")
print(f"재질 보정계수 E_FM (예: 첫 번째 값): {E_FM[0] if len(E_FM)>0 else 'N/A'}")

# 장치별 상세 출력
print('\n[장치별 상세]')
for i, (cost, q, area) in enumerate(zip(E_purchase_costs2019, E_Q, E_area), start=1):
    try:
        print(f"  - E{i:02d}: 구매비용(2019$) = {cost:,.2f}, 열부하 = {q:,.2f} W, 면적 = {area:,.2f} m^2")
    except Exception:
        print(f"  - E{i:02d}: 구매비용(2019$) = {cost}, 열부하 = {q} W, 면적 = {area} m^2")

# 총합 출력
try:
    total_purchase = float(np.nansum(E_purchase_costs2019))
except Exception:
    total_purchase = sum(E_purchase_costs2019) if hasattr(E_purchase_costs2019, '__iter__') else E_purchase_costs2019

print('\n[요약]')
try:
    print(f"총 열교환기 구매비용 합계(2019$): {total_purchase:,.2f}")
    print(f"총 설치비 추정(2019$): {float(E_totalcosts):,.2f}")
except Exception:
    print(f"총 열교환기 구매비용 합계(2019$): {total_purchase}")
    print(f"총 설치비 추정(2019$): {E_totalcosts}")
print('=================================================\n')




