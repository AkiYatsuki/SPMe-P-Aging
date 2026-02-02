import numpy as np
import config as c
from models.battery_model import BatterySystem, ExternalState

def get_initial_state_by_soh(target_soh: float, soc_start: float = 1.0) -> tuple:
    """
    根据目标 SOH 和 SOC 反推物理模型的初始状态向量 y0。
    """
    # 1. 计算几何参数 (与 BatterySystem __init__ 保持一致)
    Asurf_n = c.AREA * c.L_NEG * 3.0 * c.EPS_S_NEG / c.R_S_NEG
    Q_nominal = c.EPS_S_NEG * c.F * c.L_NEG * c.AREA * c.C_MAX_NEG
    
    # 2. 反推 L_SEI (SEI 厚度)
    # 注意：这里我们假设初始时刻死锂(Q_dead)为0，所有 SOH 损失都来自 SEI
    # 这只是为了初始化方便。实际上老电池会有大量死锂。
    # 如果想更精确，可以分配 loss: 80% SEI, 20% Dead Li
    # SOH = 1 - (lost / nominal) -> lost = (1 - SOH) * nominal
    q_lost = (1.0 - target_soh) * Q_nominal
    # q_lost = (vol_sei / V_SEI) * F -> vol_sei = q_lost * V_SEI / F
    vol_sei = q_lost * c.V_SEI / c.F
    # vol_sei = Asurf_n * L_SEI -> L_SEI = vol_sei / Asurf_n
    l_sei_init = vol_sei / Asurf_n
    
    # 确保有一个最小厚度 (新电池也不是 0，通常有初始膜)
    l_sei_init = max(l_sei_init, 5.0e-9)

    # 3. 反推 c_s_bar (负极锂浓度) 基于 SOC
    # SOC = c_s_bar / (c_smax * SOH)  <-- 注意：通常定义 SOC 是相对于当前容量
    # 或者 SOC = (c_s_bar / c_smax) <-- 定义 SOC 相对于设计容量
    # 查看您的代码：new_ext.SOC = c_s_bar / (ext.c_smax * new_ext.SOH)
    # 所以：
    c_s_bar_init = soc_start * c.C_MAX_NEG * target_soh
    
    # 4. 组装初始状态向量 y
    # [c_s_bar, c_e_bar, T, L_SEI, delta_ce_dyn]
    y0 = [
        c_s_bar_init,   # 负极浓度
        1000.0,         # 电解液浓度 (假设平衡态)
        c.T_AMB,        # 初始温度
        l_sei_init,     # 反推的 SEI 厚度
        0.0,            # 动态浓差初始为 0
        0.0,            # Q_rev 初始为 0 (无析锂)
        0.0,            # Q_dead 初始为 0 (我们把历史衰减都算在 SEI 里了，为了简化初始化)
    ]
    
    # 5. 初始化外部状态
    ext_state = ExternalState(
        SOC=soc_start,
        SOH=target_soh,
        V=4.2,          # 初始电压估算，solver 会在第一步校准
        c_smax=c.C_MAX_NEG,
        AGEING=(1.0 - l_sei_init / c.L_NEG) # 简单的老化因子同步
    )
    
    return y0, ext_state