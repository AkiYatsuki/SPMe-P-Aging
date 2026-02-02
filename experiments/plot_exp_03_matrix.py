import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# 路径管理
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

def plot_results():
    # 1. 读取数据
    csv_path = os.path.join(project_root, "results", "exp_03_matrix_high_res.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Data file not found at {csv_path}. Please run experiment first.")
        return

    df = pd.read_csv(csv_path)
    
    # 2. 准备绘图目录
    plots_dir = os.path.join(project_root, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # 3. 设置绘图风格
    # 使用 seaborn 的高级配色
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 11})

    fig = plt.figure(figsize=(16, 7), dpi=200) # 高清画布
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2]) # 右图稍微宽一点放图例

    # --- 左图: 热力图 (Heatmap) ---
    ax1 = fig.add_subplot(gs[0, 0])
    
    # 整理数据为矩阵形式
    pivot_rate = df.pivot(index="SOH_Start", columns="Ambient_Temp", values="Aging_Rate")
    pivot_rate = pivot_rate.sort_index(ascending=False) # 0.96 在上，0.80 在下

    # 画图
    sns.heatmap(pivot_rate, annot=True, fmt=".1e", cmap="YlOrRd", 
                linewidths=.5, ax=ax1, cbar_kws={'label': 'Instantaneous Aging Rate (1/hr)'})
    
    ax1.set_title('(a) Aging Rate Sensitivity Matrix', fontweight='bold', pad=15)
    ax1.set_xlabel('Ambient Temperature (°C)')
    ax1.set_ylabel('Current SOH')

    # --- 右图: 趋势线 (Line Plot) ---
    ax2 = fig.add_subplot(gs[0, 1])
    
    # 使用 Seaborn 的 lineplot 可以自动处理图例和配色
    sns.lineplot(data=df, x="SOH_Start", y="Aging_Rate", 
                 hue="Ambient_Temp", palette="flare", marker="o", 
                 linewidth=2.5, ax=ax2, legend="full")

    ax2.set_title('(b) Decelerating Aging Characteristic', fontweight='bold', pad=15)
    ax2.set_xlabel('State of Health (SOH)')
    ax2.set_ylabel('Aging Rate (1/hr)')
    ax2.invert_xaxis() # 从 0.96 到 0.80
    
    # 优化图例标题
    ax2.legend(title="Ambient Temp (°C)", loc='upper right')
    
    # 添加标注 (Optional)
    # 如果数据点足够多，可以不加箭头，保持画面干净
    
    # 4. 保存图片
    save_path = os.path.join(plots_dir, "exp_03_analysis_high_res.png")
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Plot saved to: {save_path}")
    # plt.show() # 如果在服务器上跑可以注释掉这一行

if __name__ == "__main__":
    plot_results()