import numpy as np

# --- 物理常数 ---
R = 8.314
F = 96485.3
T_REF = 298.15
T_AMB = 298.15

# --- 电池几何与材料参数 ---
N_PARALLEL = 6.0          # 并联电池数
AREA = 0.028359           # 电极面积 (m^2)
L_NEG = 1e-4              # 负极厚度
L_SEP = 2.5e-5            # 隔膜厚度
L_POS = 1e-4              # 正极厚度
R_S_NEG = 1e-5            # 负极颗粒半径
R_S_POS = 1e-5            # 正极颗粒半径

EPS_S_NEG = 0.6           # 负极活性物质体积分数
EPS_S_POS = 0.5           # 正极活性物质体积分数
EPS_E = 0.3               # 孔隙率

C_MAX_NEG = 24983.26      # 负极最大浓度
C_MAX_POS = 51217.92      # 正极最大浓度
T0_POS = 0.4              # 阳离子迁移数
D_E_REF = 2.0e-10         # 电解液扩散系数参考值
KAPPA_SEP = 0.164         # 隔膜电导率

# --- SEI 相关 ---
D_SOLV = 1.25e-21
V_SEI = 9.585e-5
C_SOLV_BULK = 2636.0
KAPPA_SEI = 5.0e-6

# --- 动力学 ---
K0 = 1e-5
ALPHA = 0.5

# --- Plating Parameters ---
K_PLATING = 1e-4       # 析锂交换电流密度系数
ALPHA_PLATING = 0.5    # 析锂传递系数
GAMMA_0 = 1.0e-4       # 死锂转化率 (1/s)
L_SEI_0 = 5.0e-9       # 初始SEI参考厚度

# --- 热学参数 ---
MASS_BATT = 0.045
CP_BATT = 1000.0
MASS_PHONE = 0.150
CP_PHONE = 900.0
H_CONV = 5.0
A_SURF = 0.0569           # 冷却面积

# --- 充电控制参数 ---
CHARGING_CURRENT_TARGET = -2.5  # A (负数充电)
CHARGING_VOLTAGE_LIMIT = 4.4    # V
START_CHARGE_SOC = 0.10         # 10%
STOP_CHARGE_SOC = 0.93          # 93%
STOP_CHARGE_I = 0.005           # A
RATIO = 0.8

# --- 5G 功耗模型参数 ---
BETA_5G_IDLE = 35.0
BETA_5G_INA = 150.0
BETA_5G_BASE_CONN = 300.0
BETA_5G_BW = 2.0        # mW/MHz
BETA_5G_MIMO = 100.0    # mW/Ant
BETA_5G_MMW = 600.0     # 毫米波额外功耗

# --- [新增] 5G 产热系数 ---
K_TH_5G_LOW = 0.98      # Idle/Inactive
K_TH_5G_HIGH = 0.70     # Connected