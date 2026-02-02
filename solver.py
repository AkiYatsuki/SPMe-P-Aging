import numpy as np

class RK4Solver:
    def __init__(self, t0, y0):
        self.t = t0
        self.state = np.array(y0, dtype=float)

    def step(self, system, dt, input_ext):
        """
        system: 必须包含 methods:
                derivatives(t, y, input) -> np.array
                calculate_state(t, y, input) -> updated_input
        """
        y = self.state
        t = self.t

        k1 = system.derivatives(t, y, input_ext)
        k2 = system.derivatives(t + 0.5*dt, y + 0.5*dt*k1, input_ext)
        k3 = system.derivatives(t + 0.5*dt, y + 0.5*dt*k2, input_ext)
        k4 = system.derivatives(t + dt, y + dt*k3, input_ext)

        delta = (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
        
        self.state = y + delta
        self.t += dt
        
        # 积分后更新物理系统的代数状态
        # 注意：Rust中是 update in-place，这里返回新的 external state
        return system.calculate_state(self.t, self.state, input_ext)