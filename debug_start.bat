@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🔍 调试守护进程启动问题
echo ================================

set "SCRIPT_DIR=%~dp0"
set "CLI_COMMAND=uv run python cli.py"
set "LOG_FILE=%SCRIPT_DIR%debug_daemon.log"

echo 📁 脚本目录: %SCRIPT_DIR%
echo 📝 CLI命令: %CLI_COMMAND%
echo 📄 日志文件: %LOG_FILE%
echo.

REM 切换到脚本目录
cd /d "%SCRIPT_DIR%"
echo ✅ 已切换到目录: %CD%

REM 测试CLI命令
echo 🔍 测试CLI命令...
%CLI_COMMAND% --help >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ CLI命令失败
    %CLI_COMMAND% --help
    pause
    exit /b 1
) else (
    echo ✅ CLI命令可用
)

REM 测试daemon命令（前台运行5秒）
echo.
echo 🧪 测试daemon命令（前台运行5秒）...
timeout /t 5 | %CLI_COMMAND% daemon
echo ✅ daemon命令测试完成

REM 测试后台启动
echo.
echo 🚀 测试后台启动...
echo 📝 使用修复后的命令（添加输入重定向）
start /b "" cmd /c "cd /d \"%SCRIPT_DIR%\" && echo. | %CLI_COMMAND% daemon > \"%LOG_FILE%\" 2>&1"

REM 等待日志文件
echo ⏳ 等待日志文件创建...
set count=0
:wait_log
if exist "%LOG_FILE%" goto log_found
timeout /t 1 /nobreak >nul
set /a count+=1
echo    等待中... (%count%/10)
if %count% lss 10 goto wait_log

echo ❌ 日志文件未创建
goto end

:log_found
echo ✅ 日志文件已创建
echo 📄 日志文件大小: 
for %%A in ("%LOG_FILE%") do echo    %%~zA bytes

echo.
echo 📋 日志内容:
type "%LOG_FILE%"

echo.
echo 🔍 检查进程...
tasklist | findstr python.exe
tasklist | findstr uv.exe

:end
echo.
echo 🏁 调试完成
pause
