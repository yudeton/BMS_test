#!/usr/bin/env python3
"""
BMS 藍牙連線測試
測試與 BMS 藍牙模組的連線，並接收原始數據
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from bleak import BleakClient, BleakScanner
from config import BLUETOOTH_CONNECT_RETRY, LOG_RAW_DATA, LOG_FILE

console = Console()

class BMSConnector:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        self.data_buffer = []
        self.received_count = 0
        self.last_receive_time = None
        self.start_time = None
        
    async def connect(self) -> bool:
        """建立藍牙連線"""
        for attempt in range(1, BLUETOOTH_CONNECT_RETRY + 1):
            console.print(f"[cyan]嘗試連線 (第 {attempt}/{BLUETOOTH_CONNECT_RETRY} 次)...[/cyan]")
            
            try:
                # 先確認設備存在
                device = await BleakScanner.find_device_by_address(
                    self.mac_address,
                    timeout=5.0
                )
                
                if not device:
                    console.print(f"[yellow]找不到設備 {self.mac_address}[/yellow]")
                    continue
                
                # 建立連線
                self.client = BleakClient(self.mac_address)
                await self.client.connect()
                
                if self.client.is_connected:
                    self.is_connected = True
                    self.start_time = time.time()
                    console.print(f"[green]✅ 成功連線到 {self.mac_address}[/green]")
                    
                    # 顯示設備資訊
                    await self.display_device_info()
                    return True
                    
            except Exception as e:
                console.print(f"[red]連線失敗: {e}[/red]")
                
            if attempt < BLUETOOTH_CONNECT_RETRY:
                await asyncio.sleep(2)
        
        return False
    
    async def display_device_info(self):
        """顯示設備資訊"""
        if not self.client:
            return
            
        try:
            # 獲取服務列表
            services = self.client.services
            
            console.print("\n[bold]📱 設備資訊:[/bold]")
            console.print(f"  MAC 地址: {self.mac_address}")
            console.print(f"  連線狀態: {'已連線' if self.is_connected else '未連線'}")
            console.print(f"  服務數量: {len(list(services))}")
            
            # 列出所有服務和特徵
            console.print("\n[bold]可用服務與特徵:[/bold]")
            for service in services:
                console.print(f"  服務 UUID: {service.uuid}")
                for char in service.characteristics:
                    properties = ", ".join(char.properties)
                    console.print(f"    └─ 特徵 UUID: {char.uuid} [{properties}]")
                    
        except Exception as e:
            console.print(f"[yellow]無法獲取設備資訊: {e}[/yellow]")
    
    async def find_data_characteristic(self):
        """尋找可能包含數據的特徵值"""
        if not self.client:
            return None
            
        try:
            services = self.client.services
            potential_chars = []
            
            console.print("\n[bold cyan]📋 分析所有特徵值：[/bold cyan]")
            
            # 探索所有服務和特徵
            for service in services:
                console.print(f"\n[yellow]服務 {service.uuid}:[/yellow]")
                
                for char in service.characteristics:
                    properties = ", ".join(char.properties)
                    console.print(f"  特徵: {char.uuid}")
                    console.print(f"    屬性: [{properties}]")
                    
                    # 收集可能的數據特徵
                    if "notify" in char.properties:
                        potential_chars.append((char.uuid, "notify"))
                        console.print(f"    [green]✓ 可通知 - 可能是數據來源[/green]")
                    elif "read" in char.properties:
                        potential_chars.append((char.uuid, "read"))
                        console.print(f"    [blue]📖 可讀取[/blue]")
            
            # 優先選擇 notify 特徵，因為 BMS 需要即時數據
            console.print(f"\n[cyan]找到 {len(potential_chars)} 個潛在特徵[/cyan]")
            
            for uuid, prop in potential_chars:
                if prop == "notify":
                    console.print(f"[green]選擇通知特徵: {uuid}[/green]")
                    return uuid
                    
            # 如果沒有 notify，嘗試第一個 read 特徵
            if potential_chars:
                uuid, prop = potential_chars[0]
                console.print(f"[yellow]選擇讀取特徵: {uuid}[/yellow]")
                return uuid
                        
        except Exception as e:
            console.print(f"[red]尋找特徵失敗: {e}[/red]")
            
        return None
    
    def handle_notification(self, sender, data: bytearray):
        """處理接收到的數據"""
        self.received_count += 1
        self.last_receive_time = time.time()
        
        # 分析數據是否符合 CAN 協議格式
        analysis = self.analyze_can_data(data)
        
        # 儲存數據
        timestamp = datetime.now()
        data_entry = {
            "timestamp": timestamp,
            "raw_data": data,
            "hex_data": data.hex(),
            "length": len(data),
            "can_analysis": analysis
        }
        self.data_buffer.append(data_entry)
        
        # 保持緩衝區大小
        if len(self.data_buffer) > 100:
            self.data_buffer.pop(0)
        
        # 記錄到檔案
        if LOG_RAW_DATA:
            self.log_data(timestamp, data, analysis)
    
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
                # 嘗試解析為 BMS 報文1格式
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
                f.write(f"{timestamp.isoformat()} | Length: {len(data)} | ")
                f.write(f"HEX: {data.hex()} | ")
                f.write(f"Bytes: {' '.join(f'{b:02X}' for b in data)}")
                
                if analysis and analysis.get("is_can_format"):
                    f.write(f" | CAN: {analysis['parsed_data']}")
                
                f.write("\n")
        except Exception as e:
            console.print(f"[yellow]記錄失敗: {e}[/yellow]")
    
    async def start_receiving(self):
        """開始接收數據"""
        if not self.client or not self.is_connected:
            console.print("[red]未連線，無法接收數據[/red]")
            return
        
        # 尋找數據特徵
        char_uuid = await self.find_data_characteristic()
        
        if not char_uuid:
            console.print("[yellow]未找到可用的數據特徵，嘗試讀取所有特徵...[/yellow]")
            await self.read_all_characteristics()
            return
        
        try:
            # 訂閱通知
            await self.client.start_notify(char_uuid, self.handle_notification)
            console.print(f"[green]開始接收數據...[/green]")
            
            # 持續顯示數據
            await self.display_live_data()
            
        except Exception as e:
            console.print(f"[red]接收數據失敗: {e}[/red]")
    
    async def read_all_characteristics(self):
        """讀取所有可讀的特徵值"""
        if not self.client:
            return
            
        services = self.client.services
        
        for service in services:
            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = await self.client.read_gatt_char(char.uuid)
                        console.print(f"[green]特徵 {char.uuid}:[/green]")
                        console.print(f"  HEX: {value.hex()}")
                        console.print(f"  Bytes: {' '.join(f'{b:02X}' for b in value)}")
                        
                        # 嘗試解析為字串
                        try:
                            text = value.decode('utf-8')
                            console.print(f"  Text: {text}")
                        except:
                            pass
                            
                    except Exception as e:
                        console.print(f"[yellow]無法讀取 {char.uuid}: {e}[/yellow]")
    
    async def display_live_data(self):
        """即時顯示接收的數據"""
        with Live(auto_refresh=True, refresh_per_second=2) as live:
            while self.is_connected:
                # 建立顯示表格
                table = Table(title="📡 即時數據接收", show_header=True)
                table.add_column("項目", style="cyan")
                table.add_column("數值", style="yellow")
                
                # 連線資訊
                uptime = int(time.time() - self.start_time) if self.start_time else 0
                table.add_row("連線時間", f"{uptime} 秒")
                table.add_row("接收封包數", str(self.received_count))
                
                # 接收頻率
                if self.last_receive_time and self.received_count > 1:
                    avg_interval = uptime / max(self.received_count - 1, 1)
                    table.add_row("平均接收間隔", f"{avg_interval:.2f} 秒")
                
                # 最新數據
                if self.data_buffer:
                    latest = self.data_buffer[-1]
                    table.add_row("", "")  # 空行
                    table.add_row("最新數據時間", latest["timestamp"].strftime("%H:%M:%S.%f")[:-3])
                    table.add_row("數據長度", f"{latest['length']} bytes")
                    table.add_row("HEX 數據", latest["hex_data"][:32] + ("..." if len(latest["hex_data"]) > 32 else ""))
                    
                    # 顯示 CAN 協議分析
                    if latest.get("can_analysis") and latest["can_analysis"].get("is_can_format"):
                        analysis = latest["can_analysis"]
                        table.add_row("", "")  # 空行
                        table.add_row("🔋 CAN 協議", f"✓ {analysis['message_type']}")
                        
                        parsed = analysis.get("parsed_data", {})
                        if "voltage" in parsed:
                            table.add_row("電壓", parsed["voltage"])
                        if "current" in parsed:
                            table.add_row("電流", parsed["current"])  
                        if "soc" in parsed:
                            table.add_row("SOC", parsed["soc"])
                        if "control" in parsed:
                            table.add_row("控制", parsed["control"])
                        if "status" in parsed:
                            table.add_row("狀態", parsed["status"])
                    
                    # 顯示最近5筆數據
                    recent_data_lines = []
                    for d in self.data_buffer[-5:]:
                        line = f"{d['timestamp'].strftime('%H:%M:%S')} | {d['hex_data'][:20]}..."
                        if d.get("can_analysis") and d["can_analysis"].get("is_can_format"):
                            can_data = d["can_analysis"]["parsed_data"]
                            if "voltage" in can_data and "soc" in can_data:
                                line += f" | {can_data['voltage']} {can_data['soc']}"
                        recent_data_lines.append(line)
                    
                    recent_data = "\n".join(recent_data_lines)
                    
                    panel = Panel(
                        recent_data,
                        title="最近接收的數據",
                        border_style="blue"
                    )
                    
                    layout = Layout()
                    layout.split_column(
                        Layout(table, size=12),
                        Layout(panel)
                    )
                    
                    live.update(layout)
                else:
                    live.update(table)
                
                await asyncio.sleep(0.5)
                
                # 檢查連線狀態
                if self.client and not self.client.is_connected:
                    self.is_connected = False
                    console.print("[red]連線已斷開[/red]")
                    break
    
    async def disconnect(self):
        """斷開連線"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main(mac_address: str):
    """主程式"""
    console.print("[bold blue]🔋 BMS 連線測試[/bold blue]")
    console.print("=" * 50)
    console.print(f"目標設備: {mac_address}\n")
    
    connector = BMSConnector(mac_address)
    
    try:
        # 建立連線
        if not await connector.connect():
            console.print("[red]無法建立連線[/red]")
            return 1
        
        # 開始接收數據
        await connector.start_receiving()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await connector.disconnect()
    
    # 顯示統計
    if connector.received_count > 0:
        console.print(f"\n[green]測試完成！共接收 {connector.received_count} 個封包[/green]")
        console.print(f"[dim]數據已保存到 {LOG_FILE}[/dim]")
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python connector.py <MAC地址>")
        console.print("範例: python connector.py AA:BB:CC:DD:EE:FF")
        sys.exit(1)
    
    mac_address = sys.argv[1]
    
    try:
        exit_code = asyncio.run(main(mac_address))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)