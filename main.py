import sys
from simulation.scanner import Scanner

def main(): 
    scanner = Scanner()
    print("=== Battery Aging Simulation System ===")
    print("1. App & SOH Matrix Scan (External Conditions)")
    print("2. Physics Parameter Sensitivity Scan (Intrnal State)")
    print("3. Run Both")

    choice = input("select mode (1/2/3): ").strip()

    # === 外部工况扫描 ===
    if choice == '1' or choice == '3': 
        print("\n>>> Running App Scan...")
        scanner.run_external_scan(
            soh_levels = [1.0, 0.90, 0.80], 
            duration = 3600
        )

    # === 内部参数扫描 ===
    if choice == '2' or choice == '3': 
        print("\n>>>Running Sensitivity Scan...")
        # 定义想要扫描的参数和倍率
        sensitivity_plan = {
            "D_E_REF": [0.5, 1.0, 2.0], #电解液扩散系数
            "K0": [0.5, 1.0, 2.0] # 反应速率常数
        }

        scanner.run_internal_scan(
            param_dict = sensitivity_plan, 
            fixed_soh = 0.90, 
            fixed_app = "gaming_heavy", 
            duration = 7200
        )

if __name__ == "__main__": 
    main(); 