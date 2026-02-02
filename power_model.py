import json
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import config

class PowerConstants:
    # 功耗系数 (mW)
    BETA_CPU_UH = 4.34
    BETA_CPU_UL = 3.42
    BETA_CPU_ON = 121.46
    BETA_BR = 2.40
    BETA_GPS_ON = 429.55
    BETA_GPS_SLEEP = 173.55
    BETA_WIFI_L = 20.0
    WIFI_HIGH_BASE = 710.0
    WIFI_CR_BASE = 48.0
    WIFI_CR_FACTOR = 7.68
    BETA_3G_IDLE = 10.0
    BETA_3G_FACH = 401.0
    BETA_3G_DCH = 570.0
    BETA_AUDIO_ON = 384.62
    
    # 产热转化系数 (K_TH)
    K_TH = {
        'cpu': 0.995, 'lcd': 0.85, 'gps': 1.0,
        'wifi_l': 0.98, 'wifi_h': 0.75,
        'cell_idle': 0.98, 'cell_active': 0.70, 'audio': 0.99
    }

class DeviceState:
    def __init__(self, data: dict):
        self.cpu = data.get('cpu', {})
        self.lcd = data.get('lcd', {})
        self.gps = data.get('gps', {})
        self.wifi = data.get('wifi', {})
        self.cellular = data.get('cellular', {})
        self.audio = data.get('audio', {})

    def calculate_power_mw(self) -> float:
        p = 0.0
        # CPU
        if self.cpu.get('is_on'):
            p += PowerConstants.BETA_CPU_ON
            beta = PowerConstants.BETA_CPU_UH if self.cpu.get('freq_high') else PowerConstants.BETA_CPU_UL
            p += beta * self.cpu.get('util', 0)
        
        # LCD
        p += PowerConstants.BETA_BR * self.lcd.get('brightness', 0)
        
        # GPS
        state = self.gps.get('state')
        if state == 'On': p += PowerConstants.BETA_GPS_ON
        elif state == 'Sleep': p += PowerConstants.BETA_GPS_SLEEP
        
        # WiFi
        w_state = self.wifi.get('state')
        if w_state == 'Low': p += PowerConstants.BETA_WIFI_L
        elif w_state == 'High':
            beta_cr = PowerConstants.WIFI_CR_BASE - PowerConstants.WIFI_CR_FACTOR * self.wifi.get('r_channel', 0)
            p_high = PowerConstants.WIFI_HIGH_BASE + beta_cr * self.wifi.get('r_uplink', 0)
            p += max(0, p_high)

        # Cellular
        c_state = self.cellular.get('state')
        if c_state == 'Idle': p += PowerConstants.BETA_3G_IDLE
        elif c_state == 'Fach': p += PowerConstants.BETA_3G_FACH
        elif c_state == 'Dch': p += PowerConstants.BETA_3G_DCH

        # Audio
        if self.audio.get('is_playing'):
            p += PowerConstants.BETA_AUDIO_ON
            
        return p

    def calculate_heat_mw(self) -> float:
        q = 0.0
        # 逻辑同上，但乘以对应的 K_TH 系数
        # CPU
        if self.cpu.get('is_on'):
            q += PowerConstants.BETA_CPU_ON * PowerConstants.K_TH['cpu']
            beta = PowerConstants.BETA_CPU_UH if self.cpu.get('freq_high') else PowerConstants.BETA_CPU_UL
            q += (beta * self.cpu.get('util', 0)) * PowerConstants.K_TH['cpu']

        # LCD
        q += (PowerConstants.BETA_BR * self.lcd.get('brightness', 0)) * PowerConstants.K_TH['lcd']

        # GPS
        state = self.gps.get('state')
        gps_p = PowerConstants.BETA_GPS_ON if state == 'On' else (PowerConstants.BETA_GPS_SLEEP if state == 'Sleep' else 0)
        q += gps_p * PowerConstants.K_TH['gps']

        # WiFi
        w_state = self.wifi.get('state')
        if w_state == 'Low':
            q += PowerConstants.BETA_WIFI_L * PowerConstants.K_TH['wifi_l']
        elif w_state == 'High':
            beta_cr = PowerConstants.WIFI_CR_BASE - PowerConstants.WIFI_CR_FACTOR * self.wifi.get('r_channel', 0)
            p_high = max(0, PowerConstants.WIFI_HIGH_BASE + beta_cr * self.wifi.get('r_uplink', 0))
            q += p_high * PowerConstants.K_TH['wifi_h']

        # Cellular
        c_state = self.cellular.get('state')
        if c_state == 'Idle': q += PowerConstants.BETA_3G_IDLE * PowerConstants.K_TH['cell_idle']
        elif c_state == 'Fach': q += PowerConstants.BETA_3G_FACH * PowerConstants.K_TH['cell_active']
        elif c_state == 'Dch': q += PowerConstants.BETA_3G_DCH * PowerConstants.K_TH['cell_active']

        # Audio
        if self.audio.get('is_playing'):
            q += PowerConstants.BETA_AUDIO_ON * PowerConstants.K_TH['audio']
            
        return q

class SimulationPlan:
    def __init__(self, filepath: str):
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.profiles = {k: DeviceState(v) for k, v in data['profiles'].items()}
        # 确保按时间排序
        self.timeline = sorted(data['timeline'], key=lambda x: x['time'])
        
    def get_state_at(self, t: float) -> Tuple[DeviceState, str]:
        active_profile = "Unknown"
        # 简单遍历查找，数据量大时可优化为二分查找
        for event in self.timeline:
            if t >= event['time']:
                active_profile = event['use_profile']
            else:
                break
        
        if active_profile in self.profiles:
            return self.profiles[active_profile], active_profile
        return None, "Unknown"