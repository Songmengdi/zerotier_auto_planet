# ZeroTier Auto Planet 部署指南

## 🚀 快速开始

### 1. 直接命令行操作

```bash
# 启动守护进程
./deploy.sh start

# 查看状态
./deploy.sh status

# 强制更新
./deploy.sh force-update

# 停止守护进程
./deploy.sh stop

# 查看实时日志
./deploy.sh logs

# 运行系统测试
./deploy.sh test

# 显示帮助
./deploy.sh help
```

### 2. 交互式菜单

直接运行脚本进入交互式菜单：

```bash
./deploy.sh
```

然后选择对应的数字选项：
- `1` - 🚀 启动守护进程
- `2` - 🛑 停止守护进程  
- `3` - 📊 查看状态
- `4` - 🔄 强制更新
- `5` - 📄 查看实时日志
- `6` - 🧪 运行测试
- `0` - 🚪 退出

## 📋 功能说明

### 启动守护进程 (start)
- 在后台启动IP监控守护进程
- 自动检测IP变动并更新Planet文件
- 默认检查间隔为300秒（5分钟）
- 生成PID文件和日志文件

### 停止守护进程 (stop)
- 优雅停止后台守护进程
- 清理PID文件
- 如果进程无响应会强制终止

### 查看状态 (status)
- 显示守护进程运行状态
- 显示ZeroTier服务状态
- 显示Planet文件信息
- 显示最近的日志内容

### 强制更新 (force-update)
- 立即执行Planet文件更新
- 不检查IP变动，直接更新
- 自动处理权限提升

### 查看实时日志 (logs)
- 实时显示守护进程日志
- 按Ctrl+C退出日志查看

### 运行测试 (test)
- 测试网络连接
- 测试文件权限
- 测试ZeroTier服务状态

## 📁 文件说明

- `.daemon.pid` - 守护进程PID文件
- `daemon.log` - 守护进程日志文件
- `deploy.sh` - 部署管理脚本

## 🔧 系统要求

- macOS 系统
- 已安装 `uv` 包管理器
- 已安装 ZeroTier One 客户端
- 管理员权限（用于修改系统文件）

## 💡 使用建议

1. **首次使用**：
   ```bash
   # 先运行测试确保环境正常
   ./deploy.sh test
   
   # 然后启动守护进程
   ./deploy.sh start
   ```

2. **日常监控**：
   ```bash
   # 查看状态
   ./deploy.sh status
   
   # 查看日志
   ./deploy.sh logs
   ```

3. **手动更新**：
   ```bash
   # 强制更新Planet文件
   ./deploy.sh force-update
   ```

4. **停止服务**：
   ```bash
   # 停止守护进程
   ./deploy.sh stop
   ```

## 🚨 注意事项

- 守护进程需要管理员权限来修改ZeroTier配置文件
- 首次运行会提示输入管理员密码
- 确保ZeroTier One客户端已正确安装
- 建议定期检查日志文件大小，必要时清理

## 🔍 故障排除

### 守护进程启动失败
1. 检查是否有足够的权限
2. 查看日志文件内容：`cat daemon.log`
3. 确认ZeroTier客户端已安装

### 无法连接到ZeroTier服务
1. 确认ZeroTier One应用正在运行
2. 检查TCP端口9993是否可访问
3. 重启ZeroTier服务

### 权限错误
1. 确保以管理员权限运行
2. 检查ZeroTier目录权限
3. 必要时手动修复权限

## 📞 支持

如有问题，请检查：
1. 系统日志：`daemon.log`
2. ZeroTier状态：`./deploy.sh status`
3. 网络连接：`./deploy.sh test`
