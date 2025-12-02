"""自定义异常类"""


class ZeroTierAutoError(Exception):
    """基础异常类"""
    pass


class ConfigError(ZeroTierAutoError):
    """配置相关异常"""
    pass


class DownloadError(ZeroTierAutoError):
    """下载相关异常"""
    pass


class FileOperationError(ZeroTierAutoError):
    """文件操作异常"""
    pass


class ServiceError(ZeroTierAutoError):
    """服务操作异常"""
    pass


class PlatformNotSupportedError(ZeroTierAutoError):
    """不支持的平台异常"""
    pass


class PermissionError(ZeroTierAutoError):
    """权限不足异常"""
    pass
