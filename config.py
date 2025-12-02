"""配置管理模块"""
from dataclasses import dataclass
from pathlib import Path
import platform
import os
from typing import Optional


@dataclass
class Config:
    """应用程序配置类"""
    
    # API配置
    api_key: str = "54fbe2f7a1d2902d"
    base_url: str = "http://songmd.yicp.fun:13000"
    
    # 文件下载URL
    @property
    def planet_url(self) -> str:
        return f"{self.base_url}/planet?key={self.api_key}"
    
    @property
    def ips_url(self) -> str:
        return f"{self.base_url}/ips?key={self.api_key}"
    
    # 平台相关路径
    @property
    def zerotier_path(self) -> Path:
        """获取ZeroTier安装路径"""
        system = platform.system().lower()
        if system == "darwin":  # macOS
            return Path("/Library/Application Support/ZeroTier/One")
        elif system == "windows":
            return Path("C:/ProgramData/ZeroTier/One")
        else:
            raise OSError(f"不支持的操作系统: {system}")
    
    @property
    def planet_file_path(self) -> Path:
        """获取planet文件路径"""
        return self.zerotier_path / "planet"
    
    @property
    def pid_file_path(self) -> Optional[Path]:
        """获取PID文件路径（仅macOS）"""
        if platform.system().lower() == "darwin":
            return self.zerotier_path / "zerotier-one.pid"
        return None
    
    # 本地存储配置
    cache_dir: Path = Path("./cache")
    local_ips_file: Path = Path("./ips")
    
    # 监控配置
    check_interval: int = 300  # 5分钟检查一次
    download_timeout: int = 30  # 下载超时时间
    max_retries: int = 3  # 最大重试次数
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保缓存目录存在
        self.cache_dir.mkdir(exist_ok=True)


def get_config() -> Config:
    """获取配置实例"""
    config = Config()
    
    # 从环境变量覆盖配置
    if api_key := os.getenv("ZEROTIER_API_KEY"):
        config.api_key = api_key
    
    if base_url := os.getenv("ZEROTIER_BASE_URL"):
        config.base_url = base_url
    
    if check_interval := os.getenv("ZEROTIER_CHECK_INTERVAL"):
        try:
            config.check_interval = int(check_interval)
        except ValueError:
            pass
    
    return config
