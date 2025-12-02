"""文件管理模块"""
import shutil
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from config import Config
from exceptions import FileOperationError, PermissionError as CustomPermissionError, PlatformNotSupportedError
from constants import PLATFORM_MACOS, PLATFORM_WINDOWS


class FileManager:
    """跨平台文件管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.platform = platform.system().lower()
    
    def check_permissions(self) -> bool:
        """
        检查是否有足够的权限进行文件操作
        
        Returns:
            bool: 是否有权限
        """
        try:
            zerotier_path = self.config.zerotier_path
            
            # 检查目录是否存在
            if not zerotier_path.exists():
                self.logger.error(f"ZeroTier目录不存在: {zerotier_path}")
                return False
            
            # 检查是否有写权限
            if not os.access(zerotier_path, os.W_OK):
                self.logger.error(f"没有写权限: {zerotier_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"权限检查失败: {e}")
            return False
    
    def create_backup(self, file_path: Path) -> Path:
        """
        创建文件备份
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            Path: 备份文件路径
            
        Raises:
            FileOperationError: 备份失败时抛出
        """
        if not file_path.exists():
            self.logger.info(f"原文件不存在，无需备份: {file_path}")
            return Path()
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.with_suffix(f".backup_{timestamp}")
            
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"文件备份成功: {file_path} -> {backup_path}")
            return backup_path
            
        except Exception as e:
            error_msg = f"创建备份失败: {file_path} -> {e}"
            self.logger.error(error_msg)
            raise FileOperationError(error_msg)
    
    def restore_backup(self, backup_path: Path, original_path: Path) -> bool:
        """
        从备份恢复文件
        
        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径
            
        Returns:
            bool: 恢复是否成功
        """
        try:
            if not backup_path.exists():
                self.logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            shutil.copy2(backup_path, original_path)
            self.logger.info(f"文件恢复成功: {backup_path} -> {original_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"文件恢复失败: {e}")
            return False
    
    def replace_planet_file(self, new_planet_path: Path) -> bool:
        """
        替换planet文件
        
        Args:
            new_planet_path: 新的planet文件路径
            
        Returns:
            bool: 替换是否成功
            
        Raises:
            FileOperationError: 文件操作失败时抛出
            CustomPermissionError: 权限不足时抛出
            PlatformNotSupportedError: 不支持的平台时抛出
        """
        # 检查平台支持
        if self.platform not in [PLATFORM_MACOS, PLATFORM_WINDOWS]:
            raise PlatformNotSupportedError(f"不支持的平台: {self.platform}")
        
        # 检查权限
        if not self.check_permissions():
            raise CustomPermissionError("权限不足，请以管理员身份运行")
        
        # 检查新文件是否存在
        if not new_planet_path.exists():
            raise FileOperationError(f"新的planet文件不存在: {new_planet_path}")
        
        target_path = self.config.planet_file_path
        backup_path = None
        
        try:
            # 创建备份
            if target_path.exists():
                backup_path = self.create_backup(target_path)
            
            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制新文件
            shutil.copy2(new_planet_path, target_path)
            
            # 设置适当的权限
            self._set_file_permissions(target_path)
            
            self.logger.info(f"Planet文件替换成功: {new_planet_path} -> {target_path}")
            return True
            
        except Exception as e:
            error_msg = f"替换planet文件失败: {e}"
            self.logger.error(error_msg)
            
            # 尝试恢复备份
            if backup_path and backup_path.exists():
                self.logger.info("尝试恢复备份文件...")
                self.restore_backup(backup_path, target_path)
            
            raise FileOperationError(error_msg)
    
    def _set_file_permissions(self, file_path: Path) -> None:
        """
        设置文件权限
        
        Args:
            file_path: 文件路径
        """
        try:
            if self.platform == PLATFORM_MACOS:
                # macOS: 设置为644权限
                os.chmod(file_path, 0o644)
            elif self.platform == PLATFORM_WINDOWS:
                # Windows: 通常不需要特殊权限设置
                pass
            
            self.logger.debug(f"文件权限设置完成: {file_path}")
            
        except Exception as e:
            self.logger.warning(f"设置文件权限失败: {e}")
    
    def verify_file_integrity(self, file_path: Path, expected_size: Optional[int] = None) -> bool:
        """
        验证文件完整性
        
        Args:
            file_path: 文件路径
            expected_size: 期望的文件大小（字节）
            
        Returns:
            bool: 文件是否完整
        """
        try:
            if not file_path.exists():
                self.logger.error(f"文件不存在: {file_path}")
                return False
            
            file_size = file_path.stat().st_size
            
            if file_size == 0:
                self.logger.error(f"文件为空: {file_path}")
                return False
            
            if expected_size and file_size != expected_size:
                self.logger.warning(f"文件大小不匹配: {file_path}, 期望: {expected_size}, 实际: {file_size}")
                return False
            
            self.logger.debug(f"文件完整性验证通过: {file_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"文件完整性验证失败: {e}")
            return False
    
    def cleanup_old_backups(self, max_backups: int = 5) -> None:
        """
        清理旧的备份文件
        
        Args:
            max_backups: 保留的最大备份数量
        """
        try:
            zerotier_path = self.config.zerotier_path
            backup_pattern = "planet.backup_*"
            
            # 查找所有备份文件
            backup_files = list(zerotier_path.glob(backup_pattern))
            
            if len(backup_files) <= max_backups:
                return
            
            # 按修改时间排序，保留最新的
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除多余的备份
            for backup_file in backup_files[max_backups:]:
                try:
                    backup_file.unlink()
                    self.logger.info(f"删除旧备份: {backup_file}")
                except Exception as e:
                    self.logger.warning(f"删除备份失败: {backup_file} - {e}")
                    
        except Exception as e:
            self.logger.error(f"清理备份文件失败: {e}")
    
    def get_file_info(self, file_path: Path) -> dict:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 文件信息
        """
        try:
            if not file_path.exists():
                return {"exists": False}
            
            stat = file_path.stat()
            return {
                "exists": True,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "permissions": oct(stat.st_mode)[-3:],
            }
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return {"exists": False, "error": str(e)}
