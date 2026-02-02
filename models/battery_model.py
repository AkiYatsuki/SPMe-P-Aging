import numpy as np
import config as c
from dataclasses import dataclass

@dataclass
class ExternalState:
    """对应 Rust 中的 ExternalCalculate"""
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

class BatterySystem:
    def __init__(self):
        # 预计算一些几何参数
        self.Asurf_n = c.AREA * c.L_NEG * 3.0 * c.EPS_S_NEG / c.R_S_NEG
        self.Asurf_p = c.AREA * c.L_POS * 3.0 * c.EPS_S_POS / c.R_S_POS
        self.L_total = c.L_POS + 2.0 * c.L_SEP + c.L_NEG

    def derivatives(self, t: float, y: np.ndarray, ext: ExternalState) -> np.ndarray:
        """
        y[0]: c_s_bar (负极平均浓度)
        y[1]: c_e_bar (电解液平均浓度)
        y[2]: T (温度)
        y[3]: L_SEI (SEI膜厚度)
        y[4]: delta_ce_dyn (动态浓差修正)
        """
        c_s_bar, c_e_bar, T, L_SEI, delta_ce_dyn = y
        
        # 1. c_s_bar rate
        dcs_dt = -ext.I / (c.EPS_S_NEG * ext.SOH) / c.F / c.L_NEG / c.AREA
        
        # 2. c_e_bar rate
        dce_dt = (1.0 - c.T0_POS) / (c.EPS_E * c.F) * (ext.I / c.L_POS - ext.I / c.L_NEG)
        
        # 3. L_SEI growth rate
        d_lsei_dt = c_s_bar * c.D_SOLV * np.exp(-3000.0 * (1.0/T - 1.0/298.15)) * c.V_SEI / 2.0 / L_SEI
        
        # 4. Temperature rate (Heat Balance)
        # Q_in = I^2*R + Q_device; Q_out = h*A*(T-Tamb)
        heat_gen = (ext.I**2 * ext.R_tot * c.N_PARALLEL) + ext.Q
        heat_diss = c.H_CONV * c.A_SURF * (T - c.T_AMB)
        dT_dt = (heat_gen - heat_diss) / (c.MASS_PHONE * c.CP_PHONE)
        
        # 5. Delta Ce relaxation
        delta_ce_target = (1.0 - c.T0_POS) / (2.0 * c.F * ext.D_e) * (ext.I * c.L_SEP)
        tau_diff = (self.L_total**2) / (20.0 * ext.D_e)
        d_delta_ce_dt = (delta_ce_target - delta_ce_dyn) / tau_diff
        
        return np.array([dcs_dt, dce_dt, dT_dt, d_lsei_dt, d_delta_ce_dt])

    def calculate_state(self, t: float, y: np.ndarray, ext: ExternalState) -> ExternalState:
        """计算 V, SOC, SOH, R_tot 等并更新 ext"""
        new_ext = ExternalState(**ext.__dict__) # Clone
        
        c_s_bar, c_e_bar, T, L_SEI, delta_ce_dyn = y
        
        # SOH Calc
        q_nominal = c.EPS_S_NEG * c.F * c.L_NEG * c.AREA * c.C_MAX_NEG
        vol_sei = self.Asurf_n * L_SEI
        q_lost = (vol_sei / c.V_SEI) * c.F
        new_ext.SOH = np.clip(1.0 - q_lost / q_nominal, 0.01, 1.0)
        new_ext.AGEING = 1.0 - L_SEI / c.L_NEG # Simplified ageing factor from Rust

        # SOC
        new_ext.SOC = c_s_bar / (ext.c_smax * new_ext.SOH)
        
        # Diffusivity & Conductivity
        new_ext.D_e = c.D_E_REF * np.exp(-1.0/T + 1.0/298.15)
        
        # R_tot
        r_ohm = self.L_total / (4.0 * c.KAPPA_SEP * c.AREA)
        r_sei = L_SEI / (self.Asurf_n * c.KAPPA_SEI)
        new_ext.R_tot = r_ohm + r_sei + 0.002

        # --- Voltage Calculation ---
        # Concentrations
        delta_ce = (1.0 - c.T0_POS) / (2.0 * c.F * new_ext.D_e) * (ext.I * c.L_SEP) # Instantaneous approx for voltage
        # Rust logic uses state y[4] for dynamics but recalculates simplified delta_ce for OCV sometimes.
        # Let's align with Rust's `calculate` method which recalculates `delta_ce`.
        
        # Exchange Currents
        theta_n = c_s_bar / ext.c_smax
        c_e_n = c_e_bar - y[4] # Use dynamic delta
        c_e_p = c_e_bar + y[4]
        
        # Avoid math domain error
        term_n = max(1e-9, (c_e_n * c_s_bar * (c.C_MAX_NEG - c_s_bar)))
        i_0n = c.K0 * new_ext.AGEING * (term_n ** c.ALPHA)
        
        theta_p_proxy = 0.4 + 0.585 * (0.99 - theta_n) # Rust logic match
        term_p = max(1e-9, (c_e_p * c.C_MAX_POS**2 * theta_p_proxy * (1.0 - theta_p_proxy)))
        i_0p = c.K0 * new_ext.AGEING * (term_p ** c.ALPHA)

        # OCV Potentials
        u_n = self._ocv_neg(theta_n)
        u_p = self._ocv_pos(theta_p_proxy)
        
        # Overpotentials (Butler-Volmer Inversion -> asinh)
        eta_n = (2 * c.R * T / c.F) * np.arcsinh(-ext.I / (2 * self.Asurf_n * i_0n))
        eta_p = (2 * c.R * T / c.F) * np.arcsinh(ext.I / (2 * self.Asurf_p * i_0p))
        
        v_conc = (2 * c.R * T / c.F) * (1 - c.T0_POS) * np.log((c_e_bar + delta_ce) / (c_e_bar - delta_ce))
        
        # Terminal Voltage
        new_ext.V = u_p - u_n + eta_p - eta_n + v_conc - new_ext.I * new_ext.R_tot
        
        # Update I based on Power (if not charging mode, handled in main)
        # Note: Rust sets I = P/V here.
        if abs(new_ext.V) > 0.1:
            new_ext.I = new_ext.P / new_ext.V
            
        return new_ext

    def solve_current_at_voltage(self, y: np.ndarray, ext: ExternalState, v_limit: float) -> float:
        """Newton-Raphson to find I for CV charging"""
        # (This implements the logic from Rust's solve_current_at_voltage)
        # Simplified context setup for brevity, relying on key params
        i_guess = -1.0 # Start with charging guess
        
        # Extract needed constants for the loop
        c_s_n = y[0]
        T = y[2]
        theta_n = np.clip(c_s_n / ext.c_smax, 0.001, 0.999)
        theta_p = np.clip(0.4 + 0.585 * (0.99 - theta_n), 0.001, 0.999)
        
        u_n = self._ocv_neg(theta_n)
        u_p = self._ocv_pos(theta_p)
        ocv = u_p - u_n
        
        term_rtf = 2.0 * c.R * T / c.F
        
        # Approx i0 (assuming average concentrations for stability in solver)
        i_0n = c.K0 * ext.AGEING * ((1000.0 * c_s_n * (c.C_MAX_NEG - c_s_n))**c.ALPHA)
        i_0p = c.K0 * ext.AGEING * ((1000.0 * c.C_MAX_POS**2 * theta_p * (1-theta_p))**c.ALPHA)
        
        for _ in range(10):
            arg_n = i_guess / (2.0 * self.Asurf_n * i_0n)
            arg_p = i_guess / (2.0 * self.Asurf_p * i_0p)
            
            # Derived V
            eta_n = term_rtf * np.arcsinh(arg_n)
            eta_p = term_rtf * np.arcsinh(arg_p)
            v_calc = ocv - eta_n - eta_p - i_guess * ext.R_tot
            
            f_val = v_calc - v_limit
            if abs(f_val) < 1e-4: return i_guess
            
            # Derivative
            d_eta_n = term_rtf * (1.0 / np.sqrt(1 + arg_n**2)) * (1.0 / (2 * self.Asurf_n * i_0n))
            d_eta_p = term_rtf * (1.0 / np.sqrt(1 + arg_p**2)) * (1.0 / (2 * self.Asurf_p * i_0p))
            df_val = -d_eta_n - d_eta_p - ext.R_tot
            
            i_guess = i_guess - f_val / df_val
            
        return i_guess

    def _ocv_neg(self, theta):
        return (0.194 + 1.5 * np.exp(-120.0 * theta)
            + 0.0351 * np.tanh((theta - 0.286) / 0.083)
            - 0.0045 * np.tanh((theta - 0.849) / 0.119)
            - 0.035 * np.tanh((theta - 0.9233) / 0.05)
            - 0.0147 * np.tanh((theta - 0.5) / 0.034)
            - 0.102 * np.tanh((theta - 0.194) / 0.142)
            - 0.022 * np.tanh((theta - 0.9) / 0.0164)
            - 0.011 * np.tanh((theta - 0.123) / 0.0096))

    def _ocv_pos(self, theta):
        return (4.04596 + np.exp(-42.30027 * theta + 16.56714)
            - 0.04880 * np.arctan(50.83402 * theta - 24.09702)
            - 0.03544 * np.arctan(13.274 * theta - 12.878)
            - 0.04444 * theta - 0.2058 * np.exp(2.6214 * theta - 2.1877))