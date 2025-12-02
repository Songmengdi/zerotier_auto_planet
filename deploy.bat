@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ZeroTier Auto Planet 部署管理脚本 (Windows版)
REM 作者: ZeroTier Auto Planet Team
REM 版本: 1.0.0

REM 配置
set "SCRIPT_DIR=%~dp0"
set "PROJECT_NAME=zerotier-auto-planet"
set "PID_FILE=%SCRIPT_DIR%.daemon.pid"
set "LOG_FILE=%SCRIPT_DIR%daemon.log"
set "CLI_COMMAND=uv run python cli.py"

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 错误: 需要管理员权限才能运行此脚本
    echo 💡 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

REM 检查依赖
call :check_dependencies
if %errorlevel% neq 0 exit /b 1

REM 显示横幅
call :print_banner

REM 处理命令行参数
if "%~1"=="" goto interactive_menu
if /i "%~1"=="start" goto start_daemon
if /i "%~1"=="stop" goto stop_daemon
if /i "%~1"=="status" goto show_status
if /i "%~1"=="force-update" goto force_update
if /i "%~1"=="logs" goto show_logs
if /i "%~1"=="test" goto run_test
if /i "%~1"=="help" goto show_help
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-h" goto show_help

echo ❌ 未知命令: %~1
echo.
goto show_help

:check_dependencies
    where uv >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ 错误: 未找到 uv 命令
        echo 💡 请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/
        exit /b 1
    )
    
    if not exist "%SCRIPT_DIR%cli.py" (
        echo ❌ 错误: 未找到 cli.py 文件
        echo 💡 请确保在项目根目录运行此脚本
        exit /b 1
    )
    exit /b 0

:print_banner
    echo.
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║                    ZeroTier Auto Planet                     ║
    echo ║                     部署管理工具 (Windows)                  ║
    echo ║                                                              ║
    echo ║  自动监控IP变动并更新ZeroTier Planet文件                   ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    exit /b 0

:check_daemon_status
    if not exist "%PID_FILE%" (
        exit /b 1
    )
    
    set /p daemon_pid=<"%PID_FILE%"
    tasklist /fi "pid eq %daemon_pid%" 2>nul | find "%daemon_pid%" >nul
    if %errorlevel% equ 0 (
        exit /b 0
    ) else (
        del "%PID_FILE%" 2>nul
        exit /b 1
    )

:get_daemon_pid
    if exist "%PID_FILE%" (
        set /p daemon_pid=<"%PID_FILE%"
        echo %daemon_pid%
    ) else (
        echo N/A
    )
    exit /b 0

:start_daemon
    echo 🚀 启动ZeroTier Auto Planet守护进程...
    
    call :check_daemon_status
    if %errorlevel% equ 0 (
        call :get_daemon_pid
        echo ⚠️  守护进程已在运行中 (PID: !daemon_pid!)
        goto end
    )
    
    REM 切换到项目目录
    cd /d "%SCRIPT_DIR%"
    
    REM 启动守护进程
    echo 📝 启动命令: %CLI_COMMAND% daemon
    start /b "" %CLI_COMMAND% daemon > "%LOG_FILE%" 2>&1
    
    REM 获取新进程PID (Windows批处理中获取PID比较复杂，这里使用简化方法)
    timeout /t 3 /nobreak >nul
    
    REM 通过进程名查找PID
    for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo csv ^| find "python.exe"') do (
        set "new_pid=%%i"
        set "new_pid=!new_pid:"=!"
    )
    
    if defined new_pid (
        echo !new_pid! > "%PID_FILE%"
        echo ✅ 守护进程启动成功!
        echo    PID: !new_pid!
        echo    日志文件: %LOG_FILE%
        echo    PID文件: %PID_FILE%
        echo.
        echo 💡 提示:
        echo    - 使用 %~nx0 status 查看状态
        echo    - 使用 %~nx0 stop 停止守护进程
        echo    - 使用 type "%LOG_FILE%" 查看日志
    ) else (
        echo ❌ 守护进程启动失败
        echo 💡 请检查日志文件: %LOG_FILE%
    )
    goto end

:stop_daemon
    echo 🛑 停止ZeroTier Auto Planet守护进程...
    
    call :check_daemon_status
    if %errorlevel% neq 0 (
        echo ⚠️  守护进程未运行
        goto end
    )
    
    call :get_daemon_pid
    echo 📝 停止进程 PID: !daemon_pid!
    
    REM 终止进程
    taskkill /pid !daemon_pid! /f >nul 2>&1
    
    REM 等待进程结束
    set count=0
    :wait_loop
    if !count! geq 10 goto force_kill
    tasklist /fi "pid eq !daemon_pid!" 2>nul | find "!daemon_pid!" >nul
    if %errorlevel% neq 0 goto cleanup_pid
    timeout /t 1 /nobreak >nul
    set /a count+=1
    echo ⏳ 等待进程结束... (!count!/10)
    goto wait_loop
    
    :force_kill
    echo ⚠️  进程未正常结束，强制终止...
    taskkill /pid !daemon_pid! /f /t >nul 2>&1
    
    :cleanup_pid
    del "%PID_FILE%" 2>nul
    echo ✅ 守护进程已停止
    goto end

:show_status
    echo 📊 ZeroTier Auto Planet 状态
    echo ========================================
    
    REM 守护进程状态
    call :check_daemon_status
    if %errorlevel% equ 0 (
        call :get_daemon_pid
        echo 🔄 守护进程: 运行中
        echo    PID: !daemon_pid!
        echo    日志文件: %LOG_FILE%
    ) else (
        echo 🔄 守护进程: 未运行
    )
    
    echo.
    
    REM 项目状态
    cd /d "%SCRIPT_DIR%"
    echo 📋 项目状态:
    %CLI_COMMAND% status
    
    echo.
    
    REM 日志文件信息
    if exist "%LOG_FILE%" (
        for %%A in ("%LOG_FILE%") do set log_size=%%~zA
        echo 📄 日志信息:
        echo    文件大小: !log_size! bytes
        echo    最后10行:
        powershell -Command "Get-Content '%LOG_FILE%' | Select-Object -Last 10"
    ) else (
        echo 📄 日志文件: 不存在
    )
    goto end

:force_update
    echo 🔄 执行强制更新...
    
    cd /d "%SCRIPT_DIR%"
    echo 📝 执行命令: %CLI_COMMAND% force-update
    
    %CLI_COMMAND% force-update
    if %errorlevel% equ 0 (
        echo ✅ 强制更新完成
    ) else (
        echo ❌ 强制更新失败
    )
    goto end

:show_logs
    if not exist "%LOG_FILE%" (
        echo ⚠️  日志文件不存在: %LOG_FILE%
        goto end
    )
    
    echo 📄 查看日志文件:
    echo ========================================
    type "%LOG_FILE%"
    goto end

:run_test
    echo 🧪 运行系统测试...
    
    cd /d "%SCRIPT_DIR%"
    echo 📝 执行命令: %CLI_COMMAND% test
    
    %CLI_COMMAND% test
    goto end

:show_menu
    echo 请选择操作:
    echo   1) 🚀 启动守护进程 (start)
    echo   2) 🛑 停止守护进程 (stop)
    echo   3) 📊 查看状态 (status)
    echo   4) 🔄 强制更新 (force-update)
    echo   5) 📄 查看日志 (logs)
    echo   6) 🧪 运行测试 (test)
    echo   0) 🚪 退出
    echo.
    exit /b 0

:interactive_menu
    :menu_loop
    echo.
    call :show_menu
    set /p choice="请输入选项 [0-6]: "
    
    if "%choice%"=="1" (
        call :start_daemon
    ) else if "%choice%"=="2" (
        call :stop_daemon
    ) else if "%choice%"=="3" (
        call :show_status
    ) else if "%choice%"=="4" (
        call :force_update
    ) else if "%choice%"=="5" (
        call :show_logs
    ) else if "%choice%"=="6" (
        call :run_test
    ) else if "%choice%"=="0" (
        echo 👋 再见!
        goto end
    ) else (
        echo ❌ 无效选项，请重新选择
    )
    
    echo.
    pause
    goto menu_loop

:show_help
    echo 用法:
    echo   %~nx0 [命令]
    echo.
    echo 命令:
    echo   start        启动守护进程
    echo   stop         停止守护进程
    echo   status       查看状态
    echo   force-update 强制更新Planet文件
    echo   logs         查看日志
    echo   test         运行系统测试
    echo   help         显示此帮助信息
    echo.
    echo 示例:
    echo   %~nx0 start     # 启动守护进程
    echo   %~nx0 status    # 查看状态
    echo   %~nx0           # 进入交互式菜单
    echo.
    echo 注意: 此脚本需要管理员权限运行
    goto end

:end
    if "%~1"=="" pause
    exit /b 0
