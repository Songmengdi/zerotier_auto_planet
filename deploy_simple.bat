@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ZeroTier Auto Planet 简化部署脚本
REM 支持: start, stop, status, force-update

set "SCRIPT_DIR=%~dp0"
set "CLI_COMMAND=uv run python cli.py"
set "LOG_FILE=%SCRIPT_DIR%daemon.log"
set "PID_FILE=%SCRIPT_DIR%.daemon.pid"

REM 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 需要管理员权限才能运行此脚本
    echo 💡 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

REM 显示横幅
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    ZeroTier Auto Planet                     ║
echo ║                     简化部署工具                            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM 处理命令行参数
if "%~1"=="" goto show_help
if /i "%~1"=="start" goto start_daemon
if /i "%~1"=="stop" goto stop_daemon
if /i "%~1"=="status" goto show_status
if /i "%~1"=="force-update" goto force_update
if /i "%~1"=="help" goto show_help

echo ❌ 未知命令: %~1
goto show_help

:start_daemon
    echo 🚀 启动ZeroTier Auto Planet守护进程...
    
    REM 检查是否已运行
    call :check_daemon_status
    if %errorlevel% equ 0 (
        call :get_daemon_pid
        echo ⚠️  守护进程已在运行中 (PID: !daemon_pid!)
        goto end
    )
    
    REM 切换到项目目录
    cd /d "%SCRIPT_DIR%"
    
    REM 测试CLI命令
    echo 🔍 测试CLI命令...
    %CLI_COMMAND% --help >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ CLI命令不可用，请检查uv和Python环境
        goto end
    )
    echo ✅ CLI命令可用
    
    REM 启动守护进程
    echo 🚀 启动守护进程...
    start /b "" cmd /c "cd /d \"%SCRIPT_DIR%\" && echo. | %CLI_COMMAND% daemon > \"%LOG_FILE%\" 2>&1"
    
    REM 等待日志文件创建
    set count=0
    :wait_log
    if exist "%LOG_FILE%" goto log_created
    timeout /t 1 /nobreak >nul
    set /a count+=1
    if %count% lss 10 goto wait_log
    
    echo ❌ 日志文件未创建，守护进程可能启动失败
    goto end
    
    :log_created
    echo ✅ 日志文件已创建
    
    REM 获取进程PID
    timeout /t 2 /nobreak >nul
    for /f "tokens=2 delims=," %%i in ('wmic process where "commandline like '%%daemon%%'" get processid /format:csv 2^>nul ^| find ","') do (
        set "new_pid=%%i"
        if defined new_pid (
            echo !new_pid! > "%PID_FILE%"
            goto pid_found
        )
    )
    
    REM 备选方法
    for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo csv 2^>nul ^| find "python.exe" 2^>nul') do (
        set "new_pid=%%i"
        set "new_pid=!new_pid:"=!"
        echo !new_pid! > "%PID_FILE%"
        goto pid_found
    )
    
    echo placeholder > "%PID_FILE%"
    
    :pid_found
    echo ✅ 守护进程启动成功!
    echo    日志文件: %LOG_FILE%
    echo    PID文件: %PID_FILE%
    echo.
    echo 💡 使用以下命令管理:
    echo    %~nx0 status       - 查看状态
    echo    %~nx0 stop         - 停止守护进程
    echo    %~nx0 force-update - 强制更新
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
    
    if "!daemon_pid!"=="placeholder" (
        REM 查找并停止daemon进程
        for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo csv 2^>nul ^| find "python.exe" 2^>nul') do (
            taskkill /pid %%i /f >nul 2>&1
        )
    ) else (
        taskkill /pid !daemon_pid! /f >nul 2>&1
    )
    
    REM 清理文件
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
    
    REM 日志信息
    if exist "%LOG_FILE%" (
        for %%A in ("%LOG_FILE%") do set log_size=%%~zA
        echo 📄 日志信息:
        echo    文件大小: !log_size! bytes
        echo    最后5行:
        powershell -Command "Get-Content '%LOG_FILE%' | Select-Object -Last 5" 2>nul
    ) else (
        echo 📄 日志文件: 不存在
    )
    goto end

:force_update
    echo 🔄 执行强制更新...
    
    cd /d "%SCRIPT_DIR%"
    %CLI_COMMAND% force-update
    if %errorlevel% equ 0 (
        echo ✅ 强制更新完成
    ) else (
        echo ❌ 强制更新失败
    )
    goto end

:check_daemon_status
    if not exist "%PID_FILE%" (
        exit /b 1
    )
    
    set /p daemon_pid=<"%PID_FILE%"
    
    if "%daemon_pid%"=="placeholder" (
        if exist "%LOG_FILE%" (
            tasklist | findstr /i "python.exe" >nul
            if %errorlevel% equ 0 (
                exit /b 0
            )
        )
        exit /b 1
    )
    
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
    ) else (
        set "daemon_pid=N/A"
    )
    exit /b 0

:show_help
    echo 用法:
    echo   %~nx0 [命令]
    echo.
    echo 命令:
    echo   start        启动守护进程
    echo   stop         停止守护进程
    echo   status       查看状态
    echo   force-update 强制更新Planet文件
    echo   help         显示此帮助信息
    echo.
    echo 示例:
    echo   %~nx0 start     # 启动守护进程
    echo   %~nx0 status    # 查看状态
    echo.
    echo 注意: 此脚本需要管理员权限运行
    goto end

:end
    pause
    exit /b 0
