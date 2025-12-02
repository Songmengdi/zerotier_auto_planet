# Windows 部署指南

## 概述

本项目为Windows平台提供了两种部署脚本：
- `deploy.bat` - 批处理文件版本
- `deploy.ps1` - PowerShell版本（推荐）

## 前提条件

### 1. 管理员权限
**重要**: 所有部署脚本都需要管理员权限运行，因为需要：
- 控制ZeroTier服务
- 访问系统目录 `C:\ProgramData\ZeroTier\One`
- 替换Planet文件

### 2. 软件依赖
- **Python 3.8+**: 确保已安装Python
- **uv**: Python包管理器
  ```cmd
  # 安装uv
  pip install uv
  ```
- **ZeroTier One**: 必须已安装ZeroTier客户端

## 使用方法

### PowerShell版本（推荐）

1. **以管理员身份运行PowerShell**
   ```powershell
   # 右键点击PowerShell -> "以管理员身份运行"
   ```

2. **设置执行策略**（首次使用）
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **运行部署脚本**
   ```powershell
   # 进入交互式菜单
   .\deploy.ps1
   
   # 或直接执行命令
   .\deploy.ps1 start        # 启动守护进程
   .\deploy.ps1 status       # 查看状态
   .\deploy.ps1 force-update # 强制更新
   .\deploy.ps1 stop         # 停止守护进程
   ```

### 批处理版本

1. **以管理员身份运行**
   ```cmd
   # 右键点击 deploy.bat -> "以管理员身份运行"
   ```

2. **使用命令**
   ```cmd
   deploy.bat start        # 启动守护进程
   deploy.bat status       # 查看状态
   deploy.bat force-update # 强制更新
   deploy.bat stop         # 停止守护进程
   ```

## 功能说明

### 可用命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `start` | 启动守护进程 | 后台运行监控服务 |
| `stop` | 停止守护进程 | 停止后台监控 |
| `status` | 查看状态 | 显示服务状态和系统信息 |
| `force-update` | 强制更新 | 立即更新Planet文件 |
| `logs` | 查看日志 | 显示运行日志 |
| `test` | 运行测试 | 测试系统功能 |
| `help` | 显示帮助 | 显示使用说明 |

### 交互式菜单

不带参数运行脚本会进入交互式菜单：
```powershell
.\deploy.ps1
```

## Windows特定配置

### ZeroTier路径
- **服务进程**: `C:\ProgramData\ZeroTier\One\zerotier-one_x64.exe`
- **GUI客户端**: `C:\Program Files (x86)\ZeroTier\One\zerotier_desktop_ui.exe`
- **Planet文件**: `C:\ProgramData\ZeroTier\One\planet`
- **CLI工具**: 使用 `zerotier-one_x64.exe -q peers` 格式

### 服务管理
- **服务名称**: `ZeroTierOneService`
- **停止命令**: `net stop "ZeroTierOneService"`
- **启动命令**: `net start "ZeroTierOneService"`

## 故障排除

### 1. 权限问题
```
❌ 错误: 需要管理员权限才能运行此脚本
```
**解决**: 右键点击PowerShell/CMD，选择"以管理员身份运行"

### 2. uv命令未找到
```
❌ 错误: 未找到 uv 命令
```
**解决**: 
```cmd
pip install uv
```

### 3. ZeroTier服务问题
```
❌ 服务停止失败
```
**解决**: 
1. 检查ZeroTier是否正确安装
2. 确认以管理员权限运行
3. 手动重启ZeroTier服务

### 4. GUI启动失败
```
⚠️ GUI应用启动失败，但服务可能正常运行
```
**解决**: 
1. 检查GUI程序路径是否正确
2. 服务正常运行即可，GUI可选

### 5. Planet文件访问问题
```
❌ 权限不足，请以管理员身份运行
```
**解决**: 
1. 确认以管理员权限运行
2. 检查 `C:\ProgramData\ZeroTier\One` 目录权限

## 日志和监控

### 日志文件
- **位置**: `daemon.log`
- **查看**: `.\deploy.ps1 logs`
- **实时监控**: `Get-Content daemon.log -Wait`

### 状态检查
```powershell
# 查看完整状态
.\deploy.ps1 status

# 检查ZeroTier服务
sc query "ZeroTierOneService"

# 检查进程
tasklist | findstr zerotier
```

## 安全注意事项

1. **管理员权限**: 仅在需要时使用管理员权限
2. **网络安全**: 确保API密钥安全
3. **文件备份**: 系统会自动备份原Planet文件
4. **日志清理**: 定期清理日志文件

## 支持的Windows版本

- Windows 10 (1809+)
- Windows 11
- Windows Server 2019+
- Windows Server 2022

## 更多信息

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 文档: [README.md]
