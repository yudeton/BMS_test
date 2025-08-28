#!/usr/bin/env python3
"""
智能協議探測工具
使用機器學習方法和啟發式算法來發現 BMS 協議
自動識別有效的通訊模式和數據結構
"""

import asyncio
import sys
import time
import random
import struct
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Set
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from bleak import BleakClient, BleakScanner

console = Console()

class SmartProtocolExplorer:
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        
        # 特徵值
        self.write_char = "0000fff2-0000-1000-8000-00805f9b34fb" 
        self.read_char = "0000fff1-0000-1000-8000-00805f9b34fb"
        
        # 學習數據
        self.command_responses = {}  # 命令 -> 響應列表
        self.response_patterns = defaultdict(int)  # 響應模式 -> 頻次
        self.successful_commands = []
        self.learning_data = []
        
        # 智能探測參數
        self.mutation_rate = 0.3
        self.generation_size = 20
        self.max_generations = 5
        
        # 已知成功的種子命令
        self.seed_commands = [
            bytes.fromhex("A58090080000000000000000BD"),
            bytes.fromhex("A58093080000000000000000C0"),
            bytes.fromhex("DD A5 03 00 FF FD 77"),
            bytes.fromhex("D203030000011234"),
        ]
    
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
    
    def notification_handler(self, sender, data):
        """處理通知數據"""
        if data:
            self.current_responses.append({
                'timestamp': datetime.now(),
                'data': data,
                'hex': data.hex().upper(),
                'length': len(data)
            })
    
    async def send_and_analyze(self, command: bytes) -> Dict:
        """發送命令並分析響應"""
        self.current_responses = []
        
        try:
            await self.client.start_notify(self.read_char, self.notification_handler)
            await self.client.write_gatt_char(self.write_char, command, response=False)
            await asyncio.sleep(0.6)
            await self.client.stop_notify(self.read_char)
            
            # 分析響應
            analysis = self.analyze_response(command, self.current_responses)
            
            # 記錄學習數據
            cmd_hex = command.hex().upper()
            if cmd_hex not in self.command_responses:
                self.command_responses[cmd_hex] = []
            self.command_responses[cmd_hex].extend(self.current_responses)
            
            return analysis
            
        except Exception as e:
            return {'error': str(e), 'score': 0}
    
    def analyze_response(self, command: bytes, responses: List[Dict]) -> Dict:
        """分析響應質量並打分"""
        if not responses:
            return {'score': 0, 'reason': 'no_response'}
        
        analysis = {
            'command': command.hex().upper(),
            'responses': responses,
            'score': 0,
            'features': {}
        }
        
        for response in responses:
            data = response['data']
            
            # 檢查是否為回音
            if data == command:
                analysis['score'] -= 10
                analysis['features']['echo'] = True
                continue
            
            # 長度分析
            if len(data) >= 8:
                analysis['score'] += 5
                analysis['features']['good_length'] = True
            
            # 數據變化性分析
            unique_bytes = len(set(data))
            if unique_bytes > len(data) // 4:  # 超過1/4的位元組不重複
                analysis['score'] += 10
                analysis['features']['data_variety'] = True
            
            # 非零數據分析
            non_zero_count = sum(1 for b in data if b != 0)
            if non_zero_count > len(data) // 3:  # 超過1/3非零
                analysis['score'] += 15
                analysis['features']['meaningful_data'] = True
            
            # 協議頭分析
            if data[0] in [0xA5, 0xD2, 0x01]:
                analysis['score'] += 5
                analysis['features']['known_header'] = True
            
            # 檢查是否包含可能的電池數據
            if len(data) >= 8:
                # 檢查是否有合理的電壓值 (例如 10V-60V)
                for i in range(len(data) - 1):
                    voltage = int.from_bytes(data[i:i+2], 'big') / 10.0
                    if 10.0 <= voltage <= 60.0:
                        analysis['score'] += 20
                        analysis['features']['possible_voltage'] = voltage
                        break
                
                # 檢查是否有合理的百分比值 (0-100)
                for b in data:
                    if 0 <= b <= 100:
                        analysis['score'] += 5
                        analysis['features']['possible_percentage'] = True
                        break
        
        # 記錄響應模式
        for response in responses:
            pattern = f"len{len(response['data'])}_start{response['data'][0]:02X}" if response['data'] else "empty"
            self.response_patterns[pattern] += 1
        
        return analysis
    
    def mutate_command(self, command: bytes) -> bytes:
        """對命令進行突變以產生新的測試命令"""
        if not command:
            return bytes([random.randint(0, 255) for _ in range(random.randint(1, 20))])
        
        mutated = bytearray(command)
        
        # 隨機選擇突變類型
        mutation_types = ['flip_bit', 'change_byte', 'add_byte', 'remove_byte', 'swap_bytes']
        mutation = random.choice(mutation_types)
        
        if mutation == 'flip_bit' and len(mutated) > 0:
            # 翻轉一個位元
            pos = random.randint(0, len(mutated) - 1)
            bit = random.randint(0, 7)
            mutated[pos] ^= (1 << bit)
        
        elif mutation == 'change_byte' and len(mutated) > 0:
            # 改變一個位元組
            pos = random.randint(0, len(mutated) - 1)
            mutated[pos] = random.randint(0, 255)
        
        elif mutation == 'add_byte':
            # 添加一個位元組
            pos = random.randint(0, len(mutated))
            mutated.insert(pos, random.randint(0, 255))
        
        elif mutation == 'remove_byte' and len(mutated) > 1:
            # 移除一個位元組
            pos = random.randint(0, len(mutated) - 1)
            del mutated[pos]
        
        elif mutation == 'swap_bytes' and len(mutated) > 1:
            # 交換兩個位元組
            pos1 = random.randint(0, len(mutated) - 1)
            pos2 = random.randint(0, len(mutated) - 1)
            mutated[pos1], mutated[pos2] = mutated[pos2], mutated[pos1]
        
        return bytes(mutated)
    
    def crossover_commands(self, cmd1: bytes, cmd2: bytes) -> bytes:
        """交叉兩個命令產生新命令"""
        if not cmd1 or not cmd2:
            return cmd1 if cmd1 else cmd2
        
        # 隨機選擇交叉點
        min_len = min(len(cmd1), len(cmd2))
        if min_len <= 1:
            return cmd1
        
        crossover_point = random.randint(1, min_len - 1)
        
        # 創建混合命令
        new_cmd = cmd1[:crossover_point] + cmd2[crossover_point:]
        return new_cmd
    
    async def genetic_exploration(self) -> List[Dict]:
        """使用遺傳算法探索協議"""
        console.print("\n[bold cyan]🧬 啟動遺傳算法探索...[/bold cyan]")
        
        # 初始化種群
        population = list(self.seed_commands)
        
        # 添加隨機命令
        for _ in range(self.generation_size - len(population)):
            length = random.choice([7, 8, 13, 20])
            random_cmd = bytes([random.randint(0, 255) for _ in range(length)])
            population.append(random_cmd)
        
        best_commands = []
        
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("遺傳算法進化", total=self.max_generations)
            
            for generation in range(self.max_generations):
                progress.update(task, description=f"第 {generation+1} 代進化")
                
                # 評估當前種群
                fitness_scores = []
                for cmd in population:
                    analysis = await self.send_and_analyze(cmd)
                    fitness_scores.append((cmd, analysis['score'], analysis))
                
                # 排序並選擇最優個體
                fitness_scores.sort(key=lambda x: x[1], reverse=True)
                
                # 記錄最佳命令
                for cmd, score, analysis in fitness_scores[:3]:  # 取前3名
                    if score > 5:  # 只記錄有意義的結果
                        best_commands.append({
                            'command': cmd.hex().upper(),
                            'score': score,
                            'analysis': analysis,
                            'generation': generation
                        })
                        console.print(f"[green]🎯 發現有效命令 (得分:{score}): {cmd.hex().upper()[:20]}...[/green]")
                
                # 選擇和繁殖下一代
                next_generation = []
                
                # 保留精英
                elite_count = max(1, self.generation_size // 4)
                for cmd, _, _ in fitness_scores[:elite_count]:
                    next_generation.append(cmd)
                
                # 生成新個體
                while len(next_generation) < self.generation_size:
                    if random.random() < 0.7:  # 70% 機率突變
                        parent = random.choice([cmd for cmd, _, _ in fitness_scores[:8]])
                        child = self.mutate_command(parent)
                    else:  # 30% 機率交叉
                        parent1 = random.choice([cmd for cmd, _, _ in fitness_scores[:6]])
                        parent2 = random.choice([cmd for cmd, _, _ in fitness_scores[:6]])
                        child = self.crossover_commands(parent1, parent2)
                    
                    next_generation.append(child)
                
                population = next_generation
                progress.advance(task, 1)
        
        return best_commands
    
    async def pattern_analysis(self):
        """分析發現的模式"""
        console.print("\n[bold cyan]📊 分析通訊模式...[/bold cyan]")
        
        if not self.response_patterns:
            console.print("[yellow]未收集到足夠的響應數據進行模式分析[/yellow]")
            return
        
        # 顯示最常見的響應模式
        console.print("\n[cyan]最常見的響應模式:[/cyan]")
        sorted_patterns = sorted(self.response_patterns.items(), key=lambda x: x[1], reverse=True)
        
        table = Table(title="響應模式分析")
        table.add_column("模式", style="cyan")
        table.add_column("出現次數", style="green")
        table.add_column("可能含義", style="yellow")
        
        for pattern, count in sorted_patterns[:10]:
            meaning = self.interpret_pattern(pattern)
            table.add_row(pattern, str(count), meaning)
        
        console.print(table)
        
        # 尋找相關性
        console.print("\n[cyan]尋找命令-響應相關性:[/cyan]")
        correlations = self.find_correlations()
        if correlations:
            for correlation in correlations[:5]:
                console.print(f"  - {correlation}")
        else:
            console.print("  未發現明顯的相關性")
    
    def interpret_pattern(self, pattern: str) -> str:
        """解釋響應模式的可能含義"""
        if "len13" in pattern and "startA5" in pattern:
            return "標準 DALY A5 協議"
        elif "len8" in pattern and "startD2" in pattern:
            return "DALY D2 新協議"
        elif "len7" in pattern:
            return "可能是 Sinowealth 協議"
        elif "len0" in pattern:
            return "無響應或空數據"
        elif "start01" in pattern:
            return "可能是 BMS 回覆"
        else:
            return "未知協議"
    
    def find_correlations(self) -> List[str]:
        """尋找命令和響應之間的相關性"""
        correlations = []
        
        # 分析命令開頭與響應的關係
        cmd_start_response = defaultdict(set)
        
        for cmd_hex, responses in self.command_responses.items():
            if cmd_hex and responses:
                try:
                    cmd_start = int(cmd_hex[:2], 16)
                    for response in responses:
                        if response['data']:
                            resp_start = response['data'][0]
                            cmd_start_response[cmd_start].add(resp_start)
                except:
                    continue
        
        for cmd_start, resp_starts in cmd_start_response.items():
            if len(resp_starts) == 1:  # 一對一映射
                resp_start = list(resp_starts)[0]
                correlations.append(f"命令開頭 0x{cmd_start:02X} → 響應開頭 0x{resp_start:02X}")
        
        return correlations
    
    async def targeted_exploration(self, successful_patterns: List[Dict]):
        """基於成功模式的定向探索"""
        console.print("\n[bold cyan]🎯 基於成功模式的定向探索...[/bold cyan]")
        
        if not successful_patterns:
            console.print("[yellow]沒有成功模式可供定向探索[/yellow]")
            return
        
        # 對每個成功模式進行擴展
        for pattern in successful_patterns[:3]:  # 只探索前3個最佳模式
            cmd_bytes = bytes.fromhex(pattern['command'])
            console.print(f"[cyan]探索成功命令的變體: {pattern['command'][:20]}...[/cyan]")
            
            # 生成該命令的變體
            variants = []
            
            # 修改單個位元組
            for i in range(len(cmd_bytes)):
                for delta in [-1, 1, 0x10, -0x10]:
                    new_cmd = bytearray(cmd_bytes)
                    new_val = (new_cmd[i] + delta) & 0xFF
                    new_cmd[i] = new_val
                    variants.append(bytes(new_cmd))
            
            # 測試變體
            tested = 0
            for variant in variants:
                if tested >= 20:  # 限制測試數量
                    break
                
                analysis = await self.send_and_analyze(variant)
                if analysis['score'] > 5:
                    console.print(f"[green]✨ 發現有效變體: {variant.hex().upper()[:20]}... (得分:{analysis['score']})[/green]")
                    self.successful_commands.append({
                        'command': variant.hex().upper(),
                        'score': analysis['score'],
                        'analysis': analysis,
                        'type': 'variant'
                    })
                
                tested += 1
                
                # 避免過快發送
                if tested % 5 == 0:
                    await asyncio.sleep(0.5)
    
    def generate_intelligence_report(self, best_commands: List[Dict]):
        """生成智能分析報告"""
        console.print("\n" + "="*80)
        console.print("[bold blue]🤖 智能協議探索報告[/bold blue]")
        console.print("="*80)
        
        console.print(f"\n[cyan]📈 探索統計:[/cyan]")
        console.print(f"  測試的命令總數: {len(self.command_responses)}")
        console.print(f"  發現的響應模式: {len(self.response_patterns)}")
        console.print(f"  高分命令數量: {len([cmd for cmd in best_commands if cmd['score'] > 10])}")
        
        if best_commands:
            console.print(f"\n[green]🎯 發現的最佳命令:[/green]")
            
            # 按分數排序
            sorted_commands = sorted(best_commands, key=lambda x: x['score'], reverse=True)
            
            table = Table(title="最佳命令排行")
            table.add_column("排名", style="cyan", width=6)
            table.add_column("命令", style="green", width=20)
            table.add_column("得分", style="yellow", width=8)
            table.add_column("特徵", style="dim", width=30)
            
            for i, cmd in enumerate(sorted_commands[:10], 1):
                features = []
                if 'meaningful_data' in cmd['analysis'].get('features', {}):
                    features.append("有意義數據")
                if 'possible_voltage' in cmd['analysis'].get('features', {}):
                    voltage = cmd['analysis']['features']['possible_voltage']
                    features.append(f"疑似電壓:{voltage:.1f}V")
                if 'known_header' in cmd['analysis'].get('features', {}):
                    features.append("已知協議頭")
                
                table.add_row(
                    str(i),
                    cmd['command'][:18] + "...",
                    str(cmd['score']),
                    ", ".join(features) if features else "無特殊特徵"
                )
            
            console.print(table)
            
            # 詳細分析最佳命令
            if sorted_commands[0]['score'] > 15:
                best = sorted_commands[0]
                console.print(f"\n[green]🏆 最佳命令詳細分析:[/green]")
                console.print(f"  命令: {best['command']}")
                console.print(f"  得分: {best['score']}")
                
                features = best['analysis'].get('features', {})
                if features:
                    console.print("  特徵:")
                    for feature, value in features.items():
                        console.print(f"    - {feature}: {value}")
        
        else:
            console.print(f"\n[red]❌ 未發現高分命令[/red]")
        
        # 給出建議
        console.print(f"\n[yellow]💡 智能建議:[/yellow]")
        if best_commands:
            best_score = max(cmd['score'] for cmd in best_commands)
            if best_score > 20:
                console.print("  🎉 發現了很可能有效的協議格式！")
                console.print("  建議：深入分析最佳命令的響應數據")
            elif best_score > 10:
                console.print("  ✨ 發現了一些有希望的協議格式")
                console.print("  建議：對高分命令進行更深入的變體測試")
            else:
                console.print("  📊 收集了有用的響應模式")
                console.print("  建議：嘗試更多的協議變體")
        else:
            console.print("  🔬 需要嘗試更多探索策略")
            console.print("  建議：使用 Android HCI 日誌捕獲真實協議")
        
        console.print("="*80)
    
    async def run_smart_exploration(self):
        """執行智能探索"""
        console.print("\n[bold green]🚀 啟動智能協議探索...[/bold green]")
        
        # 階段 1: 遺傳算法探索
        best_commands = await self.genetic_exploration()
        
        # 階段 2: 模式分析
        await self.pattern_analysis()
        
        # 階段 3: 定向探索
        await self.targeted_exploration(best_commands)
        
        # 合併所有成功命令
        all_successful = best_commands + self.successful_commands
        
        # 階段 4: 生成智能報告
        self.generate_intelligence_report(all_successful)
        
        return all_successful
    
    async def disconnect(self):
        """斷開連線"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            console.print("[yellow]已斷開連線[/yellow]")

async def main():
    if len(sys.argv) < 2:
        console.print("[red]請提供 MAC 地址[/red]")
        console.print("用法: python smart_protocol_explorer.py <MAC地址>")
        console.print("範例: python smart_protocol_explorer.py 41:18:12:01:37:71")
        return 1
    
    mac_address = sys.argv[1]
    
    explorer = SmartProtocolExplorer(mac_address)
    
    console.print("[bold blue]🤖 智能協議探測工具[/bold blue]")
    console.print("="*70)
    console.print(f"目標設備: {mac_address}")
    console.print("策略: 遺傳算法 + 模式識別 + 啟發式搜索")
    console.print("目標: 自動發現有效的 BMS 通訊協議")
    console.print("")
    
    try:
        # 建立連線
        if not await explorer.connect():
            return 1
        
        # 執行智能探索
        successful = await explorer.run_smart_exploration()
        
        # 如果找到成功的協議，提供使用建議
        if successful:
            high_score_commands = [cmd for cmd in successful if cmd.get('score', 0) > 15]
            if high_score_commands:
                console.print("\n[bold green]🎉 探索成功！[/bold green]")
                console.print("發現了可能有效的協議格式。")
                console.print("建議：使用這些命令創建專用的 BMS 通訊工具。")
            else:
                console.print("\n[yellow]📊 探索完成[/yellow]")
                console.print("收集了有用的數據，但未找到明確有效的協議。")
                console.print("建議：嘗試 Android HCI 日誌分析獲取更準確的協議信息。")
        else:
            console.print("\n[red]❌ 探索未發現有效協議[/red]")
            console.print("建議使用其他方法獲取協議信息。")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]使用者中斷探索[/yellow]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")
        return 1
    finally:
        await explorer.disconnect()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)