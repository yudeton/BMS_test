#!/usr/bin/env python3
"""
BMS 特徵值測試工具
系統化測試所有可能的數據特徵值
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from bleak import BleakClient, BleakScanner
from config import BLUETOOTH_CONNECT_RETRY, LOG_RAW_DATA, LOG_FILE

console = Console()

class CharacteristicTester:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        self.data_buffer = []
        self.received_count = 0
        self.last_receive_time = None
        self.start_time = None
        self.current_characteristic = None
        
    async def connect(self) -> bool:
        """建立藍牙連線"""
        for attempt in range(1, BLUETOOTH_CONNECT_RETRY + 1):
            console.print(f"[cyan]嘗試連線 (第 {attempt}/{BLUETOOTH_CONNECT_RETRY} 次)...[/cyan]")
            
            try:
                device = await BleakScanner.find_device_by_address(
                    self.mac_address,
                    timeout=5.0
                )
                
                if not device:
                    console.print(f"[yellow]找不到設備 {self.mac_address}[/yellow]")
                    continue
                
                self.client = BleakClient(self.mac_address)
                await self.client.connect()
                
                if self.client.is_connected:
                    self.is_connected = True
                    self.start_time = time.time()
                    console.print(f"[green]✅ 成功連線到 {self.mac_address}[/green]")
                    return True
                    
            except Exception as e:
                console.print(f"[red]連線失敗: {e}[/red]")
                
            if attempt < BLUETOOTH_CONNECT_RETRY:
                await asyncio.sleep(2)
        
        return False
    
    def get_all_characteristics(self):
        """取得所有特徵值列表"""
        if not self.client:
            return []
            
        characteristics = []
        services = self.client.services
        
        for service in services:
            for char in service.characteristics:
                characteristics.append({
                    'uuid': str(char.uuid),
                    'properties': list(char.properties),
                    'service_uuid': str(service.uuid)
                })
        
        return characteristics
    
    def handle_notification(self, sender, data: bytearray):
        """處理接收到的數據"""
        self.received_count += 1
        self.last_receive_time = time.time()
        
        # 分析數據
        analysis = self.analyze_can_data(data)
        
        timestamp = datetime.now()
        data_entry = {
            "timestamp": timestamp,
            "raw_data": data,
            "hex_data": data.hex(),
            "length": len(data),
            "can_analysis": analysis,
            "characteristic": self.current_characteristic
        }
        self.data_buffer.append(data_entry)
        
        # 保持緩衝區大小
        if len(self.data_buffer) > 100:
            self.data_buffer.pop(0)
        
        # 記錄到檔案
        if LOG_RAW_DATA:
            self.log_data(timestamp, data, analysis)
            
        # 即時顯示重要數據
        console.print(f"[green]📨 收到數據![/green] 長度:{len(data)} HEX:{data.hex()}")
        if analysis.get("is_can_format"):
            parsed = analysis.get("parsed_data", {})
            console.print(f"[cyan]🔋 CAN數據: {parsed.get('voltage', 'N/A')} {parsed.get('current', 'N/A')} {parsed.get('soc', 'N/A')}[/cyan]")
    
    def analyze_can_data(self, data: bytearray) -> dict:
        """分析數據是否符合 CAN 協議格式"""
        analysis = {
            "is_can_format": False,
            "message_type": "unknown",
            "parsed_data": {}
        }
        
        # 檢查是否為 8 bytes (CAN 協議標準長度)
        if len(data) == 8:
            analysis["is_can_format"] = True
            analysis["message_type"] = "potential_bms_report1"
            
            try:
                # 嘗試解析為 BMS 報文1格式（根據PDF文件）
                voltage = int.from_bytes(data[0:2], byteorder='big') * 0.1  # 電壓
                current = int.from_bytes(data[2:4], byteorder='big') * 0.1  # 電流  
                soc = int.from_bytes(data[4:6], byteorder='big') * 0.1      # SOC
                control = data[6]                                           # 控制
                status = data[7]                                            # 異常
                
                analysis["parsed_data"] = {
                    "voltage": f"{voltage:.1f}V",
                    "current": f"{current:.1f}A", 
                    "soc": f"{soc:.1f}%",
                    "control": f"0x{control:02X}",
                    "status": f"0x{status:02X}"
                }
            except Exception as e:
                analysis["parsed_data"]["error"] = str(e)
        
        return analysis
    
    def log_data(self, timestamp: datetime, data: bytearray, analysis: dict = None):
        """記錄數據到檔案"""
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{timestamp.isoformat()} | CHAR: {self.current_characteristic} | ")
                f.write(f"Length: {len(data)} | HEX: {data.hex()} | ")
                f.write(f"Bytes: {' '.join(f'{b:02X}' for b in data)}")
                
                if analysis and analysis.get("is_can_format"):
                    f.write(f" | CAN: {analysis['parsed_data']}")
                
                f.write("\n")
        except Exception as e:
            console.print(f"[yellow]記錄失敗: {e}[/yellow]")
    
    async def test_characteristic(self, char_uuid: str, test_duration: int = 60) -> dict:
        """測試指定特徵值"""
        self.current_characteristic = char_uuid
        self.received_count = 0
        self.data_buffer.clear()
        
        console.print(f"\n[bold yellow]🧪 測試特徵值: {char_uuid}[/bold yellow]")
        console.print(f"[dim]測試時間: {test_duration} 秒[/dim]")
        
        try:
            # 嘗試訂閱通知
            await self.client.start_notify(char_uuid, self.handle_notification)
            console.print(f"[green]✅ 成功訂閱通知[/green]")
            
            # 監聽指定時間
            start_time = time.time()
            last_report = start_time
            
            while time.time() - start_time < test_duration:
                await asyncio.sleep(1)
                
                # 每10秒報告一次進度
                if time.time() - last_report >= 10:
                    elapsed = int(time.time() - start_time)
                    console.print(f"[dim]進度: {elapsed}/{test_duration}秒 | 已接收: {self.received_count} 封包[/dim]")
                    last_report = time.time()
            
            # 停止通知
            await self.client.stop_notify(char_uuid)
            console.print(f"[yellow]測試完成，共接收 {self.received_count} 個封包[/yellow]")
            
            return {
                "characteristic": char_uuid,
                "packets_received": self.received_count,
                "test_duration": test_duration,
                "success": self.received_count > 0,
                "data_samples": self.data_buffer[-5:] if self.data_buffer else []
            }
            
        except Exception as e:
            console.print(f"[red]❌ 測試失敗: {e}[/red]")
            return {
                "characteristic": char_uuid,
                "packets_received": 0,
                "test_duration": test_duration,
                "success": False,
                "error": str(e)
            }
    
    async def read_characteristic(self, char_uuid: str) -> dict:
        """讀取指定特徵值"""
        try:
            value = await self.client.read_gatt_char(char_uuid)
            analysis = self.analyze_can_data(value)
            
            console.print(f"[green]📖 讀取特徵 {char_uuid}:[/green]")
            console.print(f"  長度: {len(value)} bytes")
            console.print(f"  HEX: {value.hex()}")
            console.print(f"  Bytes: {' '.join(f'{b:02X}' for b in value)}")
            
            if analysis.get("is_can_format"):
                console.print(f"  🔋 CAN數據: {analysis['parsed_data']}")
            
            return {
                "characteristic": char_uuid,
                "success": True,
                "data": value.hex(),
                "length": len(value),
                "analysis": analysis
            }
            
        except Exception as e:
            console.print(f"[red]❌ 讀取 {char_uuid} 失敗: {e}[/red]")
            return {
                "characteristic": char_uuid,
                "success": False,
                "error": str(e)
            }
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python characteristic_tester.py <MAC地址>")
        console.print("範例: python characteristic_tester.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    tester = CharacteristicTester(mac_address)
    
    console.print("[bold blue]🧪 BMS 特徵值測試工具[/bold blue]")
    console.print("=" * 50)
    console.print(f"目標設備: {mac_address}\n")
    
    try:
        # 建立連線
        if not await tester.connect():
            console.print("[red]無法建立連線[/red]")
            return 1
        
        # 取得所有特徵值
        characteristics = tester.get_all_characteristics()
        
        # 按優先順序測試通知特徵
        priority_chars = [
            "02f00000-0000-0000-0000-00000000ff04",  # 第2優先
            "0000fff1-0000-1000-8000-00805f9b34fb",  # 第3優先  
            "02f00000-0000-0000-0000-00000000ff02",  # 已測試過，再試一次
        ]
        
        test_results = []
        found_data = False
        
        console.print(f"\n[bold cyan]📋 開始測試 {len(priority_chars)} 個通知特徵...[/bold cyan]")
        
        for char_uuid in priority_chars:
            # 檢查特徵是否存在且支持通知
            char_info = next((c for c in characteristics if c['uuid'] == char_uuid), None)
            
            if not char_info:
                console.print(f"[yellow]⚠️ 特徵 {char_uuid} 不存在，跳過[/yellow]")
                continue
                
            if 'notify' not in char_info['properties']:
                console.print(f"[yellow]⚠️ 特徵 {char_uuid} 不支持通知，跳過[/yellow]")
                continue
            
            # 測試特徵值
            result = await tester.test_characteristic(char_uuid, test_duration=30)
            test_results.append(result)
            
            if result['success']:
                console.print(f"[green]🎉 找到數據來源: {char_uuid}[/green]")
                found_data = True
                break
        
        # 如果沒有找到數據，嘗試讀取所有可讀特徵
        if not found_data:
            console.print(f"\n[yellow]📖 通知特徵無數據，嘗試讀取所有可讀特徵...[/yellow]")
            
            readable_chars = [c for c in characteristics if 'read' in c['properties']]
            console.print(f"找到 {len(readable_chars)} 個可讀特徵")
            
            for char in readable_chars:
                await tester.read_characteristic(char['uuid'])
                await asyncio.sleep(0.5)  # 避免過快讀取
        
        # 顯示測試結果摘要
        console.print(f"\n[bold green]📊 測試結果摘要:[/bold green]")
        for result in test_results:
            status = "✅ 成功" if result['success'] else "❌ 失敗"
            console.print(f"  {result['characteristic']}: {status} ({result['packets_received']} 封包)")
        
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