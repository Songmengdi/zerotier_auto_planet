"""核心应用程序模块"""
import time
import signal
import sys
from pathlib import Path
from typing import Optional

from config import Config, get_config
from downloader import Downloader
from ip_monitor import IPMonitor
from file_manager import FileManager
from service_manager import ServiceManager
from logger import setup_logger, LoggerMixin
from exceptions import (
    ZeroTierAutoError, DownloadError, FileOperationError, 
    ServiceError, PlatformNotSupportedError
)


class ZeroTierAutoApp(LoggerMixin):
    """ZeroTier自动Planet替换应用程序"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.running = False
        
        # 设置日志
        log_file = Path("logs/zerotier_auto.log")
        self.main_logger = setup_logger(
            level="INFO",
            log_file=log_file,
            console_output=True
        )
        
        # 初始化组件
        self.downloader = Downloader(self.config)
        self.ip_monitor = IPMonitor(self.config, self.downloader)
        self.file_manager = FileManager(self.config)
        self.service_manager = ServiceManager(self.config)
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到信号 {signum}，准备退出...")
        self.running = False
    
    def check_prerequisites(self) -> bool:
        """
        检查运行前提条件
        
        Returns:
            bool: 是否满足运行条件
        """
        try:
            self.logger.info("检查运行前提条件...")
            
            # 检查平台支持
            try:
                zerotier_path = self.config.zerotier_path
                self.logger.info(f"ZeroTier路径: {zerotier_path}")
            except OSError as e:
                self.logger.error(f"不支持的平台: {e}")
                return False
            
            # 检查文件权限（如果通过CLI调用，权限应该已经检查过了）
            if not self.file_manager.check_permissions():
                self.logger.warning("文件权限检查失败，但将继续尝试操作")
            
            # 检查ZeroTier服务状态
            if not self.service_manager.check_zerotier_status():
                self.logger.warning("ZeroTier服务未运行，将尝试启动")
            
            # 测试网络连接
            try:
                self.ip_monitor.fetch_remote_ips()
                self.logger.info("网络连接正常")
            except Exception as e:
                self.logger.error(f"网络连接测试失败: {e}")
                return False
            
            self.logger.info("前提条件检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"前提条件检查失败: {e}")
            return False
    
    def update_planet_file(self) -> bool:
        """
        更新planet文件 - 跨平台支持
        
        Returns:
            bool: 更新是否成功
        """
        try:
            self.logger.info("开始更新planet文件...")
            
            # 步骤1: 下载新的planet文件
            self.logger.info("1. 下载planet文件...")
            new_planet_path = self.downloader.download_planet()
            
            # 验证下载的文件
            if not self.file_manager.verify_file_integrity(new_planet_path):
                raise FileOperationError("下载的planet文件验证失败")
            
            # 步骤2: 关闭ZeroTier应用和服务（使用跨平台方法）
            self.logger.info("2. 关闭ZeroTier应用和服务...")
            try:
                # 使用service_manager的restart方法来停止服务
                # 这里我们只需要停止部分，所以直接调用平台特定的停止方法
                import platform
                system = platform.system().lower()
                
                if system == "darwin":  # macOS
                    if not self.service_manager._stop_zerotier_macos():
                        self.logger.warning("停止ZeroTier服务失败，但继续执行")
                elif system == "windows":  # Windows
                    if not self.service_manager._stop_zerotier_windows():
                        self.logger.warning("停止ZeroTier服务失败，但继续执行")
                else:
                    self.logger.warning(f"不支持的平台: {system}")
                    
            except Exception as e:
                self.logger.warning(f"停止ZeroTier服务时出错: {e}，但继续执行")
            
            # 等待完全停止
            time.sleep(3)
            
            # 步骤3: 替换planet文件
            self.logger.info("3. 替换planet文件...")
            self.file_manager.replace_planet_file(new_planet_path)
            
            # 步骤4: 启动ZeroTier服务（使用跨平台方法）
            self.logger.info("4. 启动ZeroTier服务...")
            try:
                import platform
                system = platform.system().lower()
                
                if system == "darwin":  # macOS
                    if not self.service_manager._start_zerotier_macos():
                        raise ServiceError("启动ZeroTier服务失败")
                elif system == "windows":  # Windows
                    if not self.service_manager._start_zerotier_windows():
                        raise ServiceError("启动ZeroTier服务失败")
                else:
                    raise ServiceError(f"不支持的平台: {system}")
                    
            except Exception as e:
                raise ServiceError(f"启动ZeroTier服务失败: {e}")
            
            # 步骤5: 等待服务完全启动
            self.logger.info("5. 等待服务启动...")
            time.sleep(5)
            
            # 步骤6: 验证服务状态
            self.logger.info("6. 验证服务状态...")
            if not self.service_manager.check_zerotier_status():
                self.logger.warning("ZeroTier服务状态检查失败，但继续验证连接")
            
            # 步骤7: 验证peers连接（多次尝试）
            self.logger.info("7. 验证ZeroTier连接...")
            peers_verified = False
            for attempt in range(3):  # 尝试3次
                time.sleep(2)  # 每次等待2秒
                if self.service_manager.verify_zerotier_peers():
                    peers_verified = True
                    break
                self.logger.debug(f"第{attempt + 1}次验证peers失败，继续尝试...")
            
            if peers_verified:
                self.logger.info("✅ Planet文件更新成功，PLANET角色已生效")
            else:
                self.logger.warning("⚠️  Planet文件更新完成，但未检测到PLANET角色")
            
            # 步骤8: 启动ZeroTier GUI客户端（仅macOS需要单独启动GUI）
            import platform
            system = platform.system().lower()
            if system == "darwin":  # macOS需要单独启动GUI
                self.logger.info("8. 启动ZeroTier GUI客户端...")
                if self.service_manager._start_zerotier_gui_macos():
                    self.logger.info("✅ ZeroTier GUI客户端启动成功")
                else:
                    self.logger.warning("⚠️  ZeroTier GUI客户端启动失败，但服务正常运行")
            else:
                # Windows的GUI已经在_start_zerotier_windows中启动了
                self.logger.info("8. ZeroTier GUI客户端已随服务启动")
            
            # 清理旧备份
            self.file_manager.cleanup_old_backups()
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新planet文件失败: {e}")
            return False
    
    def run_once(self) -> bool:
        """
        执行一次检查和更新
        
        Returns:
            bool: 是否执行了更新操作
        """
        try:
            self.logger.info("开始检查IP变动...")
            
            # 检查IP变动
            has_changes, new_ip_content = self.ip_monitor.check_ip_changes()
            
            if has_changes and new_ip_content:
                self.logger.info("检测到IP变动，开始更新planet文件")
                
                # 更新本地IP记录
                self.ip_monitor.update_local_ips(new_ip_content)
                
                # 更新planet文件
                if self.update_planet_file():
                    self.logger.info("Planet文件更新完成")
                    return True
                else:
                    self.logger.error("Planet文件更新失败")
                    return False
            else:
                self.logger.info("IP无变动，无需更新")
                return False
                
        except Exception as e:
            self.logger.error(f"执行检查失败: {e}")
            return False
    
    def run_daemon(self) -> None:
        """
        以守护进程模式运行
        """
        self.logger.info(f"启动守护进程模式，检查间隔: {self.config.check_interval}秒")
        self.running = True
        
        while self.running:
            try:
                self.run_once()
                
                # 等待下次检查
                for _ in range(self.config.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                self.logger.info("收到中断信号，退出守护进程")
                break
            except Exception as e:
                self.logger.error(f"守护进程运行异常: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续
        
        self.logger.info("守护进程已退出")
    
    def force_update(self) -> bool:
        """
        强制更新planet文件（不检查IP变动）
        
        Returns:
            bool: 更新是否成功
        """
        self.logger.info("强制更新planet文件...")
        
        try:
            # 获取最新的IP列表并保存
            new_ip_content = self.ip_monitor.fetch_remote_ips()
            self.ip_monitor.update_local_ips(new_ip_content)
            
            # 更新planet文件
            return self.update_planet_file()
            
        except Exception as e:
            self.logger.error(f"强制更新失败: {e}")
            return False
    
    def status(self) -> dict:
        """
        获取应用程序状态
        
        Returns:
            dict: 状态信息
        """
        try:
            current_ips = self.ip_monitor.get_current_ips()
            zerotier_running = self.service_manager.check_zerotier_status()
            planet_info = self.file_manager.get_file_info(self.config.planet_file_path)
            
            return {
                "current_ips": sorted(current_ips),
                "zerotier_running": zerotier_running,
                "planet_file": planet_info,
                "config": {
                    "check_interval": self.config.check_interval,
                    "zerotier_path": str(self.config.zerotier_path),
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            return {"error": str(e)}
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            self.downloader.close()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


if __name__ == "__main__":
    ZeroTierAutoApp().service_manager._start_zerotier_macos()