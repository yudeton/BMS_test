#!/usr/bin/env python3
"""
協議暴力測試工具
系統性測試所有可能的 DALY BMS 協議格式
直接找出能獲取真實數據的命令格式
"""

import asyncio
import sys
import time
import struct
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Set
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from bleak import BleakClient, BleakScanner

console = Console()

class ProtocolBruteForce:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值對
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        # 測試結果
        self.successful_protocols = []
        self.responses = []
        self.tested_commands = set()
        
        # 定義已知的協議變體
        self.protocol_variants = self._initialize_protocol_variants()
    
    def _initialize_protocol_variants(self) -> List[Dict]:
        """初始化所有已知的協議變體"""
        variants = []
        
        # 1. 標準 DALY A5 協議
        variants.append({
            'name': 'DALY Standard A5',
            'format': 'A5',
            'create_func': self._create_a5_command,
            'commands': [0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98]
        })
        
        # 2. DALY D2 新協議
        variants.append({
            'name': 'DALY New D2',
            'format': 'D2', 
            'create_func': self._create_d2_command,
            'commands': [0x03, 0x04, 0x05, 0x90, 0x93, 0x94]
        })
        
        # 3. Sinowealth (JBD/Xiaoxiang) 協議
        variants.append({
            'name': 'Sinowealth JBD',
            'format': 'DD',
            'create_func': self._create_sinowealth_command,
            'commands': [0x03, 0x04, 0x05, 0x06]
        })
        
        # 4. Modbus RTU 格式
        variants.append({
            'name': 'Modbus RTU',
            'format': 'MODBUS',
            'create_func': self._create_modbus_command,
            'commands': [0x03, 0x04, 0x06]
        })
        
        # 5. 簡化 DALY 協議（無校驗和）
        variants.append({
            'name': 'DALY Simple',
            'format': 'SIMPLE',
            'create_func': self._create_simple_command,
            'commands': [0x90, 0x93, 0x94, 0x95]
        })
        
        # 6. 原始 CAN 格式
        variants.append({
            'name': 'CAN Format',
            'format': 'CAN',
            'create_func': self._create_can_command,
            'commands': [0x1806E5F4, 0x18FF50E5]  # 從您的 PDF 文檔
        })
        
        return variants
    
    def _create_a5_command(self, command: int, variant: int = 0) -> bytes:
        """創建 A5 協議命令，包含變體"""
        addresses = [0x80, 0x40, 0x01]  # 不同的主機地址
        addr = addresses[variant % len(addresses)]
        
        packet = bytearray(13)
        packet[0] = 0xA5
        packet[1] = addr
        packet[2] = command
        packet[3] = 0x08
        # packet[4:12] = 0x00  # 數據部分保持為零
        
        checksum = sum(packet[:12]) & 0xFF
        packet[12] = checksum
        
        return bytes(packet)
    
    def _create_d2_command(self, command: int, variant: int = 0) -> bytes:
        """創建 D2 協議命令"""
        packet = bytearray(8)
        packet[0] = 0xD2
        packet[1] = 0x03
        packet[2] = command
        packet[3] = 0x00
        packet[4] = 0x00
        packet[5] = 0x01
        
        # 簡化 CRC16
        crc = (sum(packet[:6]) * variant + 0x1234) & 0xFFFF
        packet[6] = (crc >> 8) & 0xFF
        packet[7] = crc & 0xFF
        
        return bytes(packet)
    
    def _create_sinowealth_command(self, command: int, variant: int = 0) -> bytes:
        """創建 Sinowealth (JBD) 協議命令"""
        packet = bytearray(7)
        packet[0] = 0xDD
        packet[1] = 0xA5
        packet[2] = command
        packet[3] = 0x00
        packet[4] = 0xFF
        packet[5] = 0xFF - command
        packet[6] = 0x77
        
        return bytes(packet)
    
    def _create_modbus_command(self, function: int, variant: int = 0) -> bytes:
        """創建 Modbus RTU 命令"""
        device_ids = [0x01, 0x02, 0x10]  # 不同設備 ID
        device_id = device_ids[variant % len(device_ids)]
        
        packet = bytearray(8)
        packet[0] = device_id
        packet[1] = function
        packet[2] = 0x00  # 寄存器地址高位
        packet[3] = 0x90  # 寄存器地址低位
        packet[4] = 0x00  # 寄存器數量高位
        packet[5] = 0x08  # 寄存器數量低位
        
        # 簡化 CRC16
        crc = 0x1234 + device_id + function
        packet[6] = (crc >> 8) & 0xFF
        packet[7] = crc & 0xFF
        
        return bytes(packet)
    
    def _create_simple_command(self, command: int, variant: int = 0) -> bytes:
        """創建簡化命令格式"""
        formats = [
            [0x5A, command, 0x00, 0x00],  # 格式 1
            [command, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # 格式 2
            [0xFF, command, 0xFE],  # 格式 3
        ]
        
        format_idx = variant % len(formats)
        return bytes(formats[format_idx])
    
    def _create_can_command(self, can_id: int, variant: int = 0) -> bytes:
        """創建 CAN 格式命令（基於您的 PDF）"""
        if can_id == 0x1806E5F4:  # Report 1
            # 請求報告 1 的數據
            return bytes([0x18, 0x06, 0xE5, 0xF4, 0x01, 0x00, 0x00, 0x00])
        elif can_id == 0x18FF50E5:  # Report 2  
            # 請求報告 2 的數據
            return bytes([0x18, 0xFF, 0x50, 0xE5, 0x02, 0x00, 0x00, 0x00])
        else:
            return bytes([0x18, 0x00, 0x00, 0x00, can_id & 0xFF, 0x00, 0x00, 0x00])
    
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
        
        self.responses.append({
            'timestamp': datetime.now(),
            'data': data,
            'hex': data.hex().upper(),
            'length': len(data)
        })
    
    def _is_echo_response(self, sent_command: bytes, response: bytes) -> bool:
        """檢查是否為回音響應"""
        return sent_command == response
    
    def _has_meaningful_data(self, data: bytes) -> bool:
        """檢查是否包含有意義的數據"""
        if len(data) < 4:
            return False
        
        # 檢查是否有非零數據（除了協議頭）
        data_portion = data[3:] if len(data) > 3 else data[1:]
        non_zero_bytes = sum(1 for b in data_portion if b != 0)
        
        # 如果超過 1/4 的數據不為零，認為是有意義的數據
        return non_zero_bytes > len(data_portion) // 4
    
    async def test_protocol_variant(self, variant: Dict, max_tests: int = 30) -> List[Dict]:
        """測試單個協議變體"""
        console.print(f"\n[cyan]🧪 測試 {variant['name']} 協議...[/cyan]")
        
        successful = []
        tested = 0
        
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # 計算總測試數量
            total_tests = min(len(variant['commands']) * 3, max_tests)  # 每個命令測試3個變體
            task = progress.add_task(f"測試 {variant['name']}", total=total_tests)
            
            for command in variant['commands']:
                if tested >= max_tests:
                    break
                
                # 測試每個命令的多個變體
                for variant_num in range(3):  # 測試3個變體
                    if tested >= max_tests:
                        break
                    
                    try:
                        # 創建命令
                        cmd_bytes = variant['create_func'](command, variant_num)
                        cmd_hex = cmd_bytes.hex().upper()
                        
                        # 避免重複測試
                        if cmd_hex in self.tested_commands:
                            tested += 1
                            progress.advance(task, 1)
                            continue
                        
                        self.tested_commands.add(cmd_hex)
                        
                        # 發送命令
                        self.responses.clear()
                        
                        await self.client.start_notify(self.read_char, self.notification_handler)
                        await self.client.write_gatt_char(self.write_char, cmd_bytes, response=False)
                        await asyncio.sleep(0.8)  # 稍短的等待時間
                        await self.client.stop_notify(self.read_char)
                        
                        # 分析響應
                        for response in self.responses:
                            response_data = response['data']
                            
                            # 檢查是否為有效響應
                            if not self._is_echo_response(cmd_bytes, response_data):
                                if self._has_meaningful_data(response_data):
                                    success_info = {
                                        'protocol': variant['name'],
                                        'command': cmd_hex,
                                        'response': response['hex'],
                                        'meaningful': True,
                                        'timestamp': response['timestamp']
                                    }
                                    successful.append(success_info)
                                    
                                    console.print(f"[green]✅ 發現有效響應！[/green]")
                                    console.print(f"   命令: {cmd_hex}")
                                    console.print(f"   響應: {response['hex']}")
                        
                        tested += 1
                        progress.advance(task, 1)
                        
                    except Exception as e:
                        console.print(f"[red]測試失敗: {e}[/red]")
                        tested += 1
                        progress.advance(task, 1)
                        continue
        
        return successful
    
    async def run_brute_force_test(self):
        """執行暴力測試"""
        console.print("\n[bold yellow]🚀 開始協議暴力測試...[/bold yellow]")
        console.print("[dim]將系統性測試所有已知協議格式[/dim]")
        
        all_successful = []
        
        for variant in self.protocol_variants:
            try:
                successful = await self.test_protocol_variant(variant)
                all_successful.extend(successful)
                
                # 如果找到成功的協議，額外測試
                if successful:
                    console.print(f"[green]🎉 {variant['name']} 協議有響應！[/green]")
                    
                    # 對成功的協議進行更深入測試
                    await self.deep_test_successful_protocol(variant, successful[0])
                
                # 短暫休息避免過載
                await asyncio.sleep(0.5)
                
            except Exception as e:
                console.print(f"[red]協議 {variant['name']} 測試失敗: {e}[/red]")
                continue
        
        self.successful_protocols = all_successful
    
    async def deep_test_successful_protocol(self, variant: Dict, success_example: Dict):
        """對成功的協議進行深入測試"""
        console.print(f"\n[yellow]🔍 深入測試成功協議: {variant['name']}[/yellow]")
        
        # 基於成功的命令，測試更多命令碼
        additional_commands = range(0x80, 0xA0)  # 測試更多命令範圍
        
        tested = 0
        for cmd in additional_commands:
            if tested > 10:  # 限制深入測試的數量
                break
            
            try:
                cmd_bytes = variant['create_func'](cmd, 0)
                cmd_hex = cmd_bytes.hex().upper()
                
                if cmd_hex in self.tested_commands:
                    continue
                
                self.tested_commands.add(cmd_hex)
                
                # 發送並測試
                self.responses.clear()
                await self.client.start_notify(self.read_char, self.notification_handler)
                await self.client.write_gatt_char(self.write_char, cmd_bytes, response=False)
                await asyncio.sleep(0.8)
                await self.client.stop_notify(self.read_char)
                
                # 檢查響應
                for response in self.responses:
                    if not self._is_echo_response(cmd_bytes, response['data']):
                        if self._has_meaningful_data(response['data']):
                            console.print(f"[green]✨ 額外發現: 0x{cmd:02X} → {response['hex']}[/green]")
                            
                            self.successful_protocols.append({
                                'protocol': variant['name'] + ' (深入)',
                                'command': cmd_hex,
                                'response': response['hex'],
                                'meaningful': True,
                                'timestamp': response['timestamp']
                            })
                
                tested += 1
                
            except Exception as e:
                console.print(f"[red]深入測試失敗: {e}[/red]")
                continue
    
    def generate_detailed_report(self):
        """生成詳細測試報告"""
        console.print("\n" + "="*70)
        console.print("[bold blue]📊 協議暴力測試詳細報告[/bold blue]")
        console.print("="*70)
        
        console.print(f"\n[cyan]📈 測試統計:[/cyan]")
        console.print(f"  測試的命令總數: {len(self.tested_commands)}")
        console.print(f"  成功的協議數: {len(self.successful_protocols)}")
        console.print(f"  測試的協議變體: {len(self.protocol_variants)}")
        
        if self.successful_protocols:
            console.print(f"\n[green]✅ 發現的有效協議:[/green]")
            
            # 按協議分組
            protocol_groups = {}
            for success in self.successful_protocols:
                protocol_name = success['protocol']
                if protocol_name not in protocol_groups:
                    protocol_groups[protocol_name] = []
                protocol_groups[protocol_name].append(success)
            
            for protocol_name, successes in protocol_groups.items():
                console.print(f"\n[yellow]{protocol_name}:[/yellow]")
                
                table = Table(title=f"{protocol_name} 成功命令")
                table.add_column("命令", style="cyan", width=20)
                table.add_column("響應", style="green", width=30)
                table.add_column("時間", style="dim", width=15)
                
                for success in successes[:5]:  # 顯示前5個
                    timestamp_str = success['timestamp'].strftime("%H:%M:%S")
                    table.add_row(
                        success['command'][:18] + "...",
                        success['response'][:28] + "...",
                        timestamp_str
                    )
                
                console.print(table)
        
        else:
            console.print(f"\n[red]❌ 未發現有效協議[/red]")
            console.print("\n[yellow]💡 可能原因:[/yellow]")
            console.print("  1. BMS 使用未知的專有協議")
            console.print("  2. 需要特殊的初始化序列")
            console.print("  3. 需要認證或配對")
            console.print("  4. 協議格式與已知變體不同")
        
        # 建議後續行動
        console.print(f"\n[yellow]🎯 建議後續行動:[/yellow]")
        if self.successful_protocols:
            console.print("  1. 分析成功協議的數據格式")
            console.print("  2. 創建專用的協議實現")
            console.print("  3. 測試更多命令以獲取完整數據")
        else:
            console.print("  1. 嘗試 Android HCI 日誌捕獲")
            console.print("  2. 使用智能協議探測工具")
            console.print("  3. 聯繫 DALY 獲取協議文檔")
        
        console.print("="*70)
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python protocol_brute_force.py <MAC地址>")
        console.print("範例: python protocol_brute_force.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    
    tester = ProtocolBruteForce(mac_address)
    
    console.print("[bold blue]💥 DALY BMS 協議暴力測試工具[/bold blue]")
    console.print("="*70)
    console.print(f"目標設備: {mac_address}")
    console.print(f"協議變體: {len(tester.protocol_variants)} 種")
    console.print("策略: 系統性測試所有已知協議格式")
    console.print("")
    
    try:
        # 建立連線
        if not await tester.connect():
            return 1
        
        # 執行暴力測試
        await tester.run_brute_force_test()
        
        # 生成詳細報告
        tester.generate_detailed_report()
        
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