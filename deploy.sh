#!/bin/bash

# ZeroTier Auto Planet 部署管理脚本
# 作者: ZeroTier Auto Planet Team
# 版本: 1.0.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="zerotier-auto-planet"
PID_FILE="$SCRIPT_DIR/.daemon.pid"
LOG_FILE="$SCRIPT_DIR/logs/daemon.log"
CLI_COMMAND="uv run python cli.py"

# 检查依赖
check_dependencies() {
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}错误: 未找到 uv 命令${NC}"
        echo -e "${YELLOW}请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        exit 1
    fi
    
    if [ ! -f "$SCRIPT_DIR/cli.py" ]; then
        echo -e "${RED}错误: 未找到 cli.py 文件${NC}"
        echo -e "${YELLOW}请确保在项目根目录运行此脚本${NC}"
        exit 1
    fi
}

# 打印横幅
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    ZeroTier Auto Planet                     ║"
    echo "║                     部署管理工具                            ║"
    echo "║                                                              ║"
    echo "║  自动监控IP变动并更新ZeroTier Planet文件                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查守护进程状态
check_daemon_status() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # 运行中
        else
            rm -f "$PID_FILE"  # 清理无效的PID文件
            return 1  # 未运行
        fi
    else
        return 1  # 未运行
    fi
}

# 获取守护进程PID
get_daemon_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo "N/A"
    fi
}

# 启动守护进程
start_daemon() {
    echo -e "${BLUE}启动ZeroTier Auto Planet守护进程...${NC}"
    
    if check_daemon_status; then
        echo -e "${YELLOW}守护进程已在运行中 (PID: $(get_daemon_pid))${NC}"
        return 0
    fi
    
    # 切换到项目目录
    cd "$SCRIPT_DIR"
    
    # 启动守护进程
    echo -e "${CYAN}启动命令: $CLI_COMMAND daemon${NC}"
    nohup $CLI_COMMAND daemon > "$LOG_FILE" 2>&1 &
    local daemon_pid=$!
    
    # 保存PID
    echo "$daemon_pid" > "$PID_FILE"
    
    # 等待一下确认启动成功
    sleep 3
    
    if check_daemon_status; then
        echo -e "${GREEN}守护进程启动成功!${NC}"
        echo -e "${WHITE}   PID: $(get_daemon_pid)${NC}"
        echo -e "${WHITE}   日志文件: $LOG_FILE${NC}"
        echo -e "${WHITE}   PID文件: $PID_FILE${NC}"
        echo ""
        echo -e "${CYAN}提示:${NC}"
        echo -e "   - 使用 ${WHITE}$0 status${NC} 查看状态"
        echo -e "   - 使用 ${WHITE}$0 stop${NC} 停止守护进程"
        echo -e "   - 使用 ${WHITE}tail -f $LOG_FILE${NC} 查看实时日志"
    else
        echo -e "${RED}守护进程启动失败${NC}"
        echo -e "${YELLOW}请检查日志文件: $LOG_FILE${NC}"
        return 1
    fi
}

# 停止守护进程
stop_daemon() {
    echo -e "${BLUE}停止ZeroTier Auto Planet守护进程...${NC}"
    
    if ! check_daemon_status; then
        echo -e "${YELLOW}守护进程未运行${NC}"
        return 0
    fi
    
    local pid=$(get_daemon_pid)
    echo -e "${CYAN}停止进程 PID: $pid${NC}"
    
    # 发送TERM信号
    kill -TERM "$pid" 2>/dev/null || true
    
    # 等待进程结束
    local count=0
    while [ $count -lt 10 ]; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            break
        fi
        sleep 1
        count=$((count + 1))
        echo -e "${CYAN}等待进程结束... ($count/10)${NC}"
    done
    
    # 如果还在运行，强制杀死
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}进程未正常结束，强制终止...${NC}"
        kill -KILL "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    # 清理PID文件
    rm -f "$PID_FILE"
    
    echo -e "${GREEN}守护进程已停止${NC}"
}

# 查看状态
show_status() {
    echo -e "${BLUE}ZeroTier Auto Planet 状态${NC}"
    echo -e "${WHITE}========================================${NC}"
    
    # 守护进程状态
    if check_daemon_status; then
        local pid=$(get_daemon_pid)
        local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo "N/A")
        echo -e "${GREEN}守护进程: 运行中${NC}"
        echo -e "${WHITE}   PID: $pid${NC}"
        echo -e "${WHITE}   运行时间: $uptime${NC}"
        echo -e "${WHITE}   日志文件: $LOG_FILE${NC}"
    else
        echo -e "${RED}守护进程: 未运行${NC}"
    fi
    
    echo ""
    
    # 项目状态
    cd "$SCRIPT_DIR"
    echo -e "${CYAN}项目状态:${NC}"
    $CLI_COMMAND status
    
    echo ""
    
    # 日志文件信息
    if [ -f "$LOG_FILE" ]; then
        local log_size=$(du -h "$LOG_FILE" | cut -f1)
        local log_lines=$(wc -l < "$LOG_FILE")
        echo -e "${CYAN}日志信息:${NC}"
        echo -e "${WHITE}   文件大小: $log_size${NC}"
        echo -e "${WHITE}   行数: $log_lines${NC}"
        echo -e "${WHITE}   最后10行:${NC}"
        echo -e "${PURPLE}$(tail -10 "$LOG_FILE" 2>/dev/null || echo "   无日志内容")${NC}"
    else
        echo -e "${YELLOW}日志文件: 不存在${NC}"
    fi
}

# 强制更新
force_update() {
    echo -e "${BLUE}执行强制更新...${NC}"
    
    cd "$SCRIPT_DIR"
    echo -e "${CYAN}执行命令: $CLI_COMMAND force-update${NC}"
    
    if $CLI_COMMAND force-update; then
        echo -e "${GREEN}强制更新完成${NC}"
    else
        echo -e "${RED}强制更新失败${NC}"
        return 1
    fi
}

# 显示菜单
show_menu() {
    echo -e "${WHITE}请选择操作:${NC}"
    echo -e "${CYAN}  1) 启动守护进程 (start)${NC}"
    echo -e "${CYAN}  2) 停止守护进程 (stop)${NC}"
    echo -e "${CYAN}  3) 查看状态 (status)${NC}"
    echo -e "${CYAN}  4) 强制更新 (force-update)${NC}"
    echo -e "${CYAN}  5) 查看实时日志${NC}"
    echo -e "${CYAN}  6) 运行测试${NC}"
    echo -e "${CYAN}  0) 退出${NC}"
    echo ""
}

# 查看实时日志
show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}日志文件不存在: $LOG_FILE${NC}"
        return 1
    fi
    
    echo -e "${BLUE}实时日志 (按 Ctrl+C 退出):${NC}"
    echo -e "${PURPLE}========================================${NC}"
    tail -f "$LOG_FILE"
}

# 运行测试
run_test() {
    echo -e "${BLUE}运行系统测试...${NC}"
    
    cd "$SCRIPT_DIR"
    echo -e "${CYAN}执行命令: $CLI_COMMAND test${NC}"
    
    $CLI_COMMAND test
}

# 交互式菜单
interactive_menu() {
    while true; do
        echo ""
        show_menu
        read -p "$(echo -e "${WHITE}请输入选项 [0-6]: ${NC}")" choice
        
        case $choice in
            1)
                start_daemon
                ;;
            2)
                stop_daemon
                ;;
            3)
                show_status
                ;;
            4)
                force_update
                ;;
            5)
                show_logs
                ;;
            6)
                run_test
                ;;
            0)
                echo -e "${GREEN}再见!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选项，请重新选择${NC}"
                ;;
        esac
        
        echo ""
        read -p "$(echo -e "${WHITE}按回车键继续...${NC}")"
    done
}

# 显示帮助
show_help() {
    echo -e "${WHITE}用法:${NC}"
    echo -e "  $0 [命令]"
    echo ""
    echo -e "${WHITE}命令:${NC}"
    echo -e "${CYAN}  start        启动守护进程${NC}"
    echo -e "${CYAN}  stop         停止守护进程${NC}"
    echo -e "${CYAN}  status       查看状态${NC}"
    echo -e "${CYAN}  force-update 强制更新Planet文件${NC}"
    echo -e "${CYAN}  logs         查看实时日志${NC}"
    echo -e "${CYAN}  test         运行系统测试${NC}"
    echo -e "${CYAN}  help         显示此帮助信息${NC}"
    echo ""
    echo -e "${WHITE}示例:${NC}"
    echo -e "  $0 start     # 启动守护进程"
    echo -e "  $0 status    # 查看状态"
    echo -e "  $0           # 进入交互式菜单"
}

# 主函数
main() {
    # 检查依赖
    check_dependencies
    
    # 显示横幅
    print_banner
    
    # 处理命令行参数
    case "${1:-}" in
        start)
            start_daemon
            ;;
        stop)
            stop_daemon
            ;;
        status)
            show_status
            ;;
        force-update)
            force_update
            ;;
        logs)
            show_logs
            ;;
        test)
            run_test
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            # 无参数时进入交互式菜单
            interactive_menu
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 信号处理
trap 'echo -e "\n${YELLOW}收到中断信号${NC}"; exit 0' INT TERM

# 运行主函数
main "$@"
