#!/usr/bin/env python3
"""
藍牙設備掃描器
掃描附近的藍牙設備，找出可能的 BMS
"""

import asyncio
import sys
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from bleak import BleakScanner
from config import BMS_NAME_PATTERNS, BLUETOOTH_SCAN_TIMEOUT

console = Console()

class BMSScanner:
    def __init__(self):
        self.devices: List[Dict] = []
        self.bms_devices: List[Dict] = []
        
    def is_likely_bms(self, device_name: str) -> bool:
        """判斷是否可能是 BMS 設備"""
        if not device_name:
            return False
            
        name_upper = device_name.upper()
        for pattern in BMS_NAME_PATTERNS:
            if pattern.upper() in name_upper:
                return True
        return False
    
    async def scan_devices(self, timeout: int = BLUETOOTH_SCAN_TIMEOUT):
        """掃描藍牙設備"""
        console.print(f"[cyan]🔍 開始掃描藍牙設備 (等待 {timeout} 秒)...[/cyan]")
        
        with Live(Spinner("dots", text="掃描中..."), refresh_per_second=10):
            # 使用 BleakScanner 掃描 BLE 設備
            devices = await BleakScanner.discover(timeout=timeout)
            
            self.devices = []
            self.bms_devices = []
            
            for device in devices:
                device_info = {
                    "address": device.address,
                    "name": device.name or "未知設備",
                    "rssi": getattr(device, 'rssi', 'N/A')
                }
                
                self.devices.append(device_info)
                
                # 檢查是否可能是 BMS
                if self.is_likely_bms(device_info["name"]):
                    self.bms_devices.append(device_info)
        
        return self.devices
    
    def display_results(self):
        """顯示掃描結果"""
        console.print("\n[bold green]✅ 掃描完成！[/bold green]\n")
        
        # 優先顯示可能的 BMS 設備
        if self.bms_devices:
            console.print("[bold yellow]🔋 發現可能的 BMS 設備:[/bold yellow]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("編號", style="cyan", width=6)
            table.add_column("設備名稱", style="green")
            table.add_column("MAC 地址", style="yellow")
            table.add_column("訊號強度", style="blue")
            
            for idx, device in enumerate(self.bms_devices, 1):
                rssi_str = f"{device['rssi']} dBm" if device['rssi'] != 'N/A' else 'N/A'
                table.add_row(
                    str(idx),
                    device["name"],
                    device["address"],
                    rssi_str
                )
            
            console.print(table)
            console.print()
        
        # 顯示所有設備
        console.print("[bold]📱 所有發現的藍牙設備:[/bold]")
        all_table = Table(show_header=True, header_style="bold cyan")
        all_table.add_column("編號", style="dim", width=6)
        all_table.add_column("設備名稱")
        all_table.add_column("MAC 地址", style="dim")
        all_table.add_column("訊號強度", style="dim")
        all_table.add_column("可能是 BMS?", style="yellow")
        
        for idx, device in enumerate(self.devices, 1):
            is_bms = "✓" if device in self.bms_devices else ""
            rssi_str = f"{device['rssi']} dBm" if device['rssi'] != 'N/A' else 'N/A'
            all_table.add_row(
                str(idx),
                device["name"],
                device["address"],
                rssi_str,
                is_bms
            )
        
        console.print(all_table)
        
        # 提供建議
        console.print("\n[bold]💡 提示:[/bold]")
        if self.bms_devices:
            console.print("  • 找到可能的 BMS 設備，請記錄 MAC 地址")
            console.print("  • 使用 [cyan]python connector.py <MAC地址>[/cyan] 測試連線")
        else:
            console.print("  • 未找到明顯的 BMS 設備")
            console.print("  • 請確認 BMS 藍牙已開啟")
            console.print("  • 可以嘗試任何 'Unknown Device' 進行連線測試")
        
        # 保存結果到檔案
        self.save_results()
    
    def save_results(self):
        """保存掃描結果到檔案"""
        with open("scan_results.txt", "w", encoding="utf-8") as f:
            f.write("=== 藍牙掃描結果 ===\n\n")
            
            if self.bms_devices:
                f.write("可能的 BMS 設備:\n")
                for device in self.bms_devices:
                    f.write(f"  - {device['name']}: {device['address']} (RSSI: {device['rssi']})\n")
                f.write("\n")
            
            f.write("所有設備:\n")
            for device in self.devices:
                f.write(f"  - {device['name']}: {device['address']} (RSSI: {device['rssi']})\n")
        
        console.print("\n[dim]掃描結果已保存到 scan_results.txt[/dim]")

async def main():
    """主程式"""
    console.print("[bold blue]🔋 BMS 藍牙掃描器[/bold blue]")
    console.print("=" * 50)
    
    scanner = BMSScanner()
    
    try:
        # 掃描設備
        await scanner.scan_devices()
        
        # 顯示結果
        scanner.display_results()
        
    except Exception as e:
        console.print(f"[bold red]❌ 錯誤: {e}[/bold red]")
        console.print("\n[yellow]可能的原因:[/yellow]")
        console.print("  • 藍牙未開啟")
        console.print("  • 需要管理員權限 (Linux/Mac)")
        console.print("  • 藍牙驅動問題")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消掃描[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]❌ 執行錯誤: {e}[/bold red]")
        
        # 檢查是否在虛擬機中
        try:
            with open("/sys/class/dmi/id/product_name", "r") as f:
                product = f.read().strip()
                if "VMware" in product or "VirtualBox" in product:
                    console.print("\n[yellow]⚠️  偵測到虛擬機環境[/yellow]")
                    console.print("[dim]虛擬機需要額外設定才能使用藍牙：[/dim]")
                    console.print("  1. VMware: VM設定 → 新增 → 其他 → 藍牙控制器")
                    console.print("  2. VirtualBox: 設定 → USB → 啟用 USB 控制器")
                    console.print("  3. 或使用實體機器進行測試")
        except:
            pass
        
        sys.exit(1)