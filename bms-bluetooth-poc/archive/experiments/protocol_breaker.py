#!/usr/bin/env python3
"""
BMS 協議破解工具
系統化地突破"回音效應"，找出真正的協議格式
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional, Dict, List, Set
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from bleak import BleakClient, BleakScanner
import itertools
import struct

console = Console()

class ProtocolBreaker:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 已確認有效的特徵對
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        self.tested_commands: Set[str] = set()
        self.successful_responses: List[Dict] = []
        self.echo_responses: List[Dict] = []
        
        # 常見的 BMS 密碼和認證序列
        self.auth_sequences = [
            # 常見 BMS 密碼
            b"123456",
            b"000000", 
            b"1234",
            b"0000",
            b"admin",
            b"password",
            
            # 十六進制格式的密碼
            bytes.fromhex("31323334"),  # "1234"
            bytes.fromhex("313233343536"),  # "123456"
            bytes.fromhex("30303030"),  # "0000"
            
            # 可能的握手序列
            bytes.fromhex("AABBCCDD"),
            bytes.fromhex("55AA55AA"),
            bytes.fromhex("FF00FF00"),
            bytes.fromhex("DEADBEEF"),
            
            # DL/Daly 特有可能序列
            bytes.fromhex("DA1Y"),  # DALY ASCII
            bytes.fromhex("444C"),    # DL ASCII  
            bytes.fromhex("424D53"),  # BMS ASCII
            
            # 可能的啟動魔術字符
            bytes.fromhex("CAFEBABE"),
            bytes.fromhex("BEEFDEAD"),
            bytes.fromhex("12345678"),
        ]
        
        # 可能的命令格式模板
        self.command_templates = [
            # 簡單命令格式
            lambda cmd: bytes([cmd]),
            lambda cmd: bytes([cmd, 0x00]),
            lambda cmd: bytes([0x01, cmd]),
            lambda cmd: bytes([0xAA, cmd, 0x55]),
            
            # 帶校驗和格式
            lambda cmd: bytes([cmd, (~cmd) & 0xFF]),
            lambda cmd: bytes([cmd, cmd ^ 0xFF]),
            
            # 長度前綴格式
            lambda cmd: bytes([0x01, cmd]),
            lambda cmd: bytes([0x02, cmd, 0x00]),
            
            # 標準通訊協議格式
            lambda cmd: bytes([0x01, 0x03, 0x00, cmd, 0x00, 0x01]),  # Modbus 風格
            lambda cmd: bytes([0x68, cmd, cmd, 0x68, 0x16]),         # DL/T645 風格
            
            # 自定義封裝格式
            lambda cmd: bytes([0xFA, 0xFB, cmd, 0xFC, 0xFD]),
            lambda cmd: bytes([0x7E, cmd, 0x7E]),
        ]
    
    async def connect(self) -> bool:
        """建立連線"""
        try:
            console.print(f"[cyan]正在連線到 {self.mac_address}...[/cyan]")
            
            device = await BleakScanner.find_device_by_address(self.mac_address, timeout=5.0)
            if not device:
                return False
            
            self.client = BleakClient(self.mac_address)
            await self.client.connect()
            
            if self.client.is_connected:
                self.is_connected = True
                console.print(f"[green]✅ 成功連線[/green]")
                return True
                
        except Exception as e:
            console.print(f"[red]連線失敗: {e}[/red]")
            return False
    
    def is_echo_response(self, command: bytes, response: bytes) -> bool:
        """檢查是否為回音響應"""
        return command == response
    
    def calculate_checksum_variants(self, data: bytes) -> List[bytes]:
        """計算各種校驗和變體"""
        variants = []
        
        # 簡單校驗和
        checksum = sum(data) & 0xFF
        variants.append(data + bytes([checksum]))
        
        # XOR 校驗
        xor_check = 0
        for b in data:
            xor_check ^= b
        variants.append(data + bytes([xor_check]))
        
        # CRC-8 近似
        crc = 0xFF
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xFF
        variants.append(data + bytes([crc]))
        
        # 補碼校驗
        complement = (~sum(data) + 1) & 0xFF
        variants.append(data + bytes([complement]))
        
        return variants
    
    async def test_command(self, command: bytes, description: str = "") -> Dict:
        """測試單個命令"""
        if command.hex() in self.tested_commands:
            return {"skip": True}
        
        self.tested_commands.add(command.hex())
        
        try:
            # 啟用通知
            notifications = []
            
            def notification_handler(sender, data):
                notifications.append(data)
            
            await self.client.start_notify(self.read_char, notification_handler)
            
            # 發送命令
            await self.client.write_gatt_char(self.write_char, command, response=False)
            
            # 等待響應
            await asyncio.sleep(0.5)
            
            # 停止通知
            await self.client.stop_notify(self.read_char)
            
            result = {
                "command": command.hex().upper(),
                "description": description,
                "responses": [data.hex().upper() for data in notifications],
                "is_echo": False,
                "success": len(notifications) > 0
            }
            
            # 分析響應
            for response_data in notifications:
                if not self.is_echo_response(command, response_data):
                    result["is_echo"] = False
                    result["real_data"] = True
                    self.successful_responses.append(result)
                    console.print(f"[green]🎉 非回音響應！{description}: {response_data.hex().upper()}[/green]")
                    return result
                else:
                    result["is_echo"] = True
            
            if result["is_echo"] and result["success"]:
                self.echo_responses.append(result)
            
            return result
            
        except Exception as e:
            return {
                "command": command.hex().upper(),
                "description": description,
                "error": str(e),
                "success": False
            }
    
    async def test_auth_sequences(self):
        """測試認證序列"""
        console.print(f"\n[bold yellow]🔐 測試認證序列...[/bold yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
        ) as progress:
            
            task = progress.add_task("測試認證序列", total=len(self.auth_sequences))
            
            for auth_seq in self.auth_sequences:
                progress.update(task, description=f"測試: {auth_seq.hex()[:16]}...")
                
                result = await self.test_command(auth_seq, f"認證序列")
                
                if result.get("real_data"):
                    console.print(f"[green]🔑 發現有效認證: {auth_seq.hex().upper()}[/green]")
                    return auth_seq
                
                progress.advance(task)
                await asyncio.sleep(0.1)
        
        return None
    
    async def test_command_templates(self):
        """測試命令格式模板"""
        console.print(f"\n[bold yellow]📝 測試命令格式模板...[/bold yellow]")
        
        # 常見的命令碼
        test_commands = [0x01, 0x02, 0x03, 0x04, 0x05, 0x10, 0x20, 0x30, 0x40, 0x50,
                        0x80, 0x90, 0xA0, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0, 0xFF]
        
        total_tests = len(self.command_templates) * len(test_commands)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
        ) as progress:
            
            task = progress.add_task("測試命令模板", total=total_tests)
            
            for template_idx, template_func in enumerate(self.command_templates):
                for cmd in test_commands:
                    try:
                        command = template_func(cmd)
                        progress.update(task, description=f"模板{template_idx+1}: 0x{cmd:02X}")
                        
                        result = await self.test_command(command, f"模板{template_idx+1}-0x{cmd:02X}")
                        
                        if result.get("real_data"):
                            console.print(f"[green]🎯 發現有效模板{template_idx+1}: {command.hex().upper()}[/green]")
                        
                        progress.advance(task)
                        await asyncio.sleep(0.05)
                        
                    except Exception:
                        progress.advance(task)
                        continue
    
    async def brute_force_short_commands(self):
        """暴力破解短命令"""
        console.print(f"\n[bold yellow]💪 暴力測試短命令 (1-3 bytes)...[/bold yellow]")
        
        # 1 字節命令
        console.print("[cyan]測試 1 字節命令...[/cyan]")
        for i in range(0, 256, 8):  # 每8個一組，避免過多
            commands = [bytes([j]) for j in range(i, min(i+8, 256))]
            
            for cmd in commands:
                result = await self.test_command(cmd, f"1byte-0x{cmd[0]:02X}")
                if result.get("real_data"):
                    return
            
            await asyncio.sleep(0.1)
        
        # 2 字節常見組合
        console.print("[cyan]測試 2 字節常見組合...[/cyan]")
        common_2byte = [
            bytes([0x01, 0x00]), bytes([0x02, 0x00]), bytes([0x03, 0x00]),
            bytes([0xAA, 0x55]), bytes([0x55, 0xAA]), bytes([0xFF, 0x00]),
            bytes([0x00, 0xFF]), bytes([0x01, 0x01]), bytes([0x02, 0x02]),
            bytes([0x10, 0x01]), bytes([0x20, 0x01]), bytes([0x30, 0x01]),
        ]
        
        for cmd in common_2byte:
            result = await self.test_command(cmd, f"2byte-{cmd.hex()}")
            if result.get("real_data"):
                return
            await asyncio.sleep(0.05)
    
    async def test_checksum_variants(self):
        """測試帶校驗和的命令變體"""
        console.print(f"\n[bold yellow]✅ 測試校驗和變體...[/bold yellow]")
        
        base_commands = [
            bytes([0x01]), bytes([0x02]), bytes([0x03]), bytes([0x04]),
            bytes([0x10]), bytes([0x20]), bytes([0x30]), 
            bytes([0x01, 0x03]), bytes([0x01, 0x04]),
        ]
        
        for base_cmd in base_commands:
            variants = self.calculate_checksum_variants(base_cmd)
            
            for variant in variants:
                result = await self.test_command(variant, f"checksum-{base_cmd.hex()}")
                if result.get("real_data"):
                    console.print(f"[green]🎯 發現有效校驗格式: {variant.hex().upper()}[/green]")
                    return variant
                
                await asyncio.sleep(0.05)
        
        return None
    
    async def test_multi_step_sequence(self):
        """測試多步驟序列"""
        console.print(f"\n[bold yellow]🔗 測試多步驟序列...[/bold yellow]")
        
        # 常見的多步驟握手模式
        sequences = [
            # 標準握手
            [bytes([0xAA]), bytes([0x55]), bytes([0x01])],
            [bytes([0xFF]), bytes([0x00]), bytes([0x03])],
            
            # 認證 -> 請求
            [b"123456", bytes([0x01])],
            [bytes.fromhex("AABBCCDD"), bytes([0x03])],
            
            # 喚醒 -> 初始化 -> 請求
            [bytes([0xFF]), bytes([0x00]), bytes([0x01]), bytes([0x03])],
        ]
        
        for seq_idx, sequence in enumerate(sequences):
            console.print(f"[dim]測試序列 {seq_idx+1}: {' -> '.join(cmd.hex() for cmd in sequence)}[/dim]")
            
            # 逐步發送序列
            for step_idx, cmd in enumerate(sequence):
                result = await self.test_command(cmd, f"seq{seq_idx+1}-step{step_idx+1}")
                
                if result.get("real_data"):
                    console.print(f"[green]🎉 序列 {seq_idx+1} 第 {step_idx+1} 步成功![/green]")
                    return sequence[:step_idx+1]
                
                # 短暫間隔
                await asyncio.sleep(0.2)
        
        return None
    
    async def comprehensive_protocol_break(self):
        """綜合協議破解"""
        console.print(f"\n[bold blue]🚀 開始綜合協議破解...[/bold blue]")
        
        # 階段1: 認證序列
        auth_result = await self.test_auth_sequences()
        if auth_result:
            console.print(f"[green]認證成功，繼續後續測試...[/green]")
        
        # 階段2: 命令模板
        await self.test_command_templates()
        
        # 如果發現有效響應，停止
        if self.successful_responses:
            console.print(f"[green]已發現 {len(self.successful_responses)} 個有效響應，停止測試[/green]")
            return
        
        # 階段3: 校驗和變體
        checksum_result = await self.test_checksum_variants()
        if checksum_result:
            console.print(f"[green]發現有效校驗格式，繼續測試...[/green]")
        
        # 階段4: 多步驟序列
        if not self.successful_responses:
            await self.test_multi_step_sequence()
        
        # 階段5: 暴力破解（最後手段）
        if not self.successful_responses:
            console.print(f"[yellow]未發現有效格式，開始暴力測試...[/yellow]")
            await self.brute_force_short_commands()
    
    def analyze_successful_responses(self):
        """分析成功的響應"""
        if not self.successful_responses:
            console.print(f"[yellow]⚠️ 未發現任何非回音響應[/yellow]")
            return
        
        console.print(f"\n[bold green]📊 成功響應分析:[/bold green]")
        
        table = Table(title="非回音響應", show_header=True)
        table.add_column("命令", style="cyan")
        table.add_column("描述", style="yellow") 
        table.add_column("響應", style="green")
        table.add_column("長度", style="magenta")
        
        for response in self.successful_responses:
            for resp_hex in response["responses"]:
                table.add_row(
                    response["command"],
                    response["description"],
                    resp_hex[:32] + ("..." if len(resp_hex) > 32 else ""),
                    f"{len(resp_hex)//2} bytes"
                )
        
        console.print(table)
    
    def show_statistics(self):
        """顯示統計資訊"""
        console.print(f"\n[bold blue]📈 測試統計:[/bold blue]")
        console.print(f"總測試命令: {len(self.tested_commands)}")
        console.print(f"回音響應: {len(self.echo_responses)}")
        console.print(f"有效響應: {len(self.successful_responses)}")
        
        if len(self.tested_commands) > 0:
            echo_rate = len(self.echo_responses) / len(self.tested_commands) * 100
            console.print(f"回音率: {echo_rate:.1f}%")
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python protocol_breaker.py <MAC地址> [模式]")
        console.print("模式: full | auth | templates | brute | checksum | sequence")
        return 1
    
    mac_address = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "full"
    
    breaker = ProtocolBreaker(mac_address)
    
    console.print("[bold red]💥 BMS 協議破解工具[/bold red]")
    console.print("=" * 60)
    console.print(f"目標設備: {mac_address}")
    console.print(f"測試模式: {mode}")
    console.print("目標: 突破回音效應，找出真正的協議格式\n")
    
    try:
        if not await breaker.connect():
            return 1
        
        start_time = time.time()
        
        if mode == "full":
            await breaker.comprehensive_protocol_break()
        elif mode == "auth":
            await breaker.test_auth_sequences()
        elif mode == "templates":
            await breaker.test_command_templates()
        elif mode == "brute":
            await breaker.brute_force_short_commands()
        elif mode == "checksum":
            await breaker.test_checksum_variants()
        elif mode == "sequence":
            await breaker.test_multi_step_sequence()
        
        elapsed_time = time.time() - start_time
        
        # 顯示結果
        breaker.analyze_successful_responses()
        breaker.show_statistics()
        
        console.print(f"\n[dim]測試完成，耗時 {elapsed_time:.1f} 秒[/dim]")
        
        if breaker.successful_responses:
            console.print(f"[green]🎉 協議破解成功！發現 {len(breaker.successful_responses)} 個有效命令[/green]")
        else:
            console.print(f"[yellow]⚠️ 未能突破協議，可能需要更深度的分析[/yellow]")
            console.print("建議: 1) 檢查是否需要特定的連接順序")
            console.print("     2) 分析 Smart BMS app 的網路封包")
            console.print("     3) 查找該型號 BMS 的技術文件")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷測試[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
    finally:
        await breaker.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)