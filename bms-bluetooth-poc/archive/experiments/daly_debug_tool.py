#!/usr/bin/env python3
"""
DALY BMS 調試工具
提供手動命令發送、原始數據查看、協議調試等功能
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.layout import Layout
from rich.live import Live
from bleak import BleakClient, BleakScanner

console = Console()

class DALYDebugTool:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值對
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.raw_data_log = []
        self.is_monitoring = False
        
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
        
        return False
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if not data:
            return
        
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp,
            'sender': sender,
            'data': data,
            'hex': data.hex().upper(),
            'length': len(data)
        }
        
        self.raw_data_log.append(entry)
        
        # 保持日誌大小
        if len(self.raw_data_log) > 1000:
            self.raw_data_log.pop(0)
        
        # 如果在監控模式，即時顯示
        if self.is_monitoring:
            self.display_raw_data(entry)
    
    def display_raw_data(self, entry):
        """顯示原始數據"""
        timestamp_str = entry['timestamp'].strftime("%H:%M:%S.%f")[:-3]
        console.print(f"[green]{timestamp_str}[/green] | [cyan]長度: {entry['length']:2d}[/cyan] | [yellow]HEX: {entry['hex']}[/yellow]")
        
        # 顯示位元組分解
        bytes_display = " ".join(f"{b:02X}" for b in entry['data'])
        console.print(f"[dim]          位元組: {bytes_display}[/dim]")
        
        # 嘗試解析為 DALY 協議
        if len(entry['data']) == 13 and entry['data'][0] == 0xA5:
            self.parse_and_display_a5(entry['data'])
    
    def parse_and_display_a5(self, data: bytes):
        """解析並顯示 0xA5 協議數據"""
        if len(data) != 13:
            return
        
        start_byte = data[0]
        host_addr = data[1] 
        command = data[2]
        data_len = data[3]
        payload = data[4:12]
        checksum = data[12]
        
        # 驗證校驗和
        calculated_checksum = sum(data[:12]) & 0xFF
        checksum_ok = calculated_checksum == checksum
        
        console.print(f"[dim]          A5解析: 地址=0x{host_addr:02X}, 命令=0x{command:02X}, 長度={data_len}, 校驗={'✓' if checksum_ok else '✗'}[/dim]")
        console.print(f"[dim]          數據: {payload.hex().upper()}[/dim]")
        
        # 簡單數據解析
        if command == 0x90:  # 電壓電流SOC
            voltage = int.from_bytes(payload[0:2], 'big') / 10.0
            current_raw = int.from_bytes(payload[2:4], 'big')
            current = (current_raw - 30000) / 10.0
            soc = int.from_bytes(payload[4:6], 'big') / 10.0
            console.print(f"[dim]          → 電壓:{voltage:.1f}V, 電流:{current:.1f}A, SOC:{soc:.1f}%[/dim]")
    
    async def send_raw_command(self, hex_string: str) -> bool:
        """發送原始十六進制命令"""
        try:
            # 解析十六進制字符串
            hex_string = hex_string.replace(" ", "").replace("-", "")
            if len(hex_string) % 2 != 0:
                console.print("[red]錯誤: 十六進制字符串長度必須為偶數[/red]")
                return False
            
            command_bytes = bytes.fromhex(hex_string)
            
            console.print(f"[cyan]📤 發送原始命令: {command_bytes.hex().upper()}[/cyan]")
            console.print(f"[dim]   長度: {len(command_bytes)} 位元組[/dim]")
            console.print(f"[dim]   位元組: {' '.join(f'{b:02X}' for b in command_bytes)}[/dim]")
            
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, command_bytes, response=False)
            
            # 等待響應
            await asyncio.sleep(2.0)
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            
            return True
            
        except ValueError as e:
            console.print(f"[red]錯誤: 無效的十六進制格式 - {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]發送失敗: {e}[/red]")
            return False
    
    def create_a5_command(self, command_code: int, host_addr: int = 0x80, payload: bytes = None) -> str:
        """創建 0xA5 協議命令"""
        packet = bytearray(13)
        packet[0] = 0xA5
        packet[1] = host_addr
        packet[2] = command_code
        packet[3] = 0x08
        
        if payload:
            payload_len = min(len(payload), 8)
            packet[4:4+payload_len] = payload[:payload_len]
        
        checksum = sum(packet[:12]) & 0xFF
        packet[12] = checksum
        
        return packet.hex().upper()
    
    async def interactive_command_builder(self):
        """互動式命令建構器"""
        console.print("\n[bold cyan]🔧 互動式命令建構器[/bold cyan]")
        
        while True:
            console.print("\n選擇命令類型:")
            console.print("1. 0xA5 協議命令")
            console.print("2. 自訂原始命令")
            console.print("3. 返回主選單")
            
            choice = Prompt.ask("請選擇", choices=["1", "2", "3"], default="3")
            
            if choice == "1":
                # 0xA5 命令建構
                console.print("\n常用 DALY 命令:")
                console.print("0x90 - 電壓電流SOC")
                console.print("0x91 - 最小最大電芯電壓") 
                console.print("0x92 - 溫度感測器")
                console.print("0x93 - MOSFET狀態")
                console.print("0x94 - 狀態資訊")
                console.print("0x95 - 電芯電壓")
                console.print("0x96 - 電芯溫度")
                console.print("0x97 - 電芯平衡狀態")
                console.print("0x98 - 故障代碼")
                
                try:
                    cmd_code = IntPrompt.ask("命令代碼 (十進制)", default=144)  # 0x90
                    host_addr = IntPrompt.ask("主機地址 (十進制)", default=128)  # 0x80
                    
                    payload_input = Prompt.ask("數據負載 (十六進制，留空為全零)", default="")
                    payload = None
                    if payload_input.strip():
                        payload = bytes.fromhex(payload_input.replace(" ", ""))
                    
                    hex_command = self.create_a5_command(cmd_code, host_addr, payload)
                    console.print(f"\n[green]生成命令: {hex_command}[/green]")
                    
                    send = Prompt.ask("是否發送此命令?", choices=["y", "n"], default="n")
                    if send == "y":
                        await self.send_raw_command(hex_command)
                        
                except ValueError:
                    console.print("[red]輸入格式錯誤[/red]")
                    
            elif choice == "2":
                # 自訂原始命令
                hex_input = Prompt.ask("輸入十六進制命令 (如: A5 80 90 08 00 00 00 00 00 00 00 00 BD)")
                if hex_input.strip():
                    await self.send_raw_command(hex_input)
                    
            else:
                break
    
    async def start_raw_monitoring(self, duration: int = 60):
        """啟動原始數據監控"""
        console.print(f"\n[bold green]🔍 啟動原始數據監控 ({duration} 秒)...[/bold green]")
        
        self.is_monitoring = True
        self.raw_data_log.clear()
        
        try:
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            console.print("[green]✅ 監控已啟動，等待數據...[/green]")
            
            start_time = time.time()
            
            while time.time() - start_time < duration:
                await asyncio.sleep(1)
                
                # 每10秒顯示統計
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0 and elapsed > 0:
                    console.print(f"[dim]監控進度: {elapsed}/{duration} 秒，已收集 {len(self.raw_data_log)} 筆數據[/dim]")
            
            # 停止監控
            await self.client.stop_notify(self.read_char)
            self.is_monitoring = False
            
            console.print(f"[yellow]監控完成，共收集 {len(self.raw_data_log)} 筆原始數據[/yellow]")
            
            # 顯示統計摘要
            self.display_monitoring_stats()
            
        except Exception as e:
            console.print(f"[red]監控錯誤: {e}[/red]")
            self.is_monitoring = False
    
    def display_monitoring_stats(self):
        """顯示監控統計"""
        if not self.raw_data_log:
            return
        
        console.print(f"\n[bold cyan]📊 監控統計摘要:[/bold cyan]")
        
        # 統計數據長度分布
        length_stats = {}
        for entry in self.raw_data_log:
            length = entry['length']
            length_stats[length] = length_stats.get(length, 0) + 1
        
        table = Table(title="數據長度分布")
        table.add_column("長度", style="cyan")
        table.add_column("次數", style="green")
        table.add_column("百分比", style="yellow")
        
        total_count = len(self.raw_data_log)
        for length, count in sorted(length_stats.items()):
            percentage = (count / total_count) * 100
            table.add_row(f"{length} bytes", str(count), f"{percentage:.1f}%")
        
        console.print(table)
        
        # 顯示最近幾筆數據
        console.print(f"\n[bold cyan]📋 最近 5 筆數據:[/bold cyan]")
        for entry in self.raw_data_log[-5:]:
            timestamp_str = entry['timestamp'].strftime("%H:%M:%S")
            console.print(f"[green]{timestamp_str}[/green] | 長度: {entry['length']} | HEX: {entry['hex']}")
    
    def display_raw_log(self, count: int = 20):
        """顯示原始數據日誌"""
        if not self.raw_data_log:
            console.print("[yellow]無原始數據記錄[/yellow]")
            return
        
        console.print(f"\n[bold cyan]📜 原始數據日誌 (最近 {count} 筆):[/bold cyan]")
        
        recent_logs = self.raw_data_log[-count:]
        
        for i, entry in enumerate(recent_logs, 1):
            timestamp_str = entry['timestamp'].strftime("%H:%M:%S.%f")[:-3]
            console.print(f"\n[cyan]{i:2d}. {timestamp_str}[/cyan]")
            console.print(f"    長度: {entry['length']} bytes")
            console.print(f"    HEX:  {entry['hex']}")
            console.print(f"    位元組: {' '.join(f'{b:02X}' for b in entry['data'])}")
            
            # 如果是 A5 協議，解析數據
            if len(entry['data']) == 13 and entry['data'][0] == 0xA5:
                data = entry['data']
                console.print(f"    A5解析: 地址=0x{data[1]:02X}, 命令=0x{data[2]:02X}, 數據={data[4:12].hex().upper()}")
    
    async def main_menu(self):
        """主選單"""
        while True:
            console.print(f"\n[bold blue]🔧 DALY BMS 調試工具 - {self.mac_address}[/bold blue]")
            console.print("=" * 60)
            console.print("1. 發送原始命令")
            console.print("2. 互動式命令建構器")
            console.print("3. 啟動原始數據監控")
            console.print("4. 查看原始數據日誌")
            console.print("5. 清除數據日誌")
            console.print("6. 離開")
            
            choice = Prompt.ask("請選擇功能", choices=["1", "2", "3", "4", "5", "6"], default="6")
            
            if choice == "1":
                hex_input = Prompt.ask("輸入十六進制命令")
                if hex_input.strip():
                    await self.send_raw_command(hex_input)
                    
            elif choice == "2":
                await self.interactive_command_builder()
                
            elif choice == "3":
                duration = IntPrompt.ask("監控時間 (秒)", default=30)
                await self.start_raw_monitoring(duration)
                
            elif choice == "4":
                count = IntPrompt.ask("顯示筆數", default=20)
                self.display_raw_log(count)
                
            elif choice == "5":
                self.raw_data_log.clear()
                console.print("[green]✅ 數據日誌已清除[/green]")
                
            else:
                break
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python daly_debug_tool.py <MAC地址>")
        console.print("範例: python daly_debug_tool.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    debug_tool = DALYDebugTool(mac_address)
    
    try:
        # 建立連線
        if not await debug_tool.connect():
            return 1
        
        # 進入主選單
        await debug_tool.main_menu()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await debug_tool.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)