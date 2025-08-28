#!/usr/bin/env python3
"""
藍牙通訊嗅探工具
監控並分析 DALY BMS 的所有藍牙通訊
用於發現 Smart BMS app 的實際通訊協議
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List, Set
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from bleak import BleakClient, BleakScanner

console = Console()

class BluetoothSniffer:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 收集到的特徵值
        self.characteristics = {}
        self.notifications_enabled = set()
        
        # 通訊記錄
        self.communication_log = []
        self.unique_patterns = set()
        
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
    
    async def discover_services(self):
        """發現所有服務和特徵值"""
        console.print("\n[cyan]🔍 發現服務和特徵值...[/cyan]")
        
        services = self.client.services
        
        for service in services:
            console.print(f"\n[yellow]服務: {service.uuid}[/yellow]")
            
            for char in service.characteristics:
                properties = []
                if 'read' in char.properties:
                    properties.append("讀取")
                if 'write' in char.properties:
                    properties.append("寫入")
                if 'notify' in char.properties:
                    properties.append("通知")
                if 'indicate' in char.properties:
                    properties.append("指示")
                
                self.characteristics[char.uuid] = {
                    'service': service.uuid,
                    'properties': properties,
                    'handle': char.handle
                }
                
                console.print(f"  特徵: {char.uuid}")
                console.print(f"    屬性: {', '.join(properties)}")
                console.print(f"    句柄: {char.handle}")
    
    def notification_handler(self, sender, data):
        """處理所有通知數據"""
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp,
            'type': 'notification',
            'sender': sender,
            'data': data,
            'hex': data.hex().upper(),
            'length': len(data)
        }
        
        self.communication_log.append(entry)
        
        # 記錄唯一模式
        if len(data) >= 2:
            pattern = f"{data[0]:02X}_{data[1]:02X}_len{len(data)}"
            self.unique_patterns.add(pattern)
        
        # 實時顯示
        timestamp_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
        console.print(f"[green]📥 {timestamp_str}[/green] | 通知來自 {sender}")
        console.print(f"   HEX: {entry['hex']}")
        console.print(f"   長度: {len(data)} | ASCII: {self.safe_ascii(data)}")
        
        # 嘗試解析
        self.analyze_data(data)
    
    def safe_ascii(self, data: bytes) -> str:
        """安全轉換為 ASCII"""
        result = ""
        for b in data:
            if 32 <= b <= 126:
                result += chr(b)
            else:
                result += "."
        return result
    
    def analyze_data(self, data: bytes):
        """分析數據模式"""
        if len(data) == 0:
            return
        
        # 檢查已知協議
        if data[0] == 0xA5 and len(data) == 13:
            console.print(f"   [cyan]檢測到: 標準 DALY A5 協議[/cyan]")
            self.parse_a5_protocol(data)
        elif data[0] == 0xD2:
            console.print(f"   [cyan]檢測到: DALY D2 協議[/cyan]")
        elif data[0] == 0xDD and len(data) >= 4:
            console.print(f"   [cyan]檢測到: 可能是 JBD/Xiaoxiang 協議[/cyan]")
        elif len(data) == 20:  # 常見的 BMS 數據包長度
            console.print(f"   [cyan]檢測到: 20 位元組數據包（可能是狀態數據）[/cyan]")
        
        # 檢查是否有校驗和
        if len(data) >= 4:
            calculated_sum = sum(data[:-1]) & 0xFF
            if calculated_sum == data[-1]:
                console.print(f"   [dim]可能包含校驗和（最後位元組）[/dim]")
    
    def parse_a5_protocol(self, data: bytes):
        """解析 A5 協議"""
        if len(data) != 13:
            return
        
        host = data[1]
        cmd = data[2]
        payload = data[4:12]
        checksum = data[12]
        
        calculated = sum(data[:12]) & 0xFF
        checksum_ok = calculated == checksum
        
        console.print(f"   [dim]A5 解析: 主機=0x{host:02X}, 命令=0x{cmd:02X}, 校驗={'✓' if checksum_ok else '✗'}[/dim]")
    
    async def monitor_all_notifications(self):
        """監控所有支持通知的特徵值"""
        console.print("\n[cyan]📡 啟動全特徵值監控...[/cyan]")
        
        for uuid, info in self.characteristics.items():
            if "通知" in info['properties'] or "指示" in info['properties']:
                try:
                    await self.client.start_notify(uuid, self.notification_handler)
                    self.notifications_enabled.add(uuid)
                    console.print(f"[green]✅ 已啟用監控: {uuid}[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ 無法監控 {uuid}: {e}[/yellow]")
        
        console.print(f"[green]正在監控 {len(self.notifications_enabled)} 個特徵值[/green]")
    
    async def send_probe_commands(self):
        """發送探測命令以觸發響應"""
        console.print("\n[cyan]🚀 發送探測命令...[/cyan]")
        
        # 找出可寫入的特徵值
        write_chars = []
        for uuid, info in self.characteristics.items():
            if "寫入" in info['properties']:
                write_chars.append(uuid)
        
        if not write_chars:
            console.print("[yellow]未找到可寫入的特徵值[/yellow]")
            return
        
        console.print(f"[dim]找到 {len(write_chars)} 個可寫入特徵值[/dim]")
        
        # 測試命令列表
        test_commands = [
            bytes.fromhex("A58090080000000000000000BD"),  # 標準 A5 查詢
            bytes.fromhex("A58093080000000000000000C0"),  # MOSFET 狀態
            bytes.fromhex("A58094080000000000000000C1"),  # 系統狀態
            bytes.fromhex("DD A5 03 00 FF FD 77"),        # JBD 格式
            bytes.fromhex("00"),                          # 簡單觸發
            bytes.fromhex("01"),                          # 簡單觸發
        ]
        
        # 對每個可寫特徵值發送測試命令
        for char_uuid in write_chars[:2]:  # 限制測試前2個
            console.print(f"\n[yellow]測試特徵值: {char_uuid}[/yellow]")
            
            for i, cmd in enumerate(test_commands[:3]):  # 限制每個特徵值3個命令
                try:
                    console.print(f"[dim]發送: {cmd.hex().upper()}[/dim]")
                    
                    # 記錄發送
                    self.communication_log.append({
                        'timestamp': datetime.now(),
                        'type': 'write',
                        'target': char_uuid,
                        'data': cmd,
                        'hex': cmd.hex().upper(),
                        'length': len(cmd)
                    })
                    
                    await self.client.write_gatt_char(char_uuid, cmd, response=False)
                    await asyncio.sleep(1)  # 等待響應
                    
                except Exception as e:
                    console.print(f"[red]寫入失敗: {e}[/red]")
    
    async def passive_monitor(self, duration: int = 60):
        """被動監控模式（等待 Smart BMS app 通訊）"""
        console.print(f"\n[bold yellow]🎯 被動監控模式 ({duration} 秒)[/bold yellow]")
        console.print("[dim]請現在打開 Smart BMS app 並操作，我將記錄所有通訊...[/dim]")
        
        start_time = time.time()
        last_activity = start_time
        
        while time.time() - start_time < duration:
            current_time = time.time()
            
            # 檢查是否有新活動
            if self.communication_log:
                last_entry_time = self.communication_log[-1]['timestamp'].timestamp()
                if last_entry_time > last_activity:
                    last_activity = last_entry_time
                    console.print(f"[green]✅ 檢測到活動[/green]")
            
            # 顯示進度
            elapsed = int(current_time - start_time)
            remaining = duration - elapsed
            
            if elapsed % 10 == 0 and elapsed > 0:
                console.print(f"[dim]剩餘時間: {remaining} 秒 | 已記錄: {len(self.communication_log)} 筆通訊[/dim]")
            
            await asyncio.sleep(1)
        
        console.print(f"[yellow]監控結束，共記錄 {len(self.communication_log)} 筆通訊[/yellow]")
    
    def generate_report(self):
        """生成分析報告"""
        console.print("\n" + "="*60)
        console.print("[bold blue]📊 通訊分析報告[/bold blue]")
        console.print("="*60)
        
        # 統計
        console.print(f"\n[cyan]📈 統計資訊:[/cyan]")
        console.print(f"  總通訊次數: {len(self.communication_log)}")
        console.print(f"  唯一模式數: {len(self.unique_patterns)}")
        
        write_count = sum(1 for log in self.communication_log if log['type'] == 'write')
        notify_count = sum(1 for log in self.communication_log if log['type'] == 'notification')
        console.print(f"  寫入次數: {write_count}")
        console.print(f"  通知次數: {notify_count}")
        
        # 唯一模式
        if self.unique_patterns:
            console.print(f"\n[cyan]🔍 發現的數據模式:[/cyan]")
            for pattern in sorted(self.unique_patterns):
                console.print(f"  - {pattern}")
        
        # 最常見的數據長度
        length_stats = {}
        for log in self.communication_log:
            length = log['length']
            length_stats[length] = length_stats.get(length, 0) + 1
        
        if length_stats:
            console.print(f"\n[cyan]📏 數據長度分布:[/cyan]")
            for length, count in sorted(length_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"  {length} 位元組: {count} 次")
        
        # 顯示前幾筆通訊
        if self.communication_log:
            console.print(f"\n[cyan]📜 最近的通訊記錄:[/cyan]")
            for log in self.communication_log[-5:]:
                timestamp_str = log['timestamp'].strftime("%H:%M:%S")
                if log['type'] == 'write':
                    console.print(f"  [yellow]{timestamp_str} 寫入[/yellow]: {log['hex']}")
                else:
                    console.print(f"  [green]{timestamp_str} 通知[/green]: {log['hex']}")
        
        console.print("="*60)
        
        # 建議
        console.print(f"\n[yellow]💡 分析建議:[/yellow]")
        if len(self.communication_log) == 0:
            console.print("  - 未捕獲到任何通訊，請確認 Smart BMS app 是否正在通訊")
            console.print("  - 嘗試在 app 中切換不同頁面或執行操作")
        elif notify_count > 0 and write_count == 0:
            console.print("  - 只收到通知，未捕獲寫入命令")
            console.print("  - Smart BMS app 可能在連線前就已發送初始化命令")
            console.print("  - 建議：斷開 app 連線，啟動監控，然後重新連線 app")
        elif write_count > 0:
            console.print("  - 成功捕獲寫入命令！")
            console.print("  - 分析這些命令格式以了解正確的通訊協議")
    
    async def disconnect(self):
        """斷開連線"""
        # 停止所有通知
        for uuid in self.notifications_enabled:
            try:
                await self.client.stop_notify(uuid)
            except:
                pass
        
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python bluetooth_sniffer.py <MAC地址> [模式]")
        console.print("模式: passive | active | both")
        console.print("範例: python bluetooth_sniffer.py 41:18:12:01:37:71 passive")
        return 1
    
    mac_address = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "passive"
    
    sniffer = BluetoothSniffer(mac_address)
    
    console.print("[bold blue]🔍 藍牙通訊嗅探工具[/bold blue]")
    console.print("="*60)
    console.print(f"目標設備: {mac_address}")
    console.print(f"監控模式: {mode}")
    console.print("")
    
    try:
        # 建立連線
        if not await sniffer.connect():
            return 1
        
        # 發現服務
        await sniffer.discover_services()
        
        # 啟動監控
        await sniffer.monitor_all_notifications()
        
        if mode == "active":
            # 主動探測模式
            await sniffer.send_probe_commands()
            await asyncio.sleep(5)  # 等待響應
        elif mode == "passive":
            # 被動監控模式
            await sniffer.passive_monitor(duration=60)
        elif mode == "both":
            # 混合模式
            await sniffer.send_probe_commands()
            await sniffer.passive_monitor(duration=30)
        
        # 生成報告
        sniffer.generate_report()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷監控[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await sniffer.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)