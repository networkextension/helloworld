#!/usr/bin/env python3
"""
命令行基础框架
单文件可执行脚本，支持 -h / --help 参数展示所有可用命令说明。

用法:
    python cli.py <command> [options]
    ./cli.py <command> [options]
"""

import argparse
import datetime
import os
import platform
import subprocess
import sys
from typing import Dict, List, Optional


__version__ = "0.1.0"


def cmd_greet(args: argparse.Namespace) -> int:
    """问候命令：输出问候语"""
    name = args.name or "World"
    print(f"Hello, {name}!")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """版本命令：输出版本信息"""
    print(f"cli.py version {__version__}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """列表命令：示例列表输出"""
    items = args.items or ["apple", "banana", "cherry"]
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    return 0


def cmd_time(args: argparse.Namespace) -> int:
    """时间命令：获取并输出当前本地时间"""
    fmt = args.format or "%Y-%m-%d %H:%M:%S"
    now = datetime.datetime.now()
    print(now.strftime(fmt))
    return 0


def _sysctl(key: str) -> Optional[str]:
    """调用 sysctl 获取系统参数值（macOS）"""
    try:
        result = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _read_cpuinfo() -> Dict[str, str]:
    """读取 /proc/cpuinfo 并解析关键字段（Linux）"""
    info: Dict[str, str] = {}
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if ":" in line:
                    key, val = line.split(":", 1)
                    info[key.strip()] = val.strip()
    except FileNotFoundError:
        pass
    return info


def get_cpu_info() -> Dict[str, Optional[str]]:
    """跨平台采集 CPU 硬件信息"""
    info: Dict[str, Optional[str]] = {
        "model": None,
        "cores_physical": None,
        "cores_logical": None,
        "architecture": platform.machine() or None,
        "frequency": None,
        "frequency_max": None,
    }

    system = platform.system()

    if system == "Darwin":
        info["model"] = _sysctl("machdep.cpu.brand_string")
        info["cores_physical"] = _sysctl("hw.physicalcpu")
        info["cores_logical"] = _sysctl("hw.logicalcpu")
        info["frequency"] = _sysctl("hw.cpufrequency")
        info["frequency_max"] = _sysctl("hw.cpufrequency_max")
    elif system == "Linux":
        cpuinfo = _read_cpuinfo()
        info["model"] = cpuinfo.get("model name")
        info["cores_physical"] = cpuinfo.get("cpu cores")
        info["cores_logical"] = cpuinfo.get("siblings")
        # 尝试读取 /sys 中的频率信息
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r") as f:
                info["frequency"] = f.read().strip()
        except FileNotFoundError:
            pass
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq", "r") as f:
                info["frequency_max"] = f.read().strip()
        except FileNotFoundError:
            pass
    else:
        # 通用回退
        info["cores_logical"] = str(os.cpu_count())

    return info


def _format_frequency(hz_str: Optional[str]) -> Optional[str]:
    """将频率字符串（Hz）格式化为可读形式"""
    if not hz_str:
        return None
    try:
        hz = int(hz_str)
        if hz >= 1_000_000_000:
            return f"{hz / 1_000_000_000:.2f} GHz"
        elif hz >= 1_000_000:
            return f"{hz / 1_000_000:.2f} MHz"
        elif hz >= 1_000:
            return f"{hz / 1_000:.2f} KHz"
        return f"{hz} Hz"
    except ValueError:
        return hz_str


def cmd_cpu(args: argparse.Namespace) -> int:
    """CPU 命令：读取并输出 CPU 硬件信息"""
    info = get_cpu_info()

    print("CPU 信息")
    print("=" * 40)
    print(f"  型号:         {info.get('model') or 'N/A'}")
    print(f"  架构:         {info.get('architecture') or 'N/A'}")
    print(f"  物理核心数:   {info.get('cores_physical') or 'N/A'}")
    print(f"  逻辑核心数:   {info.get('cores_logical') or 'N/A'}")

    freq = _format_frequency(info.get("frequency"))
    freq_max = _format_frequency(info.get("frequency_max"))
    if freq or freq_max:
        print(f"  当前频率:     {freq or 'N/A'}")
        print(f"  最大频率:     {freq_max or 'N/A'}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """构建并返回参数解析器"""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="命令行基础框架 - 支持多子命令的 CLI 工具",
        epilog="使用 '%(prog)s <command> -h' 查看具体命令的帮助信息",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="显示版本信息并退出",
    )

    subparsers = parser.add_subparsers(title="可用命令", dest="command", help="子命令说明")

    # greet 子命令
    greet_parser = subparsers.add_parser(
        "greet",
        help="输出问候语",
        description="向指定名称输出问候语。",
    )
    greet_parser.add_argument(
        "-n", "--name",
        type=str,
        default=None,
        help="要问候的名称 (默认: World)",
    )
    greet_parser.set_defaults(func=cmd_greet)

    # version 子命令
    version_parser = subparsers.add_parser(
        "version",
        help="显示版本信息",
        description="显示当前工具的版本号。",
    )
    version_parser.set_defaults(func=cmd_version)

    # list 子命令
    list_parser = subparsers.add_parser(
        "list",
        help="输出示例列表",
        description="输出一个示例列表，也可指定自定义条目。",
    )
    list_parser.add_argument(
        "items",
        nargs="*",
        default=None,
        help="自定义列表条目",
    )
    list_parser.set_defaults(func=cmd_list)

    # time 子命令
    time_parser = subparsers.add_parser(
        "time",
        help="获取当前本地时间",
        description="调用系统接口获取当前本地时间并格式化输出。",
    )
    time_parser.add_argument(
        "-f", "--format",
        type=str,
        default=None,
        help="时间格式字符串 (默认: %%Y-%%m-%%d %%H:%%M:%%S)",
    )
    time_parser.set_defaults(func=cmd_time)

    # cpu 子命令
    cpu_parser = subparsers.add_parser(
        "cpu",
        help="读取系统 CPU 硬件信息",
        description="读取系统 CPU 型号、核心数、频率等硬件信息并输出。",
    )
    cpu_parser.set_defaults(func=cmd_cpu)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
