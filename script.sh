#!/bin/bash

# ============================================================
# 系统信息摘要脚本（含错误处理）
# ============================================================

set -euo pipefail

# ------------------------------------------------------------
# 辅助函数：运行命令，失败时输出警告并返回回退值
# ------------------------------------------------------------
run_or_warn() {
    local cmd_desc="$1"
    shift
    local output

    if output=$("$@" 2>/dev/null); then
        printf '%s' "$output"
    else
        printf '%s' "[获取失败: ${cmd_desc}]" >&2
        return 1
    fi
}

# ------------------------------------------------------------
# 主函数入口
# ------------------------------------------------------------
main() {
    local os_name os_version build_version parent_proc current_time
    local has_error=0

    # 获取操作系统信息
    os_name=$(run_or_warn "操作系统名称" sw_vers -productName) || has_error=1
    os_version=$(run_or_warn "操作系统版本" sw_vers -productVersion) || has_error=1
    build_version=$(run_or_warn "构建版本" sw_vers -buildVersion) || has_error=1

    # 获取当前时间
    current_time=$(run_or_warn "系统时间" date '+%Y-%m-%d %H:%M:%S') || has_error=1

    # 获取父进程名称
    local ppid
    ppid=$(run_or_warn "父进程ID" ps -o ppid= -p $$) || has_error=1
    ppid=$(echo "$ppid" | xargs)
    parent_proc=$(run_or_warn "父进程名称" ps -o comm= -p "$ppid") || has_error=1
    parent_proc=$(echo "$parent_proc" | xargs)

    # 统一格式化输出
    cat <<EOF
========================================
            系统信息摘要
========================================
  消息      : Hello World
  当前时间  : ${current_time}
  操作系统  : ${os_name} ${os_version} (${build_version})
  父进程    : ${parent_proc}
========================================
EOF

    if [[ "$has_error" -ne 0 ]]; then
        echo "警告: 部分信息获取失败，请检查系统环境。" >&2
        return 1
    fi
}

# ------------------------------------------------------------
# 仅当脚本被直接执行时运行主函数
# ------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
