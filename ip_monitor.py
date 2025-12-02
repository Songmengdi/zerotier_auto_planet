"""IP监控模块"""
import re
from pathlib import Path
from typing import Set, Optional
import logging

from config import Config
from downloader import Downloader
from exceptions import DownloadError


class IPMonitor:
    """IP变动监控器"""
    
    def __init__(self, config: Config, downloader: Downloader):
        self.config = config
        self.downloader = downloader
        self.logger = logging.getLogger(__name__)
    
    def parse_ips(self, ip_content: str) -> Set[str]:
        """
        解析IP字符串，提取所有有效的IP地址
        
        Args:
            ip_content: IP内容字符串
            
        Returns:
            Set[str]: IP地址集合
        """
        # 使用正则表达式匹配IP地址
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = set(re.findall(ip_pattern, ip_content))
        
        # 验证IP地址的有效性
        valid_ips = set()
        for ip in ips:
            parts = ip.split('.')
            if all(0 <= int(part) <= 255 for part in parts):
                valid_ips.add(ip)
        
        return valid_ips
    
    def load_local_ips(self) -> Set[str]:
        """
        从本地文件加载IP列表
        
        Returns:
            Set[str]: 本地IP地址集合
        """
        try:
            if self.config.local_ips_file.exists():
                content = self.config.local_ips_file.read_text(encoding='utf-8').strip()
                return self.parse_ips(content)
            else:
                self.logger.info(f"本地IP文件不存在: {self.config.local_ips_file}")
                return set()
        except Exception as e:
            self.logger.error(f"读取本地IP文件失败: {e}")
            return set()
    
    def save_local_ips(self, ip_content: str) -> None:
        """
        保存IP内容到本地文件
        
        Args:
            ip_content: IP内容字符串
        """
        try:
            self.config.local_ips_file.write_text(ip_content, encoding='utf-8')
            self.logger.info(f"IP列表已保存到: {self.config.local_ips_file}")
        except Exception as e:
            self.logger.error(f"保存IP文件失败: {e}")
            raise
    
    def fetch_remote_ips(self) -> str:
        """
        从远程服务器获取IP列表
        
        Returns:
            str: 远程IP内容
            
        Raises:
            DownloadError: 下载失败时抛出
        """
        try:
            ip_content = self.downloader.download_text(self.config.ips_url)
            self.logger.info("成功获取远程IP列表")
            return ip_content
        except Exception as e:
            self.logger.error(f"获取远程IP列表失败: {e}")
            raise DownloadError(f"获取远程IP列表失败: {e}")
    
    def check_ip_changes(self) -> tuple[bool, Optional[str]]:
        """
        检查IP是否发生变动
        
        Returns:
            tuple[bool, Optional[str]]: (是否有变动, 新的IP内容)
        """
        try:
            # 获取远程IP列表
            remote_ip_content = self.fetch_remote_ips()
            remote_ips = self.parse_ips(remote_ip_content)
            
            # 获取本地IP列表
            local_ips = self.load_local_ips()
            
            # 比较IP列表
            if remote_ips != local_ips:
                self.logger.info(f"检测到IP变动:")
                self.logger.info(f"  本地IPs: {sorted(local_ips)}")
                self.logger.info(f"  远程IPs: {sorted(remote_ips)}")
                
                # 计算新增和删除的IP
                added_ips = remote_ips - local_ips
                removed_ips = local_ips - remote_ips
                
                if added_ips:
                    self.logger.info(f"  新增IPs: {sorted(added_ips)}")
                if removed_ips:
                    self.logger.info(f"  删除IPs: {sorted(removed_ips)}")
                
                return True, remote_ip_content
            else:
                self.logger.debug("IP列表无变动")
                return False, None
                
        except Exception as e:
            self.logger.error(f"检查IP变动失败: {e}")
            # 如果检查失败，返回False以避免不必要的更新
            return False, None
    
    def update_local_ips(self, new_ip_content: str) -> None:
        """
        更新本地IP列表
        
        Args:
            new_ip_content: 新的IP内容
        """
        self.save_local_ips(new_ip_content)
        self.logger.info("本地IP列表已更新")
    
    def get_current_ips(self) -> Set[str]:
        """
        获取当前的IP列表（优先使用本地，如果不存在则从远程获取）
        
        Returns:
            Set[str]: 当前IP地址集合
        """
        local_ips = self.load_local_ips()
        if local_ips:
            return local_ips
        
        try:
            remote_content = self.fetch_remote_ips()
            return self.parse_ips(remote_content)
        except Exception as e:
            self.logger.error(f"获取IP列表失败: {e}")
            return set()
