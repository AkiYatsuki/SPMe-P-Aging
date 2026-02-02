import sys
import os
# 将根目录加入路径，否则找不到 models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from simulation.init_utils import get_initial_state_by_soh
from simulation.simulator import run_single_static_test

def run_experiment():
    print("=== Experiment 1: 5G vs Idle Aging Analysis ===")
    
    # 1. 实验设定
    scenarios = [
        {"name": "Idle_WiFi", "profile": "idle_baseline", "desc": "Reference"},
        {"name": "5G_Gaming", "profile": "5g_gaming_heavy", "desc": "High Stress"}
    ]
    
    target_soh = 0.90  # 选用稳定期的电池
    duration = 3600 * 3 # 跑3小时以达到热平衡
    
    results = []

    # 2. 循环执行
    for sc in scenarios:
        print(f"Running scenario: {sc['name']}...")
        
        # 获取初始状态
        y0, ext_init = get_initial_state_by_soh(target_soh)
        
        # 运行仿真 (注意：这里不需要改 config，因为差异在 Profile 里)
        rate, avg_temp = run_single_static_test(
            y0, ext_init, 
            app_profile_name=sc['profile'], 
            duration=duration
        )
        
        results.append({
            "Scenario": sc['name'],
            "Avg_Temp_C": avg_temp,
            "Aging_Rate_Hr": rate
        })

    # 3. 分析与计算折损
    df = pd.DataFrame(results)
    
    # 提取基准值
    base_rate = df.loc[df['Scenario'] == "Idle_WiFi", "Aging_Rate_Hr"].values[0]
    base_temp = df.loc[df['Scenario'] == "Idle_WiFi", "Avg_Temp_C"].values[0]
    
    # 计算加速因子
    df['Acceleration_Factor'] = df['Aging_Rate_Hr'] / base_rate
    df['Equivalent_Life_Loss_per_Hour'] = df['Acceleration_Factor'] # 玩1小时等于待机多少小时
    
    print("\n=== Results ===")
    print(df[['Scenario', 'Avg_Temp_C', 'Acceleration_Factor']])
    
    # 4. 保存
    df.to_csv("results_exp_01_5g_aging.csv", index=False)
    print("Results saved.")

if __name__ == "__main__":
    run_experiment()