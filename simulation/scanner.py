import json
import pandas as pd
import numpy as np
import config as c
from simulation.init_utils import get_initial_state_by_soh
from simulation.simulator import run_single_static_test

class Scanner:
    def __init__(self):
        self.results = []
        # 自动加载 App 列表
        try:
            with open("Cost.json", "r") as f:
                self.available_apps = list(json.load(f)["profiles"].keys())
        except FileNotFoundError:
            self.available_apps = ["idle"]
            print("Warning: Cost.json not found, defaulting to ['idle']")

    def run_external_scan(self, soh_levels=None, apps=None, duration=3600):
        """
        模式1: 外部工况扫描 (SOH x App)
        """
        # 设置默认值
        if soh_levels is None: soh_levels = [1.0, 0.95, 0.90, 0.85, 0.80]
        if apps is None: apps = self.available_apps

        print(f"\n>>> Starting External Condition Scan (SOH x App)...")
        print(f"SOH: {soh_levels}, Apps: {apps}")

        for soh in soh_levels:
            for app in apps:
                self._run_single_case(
                    soh=soh, 
                    app_name=app, 
                    duration=duration, 
                    scan_type="External",
                    param_overrides=None
                )
        
        self._save_results("scan_external_results.csv")

    def run_internal_scan(self, param_dict, fixed_soh=0.90, fixed_app="gaming_heavy", duration=7200):
        """
        模式2: 内部参数敏感度扫描 (Parameter Sensitivity)
        param_dict: { 'PARAM_NAME': [multiplier1, multiplier2, ...] }
        """
        print(f"\n>>> Starting Internal Parameter Scan (Sensitivity)...")
        
        # 获取基准值 (从 config 获取)
        base_values = {}
        for k in param_dict.keys():
            if hasattr(c, k):
                base_values[k] = getattr(c, k)
            else:
                print(f"Warning: Parameter {k} not found in config.py")
                base_values[k] = 0.0

        for param_name, multipliers in param_dict.items():
            base_val = base_values[param_name]
            
            for mult in multipliers:
                val = base_val * mult
                overrides = {param_name: val}
                
                # 在结果中标记当前变化的参数
                tag = f"{param_name} x{mult}"
                
                self._run_single_case(
                    soh=fixed_soh,
                    app_name=fixed_app,
                    duration=duration,
                    scan_type=f"Internal ({tag})",
                    param_overrides=overrides,
                    extra_data={"Param": param_name, "Multiplier": mult, "Value": val}
                )

        self._save_results("scan_internal_results.csv")

    def _run_single_case(self, soh, app_name, duration, scan_type, param_overrides=None, extra_data=None):
        """内部通用执行逻辑"""
        # 1. 初始化
        y0, ext_init = get_initial_state_by_soh(target_soh=soh, soc_start=1.0)
        
        # 2. 运行模拟
        loss_rate, avg_temp = run_single_static_test(
            y0, ext_init, 
            app_profile_name=app_name, 
            duration=duration,
            internal_params=param_overrides
        )
        
        if loss_rate is None: return

        # 3. 组装结果
        record = {
            "Type": scan_type,
            "SOH_Start": soh,
            "App": app_name,
            "Avg_Temp_C": avg_temp,
            "Aging_Rate_Hr": loss_rate,
            "Est_Life_Hours": 0.2 / loss_rate if loss_rate > 1e-12 else np.inf
        }
        
        # 合并额外的参数信息（如果是内部扫描）
        if extra_data:
            record.update(extra_data)
            
        self.results.append(record)
        print(f"[{scan_type[:15]:<15}] SOH:{soh:.2f} | App:{app_name[:10]:<10} | T:{avg_temp:.1f}C | Rate:{loss_rate:.2e}")

    def _save_results(self, filename):
        if not self.results:
            print("No results to save.")
            return
            
        df = pd.DataFrame(self.results)
        # 将本次结果保存，随后清空缓存以便下一次扫描
        df.to_csv(filename, index=False)
        self.results = [] # Reset
        print(f"Saved results to {filename}")