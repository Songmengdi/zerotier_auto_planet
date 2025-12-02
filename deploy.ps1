# ZeroTier Auto Planet 部署管理脚本 (PowerShell版)
# 作者: ZeroTier Auto Planet Team
# 版本: 1.0.0

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "status", "force-update", "logs", "test", "help", "")]
    [string]$Command = ""
)

# 配置
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectName = "zerotier-auto-planet"
$PidFile = Join-Path $ScriptDir ".daemon.pid"
$LogFile = Join-Path $ScriptDir "daemon.log"
$CliCommand = "uv run python cli.py"

# 颜色定义
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Cyan = "Cyan"
    Magenta = "Magenta"
    White = "White"
}

# 检查管理员权限
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 检查依赖
function Test-Dependencies {
    if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
        Write-Host "❌ 错误: 未找到 uv 命令" -ForegroundColor $Colors.Red
        Write-Host "💡 请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor $Colors.Yellow
        return $false
    }
    
    if (-not (Test-Path (Join-Path $ScriptDir "cli.py"))) {
        Write-Host "❌ 错误: 未找到 cli.py 文件" -ForegroundColor $Colors.Red
        Write-Host "💡 请确保在项目根目录运行此脚本" -ForegroundColor $Colors.Yellow
        return $false
    }
    
    return $true
}

# 打印横幅
function Show-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $Colors.Cyan
    Write-Host "║                    ZeroTier Auto Planet                     ║" -ForegroundColor $Colors.Cyan
    Write-Host "║                   部署管理工具 (PowerShell)                 ║" -ForegroundColor $Colors.Cyan
    Write-Host "║                                                              ║" -ForegroundColor $Colors.Cyan
    Write-Host "║  自动监控IP变动并更新ZeroTier Planet文件                   ║" -ForegroundColor $Colors.Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $Colors.Cyan
    Write-Host ""
}

# 检查守护进程状态
function Test-DaemonStatus {
    if (-not (Test-Path $PidFile)) {
        return $false
    }
    
    try {
        $pid = Get-Content $PidFile -ErrorAction Stop
        
        # 检查进程是否存在
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            return $true
        }
        
        # 进程不存在，清理PID文件
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $false
    }
    catch {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $false
    }
}

# 获取守护进程PID
function Get-DaemonPid {
    if (Test-Path $PidFile) {
        try {
            return Get-Content $PidFile
        }
        catch {
            return "N/A"
        }
    }
    return "N/A"
}

# 启动守护进程
function Start-Daemon {
    Write-Host "🚀 启动ZeroTier Auto Planet守护进程..." -ForegroundColor $Colors.Blue
    
    if (Test-DaemonStatus) {
        $pid = Get-DaemonPid
        Write-Host "⚠️  守护进程已在运行中 (PID: $pid)" -ForegroundColor $Colors.Yellow
        return
    }
    
    # 切换到项目目录
    Set-Location $ScriptDir
    
    # 启动守护进程
    Write-Host "📝 启动命令: $CliCommand daemon" -ForegroundColor $Colors.Cyan
    
    try {
        # 测试CLI命令是否可用
        Write-Host "🔍 测试CLI命令..." -ForegroundColor $Colors.Cyan
        
        $testCommand = "$CliCommand --help"
        Write-Host "   执行命令: $testCommand" -ForegroundColor $Colors.White
        
        try {
            $testResult = & cmd /c $testCommand 2>&1
            $exitCode = $LASTEXITCODE
            
            Write-Host "   命令退出码: $exitCode" -ForegroundColor $Colors.White
            
            if ($exitCode -eq 0) {
                Write-Host "✅ CLI命令可用" -ForegroundColor $Colors.Green
            }
            else {
                Write-Host "❌ CLI命令执行失败，退出码: $exitCode" -ForegroundColor $Colors.Red
                Write-Host "   输出: $testResult" -ForegroundColor $Colors.Yellow
                Write-Host "💡 请检查uv和Python环境" -ForegroundColor $Colors.Yellow
                Read-Host "按回车键继续..."
                return
            }
        }
        catch {
            Write-Host "❌ CLI命令执行异常: $($_.Exception.Message)" -ForegroundColor $Colors.Red
            Write-Host "💡 尝试手动运行: $CliCommand --help" -ForegroundColor $Colors.Yellow
            Read-Host "按回车键继续..."
            return
        }
        
        # 方法1: 使用简单的后台进程启动
        Write-Host "🚀 启动守护进程..." -ForegroundColor $Colors.Cyan
        
        $startCommand = "cd /d `"$ScriptDir`" && echo. | $CliCommand daemon > `"$LogFile`" 2>&1"
        Write-Host "   启动命令: $startCommand" -ForegroundColor $Colors.White
        Write-Host "   工作目录: $ScriptDir" -ForegroundColor $Colors.White
        Write-Host "   日志文件: $LogFile" -ForegroundColor $Colors.White
        
        # 直接启动进程并重定向输出
        Write-Host "   正在启动进程..." -ForegroundColor $Colors.Cyan
        $process = Start-Process -FilePath "cmd" -ArgumentList "/c", $startCommand -WindowStyle Hidden -PassThru
        Write-Host "   进程已启动，PID: $($process.Id)" -ForegroundColor $Colors.Green
        
        # 保存PID
        $process.Id | Out-File $PidFile -Encoding ASCII
        
        # 等待日志文件创建
        $logWaitCount = 0
        while (-not (Test-Path $LogFile) -and $logWaitCount -lt 10) {
            Start-Sleep -Seconds 1
            $logWaitCount++
            Write-Host "⏳ 等待日志文件创建... ($logWaitCount/10)" -ForegroundColor $Colors.Cyan
        }
        
        if (Test-Path $LogFile) {
            Write-Host "✅ 日志文件已创建" -ForegroundColor $Colors.Green
            
            # 等待进程稳定
            Start-Sleep -Seconds 3
            
            # 检查进程状态
            if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
                Write-Host "✅ 守护进程启动成功!" -ForegroundColor $Colors.Green
                Write-Host "   PID: $($process.Id)" -ForegroundColor $Colors.White
                Write-Host "   日志文件: $LogFile" -ForegroundColor $Colors.White
                Write-Host "   PID文件: $PidFile" -ForegroundColor $Colors.White
                Write-Host ""
                Write-Host "💡 提示:" -ForegroundColor $Colors.Cyan
                Write-Host "   - 使用 .\deploy.ps1 status 查看状态" -ForegroundColor $Colors.White
                Write-Host "   - 使用 .\deploy.ps1 stop 停止守护进程" -ForegroundColor $Colors.White
                Write-Host "   - 使用 Get-Content '$LogFile' -Wait 查看实时日志" -ForegroundColor $Colors.White
            }
            else {
                Write-Host "❌ 进程已退出，启动失败" -ForegroundColor $Colors.Red
                Write-Host "💡 日志内容:" -ForegroundColor $Colors.Yellow
                Get-Content $LogFile -Tail 10 | ForEach-Object { Write-Host "   $_" -ForegroundColor $Colors.Red }
            }
        }
        else {
            Write-Host "❌ 日志文件未创建，守护进程可能启动失败" -ForegroundColor $Colors.Red
            Write-Host "💡 进程ID: $($process.Id)" -ForegroundColor $Colors.Yellow
        }
    }
    catch {
        Write-Host "❌ 启动守护进程时出错: $($_.Exception.Message)" -ForegroundColor $Colors.Red
        Write-Host "   错误详情: $($_.Exception.GetType().Name)" -ForegroundColor $Colors.Yellow
        Write-Host "   错误位置: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor $Colors.Yellow
        
        # 备用方法: 直接使用cmd启动
        Write-Host "🔄 尝试备用启动方法..." -ForegroundColor $Colors.Yellow
        try {
            Write-Host "   使用PowerShell直接启动..." -ForegroundColor $Colors.Cyan
            $process = Start-Process -FilePath "powershell" -ArgumentList "-Command", "Set-Location '$ScriptDir'; Write-Output '' | & $CliCommand daemon" -WindowStyle Hidden -PassThru -RedirectStandardOutput $LogFile -RedirectStandardError $LogFile
            $process.Id | Out-File $PidFile -Encoding ASCII
            Write-Host "   备用进程已启动，PID: $($process.Id)" -ForegroundColor $Colors.Green
            
            Start-Sleep -Seconds 3
            if (Test-DaemonStatus) {
                Write-Host "✅ 备用方法启动成功!" -ForegroundColor $Colors.Green
                Write-Host "   PID: $($process.Id)" -ForegroundColor $Colors.White
            }
            else {
                Write-Host "❌ 备用方法也失败了" -ForegroundColor $Colors.Red
            }
        }
        catch {
            Write-Host "❌ 备用方法也失败: $($_.Exception.Message)" -ForegroundColor $Colors.Red
        }
        
        Read-Host "按回车键继续..."
    }
}

# 停止守护进程
function Stop-Daemon {
    Write-Host "🛑 停止ZeroTier Auto Planet守护进程..." -ForegroundColor $Colors.Blue
    
    if (-not (Test-DaemonStatus)) {
        Write-Host "⚠️  守护进程未运行" -ForegroundColor $Colors.Yellow
        return
    }
    
    $pid = Get-DaemonPid
    Write-Host "📝 停止进程 ID: $pid" -ForegroundColor $Colors.Cyan
    
    try {
        # 停止进程
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "🔄 停止进程..." -ForegroundColor $Colors.Cyan
            Stop-Process -Id $pid -Force -ErrorAction Stop
            
            # 等待进程结束
            $count = 0
            while ($count -lt 10) {
                try {
                    Get-Process -Id $pid -ErrorAction Stop | Out-Null
                    Start-Sleep -Seconds 1
                    $count++
                    Write-Host "⏳ 等待进程结束... ($count/10)" -ForegroundColor $Colors.Cyan
                }
                catch {
                    break
                }
            }
            Write-Host "✅ 进程已停止" -ForegroundColor $Colors.Green
        }
        else {
            Write-Host "⚠️  未找到运行的进程" -ForegroundColor $Colors.Yellow
        }
        
        # 清理PID文件
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "✅ 守护进程已停止" -ForegroundColor $Colors.Green
    }
    catch {
        Write-Host "❌ 停止进程时出错: $($_.Exception.Message)" -ForegroundColor $Colors.Red
        # 强制清理PID文件
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

# 查看状态
function Show-Status {
    Write-Host "📊 ZeroTier Auto Planet 状态" -ForegroundColor $Colors.Blue
    Write-Host "========================================" -ForegroundColor $Colors.White
    
    # 守护进程状态
    if (Test-DaemonStatus) {
        $pid = Get-DaemonPid
        try {
            $process = Get-Process -Id $pid
            $uptime = (Get-Date) - $process.StartTime
            Write-Host "🔄 守护进程: 运行中" -ForegroundColor $Colors.Green
            Write-Host "   PID: $pid" -ForegroundColor $Colors.White
            Write-Host "   运行时间: $($uptime.ToString('dd\.hh\:mm\:ss'))" -ForegroundColor $Colors.White
            Write-Host "   日志文件: $LogFile" -ForegroundColor $Colors.White
        }
        catch {
            Write-Host "🔄 守护进程: 状态异常" -ForegroundColor $Colors.Yellow
        }
    }
    else {
        Write-Host "🔄 守护进程: 未运行" -ForegroundColor $Colors.Red
    }
    
    Write-Host ""
    
    # 项目状态
    Set-Location $ScriptDir
    Write-Host "📋 项目状态:" -ForegroundColor $Colors.Cyan
    & cmd /c "$CliCommand status"
    
    Write-Host ""
    
    # 日志文件信息
    if (Test-Path $LogFile) {
        $logInfo = Get-Item $LogFile
        $logLines = (Get-Content $LogFile | Measure-Object -Line).Lines
        Write-Host "📄 日志信息:" -ForegroundColor $Colors.Cyan
        Write-Host "   文件大小: $([math]::Round($logInfo.Length / 1KB, 2)) KB" -ForegroundColor $Colors.White
        Write-Host "   行数: $logLines" -ForegroundColor $Colors.White
        Write-Host "   最后10行:" -ForegroundColor $Colors.White
        Get-Content $LogFile -Tail 10 | ForEach-Object { Write-Host "   $_" -ForegroundColor $Colors.Magenta }
    }
    else {
        Write-Host "📄 日志文件: 不存在" -ForegroundColor $Colors.Yellow
    }
}

# 强制更新
function Invoke-ForceUpdate {
    Write-Host "🔄 执行强制更新..." -ForegroundColor $Colors.Blue
    
    Set-Location $ScriptDir
    Write-Host "📝 执行命令: $CliCommand force-update" -ForegroundColor $Colors.Cyan
    
    $result = & cmd /c "$CliCommand force-update"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 强制更新完成" -ForegroundColor $Colors.Green
    }
    else {
        Write-Host "❌ 强制更新失败" -ForegroundColor $Colors.Red
    }
}

# 查看日志
function Show-Logs {
    if (-not (Test-Path $LogFile)) {
        Write-Host "⚠️  日志文件不存在: $LogFile" -ForegroundColor $Colors.Yellow
        return
    }
    
    Write-Host "📄 实时日志 (按 Ctrl+C 退出):" -ForegroundColor $Colors.Blue
    Write-Host "========================================" -ForegroundColor $Colors.Magenta
    Get-Content $LogFile -Wait
}

# 运行测试
function Invoke-Test {
    Write-Host "🧪 运行系统测试..." -ForegroundColor $Colors.Blue
    
    Set-Location $ScriptDir
    Write-Host "📝 执行命令: $CliCommand test" -ForegroundColor $Colors.Cyan
    
    & cmd /c "$CliCommand test"
}

# 显示菜单
function Show-Menu {
    Write-Host "请选择操作:" -ForegroundColor $Colors.White
    Write-Host "  1) 🚀 启动守护进程 (start)" -ForegroundColor $Colors.Cyan
    Write-Host "  2) 🛑 停止守护进程 (stop)" -ForegroundColor $Colors.Cyan
    Write-Host "  3) 📊 查看状态 (status)" -ForegroundColor $Colors.Cyan
    Write-Host "  4) 🔄 强制更新 (force-update)" -ForegroundColor $Colors.Cyan
    Write-Host "  5) 📄 查看实时日志 (logs)" -ForegroundColor $Colors.Cyan
    Write-Host "  6) 🧪 运行测试 (test)" -ForegroundColor $Colors.Cyan
    Write-Host "  0) 🚪 退出" -ForegroundColor $Colors.Cyan
    Write-Host ""
}

# 交互式菜单
function Show-InteractiveMenu {
    while ($true) {
        Write-Host ""
        Show-Menu
        $choice = Read-Host "请输入选项 [0-6]"
        
        switch ($choice) {
            "1" { Start-Daemon }
            "2" { Stop-Daemon }
            "3" { Show-Status }
            "4" { Invoke-ForceUpdate }
            "5" { Show-Logs }
            "6" { Invoke-Test }
            "0" { 
                Write-Host "👋 再见!" -ForegroundColor $Colors.Green
                return 
            }
            default { 
                Write-Host "❌ 无效选项，请重新选择" -ForegroundColor $Colors.Red 
            }
        }
        
        Write-Host ""
        Read-Host "按回车键继续..."
    }
}

# 显示帮助
function Show-Help {
    Write-Host "用法:" -ForegroundColor $Colors.White
    Write-Host "  .\deploy.ps1 [命令]"
    Write-Host ""
    Write-Host "命令:" -ForegroundColor $Colors.White
    Write-Host "  start        启动守护进程" -ForegroundColor $Colors.Cyan
    Write-Host "  stop         停止守护进程" -ForegroundColor $Colors.Cyan
    Write-Host "  status       查看状态" -ForegroundColor $Colors.Cyan
    Write-Host "  force-update 强制更新Planet文件" -ForegroundColor $Colors.Cyan
    Write-Host "  logs         查看实时日志" -ForegroundColor $Colors.Cyan
    Write-Host "  test         运行系统测试" -ForegroundColor $Colors.Cyan
    Write-Host "  help         显示此帮助信息" -ForegroundColor $Colors.Cyan
    Write-Host ""
    Write-Host "示例:" -ForegroundColor $Colors.White
    Write-Host "  .\deploy.ps1 start     # 启动守护进程"
    Write-Host "  .\deploy.ps1 status    # 查看状态"
    Write-Host "  .\deploy.ps1           # 进入交互式菜单"
    Write-Host ""
    Write-Host "注意: 此脚本需要管理员权限运行" -ForegroundColor $Colors.Yellow
}

# 主函数
function Main {
    # 检查管理员权限
    if (-not (Test-Administrator)) {
        Write-Host "❌ 错误: 需要管理员权限才能运行此脚本" -ForegroundColor $Colors.Red
        Write-Host "💡 请右键点击PowerShell，选择'以管理员身份运行'，然后重新执行此脚本" -ForegroundColor $Colors.Yellow
        Read-Host "按回车键退出..."
        return
    }
    
    # 检查依赖
    if (-not (Test-Dependencies)) {
        Read-Host "按回车键退出..."
        return
    }
    
    # 显示横幅
    Show-Banner
    
    # 处理命令
    switch ($Command.ToLower()) {
        "start" { Start-Daemon }
        "stop" { Stop-Daemon }
        "status" { Show-Status }
        "force-update" { Invoke-ForceUpdate }
        "logs" { Show-Logs }
        "test" { Invoke-Test }
        "help" { Show-Help }
        "" { Show-InteractiveMenu }
        default {
            Write-Host "❌ 未知命令: $Command" -ForegroundColor $Colors.Red
            Write-Host ""
            Show-Help
        }
    }
    
    if ($Command -eq "") {
        Read-Host "按回车键退出..."
    }
}

# 运行主函数
Main
