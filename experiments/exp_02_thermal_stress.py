import sys
import os

# --- 关键修复代码 ---
# 获取当前文件的父目录的父目录 (即项目根目录 SPMe-P-Aging)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
# ------------------

# 现在 Python 就能找到 simulation 了
from simulation.init_utils import get_initial_state_by_soh
from simulation.simulator import run_single_static_test
import config as c

def run_experiment():
    print("=== Experiment 2: Thermal Stress Sensitivity ===")
    
    temps = [25, 35, 45]
    profile_name = "5g_gaming_heavy" # 确保 Cost.json 里有这个
    
    print(f"{'Temp(C)':<10} | {'Aging Rate':<15} | {'Avg Temp(C)'}")
    print("-" * 45)

    for T in temps:
        # 1. 准备初始状态
        y0, ext_init = get_initial_state_by_soh(0.90)
        
        # 2. 强制修改环境温度 (Hack config)
        # 注意：这里我们修改全局 config，这在单线程脚本是安全的
        original_temp = c.T_AMB
        c.T_AMB = T + 273.15 
        y0[2] = T + 273.15 # 电池初始温度也同步

        try:
            # 3. 运行
            rate, real_avg_temp = run_single_static_test(
                y0, ext_init, 
                app_profile_name=profile_name, 
                duration=3600
            )
            print(f"{T:<10} | {rate:.2e}        | {real_avg_temp:.2f}")
            
        finally:
            # 4. 恢复环境温度 (好习惯)
            c.T_AMB = original_temp

if __name__ == "__main__":
    run_experiment()