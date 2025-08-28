#!/usr/bin/env python3
"""
DL BMS 專用測試工具
基於你的 CAN 協議文件創建正確的藍牙通訊
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
import struct

console = Console()

class DLBMSTester:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 正確的特徵對（從測試中發現）
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.notification_data = []
        
        # 基於你的 PDF CAN 協議的命令
        self.dl_commands = {
            # 嘗試直接請求 CAN 報文1數據 (ID: 0x1806E5F4)
            "request_report1": bytes([0x18, 0x06, 0xE5, 0xF4, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            
            # 嘗試簡單的數據請求
            "get_data": bytes([0x01]),
            "get_status": bytes([0x02]),
            "get_voltage": bytes([0x03]),
            "get_current": bytes([0x04]),
            "get_soc": bytes([0x05]),
            
            # B04 模塊可能的喚醒序列
            "wake_b04": bytes([0xB0, 0x4A]),
            "init_dl": bytes([0x44, 0x4C]),  # 'DL' ASCII
            
            # 可能的握手序列
            "handshake1": bytes([0xAA, 0x55]),
            "handshake2": bytes([0x5A, 0xA5]),
            
            # 嘗試 CAN ID 作為命令
            "can_bms_addr": bytes([0xF4]),  # BMS 地址 244
            "can_ccs_addr": bytes([0xE5]),  # 充電機地址 229
            
            # 請求 8 bytes CAN 數據的可能格式
            "request_8bytes": bytes([0x08, 0x00]),  # 請求8字節數據
            
            # 基於你測試結果的特殊命令
            "start_monitor": bytes([0xFF, 0xFF, 0x00, 0x01]),
            "get_battery_info": bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x08]),
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
            'hex': data.hex().upper()
        })
        
        console.print(f"[green]🔔 收到通知: {data.hex().upper()}[/green]")
        
        # 立即分析是否為 CAN 協議數據
        analysis = self.analyze_can_data(data)
        if analysis:
            console.print(f"[cyan]🔋 CAN 分析: {analysis}[/cyan]")
    
    def analyze_can_data(self, data: bytes) -> Optional[str]:
        """分析是否為你的 CAN 協議數據"""
        if len(data) == 8:  # CAN 數據幀長度
            try:
                # 根據你的 PDF 報文1格式解析
                voltage = int.from_bytes(data[0:2], 'big') * 0.1  # 電壓 0.1V/bit
                current = int.from_bytes(data[2:4], 'big') * 0.1  # 電流 0.1A/bit  
                soc = int.from_bytes(data[4:6], 'big') * 0.1      # SOC 0.1%/bit
                control = data[6]                                 # 控制
                status = data[7]                                  # 異常狀態
                
                # 檢查數值是否在合理範圍
                if 20.0 <= voltage <= 100.0 and 0.0 <= soc <= 100.0:
                    return (f"電壓:{voltage:.1f}V, 電流:{current:.1f}A, "
                           f"SOC:{soc:.1f}%, 控制:0x{control:02X}, 狀態:0x{status:02X}")
                           
            except Exception:
                pass
        
        # 檢查是否為其他長度的有意義數據
        if len(data) >= 4:
            try:
                # 嘗試不同的解析方式
                val1 = int.from_bytes(data[0:2], 'big')
                val2 = int.from_bytes(data[2:4], 'big')
                
                # 電壓可能的範圍檢查
                if 200 <= val1 <= 1000:  # 20.0V - 100.0V (以 0.1V 為單位)
                    voltage = val1 * 0.1
                    return f"可能電壓: {voltage:.1f}V, 數值2: {val2}"
                
            except Exception:
                pass
        
        return None
    
    async def send_dl_command(self, cmd_name: str, cmd_data: bytes) -> bool:
        """發送 DL BMS 命令"""
        try:
            console.print(f"\n[cyan]📤 發送 {cmd_name}: {cmd_data.hex().upper()}[/cyan]")
            
            # 清空之前的通知數據
            self.notification_data.clear()
            
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, cmd_data, response=False)
            
            # 等待響應
            await asyncio.sleep(2.0)  # 較長的等待時間
            
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
    
    async def continuous_monitoring(self, duration: int = 60):
        """持續監控模式"""
        console.print(f"\n[bold green]🔄 啟動持續監控模式 ({duration} 秒)...[/bold green]")
        
        try:
            # 啟用持續通知
            await self.client.start_notify(self.read_char, self.notification_handler)
            console.print("[green]✅ 通知監聽已啟動[/green]")
            
            start_time = time.time()
            last_command_time = start_time
            
            # 定期發送查詢命令
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # 每10秒發送一次查詢命令
                if current_time - last_command_time >= 10:
                    console.print(f"[dim]發送定期查詢...[/dim]")
                    
                    # 嘗試多個可能的查詢命令
                    for cmd_name in ["get_data", "get_voltage", "get_status"]:
                        if cmd_name in self.dl_commands:
                            try:
                                await self.client.write_gatt_char(
                                    self.write_char, 
                                    self.dl_commands[cmd_name], 
                                    response=False
                                )
                                await asyncio.sleep(1)
                            except:
                                pass
                    
                    last_command_time = current_time
                
                await asyncio.sleep(1)
                
                # 顯示進度
                elapsed = int(current_time - start_time)
                if elapsed % 15 == 0 and elapsed > 0:
                    console.print(f"[dim]監控進度: {elapsed}/{duration} 秒，已收到 {len(self.notification_data)} 個通知[/dim]")
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            console.print(f"[yellow]監控完成，共收到 {len(self.notification_data)} 個通知[/yellow]")
            
        except Exception as e:
            console.print(f"[red]監控錯誤: {e}[/red]")
    
    async def test_all_commands(self):
        """測試所有 DL 命令"""
        console.print(f"\n[bold green]🧪 測試所有 DL BMS 命令...[/bold green]")
        
        successful_commands = []
        
        for cmd_name, cmd_data in self.dl_commands.items():
            success = await self.send_dl_command(cmd_name, cmd_data)
            
            if success:
                successful_commands.append(cmd_name)
                
                # 分析收到的數據
                for notif in self.notification_data:
                    if notif['data'] != cmd_data:  # 不是回音
                        console.print(f"[green]📊 真實數據: {notif['hex']} ({len(notif['data'])} bytes)[/green]")
                        analysis = self.analyze_can_data(notif['data'])
                        if analysis:
                            console.print(f"[cyan]🔋 解析結果: {analysis}[/cyan]")
            
            await asyncio.sleep(0.5)  # 命令間隔
        
        return successful_commands
    
    async def smart_discovery(self):
        """智能發現模式"""
        console.print(f"\n[bold cyan]🎯 智能發現模式...[/bold cyan]")
        
        # 1. 首先嘗試喚醒序列
        console.print("[yellow]階段1: 嘗試喚醒序列[/yellow]")
        wake_commands = ["wake_b04", "init_dl", "handshake1", "handshake2"]
        
        for cmd_name in wake_commands:
            if cmd_name in self.dl_commands:
                await self.send_dl_command(cmd_name, self.dl_commands[cmd_name])
        
        # 2. 嘗試數據請求命令  
        console.print("[yellow]階段2: 嘗試數據請求[/yellow]")
        data_commands = ["get_data", "get_voltage", "get_current", "get_soc"]
        
        for cmd_name in data_commands:
            if cmd_name in self.dl_commands:
                await self.send_dl_command(cmd_name, self.dl_commands[cmd_name])
        
        # 3. 嘗試 CAN 相關命令
        console.print("[yellow]階段3: 嘗試 CAN 協議命令[/yellow]")
        can_commands = ["request_report1", "can_bms_addr", "request_8bytes"]
        
        for cmd_name in can_commands:
            if cmd_name in self.dl_commands:
                await self.send_dl_command(cmd_name, self.dl_commands[cmd_name])
    
    def create_can_frame(self, can_id: int, data: bytes) -> bytes:
        """創建 CAN 幀格式"""
        # 嘗試創建標準的 CAN 幀格式
        frame = bytearray()
        
        # CAN ID (29位擴展幀)
        frame.extend(struct.pack('>I', can_id))  # 大端序 4 字節
        
        # DLC (數據長度)
        frame.append(len(data))
        
        # 數據
        frame.extend(data)
        
        # 填充到標準長度
        while len(frame) < 13:
            frame.append(0)
        
        return bytes(frame)
    
    async def test_can_frames(self):
        """測試 CAN 幀格式"""
        console.print(f"\n[bold blue]🚗 測試 CAN 幀格式...[/bold blue]")
        
        # 創建請求你的報文1的 CAN 幀
        can_id_1 = 0x1806E5F4  # 你的報文1 ID
        can_id_2 = 0x18FF50E5  # 你的報文2 ID
        
        # 嘗試不同的 CAN 幀格式
        test_frames = {
            "request_report1": self.create_can_frame(can_id_1, bytes([0x00] * 8)),
            "request_report2": self.create_can_frame(can_id_2, bytes([0x00] * 8)),
            "simple_can_req": bytes([0x18, 0x06, 0xE5, 0xF4]),  # 簡化的 CAN ID
        }
        
        for frame_name, frame_data in test_frames.items():
            await self.send_dl_command(frame_name, frame_data)
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python dl_bms_tester.py <MAC地址> [模式]")
        console.print("模式: commands | monitor | discovery | can")
        console.print("範例: python dl_bms_tester.py 41:18:12:01:37:71 discovery")
        return 1
    
    mac_address = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "discovery"
    
    tester = DLBMSTester(mac_address)
    
    console.print("[bold blue]🔋 DL BMS 專用測試工具[/bold blue]")
    console.print("=" * 60)
    console.print(f"目標設備: {mac_address}")
    console.print(f"測試模式: {mode}")
    console.print(f"基於: CAN 協議文件 (報文1: 0x1806E5F4, 報文2: 0x18FF50E5)")
    console.print(f"特徵對: fff2 → fff1\n")
    
    try:
        # 建立連線
        if not await tester.connect():
            return 1
        
        if mode == "commands":
            successful_commands = await tester.test_all_commands()
            console.print(f"\n[green]成功命令: {len(successful_commands)} 個[/green]")
            if successful_commands:
                console.print(f"有效命令: {', '.join(successful_commands)}")
        
        elif mode == "monitor":
            await tester.continuous_monitoring(duration=60)
        
        elif mode == "discovery":
            await tester.smart_discovery()
            
        elif mode == "can":
            await tester.test_can_frames()
        
        # 如果找到真實數據，進行持續監控
        if any('data' in notif and len(notif['data']) >= 4 and notif['data'].hex() not in ['DDA50300FFFD77', 'DDA50400FFFC77'] 
               for notif in tester.notification_data):
            console.print(f"\n[green]🎉 發現真實數據！啟動持續監控...[/green]")
            await tester.continuous_monitoring(duration=30)
        
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