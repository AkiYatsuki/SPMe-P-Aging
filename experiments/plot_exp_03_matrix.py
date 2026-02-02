import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

def plot_results():
    # 1. 读取数据
    csv_path = os.path.join(project_root, "results", "exp_03_comparison.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Data not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    plots_dir = os.path.join(project_root, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # 2. 数据透视：计算加速因子 (Factor = 5G / Idle)
    # 我们需要把长表变成宽表，以便让 5G 的速率除以 Idle 的速率
    df_pivot = df.pivot_table(index=["SOH_Start", "Ambient_Temp"], 
                              columns="Scenario", 
                              values="Aging_Rate")
    
    # 计算倍率
    df_pivot["Acceleration_Factor"] = df_pivot["5g_gaming_heavy"] / df_pivot["idle_baseline"]
    
    # 重置索引，方便 seaborn 绘图
    df_plot = df_pivot.reset_index()
    
    # 3. 开始绘图
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 11})

    fig = plt.figure(figsize=(18, 7), dpi=150)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2])

    # --- 左图: 热力图 (加速因子) ---
    ax1 = fig.add_subplot(gs[0, 0])
    
    # 整理热力图数据矩阵: 行=SOH, 列=Temp, 值=Factor
    heatmap_data = df_plot.pivot(index="SOH_Start", columns="Ambient_Temp", values="Acceleration_Factor")
    heatmap_data = heatmap_data.sort_index(ascending=False) # SOH 从高到低

    sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="Reds", 
                linewidths=.5, ax=ax1, cbar_kws={'label': 'Damage Multiplier (5G / Idle)'})
    
    ax1.set_title('(a) 5G Thermal Damage Multiplier', fontweight='bold', pad=15)
    ax1.set_xlabel('Ambient Temperature (°C)')
    ax1.set_ylabel('Current SOH')

    # --- 右图: 绝对速率对比 (折线图) ---
    ax2 = fig.add_subplot(gs[0, 1])
    
    # 为了图表清晰，我们只筛选部分数据画线 (全部画太乱)
    # 比如只看 25度 (常温) 和 45度 (高温) 的对比
    target_df = df[df["Ambient_Temp"].isin([25, 45])]
    
    sns.lineplot(data=target_df, x="SOH_Start", y="Aging_Rate", 
                 hue="Ambient_Temp", style="Scenario",
                 palette={25: "blue", 45: "red"},
                 markers=True, dashes={"idle_baseline": (2, 2), "5g_gaming_heavy": ""},
                 linewidth=2.5, ax=ax2)

    ax2.set_title('(b) Aging Rate: 5G vs Idle', fontweight='bold', pad=15)
    ax2.set_xlabel('State of Health (SOH)')
    ax2.set_ylabel('Aging Rate (1/hr) [Log Scale]')
    ax2.set_yscale("log") # 使用对数坐标，因为 5G 和 Idle 差异巨大
    ax2.invert_xaxis()
    ax2.legend(bbox_to_anchor=(1, 1), loc='upper left', title="Conditions")

    # 4. 保存
    save_path = os.path.join(plots_dir, "exp_03_comparison_analysis.png")
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Plot saved to: {save_path}")

if __name__ == "__main__":
    plot_results()