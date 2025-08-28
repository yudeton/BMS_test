#!/usr/bin/env python3
"""
BMS 即時監控程式
整合藍牙連線與 CAN 協議解析，提供即時監控功能
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from bleak import BleakClient, BleakScanner
from can_parser import CANParser
from config import (
    BLUETOOTH_CONNECT_RETRY,
    DATA_RECEIVE_INTERVAL,
    VOLTAGE_WARNING_LOW,
    VOLTAGE_WARNING_HIGH,
    SOC_WARNING_LOW,
    CURRENT_WARNING_HIGH,
    LOG_FILE
)

console = Console()

class BMSMonitor:
    """BMS 即時監控器"""
    
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.parser = CANParser()
        self.is_connected = False
        self.monitoring = False
        
        # 統計數據
        self.start_time = None
        self.received_count = 0
        self.parsed_count = 0
        self.error_count = 0
        self.last_receive_time = None
        
        # 最新數據
        self.latest_data = {}
        self.alerts = []
        
    async def connect(self) -> bool:
        """建立藍牙連線"""
        for attempt in range(1, BLUETOOTH_CONNECT_RETRY + 1):
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
                console.print(f"[red]連線失敗 (第 {attempt} 次): {e}[/red]")
                
            if attempt < BLUETOOTH_CONNECT_RETRY:
                await asyncio.sleep(2)
        
        return False
    
    def handle_notification(self, sender, data: bytearray):
        """處理接收到的數據通知"""
        self.received_count += 1
        self.last_receive_time = time.time()
        
        # 解析數據
        try:
            parsed = self.parser.parse(data)
            
            if parsed["parsed"]:
                self.parsed_count += 1
                self.latest_data = parsed
                self.check_alerts(parsed)
                
                # 記錄到檔案
                self.log_data(datetime.now(), data, parsed)
            else:
                self.error_count += 1
                
        except Exception as e:
            self.error_count += 1
            console.print(f"[red]解析錯誤: {e}[/red]")
    
    def check_alerts(self, parsed_data: dict):
        """檢查告警條件"""
        if not parsed_data.get("data"):
            return
        
        data = parsed_data["data"]
        new_alerts = []
        
        # 檢查電壓
        if "max_voltage" in data:
            voltage_str = data["max_voltage"].split()[0]
            voltage = float(voltage_str)
            
            if voltage < VOLTAGE_WARNING_LOW:
                new_alerts.append(f"⚠️ 低電壓警告: {voltage:.1f}V")
            elif voltage > VOLTAGE_WARNING_HIGH:
                new_alerts.append(f"⚠️ 高電壓警告: {voltage:.1f}V")
        
        # 檢查 SOC
        if "soc" in data:
            soc_str = data["soc"].split()[0]
            soc = float(soc_str)
            
            if soc < SOC_WARNING_LOW:
                new_alerts.append(f"⚠️ 低電量警告: {soc:.1f}%")
        
        # 檢查電流
        if "max_current" in data:
            current_str = data["max_current"].split()[0]
            current = float(current_str)
            
            if current > CURRENT_WARNING_HIGH:
                new_alerts.append(f"⚠️ 高電流警告: {current:.1f}A")
        
        # 檢查異常狀態
        if data.get("status") == "異常":
            new_alerts.append("🚨 電池組異常!")
        
        # 更新告警列表
        for alert in new_alerts:
            if alert not in self.alerts:
                self.alerts.append(alert)
                if len(self.alerts) > 5:
                    self.alerts.pop(0)
    
    def log_data(self, timestamp: datetime, raw_data: bytes, parsed: dict):
        """記錄數據到檔案"""
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n{timestamp.isoformat()}\n")
                f.write(f"Raw: {raw_data.hex()}\n")
                if parsed.get("data"):
                    f.write(f"Parsed: {parsed['data']}\n")
        except Exception:
            pass
    
    def create_display(self) -> Layout:
        """創建顯示介面"""
        layout = Layout()
        
        # 標題
        title = Panel(
            Text("🔋 BMS 即時監控系統", justify="center", style="bold cyan"),
            border_style="blue"
        )
        
        # 連線狀態
        uptime = int(time.time() - self.start_time) if self.start_time else 0
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status_table = Table(show_header=False, box=None)
        status_table.add_column("項目", style="cyan")
        status_table.add_column("數值", style="yellow")
        
        status_table.add_row("連線狀態", "✅ 已連線" if self.is_connected else "❌ 未連線")
        status_table.add_row("運行時間", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        status_table.add_row("接收封包", str(self.received_count))
        status_table.add_row("解析成功", str(self.parsed_count))
        status_table.add_row("解析失敗", str(self.error_count))
        
        if self.received_count > 0:
            success_rate = (self.parsed_count / self.received_count) * 100
            status_table.add_row("成功率", f"{success_rate:.1f}%")
        
        status_panel = Panel(status_table, title="📊 連線狀態", border_style="green")
        
        # 最新數據顯示
        if self.latest_data.get("data"):
            data = self.latest_data["data"]
            data_table = Table(show_header=False, box=None)
            data_table.add_column("參數", style="cyan")
            data_table.add_column("數值", style="yellow")
            
            # 根據數據類型顯示不同內容
            if data.get("type") == "BMS 控制信息":
                data_table.add_row("總電壓", data.get("max_voltage", "N/A"))
                data_table.add_row("電流", data.get("max_current", "N/A"))
                data_table.add_row("SOC", data.get("soc", "N/A"))
                data_table.add_row("功率", data.get("power", "N/A"))
                data_table.add_row("充電狀態", data.get("charging", "N/A"))
                data_table.add_row("系統狀態", data.get("status", "N/A"))
            else:
                for key, value in data.items():
                    if key not in ["type", "status_flags"]:
                        data_table.add_row(key, str(value))
            
            data_panel = Panel(data_table, title="⚡ 即時數據", border_style="yellow")
        else:
            data_panel = Panel("等待數據...", title="⚡ 即時數據", border_style="yellow")
        
        # 告警顯示
        if self.alerts:
            alert_text = "\n".join(self.alerts)
            alert_panel = Panel(
                Text(alert_text, style="bold red"),
                title="🚨 告警信息",
                border_style="red"
            )
        else:
            alert_panel = Panel(
                Text("系統正常", style="green"),
                title="✅ 系統狀態",
                border_style="green"
            )
        
        # 原始數據
        if self.latest_data:
            raw_text = f"HEX: {self.latest_data.get('raw_hex', 'N/A')}\n"
            raw_text += f"CAN ID: {self.latest_data.get('can_id', 'N/A')}\n"
            raw_text += f"類型: {self.latest_data.get('message_type', 'N/A')}"
            raw_panel = Panel(raw_text, title="📦 原始數據", border_style="dim")
        else:
            raw_panel = Panel("等待數據...", title="📦 原始數據", border_style="dim")
        
        # 組合佈局
        layout.split_column(
            Layout(title, size=3),
            Layout(name="main")
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["main"]["left"].split_column(
            Layout(status_panel),
            Layout(alert_panel)
        )
        
        layout["main"]["right"].split_column(
            Layout(data_panel),
            Layout(raw_panel)
        )
        
        return layout
    
    async def start_monitoring(self):
        """開始監控"""
        if not self.client or not self.is_connected:
            console.print("[red]未連線，無法開始監控[/red]")
            return
        
        # 尋找數據特徵
        services = self.client.services
        char_uuid = None
        
        for service in services:
            for char in service.characteristics:
                if "notify" in char.properties or "read" in char.properties:
                    char_uuid = char.uuid
                    break
            if char_uuid:
                break
        
        if not char_uuid:
            console.print("[yellow]未找到可用的數據特徵[/yellow]")
            return
        
        try:
            # 訂閱通知
            await self.client.start_notify(char_uuid, self.handle_notification)
            self.monitoring = True
            
            console.print(f"[green]開始監控...[/green]")
            console.print("[dim]按 Ctrl+C 停止監控[/dim]\n")
            
            # 即時顯示
            with Live(self.create_display(), refresh_per_second=2) as live:
                while self.monitoring and self.is_connected:
                    live.update(self.create_display())
                    await asyncio.sleep(0.5)
                    
                    # 檢查連線狀態
                    if self.client and not self.client.is_connected:
                        self.is_connected = False
                        console.print("[red]連線已斷開[/red]")
                        break
                        
        except Exception as e:
            console.print(f"[red]監控錯誤: {e}[/red]")
        finally:
            self.monitoring = False
    
    async def disconnect(self):
        """斷開連線"""
        self.monitoring = False
        if self.client:
            await self.client.disconnect()
            self.is_connected = False

async def main(mac_address: str):
    """主程式"""
    console.print("[bold blue]🔋 BMS 即時監控系統[/bold blue]")
    console.print("=" * 50)
    console.print(f"目標設備: {mac_address}\n")
    
    monitor = BMSMonitor(mac_address)
    
    try:
        # 建立連線
        if not await monitor.connect():
            console.print("[red]無法建立連線[/red]")
            return 1
        
        # 開始監控
        await monitor.start_monitoring()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷監控[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await monitor.disconnect()
    
    # 顯示統計
    console.print("\n" + "=" * 50)
    console.print("[bold]📊 監控統計:[/bold]")
    console.print(f"  總接收: {monitor.received_count} 封包")
    console.print(f"  解析成功: {monitor.parsed_count} 封包")
    console.print(f"  解析失敗: {monitor.error_count} 封包")
    
    if monitor.received_count > 0:
        success_rate = (monitor.parsed_count / monitor.received_count) * 100
        console.print(f"  成功率: {success_rate:.1f}%")
    
    console.print(f"\n[dim]數據已保存到 {LOG_FILE}[/dim]")
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python monitor.py <MAC地址>")
        console.print("範例: python monitor.py AA:BB:CC:DD:EE:FF")
        sys.exit(1)
    
    mac_address = sys.argv[1]
    
    try:
        exit_code = asyncio.run(main(mac_address))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]監控已停止[/yellow]")
        sys.exit(0)