"""服务管理模块"""
import subprocess
import platform
import time
import logging
from pathlib import Path
from typing import Optional

from config import Config
from exceptions import ServiceError, PlatformNotSupportedError
from constants import PLATFORM_MACOS, PLATFORM_WINDOWS, ZEROTIER_SERVICE_NAME

logger = logging.getLogger(__name__)

class ServiceManager:
    """ZeroTier服务管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logger
        self.platform = platform.system().lower()
    
    def _run_command(self, command: list[str], timeout: int = 30) -> tuple[bool, str]:
        """
        执行系统命令
        
        Args:
            command: 命令列表
            timeout: 超时时间（秒）
            
        Returns:
            tuple[bool, str]: (是否成功, 输出信息)
        """
        try:
            self.logger.debug(f"执行命令: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            success = result.returncode == 0
            output = result.stdout.strip() if result.stdout else result.stderr.strip()
            return success, output
            
        except subprocess.TimeoutExpired:
            error_msg = f"命令执行超时: {' '.join(command)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"命令执行异常: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    
    def _check_zerotier_daemon_running(self) -> bool:
        """
        专门检查ZeroTier后台服务（daemon）是否在运行
        
        Returns:
            bool: 后台服务是否在运行
        """
        try:
            # 方法1: 检查launchd服务状态
            success, output = self._run_command([
                "sudo", "launchctl", "list", "com.zerotier.one"
            ])
            if success and "PID" in output:
                self.logger.debug("通过launchctl检测到ZeroTier后台服务")
                return True
            
            # 方法2: 检查zerotier-cli是否能连接
            success, output = self._run_command(["zerotier-cli", "info"])
            if success:
                self.logger.debug("通过zerotier-cli检测到ZeroTier后台服务")
                return True
            
            # 方法3: 检查TCP端口9993是否被监听
            success, output = self._run_command(["lsof", "-i", ":9993"])
            if success and "zerotier" in output.lower():
                self.logger.debug("通过端口检测到ZeroTier后台服务")
                return True
            
            self.logger.debug("未检测到ZeroTier后台服务")
            return False
            
        except Exception as e:
            self.logger.error(f"检查ZeroTier后台服务失败: {e}")
            return False
    
    def _get_zerotier_daemon_pid(self) -> Optional[int]:
        """
        获取ZeroTier后台服务的PID
        
        Returns:
            Optional[int]: 后台服务PID，如果未找到则返回None
        """
        try:
            # 方法1: 通过launchctl获取PID
            success, output = self._run_command([
                "sudo", "launchctl", "list", "com.zerotier.one"
            ])
            if success and "PID" in output:
                for line in output.split('\n'):
                    if 'com.zerotier.one' in line:
                        parts = line.split()
                        if len(parts) > 0 and parts[0].isdigit():
                            pid = int(parts[0])
                            self.logger.debug(f"通过launchctl找到ZeroTier后台服务PID: {pid}")
                            return pid
            
            # 方法2: 通过端口查找进程
            success, output = self._run_command(["lsof", "-t", "-i", ":9993"])
            if success and output.strip():
                pid = int(output.strip().split('\n')[0])
                self.logger.debug(f"通过端口找到ZeroTier后台服务PID: {pid}")
                return pid
            
            self.logger.debug("未找到ZeroTier后台服务PID")
            return None
            
        except Exception as e:
            self.logger.error(f"获取ZeroTier后台服务PID失败: {e}")
            return None
    
    def _check_zerotier_gui_running(self) -> bool:
        """
        检查ZeroTier GUI应用是否在运行
        
        Returns:
            bool: GUI应用是否在运行
        """
        try:
            success, output = self._run_command([
                "pgrep", "-f", "/Applications/ZeroTier.app"
            ])
            if success and output.strip():
                self.logger.debug("检测到ZeroTier GUI应用正在运行")
                return True
            
            self.logger.debug("ZeroTier GUI应用未运行")
            return False
            
        except Exception as e:
            self.logger.error(f"检查ZeroTier GUI应用失败: {e}")
            return False
    
    def _get_zerotier_gui_pid(self) -> Optional[int]:
        """
        获取ZeroTier GUI应用的PID
        
        Returns:
            Optional[int]: GUI应用PID，如果未找到则返回None
        """
        try:
            success, output = self._run_command([
                "pgrep", "-f", "/Applications/ZeroTier.app"
            ])
            if success and output.strip():
                pids = [int(pid.strip()) for pid in output.split('\n') if pid.strip().isdigit()]
                if pids:
                    self.logger.debug(f"找到ZeroTier GUI应用PID: {pids[0]}")
                    return pids[0]
            
            self.logger.debug("未找到ZeroTier GUI应用PID")
            return None
            
        except Exception as e:
            self.logger.error(f"获取ZeroTier GUI应用PID失败: {e}")
            return None
    
    def _stop_zerotier_macos(self) -> bool:
        """
        停止macOS上的ZeroTier服务
        
        停止顺序:
        1. 第一步: 停止ZeroTier GUI应用 (pkill)
        2. 第二步: 停止ZeroTier后台服务 (launchctl)
        3. 第三步: 直接终止进程 (kill信号)
        
        Returns:
            bool: 是否成功停止
        """
        try:
            # 检查当前运行状态
            gui_running = self._check_zerotier_gui_running()
            daemon_running = self._check_zerotier_daemon_running()
            
            if not gui_running and not daemon_running:
                self.logger.info("ZeroTier GUI和后台服务都未运行")
                return True
            
            self.logger.info(f"当前状态 - GUI: {'运行' if gui_running else '未运行'}, 后台服务: {'运行' if daemon_running else '未运行'}")
            
            # 第一步: 停止ZeroTier GUI应用
            if gui_running:
                success, output = self._run_command([
                    "pkill", "-f", "/Applications/ZeroTier.app"
                ])
                
                if success:
                    self.logger.info("第一步: 使用pkill命令停止ZeroTier GUI应用")
                    time.sleep(3)  # 等待应用完全关闭
                    
                    # 检查GUI是否停止
                    if not self._check_zerotier_gui_running():
                        self.logger.info("GUI应用已成功停止")
                    else:
                        self.logger.warning("GUI应用可能未完全停止")
                else:
                    self.logger.debug(f"停止GUI应用失败: {output}")
            else:
                self.logger.info("第一步: GUI应用未运行，跳过")
            
            # 第二步: 停止ZeroTier后台服务
            if daemon_running:
                success, output = self._run_command([
                    "sudo", "launchctl", "unload", 
                    "/Library/LaunchDaemons/com.zerotier.one.plist"
                ])
                
                if success:
                    self.logger.info("第二步: 使用launchctl停止ZeroTier后台服务")
                    time.sleep(2)  # 等待服务完全停止
                    
                    # 检查后台服务是否停止
                    if not self._check_zerotier_daemon_running():
                        self.logger.info("后台服务已成功停止")
                        return True
                    else:
                        self.logger.warning("launchctl执行成功但后台服务仍在运行")
                else:
                    self.logger.warning(f"launchctl停止服务失败: {output}")
            else:
                self.logger.info("第二步: 后台服务未运行，跳过")
            
            # 第三步: 直接终止进程（如果前面的步骤都失败）
            # 重新检查是否还有进程在运行
            remaining_gui_pid = self._get_zerotier_gui_pid()
            remaining_daemon_pid = self._get_zerotier_daemon_pid()
            
            if not remaining_gui_pid and not remaining_daemon_pid:
                self.logger.info("前面的步骤已成功停止所有ZeroTier进程")
                return True
            
            self.logger.warning("前面的步骤未能完全停止进程，尝试直接终止")
            
            # 终止剩余的进程
            all_killed = True
            for pid_type, pid in [("GUI", remaining_gui_pid), ("后台服务", remaining_daemon_pid)]:
                if pid:
                    self.logger.info(f"第三步: 尝试终止{pid_type}进程 (PID: {pid})")
                    
                    # 首先尝试优雅停止
                    success, output = self._run_command(["sudo", "kill", "-TERM", str(pid)])
                    if success:
                        self.logger.info(f"发送TERM信号到{pid_type}进程 (PID: {pid})")
                        
                        # 等待进程完全停止
                        for i in range(10):  # 最多等待10秒
                            time.sleep(1)
                            check_success, _ = self._run_command(["kill", "-0", str(pid)])
                            if not check_success:  # 进程已不存在
                                self.logger.info(f"{pid_type}进程已优雅停止")
                                break
                        else:
                            # 如果进程仍然存在，尝试强制杀死
                            self.logger.warning(f"{pid_type}进程未正常停止，尝试强制终止")
                            success, _ = self._run_command(["sudo", "kill", "-9", str(pid)])
                            if success:
                                self.logger.info(f"{pid_type}进程已强制停止")
                                time.sleep(1)
                            else:
                                all_killed = False
                    else:
                        # 如果kill命令失败，可能是进程已经不存在了
                        if "No such process" in output:
                            self.logger.info(f"{pid_type}进程已经不存在")
                        else:
                            self.logger.error(f"停止{pid_type}进程失败: {output}")
                            all_killed = False
            
            return all_killed
        except Exception as e:
            self.logger.error(f"停止ZeroTier服务失败: {e}")
            return False
    
    def _start_zerotier_macos(self) -> bool:
        """
        启动macOS上的ZeroTier服务
        
        启动顺序:
        1. 第一步: 启动ZeroTier后台服务 (launchctl)
        2. 第二步: 启动ZeroTier GUI应用 (open)
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 检查后台服务是否已经在运行
            if self._check_zerotier_daemon_running():
                self.logger.info("ZeroTier后台服务已经在运行")
                return True
            
            # 第一步: 使用launchctl启动ZeroTier后台服务
            self.logger.info("第一步: 启动ZeroTier后台服务")
            success, output = self._run_command([
                "sudo", "launchctl", "load", 
                "/Library/LaunchDaemons/com.zerotier.one.plist"
            ])
            
            if success or "service already loaded" in output.lower():
                self.logger.info("launchctl启动服务命令执行成功")
                
                # 等待服务启动 - 增加等待时间
                for i in range(15):  # 最多等待15秒
                    time.sleep(1)
                    # 检查launchd服务状态
                    check_success, check_output = self._run_command([
                        "sudo", "launchctl", "list", "com.zerotier.one"
                    ])
                    if check_success and "PID" in check_output:
                        self.logger.info("ZeroTier后台服务启动成功")
                        # 再等待一下让服务完全初始化
                        time.sleep(3)
                        break
                    self.logger.debug(f"等待服务启动... ({i+1}/15)")
                else:
                    self.logger.warning("launchctl启动服务超时")
            else:
                self.logger.warning(f"launchctl启动服务失败: {output}")
            
            # 第二步: 启动ZeroTier GUI应用
            self.logger.info("第二步: 启动ZeroTier GUI应用")
            success, output = self._run_command([
                "open", "/Applications/ZeroTier.app"
            ])
            
            if success:
                self.logger.info("GUI应用启动命令执行成功")
                
                # 等待应用启动
                for i in range(15):  # 最多等待15秒
                    time.sleep(1)
                    if self._check_zerotier_gui_running():
                        self.logger.info("ZeroTier GUI应用启动成功")
                        break
                else:
                    self.logger.warning("GUI应用启动超时")
            else:
                self.logger.warning(f"启动GUI应用失败: {output}")
            
            # 最终检查：确保后台服务和GUI应用都正常运行
            daemon_ok = self._check_zerotier_daemon_running()
            gui_ok = self._check_zerotier_gui_running()
            
            if daemon_ok:
                self.logger.info(f"ZeroTier启动完成 - 后台服务: {'✓' if daemon_ok else '✗'}, GUI应用: {'✓' if gui_ok else '✗'}")
                return True
            
            self.logger.error("所有启动方法都失败了")
            return False
                
        except Exception as e:
            self.logger.error(f"启动ZeroTier服务失败: {e}")
            return False
    
    def _start_zerotier_gui_macos(self) -> bool:
        """
        启动macOS上的ZeroTier GUI客户端应用
        
        Returns:
            bool: 是否成功启动GUI应用
        """
        try:
            # 尝试启动ZeroTier GUI应用
            success, output = self._run_command([
                "open", "/Applications/ZeroTier.app"
            ])
            
            if success:
                self.logger.info("ZeroTier GUI应用启动命令执行成功")
                
                # 等待应用启动并检查
                time.sleep(3)
                
                # 检查应用是否真的启动了（通过检查进程）
                success, output = self._run_command([
                    "pgrep", "-f", "/Applications/ZeroTier.app"
                ])
                
                if success:
                    self.logger.info("ZeroTier GUI应用已成功启动")
                    return True
                else:
                    self.logger.warning("ZeroTier GUI应用启动命令成功但未检测到进程")
                    return False
            else:
                self.logger.error(f"启动ZeroTier GUI应用失败: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"启动ZeroTier GUI应用异常: {e}")
            return False
    
    def _check_zerotier_gui_running_windows(self) -> bool:
        """
        检查Windows上的ZeroTier GUI应用是否在运行
        
        Returns:
            bool: GUI应用是否在运行
        """
        try:
            success, output = self._run_command([
                "tasklist", "/fi", "imagename eq zerotier_desktop_ui.exe"
            ])
            if success and "zerotier_desktop_ui.exe" in output:
                self.logger.debug("检测到ZeroTier GUI应用正在运行")
                return True
            
            self.logger.debug("ZeroTier GUI应用未运行")
            return False
            
        except Exception as e:
            self.logger.error(f"检查ZeroTier GUI应用失败: {e}")
            return False
    
    def _check_zerotier_service_running_windows(self) -> bool:
        """
        检查Windows上的ZeroTier服务是否在运行
        
        Returns:
            bool: 服务是否在运行
        """
        try:
            success, output = self._run_command([
                "sc", "query", "ZeroTierOneService"
            ])
            if success and "RUNNING" in output.upper():
                self.logger.debug("ZeroTier服务正在运行")
                return True
            
            self.logger.debug("ZeroTier服务未运行")
            return False
            
        except Exception as e:
            self.logger.error(f"检查ZeroTier服务失败: {e}")
            return False
    
    def _stop_zerotier_windows(self) -> bool:
        """
        停止Windows上的ZeroTier服务
        
        停止顺序:
        1. 第一步: 停止ZeroTier GUI应用 (taskkill)
        2. 第二步: 停止ZeroTier服务 (net stop)
        
        Returns:
            bool: 是否成功停止
        """
        try:
            # 检查当前运行状态
            gui_running = self._check_zerotier_gui_running_windows()
            service_running = self._check_zerotier_service_running_windows()
            
            if not gui_running and not service_running:
                self.logger.info("ZeroTier GUI和服务都未运行")
                return True
            
            self.logger.info(f"当前状态 - GUI: {'运行' if gui_running else '未运行'}, 服务: {'运行' if service_running else '未运行'}")
            
            # 第一步: 停止ZeroTier GUI应用
            if gui_running:
                success, output = self._run_command([
                    "taskkill", "/f", "/im", "zerotier_desktop_ui.exe"
                ])
                
                if success:
                    self.logger.info("第一步: 使用taskkill命令停止ZeroTier GUI应用")
                    time.sleep(2)  # 等待应用完全关闭
                    
                    # 检查GUI是否停止
                    if not self._check_zerotier_gui_running_windows():
                        self.logger.info("GUI应用已成功停止")
                    else:
                        self.logger.warning("GUI应用可能未完全停止")
                else:
                    self.logger.debug(f"停止GUI应用失败: {output}")
            else:
                self.logger.info("第一步: GUI应用未运行，跳过")
            
            # 第二步: 停止ZeroTier服务
            if service_running:
                success, output = self._run_command([
                    "net", "stop", "ZeroTierOneService"
                ])
                
                if success:
                    self.logger.info("第二步: 使用net stop命令停止ZeroTier服务")
                    time.sleep(3)  # 等待服务完全停止
                    
                    # 检查服务是否停止
                    if not self._check_zerotier_service_running_windows():
                        self.logger.info("服务已成功停止")
                        return True
                    else:
                        self.logger.warning("net stop执行成功但服务仍在运行")
                else:
                    self.logger.warning(f"net stop停止服务失败: {output}")
                    return False
            else:
                self.logger.info("第二步: 服务未运行，跳过")
                return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"停止ZeroTier服务失败: {e}")
            return False
    
    def _start_zerotier_windows(self) -> bool:
        """
        启动Windows上的ZeroTier服务
        
        启动顺序:
        1. 第一步: 启动ZeroTier服务 (net start)
        2. 第二步: 启动ZeroTier GUI应用
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 检查服务是否已经在运行
            if self._check_zerotier_service_running_windows():
                self.logger.info("ZeroTier服务已经在运行")
            else:
                # 第一步: 启动ZeroTier服务
                self.logger.info("第一步: 启动ZeroTier服务")
                success, output = self._run_command([
                    "net", "start", "ZeroTierOneService"
                ])
                
                if success or "服务正在启动" in output or "service is starting" in output.lower():
                    self.logger.info("net start服务命令执行成功")
                    
                    # 等待服务启动
                    for i in range(15):  # 最多等待15秒
                        time.sleep(1)
                        if self._check_zerotier_service_running_windows():
                            self.logger.info("ZeroTier服务启动成功")
                            break
                        self.logger.debug(f"等待服务启动... ({i+1}/15)")
                    else:
                        self.logger.warning("服务启动超时")
                else:
                    self.logger.warning(f"net start启动服务失败: {output}")
            
            # 第二步: 启动ZeroTier GUI应用
            self.logger.info("第二步: 启动ZeroTier GUI应用")
            
            # 尝试不同的安装路径
            gui_paths = [
                r"C:\Program Files (x86)\ZeroTier\One\ZeroTier One.exe",
                r"C:\Program Files\ZeroTier\One\ZeroTier One.exe"
            ]
            
            gui_started = False
            for gui_path in gui_paths:
                # Windows的start命令需要通过cmd执行
                success, output = self._run_command([
                    "cmd", "/c", "start", "", f'"{gui_path}"'
                ], timeout=10)
                
                if success:
                    self.logger.info(f"GUI应用启动命令执行成功: {gui_path}")
                    
                    # 等待应用启动
                    for i in range(10):  # 最多等待10秒
                        time.sleep(1)
                        if self._check_zerotier_gui_running_windows():
                            self.logger.info("ZeroTier GUI应用启动成功")
                            gui_started = True
                            break
                    
                    if gui_started:
                        break
                else:
                    self.logger.debug(f"尝试启动GUI失败: {gui_path} - {output}")
            
            if not gui_started:
                self.logger.warning("GUI应用启动失败，但服务可能正常运行")
            
            # 最终检查：确保服务正常运行
            service_ok = self._check_zerotier_service_running_windows()
            gui_ok = self._check_zerotier_gui_running_windows()
            
            if service_ok:
                self.logger.info(f"ZeroTier启动完成 - 服务: {'✓' if service_ok else '✗'}, GUI应用: {'✓' if gui_ok else '✗'}")
                return True
            
            self.logger.error("服务启动失败")
            return False
                
        except Exception as e:
            self.logger.error(f"启动ZeroTier服务失败: {e}")
            return False
    
    def _restart_zerotier_windows(self) -> bool:
        """
        重启Windows上的ZeroTier服务（已弃用，使用_stop_zerotier_windows和_start_zerotier_windows）
        
        Returns:
            bool: 是否成功重启
        """
        try:
            # 使用新的停止和启动方法
            if not self._stop_zerotier_windows():
                return False
            
            time.sleep(2)  # 等待2秒
            
            return self._start_zerotier_windows()
                
        except Exception as e:
            self.logger.error(f"重启ZeroTier服务失败: {e}")
            return False
    
    def restart_zerotier_service(self) -> bool:
        """
        重启ZeroTier服务
        
        Returns:
            bool: 是否成功重启
            
        Raises:
            PlatformNotSupportedError: 不支持的平台时抛出
            ServiceError: 服务操作失败时抛出
        """
        if self.platform not in [PLATFORM_MACOS, PLATFORM_WINDOWS]:
            raise PlatformNotSupportedError(f"不支持的平台: {self.platform}")
        
        try:
            self.logger.info(f"开始重启ZeroTier服务 (平台: {self.platform})")
            
            if self.platform == PLATFORM_MACOS:
                # macOS: 先停止再启动
                if not self._stop_zerotier_macos():
                    raise ServiceError("停止ZeroTier服务失败")
                
                time.sleep(2)  # 等待2秒
                
                if not self._start_zerotier_macos():
                    raise ServiceError("启动ZeroTier服务失败")
                
            elif self.platform == PLATFORM_WINDOWS:
                # Windows: 先停止再启动
                if not self._stop_zerotier_windows():
                    raise ServiceError("停止ZeroTier服务失败")
                
                time.sleep(2)  # 等待2秒
                
                if not self._start_zerotier_windows():
                    raise ServiceError("启动ZeroTier服务失败")
            
            self.logger.info("ZeroTier服务重启完成")
            return True
            
        except Exception as e:
            error_msg = f"重启ZeroTier服务失败: {e}"
            self.logger.error(error_msg)
            raise ServiceError(error_msg)
    
    def check_zerotier_status(self) -> bool:
        """
        检查ZeroTier服务状态
        
        Returns:
            bool: 服务是否正在运行
        """
        try:
            if self.platform == PLATFORM_MACOS:
                # 检查后台服务是否运行（这是主要的服务状态）
                return self._check_zerotier_daemon_running()
                
            elif self.platform == PLATFORM_WINDOWS:
                return self._check_zerotier_service_running_windows()
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查ZeroTier服务状态失败: {e}")
            return False
    
    def verify_zerotier_peers(self) -> bool:
        """
        验证ZeroTier连接状态
        
        Returns:
            bool: 是否能看到PLANET角色
        """
        try:
            success, output = self._run_command(["zerotier-cli", "peers"])
            if success:
                has_planet = "PLANET" in output.upper()
                self.logger.info(f"ZeroTier peers检查: {'发现PLANET角色' if has_planet else '未发现PLANET角色'}")
                return has_planet
            else:
                self.logger.error(f"执行zerotier-cli peers失败: {output}")
                return False
                
        except Exception as e:
            self.logger.error(f"验证ZeroTier peers失败: {e}")
            return False
