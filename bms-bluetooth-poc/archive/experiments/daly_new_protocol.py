#!/usr/bin/env python3
"""
DALY 新版協議測試工具
專門針對 H2.1_103E_30XF 硬體版本和 12_250416_K00T 軟體版本
測試各種可能的初始化和認證序列
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
from rich.progress import Progress, SpinnerColumn, TextColumn
from bleak import BleakClient, BleakScanner

console = Console()

class DALYNewProtocol:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值對
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.responses = []
        self.successful_commands = []
        
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
                
                # 嘗試設置 MTU
                try:
                    # 某些 BMS 需要更大的 MTU
                    if hasattr(self.client, '_mtu_size'):
                        self.client._mtu_size = 517
                        console.print(f"[dim]MTU 設置為 517[/dim]")
                except:
                    pass
                    
                return True
                
        except Exception as e:
            console.print(f"[red]連線失敗: {e}[/red]")
            return False
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if not data:
            return
        
        timestamp = datetime.now()
        self.responses.append({
            'timestamp': timestamp,
            'data': data,
            'hex': data.hex().upper(),
            'length': len(data)
        })
        
        # 實時顯示
        console.print(f"[green]🔔 收到響應: {data.hex().upper()} (長度: {len(data)})[/green]")
        
        # 分析響應
        self.analyze_response(data)
    
    def analyze_response(self, data: bytes):
        """分析響應數據"""
        if len(data) == 0:
            return
        
        # 檢查是否為回音
        if self.last_command and data == self.last_command:
            console.print(f"   [yellow]⚠️ 回音響應（與發送命令相同）[/yellow]")
            return
        
        # 檢查協議類型
        if data[0] == 0xA5:
            console.print(f"   [cyan]A5 協議響應[/cyan]")
            if len(data) == 13:
                self.parse_a5_response(data)
        elif data[0] == 0xD2:
            console.print(f"   [cyan]D2 協議響應[/cyan]")
            if len(data) >= 8:
                self.parse_d2_response(data)
        elif data[0] == 0x01 and len(data) == 13:
            console.print(f"   [cyan]可能是 BMS 響應（0x01 開頭）[/cyan]")
        else:
            console.print(f"   [dim]未知格式響應[/dim]")
        
        # 檢查是否包含實際數據
        if len(data) >= 8:
            # 檢查是否有非零數據
            has_data = any(b != 0 for b in data[4:])
            if has_data:
                console.print(f"   [green]✨ 包含實際數據！[/green]")
                self.successful_commands.append({
                    'command': self.last_command.hex() if self.last_command else "unknown",
                    'response': data.hex().upper()
                })
    
    def parse_a5_response(self, data: bytes):
        """解析 A5 協議響應"""
        if len(data) != 13:
            return
        
        cmd = data[2]
        payload = data[4:12]
        
        # 簡單解析
        if cmd == 0x90:  # 電壓電流SOC
            voltage = int.from_bytes(payload[0:2], 'big') / 10.0
            current_raw = int.from_bytes(payload[2:4], 'big')
            current = (current_raw - 30000) / 10.0
            soc = int.from_bytes(payload[4:6], 'big') / 10.0
            
            if voltage > 0 or (current_raw != 0 and current_raw != 30000) or soc > 0:
                console.print(f"   [green]📊 電壓:{voltage}V, 電流:{current}A, SOC:{soc}%[/green]")
    
    def parse_d2_response(self, data: bytes):
        """解析 D2 協議響應"""
        if len(data) < 8:
            return
        
        console.print(f"   [dim]D2 數據: {data[2:].hex().upper()}[/dim]")
    
    async def send_command(self, command: bytes, description: str = "") -> bool:
        """發送命令並等待響應"""
        try:
            self.last_command = command
            self.responses.clear()
            
            console.print(f"\n[cyan]📤 發送: {command.hex().upper()}[/cyan]")
            if description:
                console.print(f"   [dim]{description}[/dim]")
            
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, command, response=False)
            
            # 等待響應
            await asyncio.sleep(1.5)
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            
            return len(self.responses) > 0
            
        except Exception as e:
            console.print(f"[red]發送失敗: {e}[/red]")
            return False
    
    async def test_authentication_sequences(self):
        """測試各種認證序列"""
        console.print("\n[bold cyan]🔐 測試認證序列...[/bold cyan]")
        
        # 常見的 BMS 密碼
        passwords = ["123456", "000000", "111111", "654321", "admin", "daly"]
        
        for password in passwords:
            console.print(f"\n[yellow]測試密碼: {password}[/yellow]")
            
            # 嘗試不同的密碼格式
            # 格式 1: ASCII 直接發送
            pwd_bytes = password.encode('ascii')
            await self.send_command(pwd_bytes, f"ASCII 密碼: {password}")
            
            # 格式 2: 帶協議頭的密碼
            cmd = bytearray([0xA5, 0x40, 0x20, len(pwd_bytes)])
            cmd.extend(pwd_bytes)
            while len(cmd) < 12:
                cmd.append(0x00)
            checksum = sum(cmd) & 0xFF
            cmd.append(checksum)
            await self.send_command(bytes(cmd), f"A5 協議密碼: {password}")
            
            # 檢查是否有成功響應
            if self.successful_commands:
                console.print(f"[green]✅ 密碼 {password} 可能成功！[/green]")
                break
    
    async def test_initialization_sequences(self):
        """測試初始化序列"""
        console.print("\n[bold cyan]🚀 測試初始化序列...[/bold cyan]")
        
        # 各種可能的初始化命令
        init_sequences = [
            # Sinowealth 協議格式
            (bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77]), "Sinowealth 基本資訊"),
            (bytes([0xDD, 0xA5, 0x04, 0x00, 0xFF, 0xFC, 0x77]), "Sinowealth 電芯電壓"),
            (bytes([0xDD, 0xA5, 0x05, 0x00, 0xFF, 0xFB, 0x77]), "Sinowealth 版本"),
            
            # 簡單喚醒命令
            (bytes([0x00]), "空命令"),
            (bytes([0x01]), "簡單喚醒"),
            (bytes([0xFF]), "重置命令"),
            
            # 修改的 A5 協議（使用不同地址）
            (bytes.fromhex("A50190080000000000000000FE"), "A5 with 0x01 address"),
            (bytes.fromhex("A54090080000000000000000FD"), "A5 with 0x40 address"),
            (bytes.fromhex("A58090080000000000000000BD"), "A5 with 0x80 address"),
            
            # D2 新協議格式
            (bytes.fromhex("D203030000011234"), "D2 基本資訊"),
            (bytes.fromhex("D203900000000000"), "D2 電壓電流"),
            
            # 組合命令（先認證後查詢）
            (bytes.fromhex("00") + bytes.fromhex("A58090080000000000000000BD"), "組合命令"),
        ]
        
        for cmd, desc in init_sequences:
            success = await self.send_command(cmd, desc)
            
            if success and self.successful_commands:
                console.print(f"[green]✅ 命令成功: {desc}[/green]")
            
            await asyncio.sleep(0.5)
    
    async def test_advanced_protocols(self):
        """測試進階協議格式"""
        console.print("\n[bold cyan]🔬 測試進階協議...[/bold cyan]")
        
        # 建立各種可能的命令格式
        test_commands = []
        
        # 1. 帶長度的命令格式
        for cmd_id in [0x90, 0x93, 0x94, 0x95]:
            # 格式: 長度 + 命令ID + 數據
            packet = bytes([0x08, cmd_id, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            test_commands.append((packet, f"長度格式命令 0x{cmd_id:02X}"))
        
        # 2. CRC16 格式
        for cmd_id in [0x90, 0x93]:
            packet = bytearray([0xA5, 0x80, cmd_id, 0x08, 0x00, 0x00, 0x00, 0x00])
            # 簡單 CRC16 (實際應該用標準 CRC16 算法)
            crc = sum(packet) & 0xFFFF
            packet.extend([crc >> 8, crc & 0xFF])
            test_commands.append((bytes(packet), f"CRC16 格式命令 0x{cmd_id:02X}"))
        
        # 3. Modbus RTU 格式
        # 設備地址 + 功能碼 + 寄存器地址 + 寄存器數量 + CRC
        modbus_cmd = bytes([0x01, 0x03, 0x00, 0x90, 0x00, 0x08])
        # 添加簡化 CRC
        modbus_cmd += bytes([0x12, 0x34])
        test_commands.append((modbus_cmd, "Modbus RTU 格式"))
        
        # 4. 自定義握手序列
        handshake = bytes([0x5A, 0xA5, 0x00, 0x00, 0xFF, 0xFF])
        test_commands.append((handshake, "自定義握手"))
        
        for cmd, desc in test_commands:
            await self.send_command(cmd, desc)
            await asyncio.sleep(0.5)
    
    async def smart_protocol_discovery(self):
        """智能協議發現"""
        console.print("\n[bold green]🤖 智能協議發現模式...[/bold green]")
        
        # 第一步：發送各種起始位元組，看哪個有響應
        console.print("\n[cyan]步驟 1: 測試起始位元組[/cyan]")
        start_bytes = [0x00, 0x01, 0x5A, 0xA5, 0xD2, 0xDD, 0xFF]
        
        for start in start_bytes:
            cmd = bytes([start])
            console.print(f"測試起始位元組: 0x{start:02X}")
            success = await self.send_command(cmd, "")
            
            if success and len(self.responses) > 0:
                response = self.responses[0]['data']
                if response != cmd:  # 不是回音
                    console.print(f"[green]✅ 起始位元組 0x{start:02X} 有有效響應！[/green]")
            
            await asyncio.sleep(0.3)
        
        # 第二步：如果發現有效起始位元組，擴展測試
        if self.successful_commands:
            console.print("\n[cyan]步驟 2: 擴展成功的命令格式[/cyan]")
            
            for success_cmd in self.successful_commands[:3]:  # 測試前3個成功命令
                base_cmd = bytes.fromhex(success_cmd['command'])
                console.print(f"擴展命令: {base_cmd.hex()}")
                
                # 嘗試添加不同的命令碼
                for cmd_code in [0x90, 0x93, 0x94, 0x95]:
                    extended = base_cmd + bytes([cmd_code])
                    await self.send_command(extended, f"擴展命令碼 0x{cmd_code:02X}")
                    await asyncio.sleep(0.3)
    
    def generate_report(self):
        """生成測試報告"""
        console.print("\n" + "="*60)
        console.print("[bold blue]📊 協議測試報告[/bold blue]")
        console.print("="*60)
        
        if self.successful_commands:
            console.print(f"\n[green]✅ 發現 {len(self.successful_commands)} 個有效命令！[/green]")
            
            table = Table(title="成功的命令")
            table.add_column("命令", style="cyan")
            table.add_column("響應", style="green")
            
            for cmd_info in self.successful_commands[:5]:  # 顯示前5個
                table.add_row(cmd_info['command'][:20] + "...", cmd_info['response'][:20] + "...")
            
            console.print(table)
            
            console.print("\n[yellow]💡 建議：[/yellow]")
            console.print("1. 使用成功的命令格式進行進一步測試")
            console.print("2. 分析響應數據格式以了解協議結構")
            console.print("3. 嘗試修改成功命令的參數")
        else:
            console.print("\n[yellow]⚠️ 未發現明確的有效命令[/yellow]")
            console.print("\n[yellow]💡 建議：[/yellow]")
            console.print("1. 確認 Smart BMS app 正在連線")
            console.print("2. 使用嗅探工具捕獲 app 的實際通訊")
            console.print("3. 可能需要特殊的初始化時序")
        
        console.print("="*60)
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python daly_new_protocol.py <MAC地址> [模式]")
        console.print("模式: auth | init | advanced | smart | all")
        console.print("範例: python daly_new_protocol.py 41:18:12:01:37:71 all")
        return 1
    
    mac_address = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    tester = DALYNewProtocol(mac_address)
    tester.last_command = None
    
    console.print("[bold blue]🔬 DALY 新版協議測試工具[/bold blue]")
    console.print("="*60)
    console.print(f"目標設備: {mac_address}")
    console.print(f"測試模式: {mode}")
    console.print(f"硬體版本: H2.1_103E_30XF")
    console.print(f"軟體版本: 12_250416_K00T")
    console.print("")
    
    try:
        # 建立連線
        if not await tester.connect():
            return 1
        
        if mode == "auth" or mode == "all":
            await tester.test_authentication_sequences()
        
        if mode == "init" or mode == "all":
            await tester.test_initialization_sequences()
        
        if mode == "advanced" or mode == "all":
            await tester.test_advanced_protocols()
        
        if mode == "smart" or mode == "all":
            await tester.smart_protocol_discovery()
        
        # 生成報告
        tester.generate_report()
        
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