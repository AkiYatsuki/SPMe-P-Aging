# models/battery_model.py

import numpy as np
import config as c
from dataclasses import dataclass

@dataclass
class ExternalState:
    I: float = 0.0
    V: float = 3.7
    D_e: float = 2e-10
    R_tot: float = 0.1
    c_smax: float = c.C_MAX_NEG
    P: float = 0.0
    Q: float = 0.0
    SOC: float = 0.7
    SOH: float = 1.0
    AGEING: float = 1.0
    # 新增监控字段
    Phi_Anode: float = 0.1  # 负极电位
    I_Plating: float = 0.0  # 析锂电流

class BatterySystem:
    def __init__(self, param_overrides=None):
        # 初始化参数字典，支持扫描
        self.p = {k: getattr(c, k) for k in dir(c) if not k.startswith("__")}
        if param_overrides:
            self.p.update(param_overrides)

        # 几何参数预计算
        self.Asurf_n = self.p['AREA'] * self.p['L_NEG'] * 3.0 * self.p['EPS_S_NEG'] / self.p['R_S_NEG']
        self.Asurf_p = self.p['AREA'] * self.p['L_POS'] * 3.0 * self.p['EPS_S_POS'] / self.p['R_S_POS']
        self.L_total = self.p['L_POS'] + 2.0 * self.p['L_SEP'] + self.p['L_NEG']

    def derivatives(self, t: float, y: np.ndarray, ext: ExternalState) -> np.ndarray:
        """
        y[0]: c_s_bar (负极锂浓度)
        y[1]: c_e_bar (电解液浓度)
        y[2]: T (温度)
        y[3]: L_SEI (SEI厚度)
        y[4]: delta_ce_dyn (动态浓差)
        y[5]: Q_rev (可逆析锂量 C) [新增]
        y[6]: Q_dead (死锂量 C) [新增]
        """
        c_s_bar, c_e_bar, T, L_SEI, delta_ce_dyn, Q_rev, Q_dead = y
        p = self.p

        # --- 1. 负极电位计算 (用于判断析锂) ---
        # 交换电流密度
        term_n = max(1e-9, (c_e_bar - delta_ce_dyn) * c_s_bar * (p['C_MAX_NEG'] - c_s_bar))
        i_0n = p['K0'] * ext.AGEING * (term_n ** p['ALPHA'])
        
        # 过电势 Eta_n
        j_n = ext.I / self.Asurf_n
        # 防止 arg_n 过大溢出
        arg_n = j_n / (2.0 * max(i_0n, 1e-9))
        eta_n = (2.0 * c.R * T / c.F) * np.arcsinh(arg_n)
        
        # 平衡电位 U_n
        theta_n = np.clip(c_s_bar / p['C_MAX_NEG'], 0.001, 0.999)
        u_n = self._ocv_neg(theta_n)
        
        # SEI 膜压降
        r_sei_film = L_SEI / (self.Asurf_n * p['KAPPA_SEI'])
        v_drop_sei = ext.I * r_sei_film
        
        # 负极真实电位 (vs Li/Li+)
        phi_anode = u_n + eta_n + v_drop_sei

        # --- 2. 析锂与回溶逻辑 ---
        i_plating = 0.0          # 析锂电流
        i_intercalation = ext.I  # 嵌入电流

        if phi_anode < 0.0:
            # [情况 A]: 析锂 (Plating)
            # Butler-Volmer 的简化形式
            exp_term = np.exp(-p['ALPHA_PLATING'] * c.F * phi_anode / (c.R * T))
            i_plating_density = -p['K_PLATING'] * p['AREA'] * exp_term
            i_plating = i_plating_density # 负值，表示锂离子离开电解液变成金属锂
            
            # 此时总电流 I = i_inter + i_plating
            i_intercalation = ext.I - i_plating

        elif ext.I > 0.0 and Q_rev > 1e-5:
            # [情况 B]: 回溶 (Stripping)
            # 只有在放电(I>0)且有可逆锂(Q_rev>0)时发生
            # 假设优先消耗可逆锂
            i_plating = ext.I # 正值，表示金属锂变回锂离子
            i_intercalation = 0.0

        # --- 3. 状态方程 ---
        
        # [0] d(c_s)/dt: 仅受嵌入电流影响
        dcs_dt = -i_intercalation / (p['EPS_S_NEG'] * ext.SOH) / c.F / p['L_NEG'] / p['AREA']
        
        # [1] d(c_e)/dt: 假设析锂不显著影响电解液浓度分布(简化)
        dce_dt = (1.0 - p['T0_POS']) / (c.EPS_E * c.F) * (ext.I / p['L_POS'] - ext.I / p['L_NEG'])
        
        # [2] d(T)/dt
        heat_gen = (ext.I**2 * ext.R_tot * c.N_PARALLEL) + ext.Q
        heat_diss = c.H_CONV * c.A_SURF * (T - c.T_AMB)
        dT_dt = (heat_gen - heat_diss) / (c.MASS_PHONE * c.CP_PHONE)

        # [3] d(L_SEI)/dt
        # Arrhenius 温度修正
        arrhenius = np.exp(-3000.0 * (1.0/T - 1.0/298.15))
        d_lsei_dt = c_s_bar * p['D_SOLV'] * arrhenius * p['V_SEI'] / 2.0 / L_SEI
        
        # [4] d(Delta_Ce)/dt
        delta_ce_target = (1.0 - p['T0_POS']) / (2.0 * c.F * ext.D_e) * (ext.I * p['L_SEP'])
        tau_diff = (self.L_total**2) / (20.0 * ext.D_e)
        d_delta_ce_dt = (delta_ce_target - delta_ce_dyn) / tau_diff

        # [5] d(Q_rev)/dt (可逆析锂)
        # 死锂转化率
        gamma = p['GAMMA_0'] * (p['L_SEI_0'] / L_SEI)
        decay_rate = gamma * Q_rev
        
        # i_plating 为负是生成，为正是消耗
        # 公式: 变化率 = -(生成/消耗电流) - 死锂转化
        d_qrev_dt = -i_plating - decay_rate

        # [6] d(Q_dead)/dt (死锂堆积)
        d_qdead_dt = decay_rate

        return np.array([dcs_dt, dce_dt, dT_dt, d_lsei_dt, d_delta_ce_dt, d_qrev_dt, d_qdead_dt])

    def calculate_state(self, t: float, y: np.ndarray, ext: ExternalState) -> ExternalState:
        new_ext = ExternalState(**ext.__dict__)
        c_s_bar, c_e_bar, T, L_SEI, delta_ce_dyn, Q_rev, Q_dead = y
        p = self.p

        # --- SOH 计算 (包含 SEI 损失和死锂损失) ---
        q_nominal = p['EPS_S_NEG'] * c.F * p['L_NEG'] * p['AREA'] * p['C_MAX_NEG']
        
        # SEI 造成的损失
        vol_sei = self.Asurf_n * L_SEI
        q_lost_sei = (vol_sei / p['V_SEI']) * c.F
        
        # 死锂造成的损失 (直接就是库仑量)
        q_lost_dead = Q_dead
        
        new_ext.SOH = np.clip(1.0 - (q_lost_sei + q_lost_dead) / q_nominal, 0.01, 1.0)
        new_ext.AGEING = 1.0 - L_SEI / p['L_NEG']

        # SOC
        new_ext.SOC = c_s_bar / (p['C_MAX_NEG'] * new_ext.SOH)
        
        # 物理参数更新
        new_ext.D_e = p['D_E_REF'] * np.exp(-1.0/T + 1.0/298.15)
        
        # R_tot 更新
        r_ohm = self.L_total / (4.0 * p['KAPPA_SEP'] * p['AREA'])
        r_sei = L_SEI / (self.Asurf_n * p['KAPPA_SEI'])
        new_ext.R_tot = r_ohm + r_sei + 0.002

        # 电压计算 (简化的单点计算，用于输出)
        theta_n = np.clip(c_s_bar / p['C_MAX_NEG'], 0.001, 0.999)
        u_n = self._ocv_neg(theta_n)
        
        theta_p = np.clip(0.4 + 0.585 * (0.99 - theta_n), 0.001, 0.999) # 简化的正极关联
        u_p = self._ocv_pos(theta_p)
        
        # 为了获取 eta，我们需要重新计算 i_0 (这里做估算)
        i_0n = p['K0'] * new_ext.AGEING * ((c_e_bar * c_s_bar * (p['C_MAX_NEG']-c_s_bar))**0.5)
        # 避免除零
        if i_0n < 1e-6: i_0n = 1e-6
        arg_n = (ext.I / self.Asurf_n) / (2*i_0n)
        eta_n = (2*c.R*T/c.F) * np.arcsinh(arg_n)
        
        # 估算 phi_anode 存入 ext 状态方便观察
        new_ext.Phi_Anode = u_n + eta_n + ext.I * r_sei 

        # 终端电压
        new_ext.V = u_p - u_n + 0.1 - ext.I * new_ext.R_tot # 0.1是估算的eta_p差值
        
        # 更新电流 I = P/V (如果在放电)
        if abs(new_ext.V) > 0.1 and not (ext.I < 0): # 非充电状态
             new_ext.I = new_ext.P / new_ext.V

        return new_ext

    def _ocv_neg(self, theta):
        # 保持原有公式
        return (0.194 + 1.5 * np.exp(-120.0 * theta)
            + 0.0351 * np.tanh((theta - 0.286) / 0.083)
            - 0.0045 * np.tanh((theta - 0.849) / 0.119)
            - 0.035 * np.tanh((theta - 0.9233) / 0.05)
            - 0.0147 * np.tanh((theta - 0.5) / 0.034)
            - 0.102 * np.tanh((theta - 0.194) / 0.142)
            - 0.022 * np.tanh((theta - 0.9) / 0.0164)
            - 0.011 * np.tanh((theta - 0.123) / 0.0096))

    def _ocv_pos(self, theta):
        # 保持原有公式
        return (4.04596 + np.exp(-42.30027 * theta + 16.56714)
            - 0.04880 * np.arctan(50.83402 * theta - 24.09702)
            - 0.03544 * np.arctan(13.274 * theta - 12.878)
            - 0.04444 * theta - 0.2058 * np.exp(2.6214 * theta - 2.1877))
            
    def solve_current_at_voltage(self, y: np.ndarray, ext: ExternalState, v_limit: float) -> float:
        # 为了兼容 7 维向量，这里需要简单更新，但不影响核心逻辑
        # 暂时返回一个估算值以保持运行
        return (v_limit - ext.V) / ext.R_tot if ext.R_tot > 0 else 0