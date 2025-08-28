#!/usr/bin/env python3
"""
DALY BMS 診斷工具
專門用於分析 BMS 狀態，檢測問題並提供解決方案
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from bleak import BleakClient, BleakScanner

console = Console()

class DALYDiagnosisTool:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值對
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.diagnosis_results = {}
        self.responses = []
        
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
        
        self.responses.append({
            'timestamp': datetime.now(),
            'sender': sender,
            'data': data,
            'hex': data.hex().upper(),
            'length': len(data)
        })
    
    def create_daly_packet_a5(self, command_code: int, host_addr: int = 0x80, data_payload: bytes = None) -> bytes:
        """創建 DALY 0xA5 協議封包"""
        packet = bytearray(13)
        packet[0] = 0xA5
        packet[1] = host_addr
        packet[2] = command_code
        packet[3] = 0x08
        
        if data_payload:
            payload_len = min(len(data_payload), 8)
            packet[4:4+payload_len] = data_payload[:payload_len]
        
        checksum = sum(packet[:12]) & 0xFF
        packet[12] = checksum
        
        return bytes(packet)
    
    async def send_command_and_wait(self, command_name: str, packet: bytes, timeout: float = 2.0) -> List[Dict]:
        """發送命令並等待響應"""
        try:
            self.responses.clear()
            
            # 啟用通知監聽
            await self.client.start_notify(self.read_char, self.notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, packet, response=False)
            
            # 等待響應
            await asyncio.sleep(timeout)
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            
            return self.responses.copy()
            
        except Exception as e:
            console.print(f"[red]發送命令失敗: {e}[/red]")
            return []
    
    def analyze_response(self, data: bytes) -> Dict:
        """分析響應數據"""
        if len(data) != 13 or data[0] != 0xA5:
            return {"error": "非標準 A5 協議響應"}
        
        # 驗證校驗和
        calculated_checksum = sum(data[:12]) & 0xFF
        checksum_ok = calculated_checksum == data[12]
        
        if not checksum_ok:
            return {"error": "校驗和錯誤"}
        
        host_addr = data[1]
        command = data[2]
        payload = data[4:12]
        
        analysis = {
            "protocol": "0xA5",
            "host_addr": f"0x{host_addr:02X}",
            "command": f"0x{command:02X}",
            "checksum_ok": checksum_ok,
            "payload": payload.hex().upper()
        }
        
        # 根據命令解析數據
        if command == 0x90:  # 電壓電流SOC
            voltage = int.from_bytes(payload[0:2], 'big') / 10.0
            current_raw = int.from_bytes(payload[2:4], 'big')
            current = (current_raw - 30000) / 10.0
            soc = int.from_bytes(payload[4:6], 'big') / 10.0
            
            analysis["parsed"] = {
                "voltage": voltage,
                "current": current,
                "soc": soc,
                "current_raw": current_raw
            }
        
        elif command == 0x93:  # MOSFET 狀態
            charge_mosfet = payload[0] == 1
            discharge_mosfet = payload[1] == 1
            
            analysis["parsed"] = {
                "charge_mosfet": charge_mosfet,
                "discharge_mosfet": discharge_mosfet
            }
        
        elif command == 0x94:  # 狀態資訊
            analysis["parsed"] = {
                "cell_count": payload[0],
                "temp_sensor_count": payload[1],
                "charger_connected": payload[2] == 1,
                "load_connected": payload[3] == 1
            }
        
        return analysis
    
    async def comprehensive_diagnosis(self) -> Dict[str, any]:
        """綜合診斷 BMS 狀態"""
        console.print("\n[bold cyan]🔍 開始綜合診斷...[/bold cyan]")
        
        diagnosis = {
            "connectivity": {"status": "unknown", "details": []},
            "basic_info": {"status": "unknown", "data": {}},
            "mosfet_status": {"status": "unknown", "data": {}},
            "system_status": {"status": "unknown", "data": {}},
            "problems": [],
            "recommendations": []
        }
        
        # 1. 測試基本連線
        console.print("[dim]檢測 1: 基本連線響應...[/dim]")
        basic_packet = self.create_daly_packet_a5(0x90, 0x80)  # 基本資訊
        responses = await self.send_command_and_wait("基本資訊", basic_packet)
        
        if responses:
            diagnosis["connectivity"]["status"] = "good"
            diagnosis["connectivity"]["details"].append("BMS 正常響應命令")
            
            # 分析響應
            for resp in responses:
                analysis = self.analyze_response(resp['data'])
                if "parsed" in analysis:
                    diagnosis["basic_info"]["status"] = "received"
                    diagnosis["basic_info"]["data"] = analysis["parsed"]
        else:
            diagnosis["connectivity"]["status"] = "poor"
            diagnosis["connectivity"]["details"].append("BMS 無響應")
            diagnosis["problems"].append("BMS 不響應基本查詢命令")
            return diagnosis
        
        # 2. 測試 MOSFET 狀態
        console.print("[dim]檢測 2: MOSFET 狀態...[/dim]")
        mosfet_packet = self.create_daly_packet_a5(0x93, 0x80)
        responses = await self.send_command_and_wait("MOSFET狀態", mosfet_packet)
        
        if responses:
            for resp in responses:
                analysis = self.analyze_response(resp['data'])
                if "parsed" in analysis:
                    diagnosis["mosfet_status"]["status"] = "received"
                    diagnosis["mosfet_status"]["data"] = analysis["parsed"]
        
        # 3. 測試系統狀態
        console.print("[dim]檢測 3: 系統狀態...[/dim]")
        system_packet = self.create_daly_packet_a5(0x94, 0x80)
        responses = await self.send_command_and_wait("系統狀態", system_packet)
        
        if responses:
            for resp in responses:
                analysis = self.analyze_response(resp['data'])
                if "parsed" in analysis:
                    diagnosis["system_status"]["status"] = "received"
                    diagnosis["system_status"]["data"] = analysis["parsed"]
        
        # 4. 問題分析
        self.analyze_problems(diagnosis)
        
        return diagnosis
    
    def analyze_problems(self, diagnosis: Dict):
        """分析問題並提供建議"""
        problems = []
        recommendations = []
        
        # 檢查基本數據
        if diagnosis["basic_info"]["status"] == "received":
            data = diagnosis["basic_info"]["data"]
            
            # 檢查電壓
            if data.get("voltage", 0) == 0:
                problems.append("電壓讀數為零")
                recommendations.append("檢查電池是否正確連接到 BMS")
            
            # 檢查電流
            current = data.get("current", 0)
            if current == -3000:  # 原始值為 0 的情況
                problems.append("電流讀數異常（顯示-3000A）")
                recommendations.append("BMS 可能處於保護模式或未檢測到電流")
            
            # 檢查 SOC
            if data.get("soc", 0) == 0:
                problems.append("SOC（電量）為零")
                recommendations.append("可能需要重新校準或初始化 BMS")
        
        # 檢查 MOSFET 狀態
        if diagnosis["mosfet_status"]["status"] == "received":
            data = diagnosis["mosfet_status"]["data"]
            
            if not data.get("charge_mosfet", False):
                problems.append("充電 MOSFET 關閉")
                recommendations.append("嘗試使用 'control' 模式開啟充電 MOSFET")
            
            if not data.get("discharge_mosfet", False):
                problems.append("放電 MOSFET 關閉")
                recommendations.append("嘗試使用 'control' 模式開啟放電 MOSFET")
        
        # 檢查系統狀態
        if diagnosis["system_status"]["status"] == "received":
            data = diagnosis["system_status"]["data"]
            
            if data.get("cell_count", 0) == 0:
                problems.append("檢測到的電芯數量為零")
                recommendations.append("BMS 可能未正確配置或電池未連接")
            
            if data.get("temp_sensor_count", 0) == 0:
                problems.append("未檢測到溫度感測器")
                recommendations.append("檢查溫度感測器連接或 BMS 配置")
        
        # 綜合建議
        if len(problems) > 3:
            recommendations.append("BMS 可能需要完整重置和重新初始化")
            recommendations.append("嘗試使用 'wakeup' 模式執行完整喚醒序列")
        
        diagnosis["problems"] = problems
        diagnosis["recommendations"] = recommendations
    
    def generate_diagnosis_report(self, diagnosis: Dict):
        """生成診斷報告"""
        console.print("\n" + "="*60)
        console.print("[bold blue]🏥 DALY BMS 診斷報告[/bold blue]")
        console.print("="*60)
        
        # 連線狀態
        conn_status = diagnosis["connectivity"]["status"]
        if conn_status == "good":
            console.print(f"[green]✅ 連線狀態: 正常[/green]")
        else:
            console.print(f"[red]❌ 連線狀態: {conn_status}[/red]")
        
        # 基本資訊
        if diagnosis["basic_info"]["status"] == "received":
            data = diagnosis["basic_info"]["data"]
            console.print(f"\n[cyan]📊 基本資訊:[/cyan]")
            console.print(f"  電壓: {data.get('voltage', 'N/A')}V")
            console.print(f"  電流: {data.get('current', 'N/A')}A")
            console.print(f"  SOC: {data.get('soc', 'N/A')}%")
        
        # MOSFET 狀態
        if diagnosis["mosfet_status"]["status"] == "received":
            data = diagnosis["mosfet_status"]["data"]
            console.print(f"\n[cyan]⚡ MOSFET 狀態:[/cyan]")
            charge_status = "開啟" if data.get('charge_mosfet', False) else "關閉"
            discharge_status = "開啟" if data.get('discharge_mosfet', False) else "關閉"
            console.print(f"  充電 MOSFET: {charge_status}")
            console.print(f"  放電 MOSFET: {discharge_status}")
        
        # 系統狀態
        if diagnosis["system_status"]["status"] == "received":
            data = diagnosis["system_status"]["data"]
            console.print(f"\n[cyan]🔧 系統狀態:[/cyan]")
            console.print(f"  電芯數量: {data.get('cell_count', 'N/A')}")
            console.print(f"  溫度感測器: {data.get('temp_sensor_count', 'N/A')}")
            console.print(f"  充電器連接: {'是' if data.get('charger_connected', False) else '否'}")
            console.print(f"  負載連接: {'是' if data.get('load_connected', False) else '否'}")
        
        # 問題列表
        if diagnosis["problems"]:
            console.print(f"\n[red]⚠️ 發現的問題:[/red]")
            for i, problem in enumerate(diagnosis["problems"], 1):
                console.print(f"  {i}. {problem}")
        
        # 建議
        if diagnosis["recommendations"]:
            console.print(f"\n[yellow]💡 建議解決方案:[/yellow]")
            for i, rec in enumerate(diagnosis["recommendations"], 1):
                console.print(f"  {i}. {rec}")
        
        # 總結
        console.print(f"\n[bold cyan]📋 診斷總結:[/bold cyan]")
        if len(diagnosis["problems"]) == 0:
            console.print("[green]BMS 狀態正常，沒有發現明顯問題。[/green]")
        elif len(diagnosis["problems"]) <= 2:
            console.print("[yellow]發現少量問題，按照建議進行排除。[/yellow]")
        else:
            console.print("[red]發現多個問題，BMS 可能需要重新初始化。[/red]")
        
        console.print("="*60)
    
    async def quick_health_check(self):
        """快速健康檢查"""
        console.print("\n[bold green]⚡ 快速健康檢查[/bold green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("檢查 BMS 響應...", total=None)
            
            # 測試基本響應
            packet = self.create_daly_packet_a5(0x90, 0x80)
            responses = await self.send_command_and_wait("快速檢查", packet)
            
            progress.update(task, description="分析響應...")
            await asyncio.sleep(0.5)
            
        if responses:
            response = responses[0]
            analysis = self.analyze_response(response['data'])
            
            if "parsed" in analysis:
                data = analysis["parsed"]
                console.print(f"[green]✅ BMS 響應正常[/green]")
                console.print(f"[dim]電壓: {data.get('voltage', 'N/A')}V, 電流: {data.get('current', 'N/A')}A, SOC: {data.get('soc', 'N/A')}%[/dim]")
                
                # 快速問題檢測
                issues = []
                if data.get('voltage', 0) == 0:
                    issues.append("電壓為零")
                if data.get('current', 0) == -3000:
                    issues.append("電流異常")
                if data.get('soc', 0) == 0:
                    issues.append("SOC為零")
                
                if issues:
                    console.print(f"[yellow]⚠️ 快速檢測發現問題: {', '.join(issues)}[/yellow]")
                    console.print("[dim]建議執行完整診斷: python daly_diagnosis_tool.py <MAC> full[/dim]")
                else:
                    console.print("[green]🎉 快速檢查未發現明顯問題[/green]")
            else:
                console.print("[yellow]⚠️ BMS 有響應但數據格式異常[/yellow]")
        else:
            console.print("[red]❌ BMS 無響應，可能有連線或硬體問題[/red]")
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python daly_diagnosis_tool.py <MAC地址> [模式]")
        console.print("模式: quick | full")
        console.print("範例: python daly_diagnosis_tool.py 41:18:12:01:37:71 full")
        return 1
    
    mac_address = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "quick"
    
    tool = DALYDiagnosisTool(mac_address)
    
    try:
        # 建立連線
        if not await tool.connect():
            return 1
        
        if mode == "quick":
            await tool.quick_health_check()
        elif mode == "full":
            diagnosis = await tool.comprehensive_diagnosis()
            tool.generate_diagnosis_report(diagnosis)
        else:
            console.print(f"[red]未知模式: {mode}[/red]")
            return 1
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷診斷[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await tool.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)