import json
import pandas as pd
import numpy as np
from simulation.init_utils import get_initial_state_by_soh
from simulation.simulator import run_single_static_test

class AgingScanner:
    def __init__(self):
        # 定义扫描配置
        self.soh_levels = [1.0, 0.95, 0.90, 0.85, 0.80]

        # --- Automatically load App list from Cost.json ---
        try: 
            with open("Cost.json", "r") as f: 
                data = json.load(f)
            # 获取profile所有键名
            self.apps = list(data["profiles"].keys())
            print(f"Loaded profiles from json: {self.apps}")

        except FileNotFoundError: 
            print("Error: Cost.json not found, jusing default fallback. ")
            self.apps = ["idle"] #Fallback

        self.results = []

    def run(self):
        print(f"Starting Parameter Sweep...")
        print(f"Scanning {len(self.soh_levels)} SOH levels x {len(self.apps)} Apps")
        print("-" * 60)
        print(f"{'SOH':<8} | {'App':<20} | {'Avg Temp':<10} | {'Aging Rate/hr'}")
        print("-" * 60)

        for soh in self.soh_levels:
            for app in self.apps:
                self._run_single_case(soh, app)

        self._save_results()

    def _run_single_case(self, soh, app):
        # 1. 准备初始状态 (SOC 设为 100% 开始)
        y0, ext_init = get_initial_state_by_soh(target_soh=soh, soc_start=1.0)
        
        # 2. 调用模拟器 (模拟 1 小时)
        loss_rate, avg_temp = run_single_static_test(
            y0, ext_init, 
            app_profile_name=app, 
            duration=3600
        )
        
        if loss_rate is None:
            return # Skip invalid cases

        # 3. 记录
        self.results.append({
            "Initial_SOH": soh,
            "App_Profile": app,
            "Avg_Temp_C": avg_temp,
            "SOH_Loss_Rate_Hr": loss_rate,
            "Est_Life_Hours": 0.2 / loss_rate if loss_rate > 1e-10 else np.inf
        })
        
        print(f"{soh*100:.0f}%     | {app:<20} | {avg_temp:.2f}°C    | {loss_rate:.3e}")

    def _save_results(self):
        df = pd.DataFrame(self.results)
        filename = "aging_scan_results.csv"
        df.to_csv(filename, index=False)
        print("-" * 60)
        print(f"Sweep complete. Data saved to {filename}")
        
        # 打印简报
        print("\nSummary (Aging Rate Matrix):")
        try:
            pivot = df.pivot(index="Initial_SOH", columns="App_Profile", values="SOH_Loss_Rate_Hr")
            print(pivot)
        except Exception:
            pass