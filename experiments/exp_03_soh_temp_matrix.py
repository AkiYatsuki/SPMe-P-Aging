import sys
import os
import pandas as pd
import numpy as np

# 路径修正
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from simulation.init_utils import get_initial_state_by_soh
from simulation.simulator import run_single_static_test
import config as c

def run_experiment():
    print("=== Experiment 3: High-Res SOH x Temperature Matrix Scan ===")
    
    # 1. 定义更高分辨率的扫描矩阵
    # SOH: 避开 1.0 (化成期)，从 0.96 细密扫描到 0.80
    # np.linspace 生成均匀分布的点
    soh_levels = np.linspace(0.96, 0.80, 9)  # [0.96, 0.94, ..., 0.80] 
    soh_levels = np.round(soh_levels, 3)     # 避免浮点数误差
    
    # 温度: 加密温度点，捕捉非线性
    temps_c = [25, 30, 35, 40, 45]
    
    profile = "5g_gaming_heavy"
    results = []
    
    print(f"Scanning {len(soh_levels)} SOH levels x {len(temps_c)} Temps = {len(soh_levels)*len(temps_c)} iterations.")
    
    # 2. 矩阵扫描
    for soh in soh_levels:
        for T_amb in temps_c:
            original_temp = c.T_AMB
            c.T_AMB = T_amb + 273.15
            
            try:
                y0, ext_init = get_initial_state_by_soh(soh)
                y0[2] = c.T_AMB 
                
                # 运行模拟 (3小时稳态)
                rate, avg_batt_temp = run_single_static_test(
                    y0, ext_init, 
                    app_profile_name=profile, 
                    duration=10800 
                )
                
                results.append({
                    "SOH_Start": soh,
                    "Ambient_Temp": T_amb,
                    "Avg_Battery_Temp": avg_batt_temp,
                    "Aging_Rate": rate,
                    "Temp_Rise": avg_batt_temp - T_amb
                })
                
                print(f"SOH: {soh:.2f} | Tamb: {T_amb}C | Rate: {rate:.2e}")
                
            finally:
                c.T_AMB = original_temp

    # 3. 保存到 results 文件夹
    df = pd.DataFrame(results)
    
    # 自动创建 results 文件夹
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    csv_path = os.path.join(results_dir, "exp_03_matrix_high_res.csv")
    df.to_csv(csv_path, index=False)
    print(f"\nData saved to: {csv_path}")

if __name__ == "__main__":
    run_experiment()