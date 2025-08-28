#!/usr/bin/env python3
"""
增強版 BMS 測試工具
探索不同的特徵組合和通訊模式
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from bleak import BleakClient, BleakScanner

console = Console()

class EnhancedBMSTester:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        self.characteristics = {}
        self.notification_data = {}
        
        # 不同的命令格式變體
        self.command_variants = {
            # 標準小象格式
            "xiaoxiang_basic": bytes.fromhex("DD A5 03 00 FF FD 77"),
            "xiaoxiang_cells": bytes.fromhex("DD A5 04 00 FF FC 77"),
            "xiaoxiang_hardware": bytes.fromhex("DD A5 05 00 FF FB 77"),
            
            # 簡化格式（可能的變體）
            "simple_basic": bytes.fromhex("03"),
            "simple_cells": bytes.fromhex("04"),
            "simple_hardware": bytes.fromhex("05"),
            
            # DALY 格式變體
            "daly_basic": bytes.fromhex("A5 40 90 08 00 00 00 00 00 00 00 00 4D"),
            "daly_cells": bytes.fromhex("A5 40 95 08 00 00 00 00 00 00 00 00 48"),
            
            # 其他可能格式
            "format_1": bytes.fromhex("AA 55 03"),
            "format_2": bytes.fromhex("68 03 00 68"),
            "wake_up": bytes.fromhex("00"),
            "init_1": bytes.fromhex("FF FF"),
            "init_2": bytes.fromhex("01 02 03"),
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
        console.print(f"\n[bold cyan]🔍 分析特徵值架構...[/bold cyan]")
        
        services = self.client.services
        
        for service in services:
            for char in service.characteristics:
                properties = list(char.properties)
                self.characteristics[str(char.uuid)] = {
                    'char': char,
                    'properties': properties,
                    'service_uuid': str(service.uuid)
                }
    
    def get_characteristic_pairs(self) -> List[Tuple[str, str]]:
        """獲取可能的命令-響應特徵對"""
        write_chars = []
        read_chars = []
        
        for uuid, info in self.characteristics.items():
            if 'write' in info['properties'] or 'write-without-response' in info['properties']:
                write_chars.append(uuid)
            if 'read' in info['properties'] or 'notify' in info['properties']:
                read_chars.append(uuid)
        
        # 生成所有可能的配對
        pairs = []
        for write_char in write_chars:
            for read_char in read_chars:
                pairs.append((write_char, read_char))
        
        return pairs
    
    def notification_handler(self, characteristic_uuid: str):
        """創建通知處理器"""
        def handler(sender, data):
            if not data:
                return
            
            timestamp = datetime.now()
            
            if characteristic_uuid not in self.notification_data:
                self.notification_data[characteristic_uuid] = []
            
            self.notification_data[characteristic_uuid].append({
                'timestamp': timestamp,
                'data': data,
                'hex': data.hex().upper()
            })
            
            console.print(f"[green]🔔 通知來自 {characteristic_uuid}: {data.hex().upper()}[/green]")
        
        return handler
    
    async def test_characteristic_pair(self, write_char: str, read_char: str, 
                                     cmd_name: str, cmd_data: bytes) -> Dict:
        """測試特定的特徵對"""
        try:
            console.print(f"\n[cyan]🧪 測試配對：{write_char[-4:]} → {read_char[-4:]}[/cyan]")
            console.print(f"[dim]命令：{cmd_name} = {cmd_data.hex().upper()}[/dim]")
            
            # 清空通知數據
            self.notification_data.clear()
            
            # 如果讀取特徵支持通知，先啟用通知
            read_info = self.characteristics[read_char]
            notification_enabled = False
            
            if 'notify' in read_info['properties']:
                try:
                    await self.client.start_notify(read_char, self.notification_handler(read_char))
                    notification_enabled = True
                    console.print(f"[green]✅ 啟用通知監聽[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ 無法啟用通知: {e}[/yellow]")
            
            # 發送命令
            await self.client.write_gatt_char(write_char, cmd_data, response=False)
            console.print(f"[cyan]📤 命令已發送[/cyan]")
            
            # 等待響應
            await asyncio.sleep(1.0)
            
            results = {
                'write_char': write_char,
                'read_char': read_char,
                'command': cmd_name,
                'command_hex': cmd_data.hex().upper(),
                'responses': []
            }
            
            # 嘗試讀取響應
            if 'read' in read_info['properties']:
                try:
                    response = await self.client.read_gatt_char(read_char)
                    if response and len(response) > 0:
                        results['responses'].append({
                            'type': 'read',
                            'data': response.hex().upper(),
                            'length': len(response),
                            'raw': response
                        })
                        console.print(f"[green]📥 讀取響應: {response.hex().upper()} ({len(response)} bytes)[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ 讀取失敗: {e}[/yellow]")
            
            # 檢查通知響應
            if notification_enabled and read_char in self.notification_data:
                for notif in self.notification_data[read_char]:
                    results['responses'].append({
                        'type': 'notification',
                        'data': notif['hex'],
                        'length': len(notif['data']),
                        'raw': notif['data'],
                        'timestamp': notif['timestamp']
                    })
            
            # 停用通知
            if notification_enabled:
                try:
                    await self.client.stop_notify(read_char)
                except:
                    pass
            
            # 分析響應
            if results['responses']:
                console.print(f"[green]✅ 收到 {len(results['responses'])} 個響應[/green]")
                for i, resp in enumerate(results['responses']):
                    console.print(f"  響應{i+1} ({resp['type']}): {resp['data']} ({resp['length']} bytes)")
                    
                    # 嘗試解析
                    if resp['length'] >= 8:  # 可能是有效數據
                        parsed = self.try_parse_response(resp['raw'])
                        if parsed:
                            console.print(f"  [green]可能解析: {parsed}[/green]")
            else:
                console.print(f"[yellow]⚠️ 無響應[/yellow]")
            
            return results
            
        except Exception as e:
            console.print(f"[red]❌ 測試失敗: {e}[/red]")
            return {
                'write_char': write_char,
                'read_char': read_char,
                'command': cmd_name,
                'error': str(e)
            }
    
    def try_parse_response(self, data: bytes) -> Optional[Dict]:
        """嘗試解析響應數據"""
        if len(data) < 4:
            return None
        
        try:
            # 檢查是否為小象協議響應
            if data[0] == 0xDD:
                cmd_type = data[1]
                if cmd_type == 0x03:  # 基本資訊
                    if len(data) >= 20:
                        voltage = int.from_bytes(data[4:6], 'big') / 100.0
                        current = int.from_bytes(data[6:8], 'big', signed=True) / 100.0
                        return {
                            'type': 'xiaoxiang_basic',
                            'voltage': f'{voltage:.2f}V',
                            'current': f'{current:.2f}A'
                        }
                elif cmd_type == 0x04:  # 單體電壓
                    cells = []
                    for i in range(4, len(data)-3, 2):
                        if i+1 < len(data):
                            cell_v = int.from_bytes(data[i:i+2], 'big') / 1000.0
                            cells.append(f'{cell_v:.3f}V')
                    if cells:
                        return {
                            'type': 'xiaoxiang_cells',
                            'cells': cells[:8]  # 前8串
                        }
            
            # 檢查其他可能格式
            if len(data) >= 8:
                # 嘗試直接解析為電壓電流
                val1 = int.from_bytes(data[0:2], 'big')
                val2 = int.from_bytes(data[2:4], 'big')
                val3 = int.from_bytes(data[4:6], 'big')
                
                # 合理的電壓範圍 (20-60V)
                if 2000 <= val1 <= 6000:
                    return {
                        'type': 'raw_voltage',
                        'voltage': f'{val1/100:.2f}V',
                        'value2': val2,
                        'value3': val3
                    }
            
            return None
            
        except Exception:
            return None
    
    async def comprehensive_test(self):
        """綜合測試所有配對和命令"""
        console.print(f"\n[bold green]🚀 開始綜合測試...[/bold green]")
        
        # 獲取所有可能的特徵對
        pairs = self.get_characteristic_pairs()
        console.print(f"[cyan]找到 {len(pairs)} 個可能的特徵配對[/cyan]")
        
        successful_tests = []
        
        # 測試重點配對
        priority_pairs = [
            ("02f00000-0000-0000-0000-00000000ff01", "02f00000-0000-0000-0000-00000000ff02"),
            ("02f00000-0000-0000-0000-00000000ff05", "02f00000-0000-0000-0000-00000000ff04"),
            ("0000fff2-0000-1000-8000-00805f9b34fb", "0000fff1-0000-1000-8000-00805f9b34fb"),
        ]
        
        # 先測試優先配對
        console.print(f"\n[cyan]🎯 測試優先配對...[/cyan]")
        for write_char, read_char in priority_pairs:
            if write_char in self.characteristics and read_char in self.characteristics:
                console.print(f"\n[yellow]--- 優先測試: {write_char[-4:]} → {read_char[-4:]} ---[/yellow]")
                
                # 測試多個命令
                for cmd_name, cmd_data in list(self.command_variants.items())[:5]:
                    result = await self.test_characteristic_pair(write_char, read_char, cmd_name, cmd_data)
                    
                    if result.get('responses'):
                        successful_tests.append(result)
                        # 如果找到有效響應，深入測試這個配對
                        if any(r['length'] > 2 for r in result['responses']):
                            console.print(f"[green]🎉 發現有效配對！深入測試...[/green]")
                            await self.deep_test_pair(write_char, read_char)
        
        # 如果優先配對沒有結果，測試其他配對
        if not successful_tests:
            console.print(f"\n[yellow]📋 測試其他配對（前10個）...[/yellow]")
            
            for i, (write_char, read_char) in enumerate(pairs[:10]):
                console.print(f"\n[yellow]--- 測試 {i+1}/10: {write_char[-4:]} → {read_char[-4:]} ---[/yellow]")
                
                # 只測試標準命令
                result = await self.test_characteristic_pair(
                    write_char, read_char, 
                    "xiaoxiang_basic", self.command_variants["xiaoxiang_basic"]
                )
                
                if result.get('responses') and any(r['length'] > 2 for r in result['responses']):
                    successful_tests.append(result)
                    console.print(f"[green]🎉 發現有效配對！[/green]")
                    break
        
        return successful_tests
    
    async def deep_test_pair(self, write_char: str, read_char: str):
        """深入測試有效的配對"""
        console.print(f"\n[bold green]🔬 深入測試配對: {write_char[-4:]} → {read_char[-4:]}[/bold green]")
        
        # 測試所有命令變體
        for cmd_name, cmd_data in self.command_variants.items():
            console.print(f"\n[cyan]測試命令: {cmd_name}[/cyan]")
            result = await self.test_characteristic_pair(write_char, read_char, cmd_name, cmd_data)
            
            if result.get('responses'):
                for resp in result['responses']:
                    if resp['length'] > 4:  # 可能包含有用數據
                        # 詳細分析
                        console.print(f"[green]📊 詳細分析 {resp['length']} bytes 數據:[/green]")
                        raw_data = resp['raw']
                        
                        # 十六進制顯示
                        hex_str = ' '.join(f'{b:02X}' for b in raw_data)
                        console.print(f"  HEX: {hex_str}")
                        
                        # ASCII 顯示（如果可能）
                        try:
                            ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in raw_data)
                            console.print(f"  ASCII: {ascii_str}")
                        except:
                            pass
                        
                        # 各種解析嘗試
                        self.analyze_data_patterns(raw_data)
            
            await asyncio.sleep(0.5)  # 避免過快發送
    
    def analyze_data_patterns(self, data: bytes):
        """分析數據模式"""
        if len(data) < 4:
            return
        
        console.print(f"  [dim]數據分析:[/dim]")
        
        # 嘗試不同的解釋
        interpretations = []
        
        # 16位大端整數
        for i in range(0, min(len(data)-1, 8), 2):
            val = int.from_bytes(data[i:i+2], 'big')
            interpretations.append(f"[{i}:{i+2}] = {val} (0x{val:04X})")
        
        # 檢查是否可能是電壓值
        for i, interp in enumerate(interpretations[:4]):
            console.print(f"    {interp}")
        
        # 檢查合理的電池數據範圍
        if len(data) >= 8:
            val1 = int.from_bytes(data[0:2], 'big')
            val2 = int.from_bytes(data[2:4], 'big') 
            val3 = int.from_bytes(data[4:6], 'big')
            
            possibilities = []
            
            # 電壓檢查 (通常 20-60V，以 10mV 為單位)
            if 2000 <= val1 <= 6000:
                possibilities.append(f"可能電壓: {val1/100:.2f}V")
            
            # 電流檢查 (±100A，以 10mA 為單位)
            if abs(val2) <= 10000:
                possibilities.append(f"可能電流: {val2/100:.2f}A")
            
            # SOC 檢查 (0-100%，以 0.1% 為單位)
            if 0 <= val3 <= 1000:
                possibilities.append(f"可能SOC: {val3/10:.1f}%")
            
            if possibilities:
                console.print(f"  [green]可能解釋: {', '.join(possibilities)}[/green]")
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python enhanced_bms_tester.py <MAC地址>")
        console.print("範例: python enhanced_bms_tester.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    tester = EnhancedBMSTester(mac_address)
    
    console.print("[bold blue]🔬 增強版 BMS 協議測試工具[/bold blue]")
    console.print("=" * 60)
    console.print(f"目標設備: {mac_address}")
    console.print("測試策略: 多重特徵配對 + 多種命令格式\n")
    
    try:
        # 建立連線
        if not await tester.connect():
            return 1
        
        # 綜合測試
        successful_tests = await tester.comprehensive_test()
        
        # 顯示結果摘要
        console.print(f"\n[bold green]📊 測試結果摘要:[/bold green]")
        
        if successful_tests:
            console.print(f"[green]✅ 成功測試: {len(successful_tests)} 個配對響應[/green]")
            
            for test in successful_tests:
                console.print(f"\n[cyan]配對: {test['write_char'][-4:]} → {test['read_char'][-4:]}[/cyan]")
                console.print(f"命令: {test['command']}")
                for resp in test['responses']:
                    console.print(f"  響應: {resp['data']} ({resp['length']} bytes)")
        else:
            console.print(f"[yellow]⚠️ 未找到有效的數據響應[/yellow]")
            console.print("可能需要：")
            console.print("1. 不同的命令格式")
            console.print("2. 特定的初始化序列") 
            console.print("3. 查閱 BMS 手冊了解專用協議")
        
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