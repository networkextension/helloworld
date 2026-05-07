#!/usr/bin/env python3
"""
命令行基础框架
单文件可执行脚本，支持 -h / --help 参数展示所有可用命令说明。

用法:
    python cli.py <command> [options]
    ./cli.py <command> [options]
"""

import argparse
import sys
from typing import List, Optional


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
