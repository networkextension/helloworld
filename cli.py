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


def _bytes_to_human(byte_str: Optional[str]) -> Optional[str]:
    """将字节数字符串转换为人类可读格式"""
    if not byte_str:
        return None
    try:
        size = int(byte_str)
        if size >= 1 << 30:
            return f"{size / (1 << 30):.2f} GB"
        elif size >= 1 << 20:
            return f"{size / (1 << 20):.2f} MB"
        elif size >= 1 << 10:
            return f"{size / (1 << 10):.2f} KB"
        return f"{size} B"
    except ValueError:
        return byte_str


def _parse_vm_stat() -> Dict[str, int]:
    """解析 macOS vm_stat 输出，返回页面计数字典"""
    stats: Dict[str, int] = {}
    try:
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # 匹配 "Pages free:                               60089."
            if ":" in line:
                key_part, val_part = line.split(":", 1)
                val_clean = val_part.strip().replace(".", "")
                if val_clean.isdigit():
                    stats[key_part.strip()] = int(val_clean)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return stats


def get_mem_info() -> Dict[str, Optional[str]]:
    """跨平台采集内存容量信息"""
    info: Dict[str, Optional[str]] = {
        "total": None,
        "available": None,
        "used": None,
        "free": None,
    }

    system = platform.system()

    if system == "Darwin":
        # 总内存
        total_bytes = _sysctl("hw.memsize")
        if total_bytes:
            info["total"] = total_bytes

        # 页面大小
        page_size_str = _sysctl("hw.pagesize")
        page_size = int(page_size_str) if page_size_str and page_size_str.isdigit() else 16384

        # vm_stat 解析
        vm = _parse_vm_stat()
        free_pages = vm.get("Pages free", 0)
        inactive_pages = vm.get("Pages inactive", 0)
        speculative_pages = vm.get("Pages speculative", 0)
        active_pages = vm.get("Pages active", 0)
        wired_pages = vm.get("Pages wired down", 0)
        compressor_pages = vm.get("Pages occupied by compressor", 0)

        free_bytes = (free_pages + inactive_pages + speculative_pages) * page_size
        used_bytes = (active_pages + wired_pages + compressor_pages) * page_size
        available_bytes = free_bytes  # 近似可用

        info["free"] = str(free_bytes)
        info["used"] = str(used_bytes)
        info["available"] = str(available_bytes)

    elif system == "Linux":
        meminfo: Dict[str, str] = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        # val 形如 " 8000000 kB"
                        num = val.strip().split()[0] if val.strip() else "0"
                        meminfo[key.strip()] = num
        except FileNotFoundError:
            pass

        def _kb_to_bytes(kb: str) -> str:
            return str(int(kb) * 1024)

        info["total"] = _kb_to_bytes(meminfo.get("MemTotal", "0"))
        info["free"] = _kb_to_bytes(meminfo.get("MemFree", "0"))
        info["available"] = _kb_to_bytes(meminfo.get("MemAvailable", meminfo.get("MemFree", "0")))
        # used ≈ total - available
        try:
            used_kb = int(meminfo.get("MemTotal", "0")) - int(meminfo.get("MemAvailable", meminfo.get("MemFree", "0")))
            info["used"] = _kb_to_bytes(str(used_kb))
        except ValueError:
            info["used"] = None

    return info


def cmd_mem(args: argparse.Namespace) -> int:
    """内存命令：读取并输出内存容量信息"""
    info = get_mem_info()

    print("内存信息")
    print("=" * 40)
    print(f"  总内存:   {_bytes_to_human(info.get('total')) or 'N/A'}")
    print(f"  已使用:   {_bytes_to_human(info.get('used')) or 'N/A'}")
    print(f"  可用内存: {_bytes_to_human(info.get('available')) or 'N/A'}")
    print(f"  空闲内存: {_bytes_to_human(info.get('free')) or 'N/A'}")

    return 0


# 常见的虚拟/伪文件系统类型，采集磁盘信息时跳过
_SKIP_FSTYPES = {
    "devfs", "devtmpfs", "tmpfs", "proc", "sysfs",
    "cgroup", "cgroup2", "overlay", "squashfs",
    "autofs", "fuse", "fusectl", "securityfs",
    "pstore", "bpf", "configfs", "debugfs",
    "tracefs", "mqueue", "hugetlbfs", "rpc_pipefs",
    "binfmt_misc", "nfsd", "efivarfs",
}


def _get_mounts() -> List[Dict[str, str]]:
    """获取系统挂载点列表，返回 [{device, mountpoint, fstype}, ...]"""
    system = platform.system()
    mounts: List[Dict[str, str]] = []

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["mount"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                # 格式: /dev/disk2s1 on / (apfs, sealed, local, journaled)
                if " on " not in line or " (" not in line:
                    continue
                device, rest = line.split(" on ", 1)
                mountpoint, rest = rest.split(" (", 1)
                fstype = rest.split(",")[0].strip()
                mounts.append({
                    "device": device.strip(),
                    "mountpoint": mountpoint.strip(),
                    "fstype": fstype,
                })
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    elif system == "Linux":
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        mounts.append({
                            "device": parts[0],
                            "mountpoint": parts[1],
                            "fstype": parts[2],
                        })
        except FileNotFoundError:
            pass

    return mounts


def get_disk_info() -> List[Dict[str, Optional[str]]]:
    """跨平台采集各挂载磁盘容量信息"""
    disks: List[Dict[str, Optional[str]]] = []
    seen: set = set()

    for mount in _get_mounts():
        mp = mount["mountpoint"]
        fstype = mount["fstype"]

        # 跳过虚拟文件系统
        if fstype in _SKIP_FSTYPES:
            continue
        # 跳过已处理的挂载点
        if mp in seen:
            continue
        seen.add(mp)

        try:
            st = os.statvfs(mp)
        except OSError:
            continue

        if st.f_blocks == 0:
            continue

        frsize = st.f_frsize
        total = frsize * st.f_blocks
        free = frsize * st.f_bavail
        used = total - free
        usage_pct = (used / total * 100) if total else 0.0

        disks.append({
            "device": mount["device"],
            "mountpoint": mp,
            "fstype": fstype,
            "total": str(total),
            "used": str(used),
            "free": str(free),
            "usage_pct": f"{usage_pct:.1f}%",
        })

    # 按挂载点排序
    disks.sort(key=lambda d: d["mountpoint"] or "")
    return disks


def cmd_disk(args: argparse.Namespace) -> int:
    """磁盘命令：读取并输出各挂载磁盘容量信息"""
    disks = get_disk_info()

    if not disks:
        print("未找到可用的磁盘挂载信息。")
        return 0

    print(f"{'挂载点':<30} {'总容量':>10} {'已用':>10} {'可用':>10} {'使用率':>8}")
    print("=" * 72)
    for d in disks:
        mp = d["mountpoint"] or "N/A"
        # 截断过长的挂载点路径
        if len(mp) > 28:
            mp = "..." + mp[-25:]
        total = _bytes_to_human(d.get("total")) or "N/A"
        used = _bytes_to_human(d.get("used")) or "N/A"
        free = _bytes_to_human(d.get("free")) or "N/A"
        pct = d.get("usage_pct") or "N/A"
        print(f"{mp:<30} {total:>10} {used:>10} {free:>10} {pct:>8}")

    return 0


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


def cmd_all(args: argparse.Namespace) -> int:
    """全量命令：一次性输出所有已支持的系统信息汇总"""
    print("系统信息汇总")
    print("=" * 50)
    print()

    # 本地时间
    cmd_time(argparse.Namespace(format=None))
    print()

    # CPU 信息
    cmd_cpu(argparse.Namespace())
    print()

    # 内存信息
    cmd_mem(argparse.Namespace())
    print()

    # 磁盘信息
    cmd_disk(argparse.Namespace())

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

    # mem 子命令
    mem_parser = subparsers.add_parser(
        "mem",
        help="读取系统内存容量信息",
        description="读取系统总内存、可用内存、已使用内存等容量数据并输出。",
    )
    mem_parser.set_defaults(func=cmd_mem)

    # disk 子命令
    disk_parser = subparsers.add_parser(
        "disk",
        help="读取各挂载磁盘容量信息",
        description="读取各挂载磁盘的总容量、已用容量、剩余容量及使用率并输出。",
    )
    disk_parser.set_defaults(func=cmd_disk)

    # all 子命令
    all_parser = subparsers.add_parser(
        "all",
        help="一键输出所有系统信息汇总",
        description="一次性输出本地时间、CPU、内存、磁盘等全部系统信息。",
    )
    all_parser.set_defaults(func=cmd_all)

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
