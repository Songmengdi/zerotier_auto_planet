# ZeroTier 自动 Planet 文件替换工具

一个用于自动监控服务端IP变动并更新ZeroTier Planet文件的Python工具，支持Mac和Windows平台。

## 功能特性

- 🔍 **自动监控**: 定期检查服务端IP变动
- 🔄 **自动更新**: 检测到IP变动时自动下载并替换Planet文件
- 🖥️ **跨平台支持**: 支持macOS和Windows系统
- 🛡️ **安全可靠**: 自动备份原文件，支持回滚
- 📊 **状态监控**: 提供详细的状态信息和日志
- 🎛️ **灵活配置**: 支持命令行参数和配置文件

## 系统要求

- Python 3.10+
- 管理员权限（用于文件替换和服务重启）
- ZeroTier One 客户端已安装

## 安装

1. 克隆项目：
```bash
git clone <repository-url>
cd zerotier_auto_planet
```

2. 安装依赖：
```bash
pip install -e .
```

## 使用方法

### 命令行接口

```bash
# 检查一次IP变动并更新（如果需要）
python -m zerotier_auto_planet check

# 以守护进程模式运行（持续监控）
python -m zerotier_auto_planet daemon

# 自定义检查间隔（秒）
python -m zerotier_auto_planet daemon --interval 600

# 强制更新Planet文件
python -m zerotier_auto_planet force-update

# 查看当前状态
python -m zerotier_auto_planet status

# 测试网络连接和权限
python -m zerotier_auto_planet test

# 生成默认配置文件
python -m zerotier_auto_planet init-config
```

### 配置说明

工具会从以下来源读取配置（优先级从高到低）：
1. 环境变量
2. 配置文件
3. 默认值

#### 环境变量

```bash
export ZEROTIER_API_KEY="your_api_key"
export ZEROTIER_BASE_URL="http://your-server.com:13000"
export ZEROTIER_CHECK_INTERVAL="300"
```

#### 配置文件

使用 `init-config` 命令生成默认配置文件：

```yaml
# ZeroTier Auto Planet 配置文件
api_key: "54fbe2f7a1d2902d"
base_url: "http://songmd.yicp.fun:13000"
check_interval: 300  # 检查间隔（秒）
download_timeout: 30  # 下载超时时间（秒）
max_retries: 3       # 最大重试次数
log_level: "INFO"    # 日志级别
```

## 工作原理

1. **IP监控**: 定期从服务器下载IP列表文件
2. **变动检测**: 比较远程IP列表与本地缓存
3. **文件下载**: 检测到变动时下载最新的Planet文件
4. **文件替换**: 备份原文件并替换为新文件
5. **服务重启**: 重启ZeroTier服务使更改生效
6. **状态验证**: 验证服务状态和PLANET角色

## 平台特定说明

### macOS

- **Planet文件路径**: `/Library/Application Support/ZeroTier/One/planet`
- **重启命令**: 通过PID文件终止进程，然后使用launchctl重启
- **权限要求**: 需要sudo权限

### Windows

- **Planet文件路径**: `C:\ProgramData\ZeroTier\One\planet`
- **重启命令**: 使用`net stop/start`命令重启服务
- **权限要求**: 需要管理员权限

## 日志

日志文件默认保存在 `logs/zerotier_auto.log`，支持自动轮转。

日志级别：
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 故障排除

### 权限问题
```bash
# macOS
sudo python -m zerotier_auto_planet check

# Windows (以管理员身份运行PowerShell)
python -m zerotier_auto_planet check
```

### 网络连接问题
```bash
# 测试网络连接
python -m zerotier_auto_planet test
```

### 服务状态检查
```bash
# 查看详细状态
python -m zerotier_auto_planet status --format json
```

## API端点

- **Planet文件**: `http://songmd.yicp.fun:13000/planet?key=54fbe2f7a1d2902d`
- **IP列表**: `http://songmd.yicp.fun:13000/ips?key=54fbe2f7a1d2902d`

## 开发

### 项目结构

```
zerotier_auto_planet/
├── __init__.py          # 包初始化
├── app.py              # 核心应用程序
├── cli.py              # 命令行接口
├── config.py           # 配置管理
├── constants.py        # 常量定义
├── downloader.py       # 文件下载器
├── exceptions.py       # 自定义异常
├── file_manager.py     # 文件管理器
├── ip_monitor.py       # IP监控器
├── logger.py           # 日志配置
├── main.py             # 主程序入口
└── service_manager.py  # 服务管理器
```

### 运行测试

```bash
python -m pytest tests/
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
