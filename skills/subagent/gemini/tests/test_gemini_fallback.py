#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Gemini Skill 降级功能测试脚本

测试场景：
1. 正常调用 gemini CLI（模拟成功）
2. 模拟 gemini CLI 失败（各种错误场景）
3. 验证自动降级到 OpenCode paper agent
4. 测试输出文件保存功能
"""

import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional

# 测试配置
GEMINI_SCRIPT = "./.claude/skills/gemini/scripts/gemini.py"
GEMINI_FALLBACK_SCRIPT = "./.claude/skills/gemini/scripts/gemini_fallback.py"
TEST_PROMPT = "解释一下量子计算的基本原理"
TEST_WORKDIR = "."


# 颜色输出
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_test_header(test_name: str):
    """打印测试标题"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}测试: {test_name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")


def print_success(message: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """打印错误消息"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def create_mock_gemini_cli(success: bool = True, error_type: str = "rate_limit") -> str:
    """
    创建模拟的 gemini CLI 脚本

    Args:
        success: 是否模拟成功
        error_type: 错误类型 (rate_limit, quota_exceeded, auth_failed, not_found)

    Returns:
        临时脚本路径
    """
    temp_dir = tempfile.mkdtemp()
    mock_script = Path(temp_dir) / "gemini"

    if success:
        # 模拟成功的 gemini CLI
        content = """#!/bin/bash
echo "这是 Gemini CLI 的模拟输出"
echo "量子计算是利用量子力学原理进行计算的技术..."
exit 0
"""
    else:
        # 模拟失败的 gemini CLI
        error_messages = {
            "rate_limit": "Error: rate limit exceeded. Please try again later.",
            "quota_exceeded": "Error: quota exceeded. Your account has reached the monthly limit.",
            "auth_failed": "Error: authentication failed. Please check your API key.",
            "not_found": "",  # 命令未找到，脚本不存在
            "network_error": "Error: connection timed out. Network error occurred.",
            "503": "Error: service unavailable (503). The server is temporarily unable to handle the request.",
        }

        if error_type == "not_found":
            # 不创建脚本，模拟命令未找到
            return "/nonexistent/path/gemini"

        error_msg = error_messages.get(error_type, "Error: unknown error")
        content = f"""#!/bin/bash
echo "{error_msg}" >&2
exit 1
"""

    mock_script.write_text(content)
    mock_script.chmod(0o755)

    return str(mock_script)


def run_test_with_mock_cli(
    mock_cli_path: str, test_name: str
) -> Tuple[bool, str, str, int]:
    """
    使用模拟的 CLI 运行测试

    Returns:
        (success, stdout, stderr, returncode)
    """
    # 临时修改 PATH，将模拟 CLI 放在最前面
    env = os.environ.copy()
    mock_dir = str(Path(mock_cli_path).parent)
    env["PATH"] = f"{mock_dir}:{env['PATH']}"

    try:
        result = subprocess.run(
            ["python3", GEMINI_SCRIPT, TEST_PROMPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            env=env,
        )

        return (result.returncode == 0, result.stdout, result.stderr, result.returncode)
    except subprocess.TimeoutExpired:
        return False, "", "Timeout", 124
    except Exception as e:
        return False, "", str(e), 1


def test_normal_success():
    """测试 1: 正常调用成功"""
    print_test_header("测试 1: Gemini CLI 正常调用")

    # 创建模拟成功的 gemini CLI
    mock_cli = create_mock_gemini_cli(success=True)

    try:
        success, stdout, stderr, returncode = run_test_with_mock_cli(
            mock_cli, "normal_success"
        )

        if success:
            print_success("Gemini CLI 调用成功")
            print_info(f"返回码: {returncode}")
            print_info(f"输出: {stdout[:100]}...")

            # 检查是否没有触发降级
            if "falling back" not in stderr.lower():
                print_success("未触发降级机制（符合预期）")
            else:
                print_error("意外触发了降级机制")
                return False

            return True
        else:
            print_error(f"Gemini CLI 调用失败: {stderr}")
            return False

    finally:
        # 清理临时文件
        shutil.rmtree(Path(mock_cli).parent, ignore_errors=True)


def test_fallback_scenarios():
    """测试 2-7: 各种错误场景的降级"""
    scenarios = [
        ("rate_limit", "速率限制错误"),
        ("quota_exceeded", "额度用尽错误"),
        ("auth_failed", "认证失败错误"),
        ("network_error", "网络错误"),
        ("503", "服务不可用 (503)"),
        ("not_found", "命令未找到"),
    ]

    results = []

    for i, (error_type, description) in enumerate(scenarios, start=2):
        print_test_header(f"测试 {i}: {description}触发降级")

        # 创建模拟失败的 gemini CLI
        mock_cli = create_mock_gemini_cli(success=False, error_type=error_type)

        try:
            success, stdout, stderr, returncode = run_test_with_mock_cli(
                mock_cli, error_type
            )

            # 检查是否触发了降级
            fallback_triggered = (
                "falling back" in stderr.lower() or "fallback" in stderr.lower()
            )
            opencode_used = "opencode" in stderr.lower() or "paper" in stderr.lower()

            if fallback_triggered:
                print_success(f"✓ 成功触发降级机制")
                print_info(f"错误信息: {stderr[:200]}...")

                if opencode_used:
                    print_success("✓ 正确调用 OpenCode paper agent")
                else:
                    print_warning("⚠ 未明确提示使用 OpenCode paper agent")

                results.append(True)
            else:
                print_error(f"✗ 未能触发降级机制")
                print_info(f"返回码: {returncode}")
                print_info(f"stderr: {stderr[:200]}...")
                results.append(False)

        except Exception as e:
            print_error(f"测试异常: {e}")
            results.append(False)
        finally:
            # 清理临时文件
            if error_type != "not_found":
                shutil.rmtree(Path(mock_cli).parent, ignore_errors=True)

    return all(results)


def test_fallback_script_directly():
    """测试 8: 直接调用降级脚本"""
    print_test_header("测试 8: 直接调用 gemini_fallback.py")

    try:
        # 检查 OpenCode 是否可用
        check_result = subprocess.run(
            ["which", "opencode"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if check_result.returncode != 0:
            print_warning("OpenCode 未安装，跳过此测试")
            return True

        # 直接调用降级脚本
        result = subprocess.run(
            ["python3", GEMINI_FALLBACK_SCRIPT, "测试prompt: 什么是机器学习?"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print_success("降级脚本执行成功")
            print_info(f"输出: {result.stdout[:100]}...")
            return True
        else:
            print_error(f"降级脚本执行失败: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print_error("降级脚本执行超时")
        return False
    except Exception as e:
        print_error(f"测试异常: {e}")
        return False


def test_output_file_saving():
    """测试 9: 验证输出文件保存功能"""
    print_test_header("测试 9: 输出文件保存")

    output_dir = Path(".tmp/docs/output")

    # 记录测试前的文件数量
    if output_dir.exists():
        files_before = list(output_dir.glob("out_*_gemini*.md"))
        count_before = len(files_before)
    else:
        count_before = 0

    print_info(f"测试前输出文件数量: {count_before}")

    # 创建模拟成功的 gemini CLI
    mock_cli = create_mock_gemini_cli(success=True)

    try:
        success, stdout, stderr, returncode = run_test_with_mock_cli(
            mock_cli, "output_test"
        )

        # 检查是否生成了新文件
        if output_dir.exists():
            files_after = list(output_dir.glob("out_*_gemini*.md"))
            count_after = len(files_after)

            if count_after > count_before:
                print_success(
                    f"✓ 成功生成输出文件 (新增 {count_after - count_before} 个)"
                )

                # 显示最新的输出文件
                latest_file = max(files_after, key=lambda p: p.stat().st_mtime)
                print_info(f"最新文件: {latest_file.name}")

                return True
            else:
                print_warning("⚠ 未生成新的输出文件")
                return False
        else:
            print_error("✗ 输出目录不存在")
            return False

    finally:
        # 清理临时文件
        shutil.rmtree(Path(mock_cli).parent, ignore_errors=True)


def run_all_tests():
    """运行所有测试"""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}Gemini Skill 降级功能测试套件{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    results = {}

    # 测试 1: 正常调用
    results["正常调用"] = test_normal_success()

    # 测试 2-7: 降级场景
    results["降级场景"] = test_fallback_scenarios()

    # 测试 8: 直接调用降级脚本
    results["直接调用降级脚本"] = test_fallback_script_directly()

    # 测试 9: 输出文件保存
    results["输出文件保存"] = test_output_file_saving()

    # 汇总结果
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}测试结果汇总{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: 通过")
        else:
            print_error(f"{test_name}: 失败")

    print(f"\n{Colors.BLUE}总计: {passed}/{total} 测试通过{Colors.RESET}")

    if passed == total:
        print(f"{Colors.GREEN}✓ 所有测试通过！{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}✗ 部分测试失败{Colors.RESET}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被用户中断{Colors.RESET}")
        sys.exit(130)
