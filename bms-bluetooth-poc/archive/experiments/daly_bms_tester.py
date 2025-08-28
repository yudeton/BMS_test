#!/usr/bin/env python3
"""
DALY BMS 專用協議測試工具
基於 DALY BMS UART 協議規範實現藍牙通訊
支援 0xA5 傳統協議和 0xD2 新版協議
"""

import asyncio
import sys
import time
import struct
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from bleak import BleakClient, BleakScanner

console = Console()

class DALYBMSTester:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值對（基於之前測試結果）
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.notification_data = []
        
        # DALY BMS 標準命令（0xA5 協議）
        self.daly_commands_a5 = {
            "pack_measurements": {
                "code": 0x90,
                "name": "電壓電流SOC",
                "description": "獲取電池組電壓、電流、SOC"
            },
            "min_max_voltage": {
                "code": 0x91, 
                "name": "最小最大電芯電壓",
                "description": "獲取電芯最小/最大電壓"
            },
            "pack_temp": {
                "code": 0x92,
                "name": "溫度感測器",
                "description": "獲取最小/最大溫度"
            },
            "mosfet_status": {
                "code": 0x93,
                "name": "MOSFET狀態", 
                "description": "充放電MOSFET開關狀態"
            },
            "status_info": {
                "code": 0x94,
                "name": "狀態資訊",
                "description": "系統狀態資訊"
            },
            "cell_voltages": {
                "code": 0x95,
                "name": "電芯電壓",
                "description": "所有電芯電壓"
            },
            "cell_temp": {
                "code": 0x96,
                "name": "電芯溫度",
                "description": "所有電芯溫度"
            },
            "cell_balance": {
                "code": 0x97,
                "name": "電芯平衡狀態",
                "description": "電芯平衡狀態"
            },
            "failure_codes": {
                "code": 0x98,
                "name": "故障代碼",
                "description": "警報和故障代碼"
            }
        }
        
        # BMS 保護狀態定義
        self.protection_states = {
            "level1_alarm": {
                0x01: "電芯過壓警報",
                0x02: "電芯欠壓警報", 
                0x04: "電池組過壓警報",
                0x08: "電池組欠壓警報",
                0x10: "充電過流警報",
                0x20: "放電過流警報",
                0x40: "充電過溫警報",
                0x80: "放電過溫警報"
            },
            "level2_alarm": {
                0x01: "充電低溫警報",
                0x02: "放電低溫警報",
                0x04: "電池組高溫警報",
                0x08: "電池組低溫警報",
                0x10: "電池包溫差過大警報"
            },
            "level1_protection": {
                0x01: "電芯過壓保護",
                0x02: "電芯欠壓保護",
                0x04: "電池組過壓保護", 
                0x08: "電池組欠壓保護",
                0x10: "充電過流保護",
                0x20: "放電過流保護",
                0x40: "充電過溫保護",
                0x80: "放電過溫保護"
            },
            "level2_protection": {
                0x01: "充電低溫保護",
                0x02: "放電低溫保護",
                0x04: "短路保護",
                0x08: "前端檢測IC錯誤",
                0x10: "軟鎖保護"
            }
        }
        
        # DALY BMS 新版命令（0xD2 協議）
        self.daly_commands_d2 = {
            "basic_info": {
                "code": 0x03,
                "name": "基本資訊", 
                "description": "電壓電流SOC (Modbus)"
            },
            "cell_info": {
                "code": 0x04,
                "name": "電芯資訊",
                "description": "電芯電壓 (Modbus)"
            }
        }
        
        # DALY BMS 控制命令（喚醒和 MOSFET 控制）
        self.daly_control_commands = {
            "discharge_mosfet_on": {
                "code": 0xD9,
                "data": bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                "name": "放電MOSFET開啟",
                "description": "開啟放電MOSFET，允許放電"
            },
            "discharge_mosfet_off": {
                "code": 0xD9,
                "data": bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                "name": "放電MOSFET關閉", 
                "description": "關閉放電MOSFET，禁止放電"
            },
            "charge_mosfet_on": {
                "code": 0xDA,
                "data": bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                "name": "充電MOSFET開啟",
                "description": "開啟充電MOSFET，允許充電"
            },
            "charge_mosfet_off": {
                "code": 0xDA,
                "data": bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                "name": "充電MOSFET關閉",
                "description": "關閉充電MOSFET，禁止充電"
            },
            "bms_reset": {
                "code": 0x00,
                "data": bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                "name": "BMS重置",
                "description": "重置BMS系統"
            }
        }
    
    def calculate_checksum_a5(self, packet: bytes) -> int:
        """計算 0xA5 協議的校驗和"""
        return sum(packet) & 0xFF
    
    def create_daly_packet_a5(self, command_code: int, host_addr: int = 0x80, data_payload: bytes = None) -> bytes:
        """創建 DALY 0xA5 協議封包"""
        # 13 位元組固定格式
        packet = bytearray(13)
        packet[0] = 0xA5        # 起始位元組
        packet[1] = host_addr   # 主機地址 (0x80=發送, 0x01=接收, 0x40=備選地址)
        packet[2] = command_code # 命令代碼
        packet[3] = 0x08        # 數據長度（固定8）
        
        # 如果有數據負載，填入前8位元組
        if data_payload:
            payload_len = min(len(data_payload), 8)
            packet[4:4+payload_len] = data_payload[:payload_len]
        # 否則保持為 0x00（已初始化）
        
        # 計算校驗和（前12位元組的和）
        checksum = self.calculate_checksum_a5(packet[:12])
        packet[12] = checksum
        
        return bytes(packet)
    
    def create_daly_packet_d2(self, command_code: int) -> bytes:
        """創建 DALY 0xD2 協議封包（Modbus格式）"""
        # 8 位元組格式
        packet = bytearray(8)
        packet[0] = 0xD2        # 起始位元組
        packet[1] = 0x03        # 功能碼
        packet[2] = command_code # 命令代碼
        packet[3] = 0x00        # 高位地址
        packet[4] = 0x00        # 低位地址  
        packet[5] = 0x01        # 讀取長度
        
        # CRC16 校驗和（簡化實現）
        crc = 0x1234  # 暫時使用固定值
        packet[6] = (crc >> 8) & 0xFF
        packet[7] = crc & 0xFF
        
        return bytes(packet)
    
    async def connect(self) -> bool:
        """建立藍牙連線"""
        try:
            console.print(f"[cyan]正在連線到 {self.mac_address}...[/cyan]")
            
            device = await BleakScanner.find_device_by_address(self.mac_address, timeout=5.0)
            if not device:
                console.print(f"[red]找不到設備 {self.mac_address}[/red]")
                return False
            
            self.client = BleakClient(self.mac_address)
            await self.client.connect()
            
            if self.client.is_connected:
                self.is_connected = True
                console.print(f"[green]✅ 成功連線到 {self.mac_address}[/green]")
                return True
                
        except Exception as e:
            console.print(f"[red]連線失敗: {e}[/red]")
            return False
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if not data:
            return
        
        timestamp = datetime.now()
        self.notification_data.append({
            'timestamp': timestamp,
            'data': data,
            'hex': data.hex().upper(),
            'length': len(data)
        })
        
        console.print(f"[green]🔔 收到通知: {data.hex().upper()} (長度: {len(data)})[/green]")
        
        # 分析是否為 DALY 協議回應
        analysis = self.parse_daly_response(data)
        if analysis:
            console.print(f"[cyan]📊 DALY 解析: {analysis}[/cyan]")
    
    def parse_daly_response(self, data: bytes) -> Optional[Dict]:
        """解析 DALY 協議回應"""
        if len(data) < 4:
            return None
        
        # 檢查 0xA5 協議回應
        if data[0] == 0xA5 and len(data) == 13:
            return self.parse_a5_response(data)
        
        # 檢查 0xD2 協議回應  
        elif data[0] == 0xD2 and len(data) >= 8:
            return self.parse_d2_response(data)
        
        return None
    
    def parse_a5_response(self, data: bytes) -> Dict:
        """解析 0xA5 協議回應"""
        if len(data) != 13:
            return {"error": "封包長度錯誤"}
        
        # 驗證校驗和
        calculated_checksum = self.calculate_checksum_a5(data[:12])
        if calculated_checksum != data[12]:
            return {"error": f"校驗和錯誤 (計算: {calculated_checksum:02X}, 收到: {data[12]:02X})"}
        
        host_addr = data[1]
        command_code = data[2] 
        data_len = data[3]
        payload = data[4:12]
        
        result = {
            "protocol": "0xA5",
            "host_addr": f"0x{host_addr:02X}",
            "command": f"0x{command_code:02X}", 
            "data_len": data_len,
            "checksum_ok": True
        }
        
        # 根據命令碼解析數據
        if command_code == 0x90:  # 電壓電流SOC
            # DALY 協議正確解析方式
            voltage = int.from_bytes(payload[0:2], 'big') / 10.0  # 0.1V 單位
            
            # 電流計算：需要減去 30000 偏移量，然後除以 10
            current_raw = int.from_bytes(payload[2:4], 'big')
            current = (current_raw - 30000) / 10.0  # 0.1A 單位，30000 偏移
            
            # SOC 百分比
            soc = int.from_bytes(payload[4:6], 'big') / 10.0      # 0.1% 單位
            
            # 額外資訊：循環次數和剩餘容量（如果有的話）
            extra_info = {}
            if len(payload) >= 8:
                remaining_cap = int.from_bytes(payload[6:8], 'big') / 100.0  # Ah
                extra_info["remaining_capacity"] = f"{remaining_cap:.2f}Ah"
            
            result["parsed"] = {
                "voltage": f"{voltage:.1f}V",
                "current": f"{current:.1f}A", 
                "soc": f"{soc:.1f}%",
                "current_raw": f"0x{current_raw:04X} ({current_raw})",
                **extra_info
            }
        
        elif command_code == 0x91:  # 最小最大電芯電壓
            max_voltage = int.from_bytes(payload[0:2], 'big') / 1000.0  # mV
            max_cell = payload[2]
            min_voltage = int.from_bytes(payload[3:5], 'big') / 1000.0  # mV  
            min_cell = payload[5]
            result["parsed"] = {
                "max_voltage": f"{max_voltage:.3f}V (Cell {max_cell})",
                "min_voltage": f"{min_voltage:.3f}V (Cell {min_cell})"
            }
            
        elif command_code == 0x92:  # 溫度
            max_temp = int.from_bytes(payload[0:1], 'big') - 40    # 攝氏度
            max_sensor = payload[1] 
            min_temp = int.from_bytes(payload[2:3], 'big') - 40
            min_sensor = payload[3]
            result["parsed"] = {
                "max_temp": f"{max_temp}°C (感測器 {max_sensor})",
                "min_temp": f"{min_temp}°C (感測器 {min_sensor})"
            }
        
        elif command_code == 0x93:  # MOSFET 狀態
            charge_mosfet = "開啟" if payload[0] == 1 else "關閉"
            discharge_mosfet = "開啟" if payload[1] == 1 else "關閉"
            bms_life = payload[2]  # BMS 生命週期
            remaining_capacity = int.from_bytes(payload[3:5], 'big') / 1000.0  # 剩餘容量 Ah
            result["parsed"] = {
                "charge_mosfet": charge_mosfet,
                "discharge_mosfet": discharge_mosfet,
                "bms_life": f"{bms_life}%",
                "remaining_capacity": f"{remaining_capacity:.3f}Ah"
            }
            
        elif command_code == 0x94:  # 狀態資訊
            # 系統狀態解析
            result["parsed"] = {
                "cell_count": payload[0],
                "temp_sensor_count": payload[1], 
                "charger_status": "連接" if payload[2] == 1 else "未連接",
                "load_status": "連接" if payload[3] == 1 else "未連接",
                "state_info": f"0x{payload[4]:02X}",
                "cycle_count": int.from_bytes(payload[5:7], 'big')
            }
            
        elif command_code == 0x95:  # 電芯電壓
            # 解析電芯電壓數據
            cell_voltages = []
            for i in range(0, min(len(payload), 8), 2):
                if i + 1 < len(payload):
                    voltage = int.from_bytes(payload[i:i+2], 'big') / 1000.0  # mV to V
                    if voltage > 0:  # 只顯示非零電壓
                        cell_voltages.append(f"{voltage:.3f}V")
            
            result["parsed"] = {
                "cell_voltages": cell_voltages if cell_voltages else ["無數據"],
                "cell_count": len(cell_voltages)
            }
            
        elif command_code == 0x96:  # 電芯溫度
            # 解析溫度數據
            temperatures = []
            for i in range(min(len(payload), 8)):
                if payload[i] != 0:
                    temp = payload[i] - 40  # 溫度偏移
                    temperatures.append(f"{temp}°C")
            
            result["parsed"] = {
                "temperatures": temperatures if temperatures else ["無數據"],
                "sensor_count": len(temperatures)
            }
            
        elif command_code == 0x97:  # 電芯平衡狀態
            # 解析平衡狀態（位元組表示）
            balance_bits = int.from_bytes(payload[0:2], 'big')
            balancing_cells = []
            for bit in range(16):  # 檢查16個可能的電芯
                if balance_bits & (1 << bit):
                    balancing_cells.append(f"Cell{bit+1}")
            
            result["parsed"] = {
                "balance_status": f"0x{balance_bits:04X}",
                "balancing_cells": balancing_cells if balancing_cells else ["無平衡"]
            }
            
        elif command_code == 0x98:  # 故障代碼
            # 解析故障和警報代碼
            level1_alarm = payload[0]
            level2_alarm = payload[1] 
            level1_protection = payload[2]
            level2_protection = payload[3]
            
            # 解析具體的警報和保護狀態
            active_alarms = []
            active_protections = []
            
            # Level 1 警報
            for bit, desc in self.protection_states["level1_alarm"].items():
                if level1_alarm & bit:
                    active_alarms.append(desc)
            
            # Level 2 警報
            for bit, desc in self.protection_states["level2_alarm"].items():
                if level2_alarm & bit:
                    active_alarms.append(desc)
            
            # Level 1 保護
            for bit, desc in self.protection_states["level1_protection"].items():
                if level1_protection & bit:
                    active_protections.append(desc)
            
            # Level 2 保護
            for bit, desc in self.protection_states["level2_protection"].items():
                if level2_protection & bit:
                    active_protections.append(desc)
            
            result["parsed"] = {
                "level1_alarm": f"0x{level1_alarm:02X}",
                "level2_alarm": f"0x{level2_alarm:02X}", 
                "level1_protection": f"0x{level1_protection:02X}",
                "level2_protection": f"0x{level2_protection:02X}",
                "active_alarms": active_alarms if active_alarms else ["無警報"],
                "active_protections": active_protections if active_protections else ["無保護"],
                "status": "正常" if all(x == 0 for x in [level1_alarm, level2_alarm, level1_protection, level2_protection]) else "有警報/保護"
            }
        
        return result
    
    def parse_d2_response(self, data: bytes) -> Dict:
        """解析 0xD2 協議回應（Modbus格式）"""
        return {
            "protocol": "0xD2", 
            "command": f"0x{data[2]:02X}",
            "data": data[3:].hex().upper(),
            "note": "Modbus協議回應"
        }
    
    async def send_daly_command(self, cmd_name: str, packet: bytes) -> bool:
        """發送 DALY 命令"""
        try:
            console.print(f"\n[cyan]📤 發送 {cmd_name}: {packet.hex().upper()}[/cyan]")
            
            # 清空之前的通知數據
            self.notification_data.clear()
            
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, packet, response=False)
            
            # 等待響應
            await asyncio.sleep(2.0)
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            
            if self.notification_data:
                console.print(f"[green]✅ 收到 {len(self.notification_data)} 個響應[/green]")
                return True
            else:
                console.print("[yellow]⚠️ 無響應[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ 命令失敗: {e}[/red]")
            return False
    
    async def test_a5_protocol(self) -> List[str]:
        """測試 0xA5 協議命令"""
        console.print(f"\n[bold green]🧪 測試 DALY 0xA5 協議命令...[/bold green]")
        
        successful_commands = []
        
        # 測試不同的主機地址
        host_addresses = [0x80, 0x40]  # 0x80 是標準，0x40 是備選
        
        for cmd_name, cmd_info in self.daly_commands_a5.items():
            success = False
            
            # 嘗試不同的主機地址
            for host_addr in host_addresses:
                packet = self.create_daly_packet_a5(cmd_info["code"], host_addr)
                host_desc = "標準" if host_addr == 0x80 else "備選"
                
                success = await self.send_daly_command(
                    f"{cmd_info['name']} (0x{cmd_info['code']:02X}, {host_desc}地址)", 
                    packet
                )
                
                if success:
                    successful_commands.append(cmd_name)
                    console.print(f"[green]✅ {cmd_info['description']} - 成功 (地址: 0x{host_addr:02X})[/green]")
                    break  # 成功就不需要試其他地址
                
                await asyncio.sleep(0.3)  # 短暫間隔
            
            if not success:
                console.print(f"[yellow]⚠️ {cmd_info['description']} - 兩個地址都無響應[/yellow]")
            
            await asyncio.sleep(0.5)  # 命令間隔
        
        return successful_commands
    
    async def test_d2_protocol(self) -> List[str]:
        """測試 0xD2 協議命令"""
        console.print(f"\n[bold blue]🧪 測試 DALY 0xD2 協議命令...[/bold blue]")
        
        successful_commands = []
        
        for cmd_name, cmd_info in self.daly_commands_d2.items():
            packet = self.create_daly_packet_d2(cmd_info["code"])
            success = await self.send_daly_command(
                f"{cmd_info['name']} (0x{cmd_info['code']:02X})",
                packet
            )
            
            if success:
                successful_commands.append(cmd_name)
                console.print(f"[green]✅ {cmd_info['description']} - 成功[/green]")
            else:
                console.print(f"[yellow]⚠️ {cmd_info['description']} - 無響應[/yellow]")
            
            await asyncio.sleep(0.5)  # 命令間隔
        
        return successful_commands
    
    async def test_control_commands(self) -> List[str]:
        """測試 BMS 控制命令（MOSFET 和重置）"""
        console.print(f"\n[bold red]⚡ 測試 DALY BMS 控制命令...[/bold red]")
        console.print("[yellow]警告：這些命令會實際控制 BMS 的 MOSFET 開關！[/yellow]")
        
        successful_commands = []
        
        # 使用 0x40 地址（基於研究結果）
        host_addr = 0x40
        
        for cmd_name, cmd_info in self.daly_control_commands.items():
            # 創建控制命令封包
            packet = self.create_daly_packet_a5(cmd_info["code"], host_addr, cmd_info["data"])
            
            console.print(f"\n[yellow]準備發送: {cmd_info['name']}[/yellow]")
            console.print(f"[dim]描述: {cmd_info['description']}[/dim]")
            console.print(f"[dim]命令: {packet.hex().upper()}[/dim]")
            
            success = await self.send_daly_command(
                f"{cmd_info['name']} (0x{cmd_info['code']:02X})",
                packet
            )
            
            if success:
                successful_commands.append(cmd_name)
                console.print(f"[green]✅ {cmd_info['description']} - 命令已發送[/green]")
                
                # 發送控制命令後，立即讀取狀態
                await asyncio.sleep(1)
                status_packet = self.create_daly_packet_a5(0x93, 0x80)  # MOSFET 狀態查詢
                await self.send_daly_command("MOSFET狀態查詢", status_packet)
                
            else:
                console.print(f"[red]❌ {cmd_info['description']} - 無響應[/red]")
            
            await asyncio.sleep(2.0)  # 控制命令間較長間隔
        
        return successful_commands
    
    async def bms_wake_up_sequence(self):
        """BMS 喚醒序列"""
        console.print(f"\n[bold cyan]🔋 啟動 DALY BMS 喚醒序列...[/bold cyan]")
        
        # 1. 嘗試重置 BMS
        console.print("[cyan]步驟 1: 嘗試重置 BMS[/cyan]")
        reset_cmd = self.daly_control_commands["bms_reset"]
        reset_packet = self.create_daly_packet_a5(reset_cmd["code"], 0x40, reset_cmd["data"])
        await self.send_daly_command("BMS重置", reset_packet)
        await asyncio.sleep(3)
        
        # 2. 嘗試開啟放電 MOSFET
        console.print("[cyan]步驟 2: 嘗試開啟放電 MOSFET[/cyan]")
        discharge_on_cmd = self.daly_control_commands["discharge_mosfet_on"]
        discharge_packet = self.create_daly_packet_a5(discharge_on_cmd["code"], 0x40, discharge_on_cmd["data"])
        await self.send_daly_command("開啟放電MOSFET", discharge_packet)
        await asyncio.sleep(2)
        
        # 3. 嘗試開啟充電 MOSFET
        console.print("[cyan]步驟 3: 嘗試開啟充電 MOSFET[/cyan]")
        charge_on_cmd = self.daly_control_commands["charge_mosfet_on"]
        charge_packet = self.create_daly_packet_a5(charge_on_cmd["code"], 0x40, charge_on_cmd["data"])
        await self.send_daly_command("開啟充電MOSFET", charge_packet)
        await asyncio.sleep(2)
        
        # 4. 檢查 MOSFET 狀態
        console.print("[cyan]步驟 4: 檢查 MOSFET 狀態[/cyan]")
        status_packet = self.create_daly_packet_a5(0x93, 0x80)
        await self.send_daly_command("MOSFET狀態檢查", status_packet)
        await asyncio.sleep(1)
        
        # 5. 檢查基本資訊
        console.print("[cyan]步驟 5: 檢查基本資訊[/cyan]")
        basic_packet = self.create_daly_packet_a5(0x90, 0x80)
        await self.send_daly_command("基本資訊檢查", basic_packet)
        
        console.print("[green]🎯 喚醒序列完成！檢查上述回應以確認 BMS 狀態[/green]")
    
    async def continuous_monitoring(self, duration: int = 60):
        """持續監控模式"""
        console.print(f"\n[bold green]🔄 啟動 DALY BMS 持續監控 ({duration} 秒)...[/bold green]")
        
        try:
            # 啟用持續通知
            await self.client.start_notify(self.read_char, self.notification_handler)
            console.print("[green]✅ 通知監聽已啟動[/green]")
            
            start_time = time.time()
            last_query_time = start_time
            query_commands = [0x90, 0x93, 0x94, 0x95]  # 輪流查詢不同數據
            command_index = 0
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # 每5秒發送一次不同的查詢命令
                if current_time - last_query_time >= 5:
                    cmd_code = query_commands[command_index % len(query_commands)]
                    cmd_names = {0x90: "電壓電流SOC", 0x93: "MOSFET狀態", 
                               0x94: "系統狀態", 0x95: "電芯電壓"}
                    
                    console.print(f"[dim]發送定期查詢（{cmd_names[cmd_code]}）...[/dim]")
                    
                    # 嘗試兩個地址
                    for addr in [0x80, 0x40]:
                        packet = self.create_daly_packet_a5(cmd_code, addr)
                        try:
                            await self.client.write_gatt_char(self.write_char, packet, response=False)
                            await asyncio.sleep(0.5)
                        except:
                            pass
                    
                    command_index += 1
                    last_query_time = current_time
                
                await asyncio.sleep(1)
                
                # 顯示進度和最新數據  
                elapsed = int(current_time - start_time)
                if elapsed % 15 == 0 and elapsed > 0:
                    console.print(f"[dim]監控進度: {elapsed}/{duration} 秒，已收到 {len(self.notification_data)} 個通知[/dim]")
                    
                    # 顯示最近的有效數據
                    if self.notification_data:
                        latest = self.notification_data[-1]
                        if latest['length'] == 13:  # DALY 回應
                            analysis = self.parse_daly_response(latest['data'])
                            if analysis and 'parsed' in analysis:
                                console.print(f"[cyan]📊 最新數據: {analysis['parsed']}[/cyan]")
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            console.print(f"[yellow]監控完成，共收到 {len(self.notification_data)} 個通知[/yellow]")
            
            # 顯示監控摘要
            self.display_monitoring_summary()
            
        except Exception as e:
            console.print(f"[red]監控錯誤: {e}[/red]")
    
    def display_monitoring_summary(self):
        """顯示監控摘要"""
        if not self.notification_data:
            return
        
        console.print(f"\n[bold cyan]📋 監控摘要:[/bold cyan]")
        
        # 統計不同命令的響應
        command_stats = {}
        latest_data = {}
        
        for entry in self.notification_data:
            if entry['length'] == 13:  # DALY 協議響應
                analysis = self.parse_daly_response(entry['data'])
                if analysis:
                    cmd = analysis.get('command', 'unknown')
                    command_stats[cmd] = command_stats.get(cmd, 0) + 1
                    if 'parsed' in analysis:
                        latest_data[cmd] = analysis['parsed']
        
        # 顯示統計
        table = Table(title="命令響應統計")
        table.add_column("命令", style="cyan")
        table.add_column("響應次數", style="green")
        table.add_column("最新數據", style="yellow", width=50)
        
        for cmd, count in command_stats.items():
            latest = str(latest_data.get(cmd, "無"))[:47] + "..." if len(str(latest_data.get(cmd, "無"))) > 50 else str(latest_data.get(cmd, "無"))
            table.add_row(cmd, str(count), latest)
        
        console.print(table)
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python daly_bms_tester.py <MAC地址> [模式]")
        console.print("模式: a5 | d2 | both | monitor | wakeup | control")
        console.print("範例: python daly_bms_tester.py 41:18:12:01:37:71 wakeup")
        return 1
    
    mac_address = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "both"
    
    tester = DALYBMSTester(mac_address)
    
    console.print("[bold blue]🔋 DALY BMS 專用協議測試工具[/bold blue]")
    console.print("=" * 60)
    console.print(f"目標設備: {mac_address}")
    console.print(f"測試模式: {mode}")
    console.print("支援協議: 0xA5 (UART) / 0xD2 (Modbus)")
    console.print("特徵對: fff2 → fff1\n")
    
    try:
        # 建立連線
        if not await tester.connect():
            return 1
        
        successful_a5 = []
        successful_d2 = []
        
        if mode in ["a5", "both"]:
            successful_a5 = await tester.test_a5_protocol()
        
        if mode in ["d2", "both"]:
            successful_d2 = await tester.test_d2_protocol()
        
        if mode == "monitor":
            await tester.continuous_monitoring(duration=60)
        
        elif mode == "wakeup":
            await tester.bms_wake_up_sequence()
            
        elif mode == "control":
            await tester.test_control_commands()
        
        # 顯示測試結果
        console.print(f"\n[bold green]📊 測試結果摘要:[/bold green]")
        if successful_a5:
            console.print(f"[green]0xA5 協議成功命令: {len(successful_a5)} 個[/green]")
            console.print(f"  命令: {', '.join(successful_a5)}")
        
        if successful_d2:
            console.print(f"[green]0xD2 協議成功命令: {len(successful_d2)} 個[/green]") 
            console.print(f"  命令: {', '.join(successful_d2)}")
        
        total_success = len(successful_a5) + len(successful_d2)
        if total_success > 0:
            console.print(f"[green]🎉 找到 DALY BMS 協議！共 {total_success} 個有效命令[/green]")
            
            # 如果有成功命令，啟動短期監控
            if total_success > 0:
                console.print(f"\n[green]啟動 30 秒監控模式...[/green]")
                await tester.continuous_monitoring(duration=30)
        else:
            console.print("[yellow]⚠️ 未找到有效的 DALY 協議響應[/yellow]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷測試[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await tester.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)