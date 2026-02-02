import sys
import os
import pandas as pd
import numpy as np

# --- 路径修正 (确保能找到 simulation 模块) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from simulation.init_utils import get_initial_state_by_soh
from simulation.simulator import run_single_static_test
import config as c

def run_experiment():
    print("=== Experiment 3: 5G vs Idle Matrix Scan (Comparison) ===")
    
    # 1. 定义实验变量
    # SOH: 从 0.96 到 0.80
    soh_levels = np.linspace(0.96, 0.80, 9)
    soh_levels = np.round(soh_levels, 3)
    
    # 温度: 25度到45度
    temps_c = [25, 30, 35, 40, 45]
    
    # 场景: 对比 5G 和 Idle
    scenarios = ["idle_baseline", "5g_gaming_heavy"]
    
    results = []
    
    total_iter = len(soh_levels) * len(temps_c) * len(scenarios)
    print(f"Total iterations: {total_iter}")
    
    # 2. 三层嵌套循环 (SOH -> Temp -> Profile)
    for soh in soh_levels:
        for T_amb in temps_c:
            # --- 关键修改：在这里遍历 Profile ---
            for profile in scenarios: 
                
                # 临时修改环境温度
                original_temp = c.T_AMB
                c.T_AMB = T_amb + 273.15
                
                try:
                    # 初始化电池状态
                    y0, ext_init = get_initial_state_by_soh(soh)
                    y0[2] = c.T_AMB # 强制同步初始温度
                    
                    # 运行仿真
                    # 注意：这里的 app_profile_name 使用的是当前循环变量 profile
                    rate, avg_batt_temp = run_single_static_test(
                        y0, ext_init, 
                        app_profile_name=profile, 
                        duration=10800 # 3小时
                    )
                    
                    # 记录结果
                    results.append({
                        "Scenario": profile,  # 必须记录场景名，画图要用
                        "SOH_Start": soh,
                        "Ambient_Temp": T_amb,
                        "Avg_Battery_Temp": avg_batt_temp,
                        "Aging_Rate": rate,
                        "Temp_Rise": avg_batt_temp - T_amb
                    })
                    
                    # 打印进度
                    print(f"[{profile}] SOH:{soh:.2f} T:{T_amb} -> Rate:{rate:.2e}")
                    
                finally:
                    # 恢复环境温度，防止污染下一次循环
                    c.T_AMB = original_temp

    # 3. 保存结果
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    df = pd.DataFrame(results)
    csv_path = os.path.join(results_dir, "exp_03_comparison.csv")
    df.to_csv(csv_path, index=False)
    print(f"\nExperiment Finished. Data saved to: {csv_path}")

if __name__ == "__main__":
    run_experiment()