#!/usr/bin/env python3
"""
BMS 設備自動斷線檢查工具
自動檢查並斷開被系統占用的 BMS 設備連接
"""

import asyncio
import subprocess
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DeviceStatus:
    """設備狀態信息"""
    mac_address: str
    name: Optional[str] = None
    connected: bool = False
    paired: bool = False
    trusted: bool = False
    available: bool = True
    error: Optional[str] = None

class BMSAutoDisconnect:
    """BMS 設備自動斷線管理器"""
    
    def __init__(self, mac_address: str = "41:18:12:01:37:71"):
        self.mac_address = mac_address.upper()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _run_bluetoothctl_command(self, command: str, timeout: int = 10) -> Tuple[bool, str]:
        """執行 bluetoothctl 命令"""
        try:
            result = subprocess.run(
                ["bluetoothctl", command, self.mac_address],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except subprocess.CalledProcessError as e:
            return False, f"Command failed: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def check_device_status(self) -> DeviceStatus:
        """檢查設備當前狀態"""
        status = DeviceStatus(mac_address=self.mac_address)
        
        try:
            # 使用 bluetoothctl info 命令檢查設備信息
            success, output = self._run_bluetoothctl_command("info")
            
            if not success:
                if "Device" in output and "not available" in output.lower():
                    status.available = False
                    status.error = "Device not found or not available"
                    return status
                else:
                    status.error = f"Failed to get device info: {output}"
                    return status
            
            # 解析輸出
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Name:'):
                    status.name = line.split(':', 1)[1].strip()
                elif line.startswith('Connected:'):
                    status.connected = 'yes' in line.lower()
                elif line.startswith('Paired:'):
                    status.paired = 'yes' in line.lower()
                elif line.startswith('Trusted:'):
                    status.trusted = 'yes' in line.lower()
            
            self.logger.debug(f"設備狀態: {status}")
            return status
            
        except Exception as e:
            status.error = f"Exception during status check: {e}"
            self.logger.error(f"檢查設備狀態失敗: {e}")
            return status
    
    def disconnect_device(self, max_retries: int = 3) -> bool:
        """斷開設備連接"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"嘗試斷開設備 {self.mac_address} (嘗試 {attempt + 1}/{max_retries})")
                
                success, output = self._run_bluetoothctl_command("disconnect", timeout=15)
                
                if success:
                    # 等待斷開完成
                    time.sleep(2)
                    
                    # 驗證斷開狀態
                    status = self.check_device_status()
                    if not status.connected:
                        self.logger.info(f"✅ 設備 {self.mac_address} 成功斷開")
                        return True
                    else:
                        self.logger.warning(f"設備顯示已斷開但狀態仍為連接，重試...")
                        continue
                else:
                    self.logger.warning(f"斷開命令失敗: {output}")
                    if "not connected" in output.lower():
                        # 設備本來就沒連接
                        self.logger.info(f"設備 {self.mac_address} 本來就沒有連接")
                        return True
                    
                # 重試前等待
                if attempt < max_retries - 1:
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"斷開設備時發生錯誤: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                
        self.logger.error(f"❌ 經過 {max_retries} 次嘗試後仍無法斷開設備 {self.mac_address}")
        return False
    
    def auto_disconnect_if_connected(self) -> Dict[str, Any]:
        """如果設備被系統連接，則自動斷開"""
        result = {
            "mac_address": self.mac_address,
            "initial_connected": False,
            "action_taken": "none",
            "final_connected": False,
            "success": False,
            "message": "",
            "device_info": {}
        }
        
        try:
            # 檢查初始狀態
            initial_status = self.check_device_status()
            result["initial_connected"] = initial_status.connected
            result["device_info"] = {
                "name": initial_status.name,
                "available": initial_status.available,
                "paired": initial_status.paired,
                "trusted": initial_status.trusted
            }
            
            if not initial_status.available:
                result["message"] = "設備不可用或未找到"
                result["success"] = True  # 設備不存在也算成功
                return result
            
            if initial_status.error:
                result["message"] = f"檢查設備狀態失敗: {initial_status.error}"
                return result
            
            if not initial_status.connected:
                result["message"] = "設備未被系統連接，無需斷開"
                result["success"] = True
                return result
            
            # 設備被連接，需要斷開
            self.logger.info(f"🔌 檢測到設備 {self.mac_address} ({initial_status.name}) 被系統連接")
            result["action_taken"] = "disconnect"
            
            # 執行斷開
            disconnect_success = self.disconnect_device()
            
            # 檢查最終狀態
            final_status = self.check_device_status()
            result["final_connected"] = final_status.connected
            
            if disconnect_success and not final_status.connected:
                result["success"] = True
                result["message"] = f"✅ 設備 {self.mac_address} 已成功從系統斷開"
                self.logger.info(result["message"])
            else:
                result["success"] = False
                result["message"] = f"❌ 無法斷開設備 {self.mac_address}"
                self.logger.error(result["message"])
                
        except Exception as e:
            result["message"] = f"自動斷線過程中發生錯誤: {e}"
            self.logger.error(result["message"])
        
        return result
    
    async def async_auto_disconnect_if_connected(self) -> Dict[str, Any]:
        """異步版本的自動斷線功能"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.auto_disconnect_if_connected
        )

def check_and_disconnect_bms(mac_address: str = "41:18:12:01:37:71") -> Dict[str, Any]:
    """便捷函數：檢查並斷開 BMS 設備連接"""
    disconnector = BMSAutoDisconnect(mac_address)
    return disconnector.auto_disconnect_if_connected()

async def async_check_and_disconnect_bms(mac_address: str = "41:18:12:01:37:71") -> Dict[str, Any]:
    """異步便捷函數：檢查並斷開 BMS 設備連接"""
    disconnector = BMSAutoDisconnect(mac_address)
    return await disconnector.async_auto_disconnect_if_connected()

# 測試功能
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔧 BMS 自動斷線檢查工具測試")
    print("=" * 50)
    
    # 測試同步版本
    result = check_and_disconnect_bms()
    
    print(f"\n📊 測試結果:")
    print(f"  設備 MAC: {result['mac_address']}")
    print(f"  初始連接狀態: {result['initial_connected']}")
    print(f"  採取的動作: {result['action_taken']}")
    print(f"  最終連接狀態: {result['final_connected']}")
    print(f"  執行成功: {result['success']}")
    print(f"  訊息: {result['message']}")
    
    if result.get('device_info'):
        info = result['device_info']
        print(f"\n📋 設備信息:")
        print(f"  名稱: {info.get('name', 'Unknown')}")
        print(f"  可用: {info.get('available', False)}")
        print(f"  已配對: {info.get('paired', False)}")
        print(f"  受信任: {info.get('trusted', False)}")
