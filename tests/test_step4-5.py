"""
Task4-5简化测试：专门验证系统提示词构建功能
测试 buildSystemPrompt 函数是否正确实现了 Cherry Studio 的行为
"""

import logging
import os
import sys

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 导入我们的模块
from chat_mcp import (
    MCPTool,
    build_system_prompt,
)

# 设置日志
logging.basicConfig(level=logging.INFO)


def test_build_system_prompt_core():
    """测试buildSystemPrompt核心功能"""
    print("🔍 测试buildSystemPrompt核心功能")

    # 测试1：有工具时的系统提示词构建
    print("\n=== 测试1: 有工具时构建系统提示词 ===")

    tools = [
        MCPTool(
            id="test1",
            name="search_tool",
            description="Search for information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Result limit"},
                },
                "required": ["query"],
            },
            server_id="test-server",
            server_name="Test Server",
        )
    ]

    user_prompt = "You are a helpful assistant."
    result = build_system_prompt(user_prompt, tools)

    print(f"输入提示词: '{user_prompt}'")
    print(f"输出长度: {len(result)} 字符")

    # 核心验证点
    verifications = [
        ("包含原始用户提示词", user_prompt in result),
        ("包含工具使用示例", "You have access to a set of tools" in result),
        (
            "包含XML示例",
            "<tool_use>" in result
            and "<tool_name>" in result
            and "<parameters>" in result,
        ),
        ("包含可用工具标题", "Available tools:" in result),
        ("包含工具名称", "search_tool" in result),
        ("包含工具描述", "Search for information" in result),
        ("包含参数描述", "Search query" in result),
        ("包含必需参数标记", "(required)" in result),
        (
            "模板替换正确",
            "{{ USER_SYSTEM_PROMPT }}" not in result
            and "{{ TOOL_USE_EXAMPLES }}" not in result
            and "{{ AVAILABLE_TOOLS }}" not in result,
        ),
    ]

    passed = 0
    for desc, check in verifications:
        status = "✅" if check else "❌"
        print(f"  {status} {desc}")
        if check:
            passed += 1

    print(f"\n✅ 通过验证: {passed}/{len(verifications)}")

    # 测试2：无工具时返回原始提示词
    print("\n=== 测试2: 无工具时返回原始提示词 ===")

    # 空工具列表
    result_empty = build_system_prompt(user_prompt, [])
    print(f"空工具列表: '{result_empty}' (应该等于原始提示词)")
    print("✅ 空工具列表正确" if result_empty == user_prompt else "❌ 空工具列表错误")

    # None工具列表
    result_none = build_system_prompt(user_prompt, None)
    print(f"None工具列表: '{result_none}' (应该等于原始提示词)")
    print(
        "✅ None工具列表正确" if result_none == user_prompt else "❌ None工具列表错误"
    )

    # 测试3：展示完整的增强提示词
    print("\n=== 测试3: 完整增强提示词示例 ===")
    print(f"完整的增强提示词:\n{'-'*50}")
    print(result)
    print(f"{'-'*50}")

    return passed == len(verifications)


def test_xml_format_compliance():
    """测试XML格式是否符合Cherry Studio标准"""
    print("\n🔍 验证XML格式合规性")

    tools = [
        MCPTool(
            id="test1",
            name="example_tool",
            description="An example tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter 1"},
                    "param2": {"type": "number", "description": "Parameter 2"},
                },
                "required": ["param1"],
            },
            server_id="test",
            server_name="Test",
        )
    ]

    result = build_system_prompt("You are an assistant.", tools)

    # 检查XML结构
    xml_checks = [
        ("包含<tool_use>开始标签", "<tool_use>" in result),
        ("包含</tool_use>结束标签", "</tool_use>" in result),
        ("包含<tool_name>标签", "<tool_name>" in result),
        ("包含</tool_name>标签", "</tool_name>" in result),
        ("包含<parameters>标签", "<parameters>" in result),
        ("包含</parameters>标签", "</parameters>" in result),
        ("XML嵌套正确", result.count("<tool_use>") == result.count("</tool_use>")),
        (
            "包含JSON格式示例",
            '"parameter_name"' in result and '"parameter_value"' in result,
        ),
    ]

    passed = 0
    for desc, check in xml_checks:
        status = "✅" if check else "❌"
        print(f"  {status} {desc}")
        if check:
            passed += 1

    print(f"\n✅ XML格式验证: {passed}/{len(xml_checks)}")

    return passed == len(xml_checks)


def test_multiple_tools():
    """测试多个工具的情况"""
    print("\n🔍 测试多工具场景")

    tools = [
        MCPTool(
            id="tool1",
            name="search_arxiv",
            description="Search arXiv papers",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
            server_id="arxiv",
            server_name="ArXiv",
        ),
        MCPTool(
            id="tool2",
            name="get_weather",
            description="Get weather information",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location"}
                },
                "required": ["location"],
            },
            server_id="weather",
            server_name="Weather",
        ),
    ]

    result = build_system_prompt("You are an assistant.", tools)

    multi_tool_checks = [
        ("包含第一个工具", "search_arxiv" in result),
        ("包含第二个工具", "get_weather" in result),
        ("包含第一个工具描述", "Search arXiv papers" in result),
        ("包含第二个工具描述", "Get weather information" in result),
        (
            "工具列表格式正确",
            result.count("- **") >= 2,
        ),  # 每个工具都有"- **工具名**"格式
    ]

    passed = 0
    for desc, check in multi_tool_checks:
        status = "✅" if check else "❌"
        print(f"  {status} {desc}")
        if check:
            passed += 1

    print(f"\n✅ 多工具验证: {passed}/{len(multi_tool_checks)}")

    return passed == len(multi_tool_checks)


def main():
    """主测试函数"""
    print("🚀 Task4-5核心功能测试")
    print("=" * 60)

    # 运行所有测试
    test1_pass = test_build_system_prompt_core()
    test2_pass = test_xml_format_compliance()
    test3_pass = test_multiple_tools()

    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print(f"✅ 核心功能测试: {'通过' if test1_pass else '失败'}")
    print(f"✅ XML格式测试: {'通过' if test2_pass else '失败'}")
    print(f"✅ 多工具测试: {'通过' if test3_pass else '失败'}")

    all_passed = test1_pass and test2_pass and test3_pass

    print(f"\n🎯 Task4-5总体状态: {'✅ 完成' if all_passed else '❌ 需要修复'}")

    if all_passed:
        print("\n🎉 恭喜！Task4-5已成功实现：")
        print("  - buildSystemPrompt函数正确实现模板替换")
        print("  - 工具信息格式化为XML格式描述")
        print("  - 支持多工具和单工具场景")
        print("  - 正确处理无工具的边界情况")

    return all_passed


if __name__ == "__main__":
    # 检查虚拟环境
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print("✅ 在虚拟环境中运行")
    else:
        print("⚠️  不在虚拟环境中运行")

    success = main()
    sys.exit(0 if success else 1)
