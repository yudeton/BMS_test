#!/usr/bin/env python3
"""
HCI 日誌分析工具
專門分析從 Android HCI 日誌中提取的 DALY BMS 通訊協議
"""

import sys
import struct
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import binascii
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

class HCILogAnalyzer:
    def __init__(self, log_file: str, target_mac: str = None):
        self.log_file = log_file
        self.target_mac = target_mac.lower().replace(":", "") if target_mac else None
        
        # 分析結果
        self.gatt_writes = []
        self.gatt_notifications = []
        self.connection_events = []
        self.protocol_sequences = []
        
        # BLE 相關常數
        self.GATT_WRITE_CMD = 0x52
        self.GATT_WRITE_REQ = 0x12
        self.GATT_NOTIFICATION = 0x1B
        self.ATT_HANDLE_VALUE_NTF = 0x1B
        
        # 已知的 DALY BMS 特徵值
        self.known_characteristics = {
            "fff2": "寫入特徵值",
            "fff1": "通知特徵值"
        }
    
    def read_btsnoop_log(self) -> List[Dict]:
        """讀取 btsnoop HCI 日誌文件"""
        console.print(f"[cyan]正在讀取 HCI 日誌: {self.log_file}[/cyan]")
        
        packets = []
        
        try:
            with open(self.log_file, 'rb') as f:
                # 讀取文件頭
                header = f.read(16)
                if header[:8] != b'btsnoop\x00':
                    console.print("[red]錯誤：這不是有效的 btsnoop 文件[/red]")
                    return []
                
                # 解析封包記錄
                packet_num = 0
                while True:
                    # 讀取封包記錄頭 (24 字節)
                    record_header = f.read(24)
                    if len(record_header) < 24:
                        break
                    
                    # 解析記錄頭
                    orig_len, incl_len, flags, drops, timestamp_us = struct.unpack('>IIIIQ', record_header)
                    
                    # 讀取封包數據
                    packet_data = f.read(incl_len)
                    if len(packet_data) < incl_len:
                        break
                    
                    packet_info = {
                        'packet_num': packet_num,
                        'timestamp': timestamp_us,
                        'orig_len': orig_len,
                        'incl_len': incl_len,
                        'flags': flags,
                        'data': packet_data
                    }
                    
                    packets.append(packet_info)
                    packet_num += 1
                    
                    if packet_num % 1000 == 0:
                        console.print(f"[dim]已讀取 {packet_num} 個封包...[/dim]")
        
        except FileNotFoundError:
            console.print(f"[red]錯誤：找不到文件 {self.log_file}[/red]")
            return []
        except Exception as e:
            console.print(f"[red]讀取文件時發生錯誤: {e}[/red]")
            return []
        
        console.print(f"[green]成功讀取 {len(packets)} 個封包[/green]")
        return packets
    
    def extract_mac_from_packet(self, data: bytes) -> Optional[str]:
        """從封包中提取 MAC 地址"""
        try:
            # HCI ACL 數據封包格式
            if len(data) < 4:
                return None
            
            # 跳過 HCI 頭部，尋找 L2CAP 和 ATT 數據
            # 這是簡化的實現，實際的 HCI 解析更複雜
            
            # 在數據中搜索可能的 MAC 地址模式
            for i in range(len(data) - 6):
                # 檢查是否像 MAC 地址（6個連續字節）
                mac_bytes = data[i:i+6]
                if self.is_valid_mac(mac_bytes):
                    return mac_bytes.hex().lower()
            
            return None
        except:
            return None
    
    def is_valid_mac(self, mac_bytes: bytes) -> bool:
        """檢查是否為有效的 MAC 地址"""
        if len(mac_bytes) != 6:
            return False
        
        # 檢查是否為全零或全 FF（通常不是有效 MAC）
        if mac_bytes == b'\x00' * 6 or mac_bytes == b'\xFF' * 6:
            return False
        
        return True
    
    def parse_gatt_packet(self, packet: Dict) -> Optional[Dict]:
        """解析 GATT 封包"""
        data = packet['data']
        
        try:
            # 簡化的 GATT 解析
            # 實際實現需要完整的 HCI/L2CAP/ATT 解析
            
            # 尋找 ATT 操作碼
            for i in range(len(data) - 1):
                opcode = data[i]
                
                if opcode == self.GATT_WRITE_CMD or opcode == self.GATT_WRITE_REQ:
                    # GATT 寫入操作
                    if i + 3 < len(data):
                        handle = struct.unpack('<H', data[i+1:i+3])[0]
                        value_data = data[i+3:]
                        
                        return {
                            'type': 'gatt_write',
                            'opcode': opcode,
                            'handle': handle,
                            'data': value_data,
                            'timestamp': packet['timestamp'],
                            'packet_num': packet['packet_num']
                        }
                
                elif opcode == self.GATT_NOTIFICATION:
                    # GATT 通知
                    if i + 3 < len(data):
                        handle = struct.unpack('<H', data[i+1:i+3])[0]
                        value_data = data[i+3:]
                        
                        return {
                            'type': 'gatt_notification',
                            'opcode': opcode,
                            'handle': handle,
                            'data': value_data,
                            'timestamp': packet['timestamp'],
                            'packet_num': packet['packet_num']
                        }
            
            return None
        except:
            return None
    
    def analyze_packets(self, packets: List[Dict]):
        """分析封包找出 GATT 通訊"""
        console.print("[cyan]正在分析 GATT 通訊...[/cyan]")
        
        for packet in packets:
            # 如果指定了目標 MAC，先檢查
            if self.target_mac:
                mac = self.extract_mac_from_packet(packet['data'])
                if mac and self.target_mac not in mac:
                    continue
            
            # 解析 GATT 操作
            gatt_info = self.parse_gatt_packet(packet)
            if gatt_info:
                if gatt_info['type'] == 'gatt_write':
                    self.gatt_writes.append(gatt_info)
                elif gatt_info['type'] == 'gatt_notification':
                    self.gatt_notifications.append(gatt_info)
        
        console.print(f"[green]找到 {len(self.gatt_writes)} 個 GATT 寫入操作[/green]")
        console.print(f"[green]找到 {len(self.gatt_notifications)} 個 GATT 通知[/green]")
    
    def identify_protocol_sequences(self):
        """識別協議序列"""
        console.print("[cyan]正在識別協議序列...[/cyan]")
        
        # 按時間排序
        all_operations = []
        
        for write in self.gatt_writes:
            all_operations.append({
                'timestamp': write['timestamp'],
                'type': 'write',
                'handle': write['handle'],
                'data': write['data'],
                'packet_num': write['packet_num']
            })
        
        for notif in self.gatt_notifications:
            all_operations.append({
                'timestamp': notif['timestamp'],
                'type': 'notification',
                'handle': notif['handle'],
                'data': notif['data'],
                'packet_num': notif['packet_num']
            })
        
        # 按時間排序
        all_operations.sort(key=lambda x: x['timestamp'])
        
        # 識別請求-響應對
        sequences = []
        i = 0
        while i < len(all_operations):
            op = all_operations[i]
            
            if op['type'] == 'write':
                # 尋找後續的通知響應
                responses = []
                j = i + 1
                
                while j < len(all_operations) and j < i + 5:  # 檢查後續 5 個操作
                    next_op = all_operations[j]
                    
                    # 如果時間間隔太大，停止
                    if next_op['timestamp'] - op['timestamp'] > 5000000:  # 5秒
                        break
                    
                    if next_op['type'] == 'notification':
                        responses.append(next_op)
                    
                    j += 1
                
                sequence = {
                    'write': op,
                    'responses': responses,
                    'sequence_id': len(sequences)
                }
                sequences.append(sequence)
            
            i += 1
        
        self.protocol_sequences = sequences
        console.print(f"[green]識別出 {len(sequences)} 個協議序列[/green]")
    
    def analyze_daly_protocol(self):
        """分析 DALY 協議格式"""
        console.print("[cyan]正在分析 DALY 協議格式...[/cyan]")
        
        protocol_patterns = defaultdict(int)
        
        for seq in self.protocol_sequences:
            write_data = seq['write']['data']
            
            if len(write_data) > 0:
                # 分析協議模式
                pattern = f"len{len(write_data)}_start{write_data[0]:02X}"
                protocol_patterns[pattern] += 1
                
                # 檢查已知的 DALY 協議格式
                analysis = self.analyze_command_format(write_data)
                if analysis:
                    seq['analysis'] = analysis
        
        # 顯示協議模式統計
        console.print("\n[cyan]發現的協議模式:[/cyan]")
        for pattern, count in sorted(protocol_patterns.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {pattern}: {count} 次")
    
    def analyze_command_format(self, data: bytes) -> Optional[Dict]:
        """分析命令格式"""
        if len(data) == 0:
            return None
        
        analysis = {'raw': data.hex().upper()}
        
        # 檢查 DALY A5 協議
        if data[0] == 0xA5 and len(data) == 13:
            analysis.update({
                'protocol': 'DALY_A5',
                'start_byte': f"0x{data[0]:02X}",
                'host_addr': f"0x{data[1]:02X}",
                'command': f"0x{data[2]:02X}",
                'data_length': data[3],
                'payload': data[4:12].hex().upper(),
                'checksum': f"0x{data[12]:02X}",
                'checksum_valid': sum(data[:12]) & 0xFF == data[12]
            })
        
        # 檢查 DALY D2 協議  
        elif data[0] == 0xD2 and len(data) >= 8:
            analysis.update({
                'protocol': 'DALY_D2',
                'start_byte': f"0x{data[0]:02X}",
                'function': f"0x{data[1]:02X}",
                'command': f"0x{data[2]:02X}",
                'payload': data[3:].hex().upper()
            })
        
        # 檢查 Sinowealth 協議
        elif data[0] == 0xDD and len(data) >= 7:
            analysis.update({
                'protocol': 'Sinowealth',
                'start_bytes': data[:2].hex().upper(),
                'command': f"0x{data[2]:02X}",
                'payload': data[3:].hex().upper()
            })
        
        else:
            analysis.update({
                'protocol': 'Unknown',
                'start_byte': f"0x{data[0]:02X}",
                'length': len(data)
            })
        
        return analysis
    
    def generate_protocol_report(self):
        """生成協議分析報告"""
        console.print("\n" + "="*80)
        console.print("[bold blue]📊 HCI 日誌協議分析報告[/bold blue]")
        console.print("="*80)
        
        # 統計信息
        console.print(f"\n[cyan]📈 統計信息:[/cyan]")
        console.print(f"  GATT 寫入操作: {len(self.gatt_writes)}")
        console.print(f"  GATT 通知: {len(self.gatt_notifications)}")
        console.print(f"  協議序列: {len(self.protocol_sequences)}")
        
        # 顯示重要的協議序列
        if self.protocol_sequences:
            console.print(f"\n[green]🔍 重要協議序列:[/green]")
            
            table = Table(title="Smart BMS 通訊序列")
            table.add_column("序列", width=8)
            table.add_column("寫入命令", width=30)
            table.add_column("協議分析", width=20)
            table.add_column("響應數", width=10)
            
            for i, seq in enumerate(self.protocol_sequences[:10]):  # 顯示前10個
                write_data = seq['write']['data']
                cmd_hex = write_data.hex().upper()
                
                analysis = seq.get('analysis', {})
                protocol = analysis.get('protocol', 'Unknown')
                
                table.add_row(
                    str(i+1),
                    cmd_hex[:28] + "..." if len(cmd_hex) > 28 else cmd_hex,
                    protocol,
                    str(len(seq['responses']))
                )
            
            console.print(table)
        
        # 詳細分析最重要的序列
        if self.protocol_sequences:
            console.print(f"\n[green]🎯 詳細協議分析:[/green]")
            
            # 找出最有可能是初始化的序列（通常是前幾個）
            init_sequences = self.protocol_sequences[:3]
            
            for i, seq in enumerate(init_sequences):
                console.print(f"\n[yellow]序列 {i+1} (可能的初始化命令):[/yellow]")
                
                write_data = seq['write']['data']
                analysis = seq.get('analysis', {})
                
                if analysis:
                    console.print(f"  協議類型: {analysis.get('protocol', 'Unknown')}")
                    console.print(f"  原始數據: {analysis['raw']}")
                    
                    if analysis.get('protocol') == 'DALY_A5':
                        console.print(f"  主機地址: {analysis['host_addr']}")
                        console.print(f"  命令代碼: {analysis['command']}")
                        console.print(f"  數據負載: {analysis['payload']}")
                        console.print(f"  校驗和正確: {analysis['checksum_valid']}")
                    
                    # 顯示響應
                    if seq['responses']:
                        console.print(f"  響應數量: {len(seq['responses'])}")
                        for j, resp in enumerate(seq['responses'][:2]):  # 顯示前2個響應
                            resp_hex = resp['data'].hex().upper()
                            console.print(f"    響應 {j+1}: {resp_hex}")
                    else:
                        console.print("  無響應")
        
        # 提供 Python 實現建議
        if self.protocol_sequences:
            console.print(f"\n[yellow]💡 Python 實現建議:[/yellow]")
            
            # 找出最常見的協議格式
            protocol_count = defaultdict(int)
            for seq in self.protocol_sequences:
                analysis = seq.get('analysis', {})
                protocol = analysis.get('protocol', 'Unknown')
                protocol_count[protocol] += 1
            
            most_common = max(protocol_count.items(), key=lambda x: x[1])
            console.print(f"  最常用協議: {most_common[0]} ({most_common[1]} 次)")
            
            # 生成示例代碼
            if most_common[0] == 'DALY_A5':
                console.print("\n  示例 Python 代碼:")
                code = '''# 基於 HCI 分析的 DALY A5 協議實現
def create_daly_a5_command(host_addr, command, payload=None):
    packet = bytearray(13)
    packet[0] = 0xA5
    packet[1] = host_addr
    packet[2] = command  
    packet[3] = 0x08
    if payload:
        packet[4:4+len(payload)] = payload
    checksum = sum(packet[:12]) & 0xFF
    packet[12] = checksum
    return bytes(packet)

# 使用分析出的參數
command = create_daly_a5_command(0x80, 0x90)  # 基本資訊查詢'''
                
                syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                console.print(syntax)
        
        console.print("="*80)
    
    def export_commands_to_file(self, filename: str):
        """導出發現的命令到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# DALY BMS 協議命令 (從 HCI 日誌提取)\n")
                f.write(f"# 分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 目標設備: {self.target_mac if self.target_mac else 'All'}\n\n")
                
                f.write("# 發現的命令序列:\n")
                for i, seq in enumerate(self.protocol_sequences):
                    write_data = seq['write']['data']
                    analysis = seq.get('analysis', {})
                    
                    f.write(f"\n# 序列 {i+1}\n")
                    f.write(f"command_{i+1} = bytes.fromhex('{write_data.hex().upper()}')\n")
                    
                    if analysis:
                        f.write(f"# 協議: {analysis.get('protocol', 'Unknown')}\n")
                        if 'command' in analysis:
                            f.write(f"# 命令代碼: {analysis['command']}\n")
                    
                    if seq['responses']:
                        f.write(f"# 預期響應: {len(seq['responses'])} 個\n")
                        for j, resp in enumerate(seq['responses']):
                            f.write(f"# 響應 {j+1}: {resp['data'].hex().upper()}\n")
            
            console.print(f"[green]✅ 命令已導出到: {filename}[/green]")
        
        except Exception as e:
            console.print(f"[red]導出失敗: {e}[/red]")

def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 HCI 日誌文件路徑[/red]")
        console.print("用法: python hci_log_analyzer.py <日誌文件> [目標MAC地址]")
        console.print("範例: python hci_log_analyzer.py btsnoop_hci.log 41:18:12:01:37:71")
        return 1
    
    log_file = sys.argv[1]
    target_mac = sys.argv[2] if len(sys.argv) > 2 else None
    
    analyzer = HCILogAnalyzer(log_file, target_mac)
    
    console.print("[bold blue]🔍 HCI 日誌分析工具[/bold blue]")
    console.print("="*60)
    console.print(f"日誌文件: {log_file}")
    if target_mac:
        console.print(f"目標設備: {target_mac}")
    console.print("")
    
    try:
        # 讀取日誌
        packets = analyzer.read_btsnoop_log()
        if not packets:
            return 1
        
        # 分析封包
        analyzer.analyze_packets(packets)
        
        # 識別協議序列
        analyzer.identify_protocol_sequences()
        
        # 分析 DALY 協議
        analyzer.analyze_daly_protocol()
        
        # 生成報告
        analyzer.generate_protocol_report()
        
        # 導出命令
        if analyzer.protocol_sequences:
            output_file = f"daly_commands_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            analyzer.export_commands_to_file(output_file)
        
    except Exception as e:
        console.print(f"[red]分析過程中發生錯誤: {e}[/red]")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())