import numpy as np
import pandas as pd
import config as c
from power_model import SimulationPlan
from battery_model import BatterySystem, ExternalState
from solver import RK4Solver

def main():
    # 1. 初始化
    system = BatterySystem()
    # 初始状态 [c_s_bar, c_e_bar, T, L_SEI, delta_ce_dyn]
    y0 = [19986.6, 1000.0, 298.15, 5.0e-9, 0.0]
    
    solver = RK4Solver(0.0, y0)
    
    ext_state = ExternalState(
        I=0.2, V=3.7, SOC=0.7, c_smax=24983.26
    )

    try:
        plan = SimulationPlan("Cost.json")
    except FileNotFoundError:
        print("错误: 未找到 Cost.json")
        return

    history = []
    is_charging = False
    
    dt = 1.0
    max_time = 30000.0 # 为了演示改为较小时间，原代码是 3e8

    print("开始模拟...")

    while solver.t < max_time:
        # A. 获取当前负载配置
        device_state, profile_name = plan.get_state_at(solver.t)
        if device_state is None:
            print(f"Time {solver.t} out of plan.")
            break

        # B. 充电逻辑判定
        if not is_charging:
            if ext_state.SOC < c.START_CHARGE_SOC or ext_state.V < 2.7:
                is_charging = True
                print(f"T={solver.t:.1f}: Start Charging (SOC={ext_state.SOC*100:.1f}%)")

        # C. 设定目标电流/功率
        if is_charging:
            profile_name = "CHARGING"
            
            # CC 阶段
            i_cc = c.CHARGING_CURRENT_TARGET
            # CV 阶段 (计算限制电流)
            i_cv = system.solve_current_at_voltage(solver.state, ext_state, c.CHARGING_VOLTAGE_LIMIT)
            
            # 取绝对值较小的 (数学上较大的负数)
            target_i = max(i_cc, i_cv)
            target_i = min(target_i, 0.0) # 确保不放电

            # 停止判定
            if abs(target_i) < c.STOP_CHARGE_I and ext_state.SOC > c.STOP_CHARGE_SOC:
                is_charging = False
                target_i = 0.0
                print(f"T={solver.t:.1f}: Stop Charging")

            ext_state.I = target_i
            ext_state.P = target_i * ext_state.V
            ext_state.Q = abs(ext_state.P) * c.RATIO
            
        else:
            # 放电模式：从 PowerModel 获取功率
            # 注意：Rust中除以了1000 (mW -> W) 和 n_parallel
            p_elec = device_state.calculate_power_mw() / 1000.0 / c.N_PARALLEL
            q_heat = device_state.calculate_heat_mw() / 1000.0
            
            ext_state.P = p_elec
            ext_state.Q = q_heat
            # 电流会在 solver step 后通过 calculate_state 更新 (I = P/V)

        # D. 执行一步积分
        # Rust 逻辑: sys.calculate -> solver.step -> sys.calculate
        # 我们在 step 内部已经做了一次 calculate，但在 step 之前需要根据 P 更新 I 吗？
        # Rust 中 calculate 更新 I = P/V。
        # 这里我们在 step 之前手动进行一次 pre-calculation 更好，或者让 system 处理。
        # 简单起见，如果非充电模式，估算 I = P / V_prev
        if not is_charging and ext_state.V > 0.1:
            ext_state.I = ext_state.P / ext_state.V

        # 步进
        ext_state = solver.step(system, dt, ext_state)

        # E. 记录数据
        if int(solver.t) % 100 == 0: # 降采样
            history.append({
                "Time": solver.t,
                "Profile": profile_name,
                "Current(A)": ext_state.I,
                "Voltage(V)": ext_state.V,
                "Q(W)": ext_state.Q,
                "T(K)": solver.state[2],
                "SOC": ext_state.SOC,
                "SOH": ext_state.SOH
            })

    # 保存
    df = pd.DataFrame(history)
    df.to_csv("simulation_results_py.csv", index=False, float_format='%.4f')
    print(f"模拟结束，已保存 {len(df)} 条记录。")

if __name__ == "__main__":
    main()