package main

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

// runOrWarn runs a command and returns its output.
// If the command fails, it prints a warning to stderr and returns an error.
func runOrWarn(cmdDesc string, name string, args ...string) (string, error) {
	cmd := exec.Command(name, args...)
	output, err := cmd.Output()
	if err != nil {
		fmt.Fprintf(os.Stderr, "[获取失败: %s]", cmdDesc)
		return "", err
	}
	return strings.TrimSpace(string(output)), nil
}

func main() {
	hasError := false

	// 获取操作系统信息
	osName, err := runOrWarn("操作系统名称", "sw_vers", "-productName")
	if err != nil {
		hasError = true
	}

	osVersion, err := runOrWarn("操作系统版本", "sw_vers", "-productVersion")
	if err != nil {
		hasError = true
	}

	buildVersion, err := runOrWarn("构建版本", "sw_vers", "-buildVersion")
	if err != nil {
		hasError = true
	}

	// 获取当前时间（使用 date 命令以与原始脚本行为保持一致，失败时回退到 time.Now）
	currentTime, err := runOrWarn("系统时间", "date", "+%Y-%m-%d %H:%M:%S")
	if err != nil {
		hasError = true
		currentTime = time.Now().Format("2006-01-02 15:04:05")
	}

	// 获取父进程名称
	var parentProc string
	ppidStr, err := runOrWarn("父进程ID", "ps", "-o", "ppid=", "-p", strconv.Itoa(os.Getpid()))
	if err != nil {
		hasError = true
	} else {
		ppid, err := strconv.Atoi(ppidStr)
		if err != nil {
			hasError = true
		} else {
			parentProc, err = runOrWarn("父进程名称", "ps", "-o", "comm=", "-p", strconv.Itoa(ppid))
			if err != nil {
				hasError = true
			}
		}
	}

	// 统一格式化输出
	fmt.Println("========================================")
	fmt.Println("            系统信息摘要")
	fmt.Println("========================================")
	fmt.Println("  消息      : Hello World")
	fmt.Printf("  当前时间  : %s\n", currentTime)
	fmt.Printf("  操作系统  : %s %s (%s)\n", osName, osVersion, buildVersion)
	fmt.Printf("  父进程    : %s\n", parentProc)
	fmt.Println("========================================")

	if hasError {
		fmt.Fprintln(os.Stderr, "警告: 部分信息获取失败，请检查系统环境。")
		os.Exit(1)
	}
}
