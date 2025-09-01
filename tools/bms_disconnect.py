#!/usr/bin/env python3
"""
BMS 設備斷線命令行工具
用於手動或腳本自動化斷開 BMS 設備的系統連接
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
# 載入 .env（若存在）
load_dotenv(dotenv_path=project_root / ".env", override=False)
# 將專案根目錄與 bms-monitor 模組目錄加入 Python 路徑
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "bms-monitor"))

# 直接從 app 套件導入（bms-monitor 目錄名含連字號，無法作為頂層模組名）
from app.utils.bms_auto_disconnect import BMSAutoDisconnect, check_and_disconnect_bms

def setup_logging(level: str = "INFO"):
    """設置日誌"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def print_status_table(result: dict):
    """以表格形式打印狀態信息"""
    print("\n" + "=" * 60)
    print("🔧 BMS 設備斷線檢查結果")
    print("=" * 60)
    
    # 基本信息
    print(f"📱 設備 MAC 地址: {result['mac_address']}")
    
    if result.get('device_info', {}).get('name'):
        print(f"📛 設備名稱:     {result['device_info']['name']}")
    
    # 狀態信息
    print(f"\n🔍 檢查結果:")
    print(f"  初始連接狀態: {'🔴 已連接' if result['initial_connected'] else '⚪ 未連接'}")
    print(f"  最終連接狀態: {'🔴 已連接' if result['final_connected'] else '⚪ 未連接'}")
    
    # 動作信息
    action_icons = {
        "none": "⚪",
        "disconnect": "🔌"
    }
    action_descriptions = {
        "none": "無需動作",
        "disconnect": "執行斷線"
    }
    
    action = result.get('action_taken', 'none')
    print(f"  採取動作:     {action_icons.get(action, '❓')} {action_descriptions.get(action, action)}")
    
    # 執行結果
    success_icon = "✅" if result['success'] else "❌"
    print(f"  執行結果:     {success_icon} {result['message']}")
    
    # 設備詳細信息
    if result.get('device_info'):
        info = result['device_info']
        print(f"\n📋 設備詳細信息:")
        print(f"  設備可用:     {'✅' if info.get('available', False) else '❌'}")
        print(f"  已配對:       {'✅' if info.get('paired', False) else '❌'}")
        print(f"  受信任:       {'✅' if info.get('trusted', False) else '❌'}")
    
    print("=" * 60)

def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="BMS 設備自動斷線工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  %(prog)s                                    # 使用預設 MAC 地址
  %(prog)s -m AA:BB:CC:DD:EE:FF              # 指定 MAC 地址  
  %(prog)s --check-only                      # 僅檢查狀態，不斷線
  %(prog)s --json                            # 以 JSON 格式輸出
  %(prog)s --verbose                         # 詳細日誌輸出
        """
    )
    
    default_mac = os.getenv("BMS_MAC_ADDRESS", "41:18:12:01:37:71")
    parser.add_argument(
        "-m", "--mac-address", 
        default=default_mac,
        help=f"BMS 設備 MAC 地址 (預設: {default_mac})"
    )
    
    parser.add_argument(
        "--check-only", 
        action="store_true",
        help="僅檢查設備狀態，不執行斷線"
    )
    
    parser.add_argument(
        "--json", 
        action="store_true",
        help="以 JSON 格式輸出結果"
    )
    
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="顯示詳細日誌"
    )
    
    parser.add_argument(
        "--quiet", "-q", 
        action="store_true",
        help="安靜模式，僅輸出錯誤"
    )
    
    args = parser.parse_args()
    
    # 設置日誌級別
    if args.quiet:
        log_level = "ERROR"
    elif args.verbose:
        log_level = "DEBUG"  
    else:
        log_level = "INFO"
    
    setup_logging(log_level)
    
    try:
        # 創建斷線管理器
        disconnector = BMSAutoDisconnect(args.mac_address)
        
        if args.check_only:
            # 僅檢查狀態
            if not args.quiet:
                print(f"🔍 檢查設備 {args.mac_address} 的連接狀態...")
            
            status = disconnector.check_device_status()
            
            result = {
                "mac_address": args.mac_address,
                "initial_connected": status.connected,
                "action_taken": "check_only", 
                "final_connected": status.connected,
                "success": not bool(status.error),
                "message": status.error or f"設備狀態: {'已連接' if status.connected else '未連接'}",
                "device_info": {
                    "name": status.name,
                    "available": status.available,
                    "paired": status.paired,
                    "trusted": status.trusted
                }
            }
        else:
            # 執行自動斷線
            if not args.quiet:
                print(f"🔧 檢查並斷開設備 {args.mac_address} 的系統連接...")
            
            result = disconnector.auto_disconnect_if_connected()
        
        # 輸出結果
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if not args.quiet:
                print_status_table(result)
            else:
                # 安靜模式只輸出重要信息
                if not result['success']:
                    print(f"ERROR: {result['message']}", file=sys.stderr)
        
        # 設置退出代碼
        sys.exit(0 if result['success'] else 1)
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n⚠️  操作被用戶中斷")
        sys.exit(130)
        
    except Exception as e:
        error_msg = f"執行過程中發生未預期的錯誤: {e}"
        if args.json:
            error_result = {
                "mac_address": args.mac_address,
                "success": False,
                "error": error_msg
            }
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
        else:
            print(f"❌ {error_msg}", file=sys.stderr)
        
        if args.verbose:
            import traceback
            traceback.print_exc()
            
        sys.exit(1)

if __name__ == "__main__":
    main()
