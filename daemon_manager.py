"""守护进程管理模块"""
import os
import sys
import subprocess
import time
import platform
from pathlib import Path
from typing import Optional
import logging

from config import Config


class DaemonManager:
    """守护进程管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def is_running(self) -> bool:
        """
        检查守护进程是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        pid = self.get_pid()
        if pid is None:
            return False
        
        system = platform.system().lower()
        
        if system == "windows":
            # Windows: 使用 tasklist 命令检查进程
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                return str(pid) in result.stdout
            except Exception:
                # 如果 tasklist 失败，尝试使用 psutil
                try:
                    import psutil
                    return psutil.pid_exists(pid)
                except ImportError:
                    # 如果都失败，保守处理
                    return True
        else:
            # Linux/macOS: 使用信号检查
            try:
                # 发送信号 0 来检查进程是否存在
                os.kill(pid, 0)
                return True
            except PermissionError:
                # 权限不足，但进程可能存在，使用 ps 命令检查
                try:
                    result = subprocess.run(
                        ["ps", "-p", str(pid)], 
                        capture_output=True, 
                        text=True
                    )
                    return result.returncode == 0
                except Exception:
                    # 如果 ps 命令也失败，假设进程存在（保守处理）
                    return True
            except (OSError, ProcessLookupError):
                # 进程不存在，清理 PID 文件
                self._cleanup_pid_file()
                return False
    
    def get_pid(self) -> Optional[int]:
        """
        获取守护进程的 PID
        
        Returns:
            Optional[int]: PID 或 None
        """
        try:
            if self.config.daemon_pid_file.exists():
                pid_str = self.config.daemon_pid_file.read_text().strip()
                return int(pid_str)
        except (ValueError, FileNotFoundError):
            pass
        return None
    
    def start_daemon(self, interval: Optional[int] = None) -> bool:
        """
        启动守护进程
        
        Args:
            interval: 检查间隔（秒），如果为 None 则使用配置默认值
            
        Returns:
            bool: 启动是否成功
        """
        if self.is_running():
            self.logger.warning("守护进程已在运行")
            return False
        
        try:
            # 构建命令行参数
            cmd = [sys.executable, "-m", "cli", "daemon", "--background"]
            if interval:
                cmd.extend(["--interval", str(interval)])
            
            # 启动后台进程
            self.logger.info(f"启动守护进程: {' '.join(cmd)}")
            
            # 重定向输出到日志文件
            system = platform.system().lower()
            
            with open(self.config.daemon_log_file, 'a', encoding='utf-8') as log_file:
                if system == "windows":
                    # Windows: 使用 CREATE_NEW_PROCESS_GROUP 和 DETACHED_PROCESS
                    process = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
                        cwd=Path.cwd()
                    )
                else:
                    # Linux/macOS: 使用 start_new_session
                    process = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,  # 创建新的会话，脱离父进程
                        cwd=Path.cwd()
                    )
            
            # 写入 PID 文件
            self.config.daemon_pid_file.write_text(str(process.pid))
            
            # 确保 PID 文件权限正确（仅在 Unix 系统上设置）
            if system != "windows":
                try:
                    import stat
                    # 设置文件权限为 644，允许所有用户读取
                    os.chmod(self.config.daemon_pid_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                except Exception as e:
                    self.logger.warning(f"设置 PID 文件权限失败: {e}")
            
            # 等待一小段时间确保进程启动
            time.sleep(2)
            
            # 验证进程是否真的在运行
            if self.is_running():
                self.logger.info(f"守护进程启动成功，PID: {process.pid}")
                return True
            else:
                self.logger.error("守护进程启动失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动守护进程失败: {e}")
            return False
    
    def stop_daemon(self) -> bool:
        """
        停止守护进程
        
        Returns:
            bool: 停止是否成功
        """
        pid = self.get_pid()
        if pid is None:
            self.logger.warning("守护进程未运行")
            return True
        
        system = platform.system().lower()
        
        try:
            self.logger.info(f"停止守护进程，PID: {pid}")
            
            if system == "windows":
                # Windows: 使用 taskkill 命令
                try:
                    # 先尝试优雅终止
                    subprocess.run(
                        ["taskkill", "/PID", str(pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    # 等待进程退出
                    for _ in range(10):  # 最多等待 10 秒
                        if not self.is_running():
                            self.logger.info("守护进程已正常退出")
                            self._cleanup_pid_file()
                            return True
                        time.sleep(1)
                    
                    # 如果进程仍未退出，强制终止
                    self.logger.warning("守护进程未响应，强制终止")
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                except Exception as e:
                    self.logger.error(f"使用 taskkill 失败: {e}")
                    # 尝试使用 psutil 作为备选
                    try:
                        import psutil
                        process = psutil.Process(pid)
                        process.terminate()
                        process.wait(timeout=10)
                    except Exception as psutil_e:
                        self.logger.error(f"使用 psutil 也失败: {psutil_e}")
                        return False
            else:
                # Linux/macOS: 使用信号
                import signal
                
                # 发送 SIGTERM 信号
                os.kill(pid, signal.SIGTERM)
                
                # 等待进程退出
                for _ in range(10):  # 最多等待 10 秒
                    if not self.is_running():
                        self.logger.info("守护进程已正常退出")
                        self._cleanup_pid_file()
                        return True
                    time.sleep(1)
                
                # 如果进程仍未退出，发送 SIGKILL 信号强制终止
                self.logger.warning("守护进程未响应 SIGTERM，发送 SIGKILL 强制终止")
                os.kill(pid, signal.SIGKILL)
            
            # 最终等待检查
            for _ in range(5):  # 最多等待 5 秒
                if not self.is_running():
                    self.logger.info("守护进程已被强制终止")
                    self._cleanup_pid_file()
                    return True
                time.sleep(1)
            
            self.logger.error("无法停止守护进程")
            return False
            
        except ProcessLookupError:
            # 进程已经不存在了
            self.logger.info("守护进程已不存在")
            self._cleanup_pid_file()
            return True
        except Exception as e:
            self.logger.error(f"停止守护进程失败: {e}")
            return False
    
    def get_status(self) -> dict:
        """
        获取守护进程状态
        
        Returns:
            dict: 状态信息
        """
        pid = self.get_pid()
        running = self.is_running()
        
        status = {
            "running": running,
            "pid": pid,
            "pid_file": str(self.config.daemon_pid_file),
            "log_file": str(self.config.daemon_log_file)
        }
        
        if running and pid:
            try:
                # 获取进程创建时间
                import psutil
                process = psutil.Process(pid)
                status["start_time"] = process.create_time()
                status["memory_info"] = process.memory_info()._asdict()
            except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                # 如果没有 psutil、进程不存在或权限不足，跳过详细信息
                pass
            except Exception as e:
                # 其他异常也跳过，避免影响主要功能
                self.logger.debug(f"获取进程详细信息失败: {e}")
        
        return status
    
    def _cleanup_pid_file(self) -> None:
        """清理 PID 文件"""
        try:
            if self.config.daemon_pid_file.exists():
                self.config.daemon_pid_file.unlink()
        except Exception as e:
            self.logger.error(f"清理 PID 文件失败: {e}")
    
    def restart_daemon(self, interval: Optional[int] = None) -> bool:
        """
        重启守护进程
        
        Args:
            interval: 检查间隔（秒）
            
        Returns:
            bool: 重启是否成功
        """
        self.logger.info("重启守护进程...")
        
        # 先停止
        if not self.stop_daemon():
            self.logger.error("停止守护进程失败，无法重启")
            return False
        
        # 等待一下
        time.sleep(1)
        
        # 再启动
        return self.start_daemon(interval)
