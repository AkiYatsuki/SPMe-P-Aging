import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# ==========================================
# 1. 数据准备 (剔除 SOH 1.00)
# ==========================================
data = {
    "SOH_Start": [0.95, 0.95, 0.95, 0.90, 0.90, 0.90, 0.85, 0.85, 0.85, 0.80, 0.80, 0.80],
    "Ambient_Temp": [25, 35, 45, 25, 35, 45, 25, 35, 45, 25, 35, 45],
    "Aging_Rate": [
        3.49e-07, 4.76e-07, 6.36e-07,
        1.60e-07, 2.19e-07, 2.92e-07,
        9.77e-08, 1.33e-07, 1.78e-07,
        6.62e-08, 9.02e-08, 1.21e-07
    ],
    "Temp_Rise": [
        8.25, 8.25, 8.25,
        8.29, 8.29, 8.29,
        8.34, 8.34, 8.34,
        8.40, 8.40, 8.40
    ]
}

df = pd.DataFrame(data)

# ==========================================
# 2. 绘图设置
# ==========================================
# 设置专业学术风格
plt.rcParams.update({'font.size': 12, 'font.family': 'sans-serif'})
fig = plt.figure(figsize=(16, 6), dpi=150)
gs = fig.add_gridspec(1, 2)

# --- 左图: 衰老速率热力图 (The "Death Map") ---
ax1 = fig.add_subplot(gs[0, 0])

# 数据透视: 行=SOH, 列=Temp
pivot_rate = df.pivot(index="SOH_Start", columns="Ambient_Temp", values="Aging_Rate")
# SOH 倒序排列，符合直觉 (上面是新，下面是老)
pivot_rate = pivot_rate.sort_index(ascending=False)

# 绘制热力图
sns.heatmap(pivot_rate, annot=True, fmt=".2e", cmap="YlOrRd", 
            linewidths=.5, ax=ax1, cbar_kws={'label': 'Instantaneous Aging Rate (1/hr)'})

ax1.set_title('(a) Aging Rate Sensitivity Matrix', fontweight='bold')
ax1.set_xlabel('Ambient Temperature (°C)')
ax1.set_ylabel('Current SOH')

# --- 右图: 衰老速率 vs SOH 趋势线 (展示 SEI 保护机制) ---
ax2 = fig.add_subplot(gs[0, 1])

# 按温度分组绘制
temps = sorted(df['Ambient_Temp'].unique())
colors = ['green', 'orange', 'red']
markers = ['o', 's', '^']

for i, temp in enumerate(temps):
    subset = df[df['Ambient_Temp'] == temp]
    # SOH 作为 X 轴
    ax2.plot(subset['SOH_Start'], subset['Aging_Rate'], 
             marker=markers[i], color=colors[i], linewidth=2, markersize=8,
             label=f'{temp}°C Ambient')

# 装饰
ax2.set_title('(b) Decelerating Aging Characteristic', fontweight='bold')
ax2.set_xlabel('State of Health (SOH)')
ax2.set_ylabel('Aging Rate (1/hr)')
ax2.invert_xaxis() # X轴反向：从 0.95 到 0.80
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend(title="5G Scenario")

# 添加物理标注
ax2.annotate("SEI Thickening\n(Protective Effect)", 
             xy=(0.85, 1.5e-7), xytext=(0.90, 4e-7),
             arrowprops=dict(facecolor='black', shrink=0.05))

# ==========================================
# 3. 保存
# ==========================================
plt.tight_layout()
plt.savefig('SOH_Temp_Matrix_Analysis.png')
print("Plot saved.")
plt.show()