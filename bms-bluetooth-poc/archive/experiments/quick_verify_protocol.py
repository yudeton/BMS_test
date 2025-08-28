#!/usr/bin/env python3
"""
快速協議驗證工具
基於智能探測的結果，快速驗證發現的協議格式
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

class QuickProtocolVerifier:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值對
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.responses = []
        
        # 從智能探測發現的最佳命令
        self.discovered_commands = {
            "best_command": {
                "hex": "A58093080000000000000000C0",
                "description": "最佳命令 (得分50) - MOSFET狀態",
                "expected_features": ["18.9V電壓", "有意義數據"]
            }
        }
        
        # 基於最佳命令的變體測試
        self.test_commands = {
            "basic_info": "A58090080000000000000000BD",      # 基本資訊
            "mosfet_status": "A58093080000000000000000C0",    # MOSFET狀態（最佳）
            "system_status": "A58094080000000000000000C1",    # 系統狀態
            "cell_voltages": "A58095080000000000000000C2",    # 電芯電壓
            "temperatures": "A58096080000000000000000C3",     # 溫度
            "min_max_voltage": "A58091080000000000000000BE",  # 最大最小電壓
        }
    
    async def connect(self) -> bool:
        """建立藍牙連線"""
        try:
            console.print(f"[cyan]正在連線到 {self.mac_address}...[/cyan]")
            
            # 直接嘗試連接，不先掃描
            self.client = BleakClient(self.mac_address)
            await self.client.connect()
            
            if self.client.is_connected:
                self.is_connected = True
                console.print(f"[green]✅ 成功連線到 {self.mac_address}[/green]")
                return True
            else:
                console.print(f"[red]連線失敗[/red]")
                return False
                
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
    
    async def test_command(self, cmd_hex: str, description: str) -> Dict:
        """測試單個命令並分析響應"""
        try:
            command = bytes.fromhex(cmd_hex.replace(" ", ""))
            self.responses.clear()
            
            console.print(f"\n[cyan]📤 測試: {description}[/cyan]")
            console.print(f"   命令: {cmd_hex}")
            
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, command, response=False)
            
            # 等待響應
            await asyncio.sleep(1.5)
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            
            # 分析響應
            analysis = self.analyze_response(command, self.responses)
            
            # 顯示結果
            if analysis['has_real_data']:
                console.print(f"[green]✅ 發現真實數據！[/green]")
                if analysis['parsed_data']:
                    for key, value in analysis['parsed_data'].items():
                        console.print(f"   {key}: {value}")
            elif analysis['is_echo']:
                console.print(f"[yellow]⚠️ 回音響應[/yellow]")
            else:
                console.print(f"[red]❌ 無響應或無效數據[/red]")
            
            return analysis
            
        except Exception as e:
            console.print(f"[red]測試失敗: {e}[/red]")
            return {'error': str(e), 'has_real_data': False}
    
    def analyze_response(self, command: bytes, responses: List[Dict]) -> Dict:
        """分析響應數據"""
        analysis = {
            'command': command.hex().upper(),
            'has_real_data': False,
            'is_echo': False,
            'parsed_data': {},
            'raw_responses': []
        }
        
        if not responses:
            analysis['reason'] = 'no_response'
            return analysis
        
        for response in responses:
            data = response['data']
            analysis['raw_responses'].append(response['hex'])
            
            # 檢查是否為回音
            if data == command:
                analysis['is_echo'] = True
                continue
            
            # 檢查是否有真實數據
            if len(data) >= 8:
                # 檢查數據變化性
                unique_bytes = len(set(data))
                if unique_bytes > len(data) // 4:
                    analysis['has_real_data'] = True
                
                # 嘗試解析 A5 協議
                if data[0] == 0xA5 and len(data) == 13:
                    parsed = self.parse_a5_response(data)
                    if parsed:
                        analysis['parsed_data'].update(parsed)
                        analysis['has_real_data'] = True
        
        return analysis
    
    def parse_a5_response(self, data: bytes) -> Optional[Dict]:
        """解析 A5 協議響應"""
        if len(data) != 13:
            return None
        
        # 驗證校驗和
        calculated_checksum = sum(data[:12]) & 0xFF
        if calculated_checksum != data[12]:
            return {'checksum_error': True}
        
        cmd = data[2]
        payload = data[4:12]
        parsed = {}
        
        # 根據命令類型解析
        if cmd == 0x90:  # 基本資訊
            voltage = int.from_bytes(payload[0:2], 'big') / 10.0
            current_raw = int.from_bytes(payload[2:4], 'big')
            current = (current_raw - 30000) / 10.0
            soc = int.from_bytes(payload[4:6], 'big') / 10.0
            
            parsed = {
                'voltage': f"{voltage:.1f}V",
                'current': f"{current:.1f}A",
                'soc': f"{soc:.1f}%",
                'current_raw': f"0x{current_raw:04X}"
            }
        
        elif cmd == 0x93:  # MOSFET 狀態
            charge_mosfet = "開啟" if payload[0] == 1 else "關閉"
            discharge_mosfet = "開啟" if payload[1] == 1 else "關閉"
            bms_life = payload[2] if payload[2] != 0 else "未知"
            
            # 嘗試提取電壓信息（基於智能探測的發現）
            possible_voltages = []
            for i in range(len(payload) - 1):
                voltage = int.from_bytes(payload[i:i+2], 'big') / 10.0
                if 5.0 <= voltage <= 60.0:  # 合理的電壓範圍
                    possible_voltages.append(f"{voltage:.1f}V")
            
            parsed = {
                'charge_mosfet': charge_mosfet,
                'discharge_mosfet': discharge_mosfet,
                'bms_life': f"{bms_life}%" if isinstance(bms_life, int) else bms_life,
                'possible_voltages': possible_voltages if possible_voltages else ["無檢測到電壓"]
            }
        
        elif cmd == 0x94:  # 系統狀態
            parsed = {
                'cell_count': payload[0] if payload[0] != 0 else "未檢測",
                'temp_sensor_count': payload[1] if payload[1] != 0 else "未檢測",
                'system_state': f"0x{payload[4]:02X}" if len(payload) > 4 else "未知"
            }
        
        # 通用數據提取
        non_zero_bytes = [f"0x{b:02X}" for b in payload if b != 0]
        if non_zero_bytes:
            parsed['non_zero_data'] = non_zero_bytes
        
        return parsed if parsed else None
    
    async def comprehensive_test(self):
        """全面測試所有發現的命令"""
        console.print("\n[bold green]🚀 全面協議驗證測試[/bold green]")
        console.print("基於智能探測結果，測試所有相關命令\n")
        
        successful_commands = []
        
        for cmd_name, cmd_hex in self.test_commands.items():
            result = await self.test_command(cmd_hex, cmd_name)
            
            if result.get('has_real_data'):
                successful_commands.append({
                    'name': cmd_name,
                    'command': cmd_hex,
                    'result': result
                })
            
            await asyncio.sleep(0.5)  # 避免過快發送
        
        return successful_commands
    
    def generate_verification_report(self, successful_commands: List[Dict]):
        """生成驗證報告"""
        console.print("\n" + "="*70)
        console.print("[bold blue]📊 協議驗證報告[/bold blue]")
        console.print("="*70)
        
        if successful_commands:
            console.print(f"\n[green]✅ 成功驗證 {len(successful_commands)} 個命令！[/green]")
            
            table = Table(title="成功的命令")
            table.add_column("命令類型", style="cyan")
            table.add_column("十六進制", style="green")
            table.add_column("解析結果", style="yellow")
            
            for cmd_info in successful_commands:
                name = cmd_info['name']
                hex_cmd = cmd_info['command']
                parsed = cmd_info['result'].get('parsed_data', {})
                
                # 格式化解析結果
                parsed_str = ", ".join([f"{k}:{v}" for k, v in parsed.items()])
                if len(parsed_str) > 40:
                    parsed_str = parsed_str[:37] + "..."
                
                table.add_row(name, hex_cmd, parsed_str or "有數據但未解析")
            
            console.print(table)
            
            # 特別分析最佳命令
            best_cmd = next((cmd for cmd in successful_commands if cmd['name'] == 'mosfet_status'), None)
            if best_cmd:
                console.print(f"\n[green]🎯 最佳命令詳細分析 (MOSFET狀態):[/green]")
                parsed = best_cmd['result']['parsed_data']
                for key, value in parsed.items():
                    console.print(f"  {key}: {value}")
                
                # 檢查是否找到了智能探測提到的18.9V
                possible_voltages = parsed.get('possible_voltages', [])
                if any('18.9' in v or '18.8' in v or '19.' in v for v in possible_voltages):
                    console.print(f"[green]🎉 確認！找到智能探測預測的~18.9V電壓！[/green]")
        
        else:
            console.print(f"\n[red]❌ 未找到有效的協議命令[/red]")
            console.print("這可能意味著需要進一步的協議分析")
        
        # 提供下一步建議
        console.print(f"\n[yellow]💡 下一步建議:[/yellow]")
        if successful_commands:
            console.print("1. 使用成功的命令創建專用 BMS 通訊庫")
            console.print("2. 對比這些數據與 Smart BMS app 的顯示")
            console.print("3. 實現完整的 BMS 監控功能")
        else:
            console.print("1. 嘗試更多協議變體")
            console.print("2. 使用 HCI 日誌分析獲取準確協議")
            console.print("3. 檢查 BMS 是否需要特殊初始化")
        
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
        console.print("用法: python quick_verify_protocol.py <MAC地址>")
        console.print("範例: python quick_verify_protocol.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    
    verifier = QuickProtocolVerifier(mac_address)
    
    console.print("[bold blue]⚡ 快速協議驗證工具[/bold blue]")
    console.print("="*70)
    console.print(f"目標設備: {mac_address}")
    console.print("基於智能探測結果進行驗證")
    console.print(f"最佳命令: A58093...C0 (得分50)")
    console.print("")
    
    try:
        # 建立連線
        if not await verifier.connect():
            return 1
        
        # 執行全面測試
        successful = await verifier.comprehensive_test()
        
        # 生成驗證報告
        verifier.generate_verification_report(successful)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷驗證[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await verifier.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)