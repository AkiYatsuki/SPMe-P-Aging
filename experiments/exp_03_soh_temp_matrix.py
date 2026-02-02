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
    print("=== Experiment 3: SOH x Temperature Matrix Scan ===")
    print("Hypothesis: Aged batteries (Lower SOH) suffer more from Thermal Stress.")

    # 1. 定义扫描矩阵
    # SOH: 从新电池 (1.0) 到 寿命末期 (0.8)
    soh_levels = [1.0, 0.95, 0.90, 0.85, 0.80]
    
    # 环境温度: 模拟不同散热条件或气温
    temps_c = [25, 35, 45]
    
    # 固定使用高负载 Profile (放大效应)
    profile = "5g_gaming_heavy"
    
    results = []
    
    # 2. 矩阵扫描
    for soh in soh_levels:
        for T_amb in temps_c:
            # 准备参数覆盖
            # 注意：我们需要强制覆盖 config 中的环境温度
            # 同时也需要确保 y0 中的初始温度也是 T_amb
            
            # 临时修改全局配置
            original_temp = c.T_AMB
            c.T_AMB = T_amb + 273.15
            
            try:
                # 获取初始状态
                y0, ext_init = get_initial_state_by_soh(soh)
                # 强制同步初始温度（否则电池从25度开始升温，误差大）
                y0[2] = c.T_AMB 
                
                # 运行模拟 (3小时稳态)
                rate, avg_batt_temp = run_single_static_test(
                    y0, ext_init, 
                    app_profile_name=profile, 
                    duration=10800 
                )
                
                # 记录结果
                results.append({
                    "SOH_Start": soh,
                    "Ambient_Temp": T_amb,
                    "Avg_Battery_Temp": avg_batt_temp,
                    "Aging_Rate": rate,
                    # 计算温升 (电池平均温度 - 环境温度)
                    "Temp_Rise": avg_batt_temp - T_amb
                })
                
                print(f"SOH: {soh:.2f} | Tamb: {T_amb}C | Tbatt: {avg_batt_temp:.1f}C (+{avg_batt_temp-T_amb:.1f}) | Rate: {rate:.2e}")
                
            finally:
                # 恢复环境温度
                c.T_AMB = original_temp

    # 3. 数据分析
    df = pd.DataFrame(results)
    
    # 创建透视表 (Pivot Table) 方便观察
    print("\n=== Aging Rate Matrix (The 'Death Map') ===")
    pivot_rate = df.pivot(index="SOH_Start", columns="Ambient_Temp", values="Aging_Rate")
    print(pivot_rate)
    
    print("\n=== Temperature Rise Matrix (Internal Resistance Effect) ===")
    pivot_temp = df.pivot(index="SOH_Start", columns="Ambient_Temp", values="Temp_Rise")
    print(pivot_temp)
    
    # 保存
    df.to_csv("results_exp_03_matrix.csv", index=False)
    print("\nResults saved to results_exp_03_matrix.csv")

if __name__ == "__main__":
    run_experiment()