@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ZeroTier Auto Planet 部署管理脚本 (Windows版)
:: 作者: ZeroTier Auto Planet Team
:: 版本: 1.0.0

:: 配置
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PROJECT_NAME=zerotier-auto-planet"
set "PID_FILE=%SCRIPT_DIR%\.daemon.pid"
set "LOG_FILE=%SCRIPT_DIR%\logs\daemon.log"
set "CLI_COMMAND=uv run python cli.py"

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 此脚本需要管理员权限运行
    echo 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

:: 处理命令行参数
if "%~1"=="" goto :interactive_menu
if /i "%~1"=="start" goto :start_daemon
if /i "%~1"=="stop" goto :stop_daemon
if /i "%~1"=="status" goto :show_status
if /i "%~1"=="force-update" goto :force_update
if /i "%~1"=="logs" goto :show_logs
if /i "%~1"=="test" goto :run_test
if /i "%~1"=="help" goto :show_help
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="-h" goto :show_help

echo [错误] 未知命令: %~1
echo.
goto :show_help

:: ========================================
:: 打印横幅
:: ========================================
:print_banner
echo.
echo ================================================================
echo                     ZeroTier Auto Planet                      
echo                    部署管理工具 [Windows]                   
echo                                                              
echo   自动监控IP变动并更新ZeroTier Planet文件                    
echo ================================================================
echo.
goto :eof

:: ========================================
:: 检查依赖
:: ========================================
:check_dependencies
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 uv 命令
    echo 请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/
    exit /b 1
)

if not exist "%SCRIPT_DIR%\cli.py" (
    echo [错误] 未找到 cli.py 文件
    echo 请确保在项目根目录运行此脚本
    exit /b 1
)
goto :eof

:: ========================================
:: 检查守护进程状态 (通过PID文件)
:: ========================================
:check_daemon_status
set "DAEMON_RUNNING=0"
set "DAEMON_PID="

if not exist "%PID_FILE%" goto :eof

set /p DAEMON_PID=<"%PID_FILE%"
if "!DAEMON_PID!"=="" goto :eof

:: 检查进程是否存在 (检查uv进程或其子进程)
tasklist /FI "PID eq !DAEMON_PID!" 2>nul | find "!DAEMON_PID!" >nul
if %errorlevel% equ 0 (
    set "DAEMON_RUNNING=1"
) else (
    :: PID文件存在但进程不存在，清理无效的PID文件
    del /f "%PID_FILE%" >nul 2>&1
)
goto :eof

:: ========================================
:: 获取守护进程PID
:: ========================================
:get_daemon_pid
if "!DAEMON_PID!"=="" (
    if exist "%PID_FILE%" (
        set /p DAEMON_PID=<"%PID_FILE%"
    ) else (
        set "DAEMON_PID=N/A"
    )
)
goto :eof

:: ========================================
:: 启动守护进程
:: ========================================
:start_daemon
call :print_banner
call :check_dependencies
if %errorlevel% neq 0 exit /b 1

echo [启动] 启动ZeroTier Auto Planet守护进程...

call :check_daemon_status
if "!DAEMON_RUNNING!"=="1" (
    call :get_daemon_pid
    echo [警告] 守护进程已在运行中 (PID: !DAEMON_PID!)
    goto :end
)

:: 确保日志目录存在
if not exist "%SCRIPT_DIR%\logs" mkdir "%SCRIPT_DIR%\logs"

:: 切换到项目目录并启动守护进程
cd /d "%SCRIPT_DIR%"
echo [信息] 启动命令: %CLI_COMMAND% daemon

:: 使用 PowerShell 在后台启动进程并获取PID
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "$p = Start-Process -FilePath 'uv' -ArgumentList 'run','python','cli.py','daemon' -WorkingDirectory '%SCRIPT_DIR%' -WindowStyle Hidden -PassThru -RedirectStandardOutput '%LOG_FILE%' -RedirectStandardError '%LOG_FILE%.err'; $p.Id"') do set "NEW_PID=%%i"

if "!NEW_PID!"=="" (
    echo [错误] 无法启动守护进程
    exit /b 1
)

:: 保存PID
echo !NEW_PID!>"%PID_FILE%"

:: 等待确认启动成功
timeout /t 3 /nobreak >nul

call :check_daemon_status
if "!DAEMON_RUNNING!"=="1" (
    echo [成功] 守护进程启动成功!
    echo    PID: !NEW_PID!
    echo    日志文件: %LOG_FILE%
    echo    PID文件: %PID_FILE%
    echo.
    echo [提示]
    echo    - 使用 %~nx0 status 查看状态
    echo    - 使用 %~nx0 stop 停止守护进程
    echo    - 使用 %~nx0 logs 查看日志
) else (
    echo [错误] 守护进程启动失败
    echo 请检查日志文件: %LOG_FILE%
    exit /b 1
)
goto :end

:: ========================================
:: 停止守护进程
:: ========================================
:stop_daemon
call :print_banner
echo [停止] 停止ZeroTier Auto Planet守护进程...

call :check_daemon_status
if "!DAEMON_RUNNING!"=="0" (
    echo [警告] 守护进程未运行
    goto :end
)

call :get_daemon_pid
echo [信息] 停止进程 PID: !DAEMON_PID!

:: 终止进程及其子进程 (/T 终止进程树)
taskkill /PID !DAEMON_PID! /T /F >nul 2>&1

:: 等待进程结束
timeout /t 2 /nobreak >nul

:stop_done
:: 清理PID文件
del /f "%PID_FILE%" >nul 2>&1
echo [成功] 守护进程已停止
goto :end

:: ========================================
:: 查看状态
:: ========================================
:show_status
call :print_banner
echo [状态] ZeroTier Auto Planet 状态
echo ========================================

call :check_daemon_status
if "!DAEMON_RUNNING!"=="1" (
    call :get_daemon_pid
    echo [运行中] 守护进程: 运行中
    echo    PID: !DAEMON_PID!
    echo    日志文件: %LOG_FILE%
) else (
    echo [未运行] 守护进程: 未运行
)

echo.

:: 项目状态
cd /d "%SCRIPT_DIR%"
echo [项目状态]
%CLI_COMMAND% status

echo.

:: 日志文件信息
if exist "%LOG_FILE%" (
    echo [日志信息]
    for %%A in ("%LOG_FILE%") do echo    文件大小: %%~zA 字节
    echo    最后10行:
    echo ----------------------------------------
    powershell -Command "Get-Content '%LOG_FILE%' -Tail 10"
    echo ----------------------------------------
) else (
    echo [日志文件] 不存在
)
goto :end

:: ========================================
:: 强制更新
:: ========================================
:force_update
call :print_banner
call :check_dependencies
if %errorlevel% neq 0 exit /b 1

echo [更新] 执行强制更新...

cd /d "%SCRIPT_DIR%"
echo [信息] 执行命令: %CLI_COMMAND% force-update

%CLI_COMMAND% force-update
if %errorlevel% equ 0 (
    echo [成功] 强制更新完成
) else (
    echo [错误] 强制更新失败
    exit /b 1
)
goto :end

:: ========================================
:: 查看日志
:: ========================================
:show_logs
call :print_banner
if not exist "%LOG_FILE%" (
    echo [警告] 日志文件不存在: %LOG_FILE%
    goto :end
)

echo [日志] 显示日志内容 (最后50行):
echo ========================================
powershell -Command "Get-Content '%LOG_FILE%' -Tail 50"
echo ========================================
echo.
echo [提示] 使用以下命令实时查看日志:
echo    powershell -Command "Get-Content '%LOG_FILE%' -Wait -Tail 20"
goto :end

:: ========================================
:: 运行测试
:: ========================================
:run_test
call :print_banner
call :check_dependencies
if %errorlevel% neq 0 exit /b 1

echo [测试] 运行系统测试...

cd /d "%SCRIPT_DIR%"
echo [信息] 执行命令: %CLI_COMMAND% test

%CLI_COMMAND% test
goto :end

:: ========================================
:: 显示帮助
:: ========================================
:show_help
call :print_banner
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
echo   %~nx0 start     启动守护进程
echo   %~nx0 status    查看状态
echo   %~nx0           进入交互式菜单
goto :end

:: ========================================
:: 交互式菜单
:: ========================================
:interactive_menu
call :print_banner
call :check_dependencies
if %errorlevel% neq 0 exit /b 1

:menu_loop
echo.
echo 请选择操作:
echo   1) 启动守护进程 (start)
echo   2) 停止守护进程 (stop)
echo   3) 查看状态 (status)
echo   4) 强制更新 (force-update)
echo   5) 查看日志
echo   6) 运行测试
echo   0) 退出
echo.
set /p "CHOICE=请输入选项 [0-6]: "

if "!CHOICE!"=="1" (
    call :start_daemon_menu
    goto :menu_continue
)
if "!CHOICE!"=="2" (
    call :stop_daemon_menu
    goto :menu_continue
)
if "!CHOICE!"=="3" (
    call :show_status_menu
    goto :menu_continue
)
if "!CHOICE!"=="4" (
    call :force_update_menu
    goto :menu_continue
)
if "!CHOICE!"=="5" (
    call :show_logs_menu
    goto :menu_continue
)
if "!CHOICE!"=="6" (
    call :run_test_menu
    goto :menu_continue
)
if "!CHOICE!"=="0" (
    echo [再见] 再见!
    exit /b 0
)

echo [错误] 无效选项，请重新选择

:menu_continue
echo.
pause
goto :menu_loop

:: 菜单子函数 (不显示横幅)
:start_daemon_menu
echo.
echo [启动] 启动ZeroTier Auto Planet守护进程...
call :check_daemon_status
if "!DAEMON_RUNNING!"=="1" (
    call :get_daemon_pid
    echo [警告] 守护进程已在运行中 (PID: !DAEMON_PID!)
    goto :eof
)
if not exist "%SCRIPT_DIR%\logs" mkdir "%SCRIPT_DIR%\logs"
cd /d "%SCRIPT_DIR%"
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "$p = Start-Process -FilePath 'uv' -ArgumentList 'run','python','cli.py','daemon' -WorkingDirectory '%SCRIPT_DIR%' -WindowStyle Hidden -PassThru -RedirectStandardOutput '%LOG_FILE%' -RedirectStandardError '%LOG_FILE%.err'; $p.Id"') do set "NEW_PID=%%i"
if "!NEW_PID!"=="" (
    echo [错误] 无法启动守护进程
    goto :eof
)
echo !NEW_PID!>"%PID_FILE%"
timeout /t 3 /nobreak >nul
call :check_daemon_status
if "!DAEMON_RUNNING!"=="1" (
    echo [成功] 守护进程启动成功! PID: !NEW_PID!
) else (
    echo [错误] 守护进程启动失败
)
goto :eof

:stop_daemon_menu
echo.
echo [停止] 停止ZeroTier Auto Planet守护进程...
call :check_daemon_status
if "!DAEMON_RUNNING!"=="0" (
    echo [警告] 守护进程未运行
    goto :eof
)
call :get_daemon_pid
echo [信息] 停止进程 PID: !DAEMON_PID!
taskkill /PID !DAEMON_PID! /T /F >nul 2>&1
timeout /t 2 /nobreak >nul
del /f "%PID_FILE%" >nul 2>&1
echo [成功] 守护进程已停止
goto :eof

:show_status_menu
echo.
call :check_daemon_status
if "!DAEMON_RUNNING!"=="1" (
    call :get_daemon_pid
    echo [运行中] 守护进程 PID: !DAEMON_PID!
) else (
    echo [未运行] 守护进程未运行
)
cd /d "%SCRIPT_DIR%"
%CLI_COMMAND% status
goto :eof

:force_update_menu
echo.
echo [更新] 执行强制更新...
cd /d "%SCRIPT_DIR%"
%CLI_COMMAND% force-update
goto :eof

:show_logs_menu
echo.
if not exist "%LOG_FILE%" (
    echo [警告] 日志文件不存在
    goto :eof
)
echo [日志] 最后20行:
powershell -Command "Get-Content '%LOG_FILE%' -Tail 20"
goto :eof

:run_test_menu
echo.
echo [测试] 运行系统测试...
cd /d "%SCRIPT_DIR%"
%CLI_COMMAND% test
goto :eof

:end
endlocal
