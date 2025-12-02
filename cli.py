"""命令行接口模块"""
import click
import json
import sys
from pathlib import Path

from app import ZeroTierAutoApp
from config import get_config
from constants import APP_NAME, APP_VERSION
from utils import ensure_admin_privileges, check_zerotier_installed, check_windows_admin_privileges
from daemon_manager import DaemonManager
import platform


def require_admin(f):
    """装饰器：要求管理员权限"""
    import functools
    
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 检查ZeroTier是否安装
        if not check_zerotier_installed():
            click.echo("未检测到ZeroTier安装，请先安装ZeroTier One客户端", err=True)
            sys.exit(1)
        
        # 检查并确保管理员权限
        system = platform.system().lower()
        if system == "windows":
            # Windows: 使用更严格的权限检查
            if not check_windows_admin_privileges():
                click.echo("需要管理员权限才能执行此操作", err=True)
                click.echo("请右键点击命令提示符或PowerShell，选择'以管理员身份运行'", err=True)
                sys.exit(1)
        else:
            # macOS/Linux: 使用原有的权限检查
            if not ensure_admin_privileges():
                click.echo("需要管理员权限才能执行此操作", err=True)
                sys.exit(1)
        
        return f(*args, **kwargs)
    return wrapper


@click.group()
@click.version_option(version=APP_VERSION, prog_name=APP_NAME)
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--config-file', '-c', type=click.Path(exists=True), help='配置文件路径')
@click.pass_context
def cli(ctx, verbose, config_file):
    """ZeroTier自动Planet文件替换工具"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file


@cli.command()
@require_admin
@click.pass_context
def check(ctx):
    """检查一次IP变动并更新（如果需要）"""
    try:
        config = get_config()
        app = ZeroTierAutoApp(config)
        
        # 检查前提条件
        if not app.check_prerequisites():
            click.echo("前提条件检查失败", err=True)
            sys.exit(1)
        
        # 执行一次检查
        click.echo("检查IP变动...")
        updated = app.run_once()
        
        if updated:
            click.echo("检测到IP变动，Planet文件已更新")
        else:
            click.echo("IP无变动，无需更新")
        
        app.cleanup()
        
    except Exception as e:
        click.echo(f"执行失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@require_admin
@click.option('--interval', '-i', type=int, help='检查间隔（秒）')
@click.option('--background', is_flag=True, help='后台运行模式（内部使用）')
@click.pass_context
def daemon(ctx, interval, background):
    """以守护进程模式运行"""
    try:
        config = get_config()
        
        # 覆盖检查间隔
        if interval:
            config.check_interval = interval
        
        app = ZeroTierAutoApp(config)
        
        # 检查前提条件
        if not app.check_prerequisites():
            click.echo("前提条件检查失败", err=True)
            sys.exit(1)
        
        # 如果是后台模式，写入 PID 文件
        if background:
            import os
            config.daemon_pid_file.write_text(str(os.getpid()))
            click.echo(f"后台守护进程启动，PID: {os.getpid()}")
            click.echo(f"检查间隔: {config.check_interval}秒")
        else:
            click.echo(f"启动守护进程模式，检查间隔: {config.check_interval}秒")
            click.echo("按 Ctrl+C 停止")
        
        # 运行守护进程
        app.run_daemon()
        app.cleanup()
        
        # 清理 PID 文件
        if background and config.daemon_pid_file.exists():
            config.daemon_pid_file.unlink()
        
    except KeyboardInterrupt:
        if not background:
            click.echo("\n用户中断，程序退出")
        # 清理 PID 文件
        if background and config.daemon_pid_file.exists():
            config.daemon_pid_file.unlink()
    except Exception as e:
        click.echo(f"守护进程运行失败: {e}", err=True)
        # 清理 PID 文件
        if background and config.daemon_pid_file.exists():
            config.daemon_pid_file.unlink()
        sys.exit(1)


@cli.command()
@require_admin
@click.pass_context
def force_update(ctx):
    """强制更新Planet文件（不检查IP变动）"""
    try:
        config = get_config()
        app = ZeroTierAutoApp(config)
        
        # 检查前提条件
        if not app.check_prerequisites():
            click.echo("前提条件检查失败", err=True)
            sys.exit(1)
        
        click.echo("强制更新Planet文件...")
        
        if app.force_update():
            click.echo("Planet文件强制更新成功")
        else:
            click.echo("Planet文件强制更新失败", err=True)
            sys.exit(1)
        
        app.cleanup()
        
    except Exception as e:
        click.echo(f"强制更新失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'text']), default='text', help='输出格式')
@click.pass_context
def status(ctx, format):
    """显示当前状态"""
    try:
        config = get_config()
        app = ZeroTierAutoApp(config)
        
        status_info = app.status()
        
        if format == 'json':
            click.echo(json.dumps(status_info, indent=2, ensure_ascii=False))
        else:
            # 文本格式输出
            click.echo("ZeroTier Auto Planet 状态")
            click.echo("=" * 40)
            
            if 'error' in status_info:
                click.echo(f"错误: {status_info['error']}")
                sys.exit(1)
            
            # 当前IP列表
            current_ips = status_info.get('current_ips', [])
            if current_ips:
                click.echo(f"当前IP列表: {', '.join(current_ips)}")
            else:
                click.echo("当前IP列表: 无")
            
            # ZeroTier服务状态
            zerotier_running = status_info.get('zerotier_running', False)
            status_icon = "运行" if zerotier_running else "停止"
            click.echo(f"ZeroTier服务: {status_icon}{'中' if zerotier_running else ''}")
            
            # Planet文件信息
            planet_info = status_info.get('planet_file', {})
            if planet_info.get('exists'):
                size = planet_info.get('size', 0)
                modified = planet_info.get('modified', 'Unknown')
                click.echo(f"Planet文件: 存在 ({size} bytes, 修改时间: {modified})")
            else:
                click.echo("Planet文件: 不存在")
            
            # 配置信息
            config_info = status_info.get('config', {})
            click.echo(f"检查间隔: {config_info.get('check_interval', 'Unknown')}秒")
            click.echo(f"ZeroTier路径: {config_info.get('zerotier_path', 'Unknown')}")
        
        app.cleanup()
        
    except Exception as e:
        click.echo(f"获取状态失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def test(ctx):
    """测试网络连接和权限"""
    try:
        config = get_config()
        app = ZeroTierAutoApp(config)
        
        click.echo("运行系统测试...")
        
        # 测试网络连接
        click.echo("1. 测试网络连接...")
        try:
            ips = app.ip_monitor.fetch_remote_ips()
            parsed_ips = app.ip_monitor.parse_ips(ips)
            click.echo(f"   网络连接正常，获取到 {len(parsed_ips)} 个IP地址")
        except Exception as e:
            click.echo(f"   网络连接失败: {e}")
        
        # 测试文件权限
        click.echo("2. 测试文件权限...")
        if app.file_manager.check_permissions():
            click.echo("   文件权限检查通过")
        else:
            click.echo("   文件权限不足，请以管理员身份运行")
        
        # 测试ZeroTier服务
        click.echo("3. 测试ZeroTier服务...")
        if app.service_manager.check_zerotier_status():
            click.echo("   ZeroTier服务正在运行")
        else:
            click.echo("   ZeroTier服务未运行")
        
        # 测试ZeroTier CLI
        click.echo("4. 测试ZeroTier CLI...")
        if app.service_manager.verify_zerotier_peers():
            click.echo("   ZeroTier CLI可用，发现PLANET角色")
        else:
            click.echo("   ZeroTier CLI不可用或未发现PLANET角色")
        
        click.echo("测试完成")
        app.cleanup()
        
    except Exception as e:
        click.echo(f"测试失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='输出配置文件路径')
@click.pass_context
def init_config(ctx, output):
    """生成默认配置文件"""
    try:
        config_content = """# ZeroTier Auto Planet 配置文件
# 
# API配置
api_key: "54fbe2f7a1d2902d"
base_url: "http://songmd.yicp.fun:13000"

# 监控配置
check_interval: 300  # 检查间隔（秒）
download_timeout: 30  # 下载超时时间（秒）
max_retries: 3       # 最大重试次数

# 日志配置
log_level: "INFO"    # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""
        
        if output:
            config_path = Path(output)
        else:
            config_path = Path("config.yaml")
        
        config_path.write_text(config_content, encoding='utf-8')
        click.echo(f"配置文件已生成: {config_path}")
        
    except Exception as e:
        click.echo(f"生成配置文件失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@require_admin
@click.option('--interval', '-i', type=int, help='检查间隔（秒）')
@click.pass_context
def start(ctx, interval):
    """启动后台IP检测守护进程"""
    try:
        config = get_config()
        daemon_manager = DaemonManager(config)
        
        # 检查是否已经在运行
        if daemon_manager.is_running():
            click.echo("守护进程已在运行")
            pid = daemon_manager.get_pid()
            if pid:
                click.echo(f"PID: {pid}")
            sys.exit(0)
        
        # 启动守护进程
        click.echo("启动后台IP检测守护进程...")
        if daemon_manager.start_daemon(interval):
            pid = daemon_manager.get_pid()
            click.echo(f"✅ 守护进程启动成功，PID: {pid}")
            click.echo(f"日志文件: {config.daemon_log_file}")
            click.echo("使用 'uv run cli.py stop' 停止守护进程")
        else:
            click.echo("❌ 守护进程启动失败", err=True)
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"启动守护进程失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@require_admin
@click.pass_context
def stop(ctx):
    """停止后台IP检测守护进程"""
    try:
        config = get_config()
        daemon_manager = DaemonManager(config)
        
        # 检查是否在运行
        if not daemon_manager.is_running():
            click.echo("守护进程未运行")
            sys.exit(0)
        
        # 停止守护进程
        pid = daemon_manager.get_pid()
        click.echo(f"停止守护进程 (PID: {pid})...")
        
        if daemon_manager.stop_daemon():
            click.echo("✅ 守护进程已停止")
        else:
            click.echo("❌ 停止守护进程失败", err=True)
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"停止守护进程失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def daemon_status(ctx):
    """显示守护进程状态"""
    try:
        config = get_config()
        daemon_manager = DaemonManager(config)
        
        status = daemon_manager.get_status()
        
        click.echo("守护进程状态")
        click.echo("=" * 40)
        
        if status["running"]:
            click.echo(f"状态: 运行中")
            click.echo(f"PID: {status['pid']}")
            
            # 显示详细信息（如果可用）
            if "start_time" in status:
                import datetime
                start_time = datetime.datetime.fromtimestamp(status["start_time"])
                click.echo(f"启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if "memory_info" in status:
                memory_mb = status["memory_info"]["rss"] / 1024 / 1024
                click.echo(f"内存使用: {memory_mb:.1f} MB")
        else:
            click.echo("状态: 未运行")
        
        click.echo(f"PID文件: {status['pid_file']}")
        click.echo(f"日志文件: {status['log_file']}")
        
        # 显示日志文件是否存在
        if Path(status['log_file']).exists():
            log_size = Path(status['log_file']).stat().st_size
            click.echo(f"日志大小: {log_size} bytes")
        else:
            click.echo("日志文件: 不存在")
        
    except Exception as e:
        click.echo(f"获取守护进程状态失败: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
