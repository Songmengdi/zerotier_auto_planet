"""工具函数模块"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def is_admin() -> bool:
    """
    检查当前是否以管理员权限运行
    
    Returns:
        bool: 是否有管理员权限
    """
    try:
        if platform.system().lower() == "windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            # macOS/Linux: 检查是否为root用户或能够sudo
            return os.geteuid() == 0
    except Exception:
        return False


def check_windows_admin_privileges() -> bool:
    """
    检查Windows系统的管理员权限（更详细的检查）
    
    Returns:
        bool: 是否有管理员权限
    """
    try:
        if platform.system().lower() != "windows":
            return False
            
        import ctypes
        
        # 方法1: 检查是否是管理员
        if not ctypes.windll.shell32.IsUserAnAdmin():
            return False
        
        # 方法2: 尝试执行需要管理员权限的操作
        try:
            # 尝试执行net命令（需要管理员权限）
            result = subprocess.run(
                ["net", "session"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
            
    except Exception:
        return False


def run_as_admin(command_args: list[str]) -> bool:
    """
    以管理员权限重新运行当前程序
    
    Args:
        command_args: 命令行参数
        
    Returns:
        bool: 是否成功重新启动
    """
    try:
        if platform.system().lower() == "windows":
            # Windows: 使用runas
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(command_args), None, 1
            )
            return True
        else:
            # macOS/Linux: 使用sudo
            cmd = ["sudo", sys.executable] + command_args
            result = subprocess.run(cmd)
            return result.returncode == 0
    except Exception as e:
        print(f"以管理员权限运行失败: {e}")
        return False


def ensure_admin_privileges() -> bool:
    """
    确保程序以管理员权限运行，如果没有则自动提升权限
    
    Returns:
        bool: 是否成功获得管理员权限
    """
    if is_admin():
        return True
    
    system = platform.system().lower()
    
    if system == "windows":
        print("⚠️  需要管理员权限来修改ZeroTier文件和重启服务")
        print("🔐 正在请求管理员权限...")
        print("📝 请在弹出的UAC对话框中点击'是'来授予管理员权限")
        
        # Windows: 重新以管理员权限运行
        if run_as_admin(sys.argv):
            # 如果成功重新启动，退出当前进程
            sys.exit(0)
        else:
            print("❌ 无法获得管理员权限，请手动以管理员身份运行此程序")
            return False
    else:
        # macOS/Linux
        print("⚠️  需要管理员权限来修改ZeroTier文件和重启服务")
        print("🔐 正在请求管理员权限...")
        
        # 重新以管理员权限运行
        if run_as_admin(sys.argv):
            # 如果成功重新启动，退出当前进程
            sys.exit(0)
        else:
            print("❌ 无法获得管理员权限")
            return False


def check_zerotier_installed() -> bool:
    """
    检查ZeroTier是否已安装

    Returns:
        bool: 是否已安装ZeroTier
    """
    system = platform.system().lower()

    if system == "darwin":  # macOS
        zerotier_path = Path("/Library/Application Support/ZeroTier/One")
        cli_path = Path("/usr/local/bin/zerotier-cli")
        return zerotier_path.exists() or cli_path.exists()
    elif system == "windows":
        zerotier_path = Path("C:/ProgramData/ZeroTier/One")
        return zerotier_path.exists()
    elif system == "linux":  # Linux
        zerotier_path = Path("/var/lib/zerotier-one")
        cli_path = Path("/usr/sbin/zerotier-cli")
        return zerotier_path.exists() or cli_path.exists()

    return False


def get_current_user() -> str:
    """
    获取当前用户名
    
    Returns:
        str: 用户名
    """
    try:
        if platform.system().lower() == "windows":
            return os.environ.get("USERNAME", "unknown")
        else:
            return os.environ.get("USER", "unknown")
    except Exception:
        return "unknown"
