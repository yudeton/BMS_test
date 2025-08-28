#!/usr/bin/env python3
"""
Smart BMS 請求-響應協議測試工具
基於小象 BMS (Xiaoxiang/JBD) 標準協議實現
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from bleak import BleakClient, BleakScanner

console = Console()

class SmartBMSTester:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        self.characteristics = {}
        
        # Smart BMS 標準命令
        self.commands = {
            "basic_info": bytes.fromhex("DD A5 03 00 FF FD 77"),      # 基本資訊（電壓、電流、SOC）
            "cell_voltages": bytes.fromhex("DD A5 04 00 FF FC 77"),   # 單體電壓
            "hardware_info": bytes.fromhex("DD A5 05 00 FF FB 77"),   # 硬體資訊
            "device_name": bytes.fromhex("DD A5 06 00 FF FA 77"),     # 設備名稱
        }
        
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
                await self.analyze_characteristics()
                return True
                
        except Exception as e:
            console.print(f"[red]連線失敗: {e}[/red]")
            return False
    
    async def analyze_characteristics(self):
        """分析特徵值功能"""
        console.print(f"\n[bold cyan]🔍 分析特徵值功能...[/bold cyan]")
        
        services = self.client.services
        
        for service in services:
            console.print(f"\n[yellow]服務 {service.uuid}:[/yellow]")
            
            for char in service.characteristics:
                properties = list(char.properties)
                self.characteristics[str(char.uuid)] = {
                    'char': char,
                    'properties': properties,
                    'service_uuid': str(service.uuid)
                }
                
                # 分析功能
                function_desc = []
                if 'write' in properties or 'write-without-response' in properties:
                    function_desc.append("📝 可寫入(命令通道)")
                if 'read' in properties:
                    function_desc.append("📖 可讀取(響應通道)")
                if 'notify' in properties:
                    function_desc.append("🔔 可通知(可能響應通道)")
                if 'indicate' in properties:
                    function_desc.append("📢 可指示(確認響應通道)")
                
                console.print(f"  特徵: {char.uuid}")
                console.print(f"    屬性: {', '.join(properties)}")
                if function_desc:
                    console.print(f"    功能: {', '.join(function_desc)}")
    
    def find_command_characteristic(self) -> Optional[str]:
        """尋找命令發送特徵值（可寫入）"""
        for uuid, info in self.characteristics.items():
            if 'write' in info['properties'] or 'write-without-response' in info['properties']:
                console.print(f"[green]🎯 找到命令特徵: {uuid}[/green]")
                return uuid
        return None
    
    def find_response_characteristics(self) -> List[str]:
        """尋找響應接收特徵值（可讀取或通知）"""
        response_chars = []
        for uuid, info in self.characteristics.items():
            if 'read' in info['properties'] or 'notify' in info['properties']:
                response_chars.append(uuid)
        
        console.print(f"[cyan]🔍 找到 {len(response_chars)} 個響應特徵[/cyan]")
        return response_chars
    
    async def send_command(self, command_name: str, command_bytes: bytes) -> Optional[bytes]:
        """發送命令並獲取響應"""
        if not self.is_connected:
            console.print("[red]未連線[/red]")
            return None
        
        # 尋找命令特徵
        cmd_char = self.find_command_characteristic()
        if not cmd_char:
            console.print("[red]❌ 找不到命令發送特徵[/red]")
            return None
        
        try:
            console.print(f"[cyan]📤 發送命令 '{command_name}': {command_bytes.hex().upper()}[/cyan]")
            
            # 發送命令
            await self.client.write_gatt_char(cmd_char, command_bytes, response=False)
            
            # 等待響應（短暫延遲）
            await asyncio.sleep(0.5)
            
            # 嘗試從所有可能的響應特徵讀取
            response_chars = self.find_response_characteristics()
            
            for resp_char in response_chars:
                try:
                    if 'read' in self.characteristics[resp_char]['properties']:
                        response = await self.client.read_gatt_char(resp_char)
                        if response and len(response) > 0:
                            console.print(f"[green]📥 從 {resp_char} 收到響應: {response.hex().upper()}[/green]")
                            return response
                except Exception as e:
                    # 嘗試下一個特徵
                    continue
            
            console.print("[yellow]⚠️ 未收到響應[/yellow]")
            return None
            
        except Exception as e:
            console.print(f"[red]❌ 發送命令失敗: {e}[/red]")
            return None
    
    def parse_basic_info(self, data: bytes) -> Dict:
        """解析基本資訊響應"""
        if not data or len(data) < 10:
            return {"error": "數據長度不足"}
        
        try:
            parsed = {}
            
            # 檢查標頭
            if data[0] == 0xDD and data[1] == 0x03:  # 響應標識
                # 解析基本資訊（根據標準協議）
                total_voltage = int.from_bytes(data[4:6], byteorder='big') / 100.0  # 0.01V
                current = int.from_bytes(data[6:8], byteorder='big', signed=True) / 100.0  # 0.01A
                remaining_capacity = int.from_bytes(data[8:10], byteorder='big') / 100.0  # 0.01Ah
                nominal_capacity = int.from_bytes(data[10:12], byteorder='big') / 100.0  # 0.01Ah
                
                if len(data) > 12:
                    cycles = int.from_bytes(data[12:14], byteorder='big')
                    parsed["cycles"] = cycles
                
                if len(data) > 14:
                    production_date = int.from_bytes(data[14:16], byteorder='big')
                    parsed["production_date"] = production_date
                
                if len(data) > 16:
                    # 平衡狀態等其他資訊
                    balance_status = int.from_bytes(data[16:18], byteorder='big')
                    parsed["balance_status"] = f"0x{balance_status:04X}"
                
                if len(data) > 18:
                    # 保護狀態
                    protection_status = int.from_bytes(data[18:20], byteorder='big')
                    parsed["protection_status"] = f"0x{protection_status:04X}"
                
                if len(data) > 20:
                    # 軟體版本
                    software_version = data[20]
                    parsed["software_version"] = f"v{software_version}"
                
                if len(data) > 21:
                    # SOC
                    soc = data[21]
                    parsed["soc"] = f"{soc}%"
                
                if len(data) > 22:
                    # MOSFET 控制狀態
                    mosfet_status = data[22]
                    parsed["mosfet_status"] = f"0x{mosfet_status:02X}"
                
                if len(data) > 23:
                    # 電池串數
                    battery_strings = data[23]
                    parsed["battery_strings"] = battery_strings
                
                if len(data) > 24:
                    # 溫度感測器數量
                    temp_sensors = data[24]
                    parsed["temp_sensors"] = temp_sensors
                    
                    # 溫度數據
                    temp_offset = 25
                    temperatures = []
                    for i in range(min(temp_sensors, 3)):  # 最多3個溫度感測器
                        if temp_offset + 1 < len(data):
                            temp = int.from_bytes(data[temp_offset:temp_offset+2], byteorder='big', signed=True) / 10.0
                            temperatures.append(f"{temp:.1f}°C")
                            temp_offset += 2
                    parsed["temperatures"] = temperatures
                
                parsed.update({
                    "total_voltage": f"{total_voltage:.2f}V",
                    "current": f"{current:.2f}A",  
                    "remaining_capacity": f"{remaining_capacity:.2f}Ah",
                    "nominal_capacity": f"{nominal_capacity:.2f}Ah"
                })
                
            return parsed
            
        except Exception as e:
            return {"error": f"解析失敗: {e}"}
    
    def parse_cell_voltages(self, data: bytes) -> Dict:
        """解析單體電壓響應"""
        if not data or len(data) < 4:
            return {"error": "數據長度不足"}
        
        try:
            parsed = {"cell_voltages": []}
            
            if data[0] == 0xDD and data[1] == 0x04:  # 單體電壓響應
                cell_count = (len(data) - 7) // 2  # 減去頭部和校驗
                
                for i in range(cell_count):
                    offset = 4 + i * 2
                    if offset + 1 < len(data):
                        voltage = int.from_bytes(data[offset:offset+2], byteorder='big') / 1000.0
                        parsed["cell_voltages"].append(f"{voltage:.3f}V")
                
                # 計算差壓
                if len(parsed["cell_voltages"]) > 1:
                    voltages = [float(v.replace('V', '')) for v in parsed["cell_voltages"]]
                    max_voltage = max(voltages)
                    min_voltage = min(voltages)
                    parsed["voltage_diff"] = f"{(max_voltage - min_voltage)*1000:.0f}mV"
                    parsed["max_voltage"] = f"{max_voltage:.3f}V"
                    parsed["min_voltage"] = f"{min_voltage:.3f}V"
            
            return parsed
            
        except Exception as e:
            return {"error": f"解析失敗: {e}"}
    
    async def test_all_commands(self):
        """測試所有標準命令"""
        console.print(f"\n[bold green]🧪 開始測試 Smart BMS 標準命令...[/bold green]")
        
        results = {}
        
        for cmd_name, cmd_bytes in self.commands.items():
            console.print(f"\n[cyan]--- 測試 {cmd_name} ---[/cyan]")
            
            response = await self.send_command(cmd_name, cmd_bytes)
            
            if response:
                console.print(f"[green]✅ 響應長度: {len(response)} bytes[/green]")
                console.print(f"[dim]原始數據: {response.hex().upper()}[/dim]")
                
                # 嘗試解析數據
                if cmd_name == "basic_info":
                    parsed = self.parse_basic_info(response)
                    if "error" not in parsed:
                        console.print("[green]🔋 解析成功:[/green]")
                        for key, value in parsed.items():
                            console.print(f"  {key}: {value}")
                    else:
                        console.print(f"[yellow]⚠️ {parsed['error']}[/yellow]")
                
                elif cmd_name == "cell_voltages":
                    parsed = self.parse_cell_voltages(response)
                    if "error" not in parsed:
                        console.print("[green]⚡ 單體電壓:[/green]")
                        for i, voltage in enumerate(parsed["cell_voltages"]):
                            console.print(f"  Cell {i+1}: {voltage}")
                        if "voltage_diff" in parsed:
                            console.print(f"  差壓: {parsed['voltage_diff']}")
                    else:
                        console.print(f"[yellow]⚠️ {parsed['error']}[/yellow]")
                
                results[cmd_name] = {
                    "success": True,
                    "response": response.hex(),
                    "length": len(response)
                }
            else:
                results[cmd_name] = {
                    "success": False,
                    "error": "無響應"
                }
        
        return results
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python smart_bms_tester.py <MAC地址>")
        console.print("範例: python smart_bms_tester.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    tester = SmartBMSTester(mac_address)
    
    console.print("[bold blue]🔋 Smart BMS 協議測試工具[/bold blue]")
    console.print("=" * 50)
    console.print(f"目標設備: {mac_address}")
    console.print("協議: 小象 BMS (Xiaoxiang/JBD) 標準\n")
    
    try:
        # 建立連線
        if not await tester.connect():
            return 1
        
        # 測試所有命令
        results = await tester.test_all_commands()
        
        # 顯示測試摘要
        console.print(f"\n[bold green]📊 測試結果摘要:[/bold green]")
        successful_commands = 0
        
        for cmd_name, result in results.items():
            status = "✅ 成功" if result["success"] else "❌ 失敗"
            console.print(f"  {cmd_name}: {status}")
            if result["success"]:
                successful_commands += 1
        
        console.print(f"\n[cyan]成功命令: {successful_commands}/{len(results)}[/cyan]")
        
        if successful_commands > 0:
            console.print(f"[green]🎉 找到 Smart BMS 協議！設備正常響應 {successful_commands} 個命令[/green]")
        else:
            console.print(f"[yellow]⚠️ 設備可能不使用標準 Smart BMS 協議[/yellow]")
        
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