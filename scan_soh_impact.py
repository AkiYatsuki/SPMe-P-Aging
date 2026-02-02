import numpy as np
import pandas as pd
import config as c
from battery_model import BatterySystem
from solver import RK4Solver
from init_utils import get_initial_state_by_soh
import main # 复用 main 中的 run_simulation 逻辑（如果已封装）

def run_short_term_simulation(y0, ext_state, app_profile, duration=3600):
    """
    运行短时间的模拟（例如 1 小时或 1 个放电周期），
    计算这一段时间内的瞬时衰老速率。
    """
    system = BatterySystem()
    solver = RK4Solver(0.0, y0)
    
    sei_thickness_start = y0[3]
    soh_start = ext_state.SOH
    
    # ... 这里插入模拟循环 (step) ...
    # 模拟该 App 运行 duration 秒
    # 伪代码：
    # while solver.t < duration:
    #    ... solver.step ...
    
    # 模拟结束，读取状态
    sei_thickness_end = solver.state[3]
    
    # 计算 SEI 增量速率 (m/s)
    sei_growth_rate = (sei_thickness_end - sei_thickness_start) / duration
    
    # 也可以计算 SOH 衰减速率
    # Delta SOH / hour
    soh_drop_per_hour = (soh_start - ext_state.SOH) * (3600.0 / duration)
    
    avg_temp = np.mean([T for T in history_temps]) # 假设记录了温度
    
    return soh_drop_per_hour, avg_temp

def parameter_sweep():
    # 扫描维度 1: 电池健康状态
    soh_levels = [1.0, 0.95, 0.90, 0.85, 0.80]
    
    # 扫描维度 2: App 类型 (假设对应 Cost.json 里的 profile key)
    apps = ["video_hd", "gaming", "wechat_voice"] 
    
    results = []
    
    for soh in soh_levels:
        for app in apps:
            print(f"Scanning: SOH={soh*100}%, App={app}")
            
            # 1. 自动计算初始物理状态
            y0, ext_init = get_initial_state_by_soh(target_soh=soh)
            
            # 2. 运行模拟 (只跑 1 个小时或 1 个完整放电过程即可)
            # 因为我们关注的是"速率"，不需要跑几年
            rate, avg_T = run_short_term_simulation(y0, ext_init, app)
            
            results.append({
                "Start_SOH": soh,
                "App": app,
                "Aging_Rate_per_Hour": rate,
                "Avg_Temperature": avg_T
            })
            
    # 保存结果
    df = pd.DataFrame(results)
    df.to_csv("aging_matrix.csv", index=False)
    print("扫描完成")

if __name__ == "__main__":
    parameter_sweep()