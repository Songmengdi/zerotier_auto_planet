"""文件下载器模块"""
import requests
import hashlib
from pathlib import Path
from typing import Optional
import time

from config import Config
from exceptions import DownloadError
from constants import DEFAULT_TIMEOUT, DEFAULT_RETRIES


class Downloader:
    """文件下载器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        # 注意：requests.Session没有timeout属性，需要在每次请求时设置
    
    def download_file(self, url: str, local_path: Path, max_retries: Optional[int] = None) -> bool:
        """
        下载文件到本地路径
        
        Args:
            url: 下载URL
            local_path: 本地保存路径
            max_retries: 最大重试次数
            
        Returns:
            bool: 下载是否成功
            
        Raises:
            DownloadError: 下载失败时抛出
        """
        if max_retries is None:
            max_retries = self.config.max_retries
        
        # 确保目录存在
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, stream=True, timeout=self.config.download_timeout)
                response.raise_for_status()
                
                # 写入文件
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证文件是否下载完整
                if local_path.exists() and local_path.stat().st_size > 0:
                    return True
                else:
                    raise DownloadError(f"下载的文件为空: {local_path}")
                    
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    time.sleep(wait_time)
                    continue
                else:
                    break
        
        # 所有重试都失败了
        raise DownloadError(f"下载失败 {url} -> {local_path}: {last_error}")
    
    def download_text(self, url: str, max_retries: Optional[int] = None) -> str:
        """
        下载文本内容
        
        Args:
            url: 下载URL
            max_retries: 最大重试次数
            
        Returns:
            str: 文本内容
            
        Raises:
            DownloadError: 下载失败时抛出
        """
        if max_retries is None:
            max_retries = self.config.max_retries
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.config.download_timeout)
                response.raise_for_status()
                return response.text.strip()
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    break
        
        raise DownloadError(f"下载文本失败 {url}: {last_error}")
    
    def download_planet(self) -> Path:
        """
        下载planet文件
        
        Returns:
            Path: 下载的文件路径
        """
        local_path = self.config.cache_dir / "planet"
        self.download_file(self.config.planet_url, local_path)
        return local_path
    
    def download_ips(self) -> str:
        """
        下载IP列表
        
        Returns:
            str: IP列表内容
        """
        return self.download_text(self.config.ips_url)
    
    def get_file_hash(self, file_path: Path) -> str:
        """
        计算文件MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MD5哈希值
        """
        if not file_path.exists():
            return ""
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def close(self):
        """关闭会话"""
        self.session.close()
