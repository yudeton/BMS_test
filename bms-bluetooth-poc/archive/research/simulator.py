#!/usr/bin/env python3
"""
BMS 數據模擬器
在沒有真實 BMS 的情況下測試解析功能
"""

import time
import random
from datetime import datetime
from can_parser import CANParser
from config import CAN_ID_BMS_TO_CHARGER, CAN_ID_CHARGER_BROADCAST
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

console = Console()

class BMSSimulator:
    """BMS 數據模擬器"""
    
    def __init__(self):
        self.parser = CANParser()
        self.running = False
        
        # 模擬數據狀態
        self.voltage = 48.0
        self.current = 0.0
        self.soc = 85.0
        self.is_charging = False
        
    def generate_bms_data(self) -> bytes:
        """生成模擬的 BMS CAN 數據"""
        
        # 模擬電壓變化 (45V-54V)
        self.voltage += random.uniform(-0.1, 0.1)
        self.voltage = max(45.0, min(54.0, self.voltage))
        
        # 模擬電流變化
        if self.is_charging:
            self.current = random.uniform(5.0, 25.0)  # 充電電流
        else:
            self.current = random.uniform(-15.0, 0.0)  # 放電電流
        
        # 模擬 SOC 變化
        if self.is_charging and self.soc < 100:
            self.soc += random.uniform(0, 0.05)
        elif not self.is_charging and self.soc > 0:
            self.soc -= random.uniform(0, 0.02)
        
        self.soc = max(0, min(100, self.soc))
        
        # 隨機切換充放電狀態
        if random.random() < 0.05:  # 5% 機率切換
            self.is_charging = not self.is_charging
        
        # 構建 CAN 數據包
        can_id = CAN_ID_BMS_TO_CHARGER.to_bytes(4, byteorder='big')
        
        # 電壓 (0.1V/bit)
        voltage_raw = int(self.voltage * 10)
        voltage_bytes = voltage_raw.to_bytes(2, byteorder='big')
        
        # 電流 (0.1A/bit)
        current_raw = int(abs(self.current) * 10)
        current_bytes = current_raw.to_bytes(2, byteorder='big')
        
        # SOC (0.1%/bit)
        soc_raw = int(self.soc * 10)
        soc_bytes = soc_raw.to_bytes(2, byteorder='big')
        
        # 控制和狀態
        control = 0 if self.is_charging else 1
        status = 1 if self.soc < 10 else 0  # 低電量時異常
        
        data = can_id + voltage_bytes + current_bytes + soc_bytes + bytes([control, status])
        return data
    
    def generate_charger_data(self) -> bytes:
        """生成模擬的充電機數據"""
        can_id = CAN_ID_CHARGER_BROADCAST.to_bytes(4, byteorder='big')
        
        # 充電機輸出數據 (如果在充電)
        if self.is_charging:
            output_voltage = self.voltage + random.uniform(-0.2, 0.2)
            output_current = abs(self.current) + random.uniform(-1.0, 1.0)
        else:
            output_voltage = 0
            output_current = 0
        
        voltage_raw = int(output_voltage * 10)
        current_raw = int(output_current * 10)
        soc_raw = int(self.soc * 10)
        
        voltage_bytes = voltage_raw.to_bytes(2, byteorder='big')
        current_bytes = current_raw.to_bytes(2, byteorder='big')
        soc_bytes = soc_raw.to_bytes(2, byteorder='big')
        
        # 狀態標誌
        status_flags = 0
        if not self.is_charging:
            status_flags |= (1 << 3)  # 啟動狀態位
        
        data = can_id + voltage_bytes + current_bytes + soc_bytes + bytes([status_flags, 0])
        return data
    
    def create_display(self, parsed_data_list) -> Layout:
        """創建顯示界面"""
        layout = Layout()
        
        # 標題
        title = Panel(
            "🔋 BMS 數據模擬器 (測試模式)",
            style="bold cyan",
            border_style="blue"
        )
        
        # 模擬狀態
        status_table = Table(show_header=False, box=None)
        status_table.add_column("項目", style="cyan")
        status_table.add_column("數值", style="yellow")
        
        status_table.add_row("當前電壓", f"{self.voltage:.1f} V")
        status_table.add_row("當前電流", f"{self.current:.1f} A")
        status_table.add_row("當前 SOC", f"{self.soc:.1f} %")
        status_table.add_row("充電狀態", "充電中" if self.is_charging else "放電中")
        
        status_panel = Panel(status_table, title="📊 模擬狀態", border_style="green")
        
        # 解析結果
        if parsed_data_list:
            latest = parsed_data_list[-1]
            if latest.get("data"):
                data = latest["data"]
                result_table = Table(show_header=False, box=None)
                result_table.add_column("參數", style="cyan")
                result_table.add_column("解析值", style="yellow")
                
                for key, value in data.items():
                    if key != "type":
                        result_table.add_row(key, str(value))
                
                result_panel = Panel(result_table, title="⚡ 解析結果", border_style="yellow")
            else:
                result_panel = Panel("解析失敗", title="❌ 解析結果", border_style="red")
        else:
            result_panel = Panel("等待數據...", title="⚡ 解析結果", border_style="dim")
        
        # 最近數據
        recent_text = ""
        for data in parsed_data_list[-5:]:
            timestamp = datetime.now().strftime("%H:%M:%S")
            msg_type = data.get("message_type", "UNKNOWN")
            recent_text += f"{timestamp} | {msg_type}\n"
        
        recent_panel = Panel(recent_text or "無數據", title="📦 最近數據", border_style="dim")
        
        # 佈局
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
            Layout(recent_panel)
        )
        
        layout["main"]["right"] = Layout(result_panel)
        
        return layout
    
    def run(self):
        """運行模擬器"""
        console.print("[bold blue]🔋 BMS 數據模擬器[/bold blue]")
        console.print("=" * 50)
        console.print("[dim]這個模擬器會生成假的 BMS 數據來測試解析功能[/dim]")
        console.print("[dim]按 Ctrl+C 停止模擬[/dim]\n")
        
        self.running = True
        parsed_data_list = []
        
        with Live(self.create_display(parsed_data_list), refresh_per_second=2) as live:
            try:
                while self.running:
                    # 生成並解析 BMS 數據
                    bms_data = self.generate_bms_data()
                    parsed = self.parser.parse(bms_data)
                    parsed_data_list.append(parsed)
                    
                    # 隨機生成充電機數據
                    if random.random() < 0.3:  # 30% 機率
                        charger_data = self.generate_charger_data()
                        parsed_charger = self.parser.parse(charger_data)
                        parsed_data_list.append(parsed_charger)
                    
                    # 保持列表大小
                    if len(parsed_data_list) > 20:
                        parsed_data_list = parsed_data_list[-20:]
                    
                    live.update(self.create_display(parsed_data_list))
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                self.running = False
                console.print("\n[yellow]模擬已停止[/yellow]")

if __name__ == "__main__":
    simulator = BMSSimulator()
    simulator.run()