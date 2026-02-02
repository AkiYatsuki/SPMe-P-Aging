import numpy as np
import config as c

from models.power_model import SimulationPlan
from models.battery_model import BatterySystem
from solver import RK4Solver

def run_single_static_test(y0, ext_state, app_profile_name, duration=3600, internal_params=None):
    """
    运行单次静态负载测试。
    输入: 物理初值 y0, 外部状态 ext_state, App名称, 持续时间
    输出: (SOH衰减速率/小时, 平均温度)
    """
    # 1. 初始化系统
    system = BatterySystem(param_overrides=internal_params)
    solver = RK4Solver(0.0, y0)
    
    # 2. 获取负载配置
    try:
        plan = SimulationPlan("Cost.json")
        if app_profile_name not in plan.profiles:
            print(f"Warning: Profile '{app_profile_name}' not found.")
            return None, None
        device_state = plan.profiles[app_profile_name]
    except FileNotFoundError:
        print("Error: Cost.json not found.")
        return None, None

    # 3. 数据收集
    temps = []
    soh_start = ext_state.SOH
    
    # 4. 积分循环
    dt = 1.0
    current_time = 0.0
    
    while current_time < duration:
        # 计算功率
        p_elec = device_state.calculate_power_mw() / 1000.0 / c.N_PARALLEL
        q_heat = device_state.calculate_heat_mw() / 1000.0
        
        ext_state.P = p_elec
        ext_state.Q = q_heat
        
        # 更新电流 I = P/V
        if ext_state.V > 0.1:
            ext_state.I = ext_state.P / ext_state.V
            
        # 步进
        ext_state = solver.step(system, dt, ext_state)
        current_time += dt
        
        # 记录温度 (K)
        temps.append(solver.state[2])
        
        # 低压保护
        if ext_state.V < 2.5:
            break
            
    # 5. 计算指标
    soh_end = ext_state.SOH
    avg_temp_c = np.mean(temps) - 273.15
    
    actual_hours = current_time / 3600.0
    loss_rate = (soh_start - soh_end) / actual_hours if actual_hours > 0 else 0.0
    
    return loss_rate, avg_temp_c