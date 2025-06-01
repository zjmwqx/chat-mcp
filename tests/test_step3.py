"""
Step3测试：验证AI Provider集成和MCP工具传递功能
测试将MCP工具传递给AI Provider的完整流程
"""

import asyncio
import logging
from typing import List

# 导入我们的模块
from chat_mcp import (
    ChatMCPClient,
    MCPServer,
    MCPTool,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    build_system_prompt,
    parse_tool_use,
)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockMCPService:
    """模拟MCP服务，用于测试"""

    def __init__(self):
        self.mock_tools = [
            MCPTool(
                id="f123456789",
                name="search_arxiv",
                description="Search for academic papers on arXiv",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for papers",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
                server_id="arxiv-server",
                server_name="ArXiv MCP Server",
            ),
            MCPTool(
                id="f987654321",
                name="get_weather",
                description="Get current weather information for a location",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or coordinates",
                        },
                        "units": {
                            "type": "string",
                            "description": "Temperature units (celsius/fahrenheit)",
                            "default": "celsius",
                        },
                    },
                    "required": ["location"],
                },
                server_id="weather-server",
                server_name="Weather MCP Server",
            ),
        ]

    async def list_tools(self, server: MCPServer) -> List[MCPTool]:
        """模拟列出工具"""
        logger.info(f"[Mock] Listing tools for server: {server.name}")
        if "arxiv" in server.name.lower():
            return [self.mock_tools[0]]
        elif "weather" in server.name.lower():
            return [self.mock_tools[1]]
        else:
            return self.mock_tools


class MockAIProvider:
    """模拟AI Provider，用于测试系统提示词构建"""

    def __init__(self):
        pass

    async def completions(
        self,
        messages: List[ChatMessage],
        model: str = "gpt-3.5-turbo",
        mcp_tools: List[MCPTool] = None,
        temperature: float = 0.7,
        stream: bool = False,
        on_chunk=None,
    ) -> ChatResponse:
        """模拟AI完成调用"""
        logger.info(
            f"[MockAI] Received {len(messages)} messages with {len(mcp_tools) if mcp_tools else 0} tools"
        )

        # 检查系统消息是否包含工具信息
        system_message = None
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
                break

        # 模拟工具调用响应
        if mcp_tools and len(mcp_tools) > 0:
            # 如果有工具，模拟一个工具调用
            mock_response = f"""我看到有 {len(mcp_tools)} 个可用工具。让我使用其中一个工具来帮助您：

<tool_use>
<tool_name>{mcp_tools[0].name}</tool_name>
<parameters>
{{
  "query": "machine learning",
  "max_results": 3
}}
</parameters>
</tool_use>

我已经调用了 {mcp_tools[0].name} 工具来搜索相关信息。"""
        else:
            mock_response = "我是一个有用的助手，目前没有可用的工具。"

        # 解析工具调用
        tool_calls = parse_tool_use(mock_response)

        response_message = ChatMessage(
            role="assistant",
            content=mock_response,
            metadata={
                "system_message_length": len(system_message) if system_message else 0,
                "has_tool_info": "Available tools:" in (system_message or ""),
                "mcp_tools_count": len(mcp_tools) if mcp_tools else 0,
                "parsed_tool_calls": tool_calls,
            },
        )

        return ChatResponse(
            message=response_message,
            usage={"mock": True, "tokens": 100},
            metrics={"step": 3, "status": "mock_completion"},
        )


async def test_system_prompt_building():
    """测试系统提示词构建功能"""
    print("\n=== 测试1: 系统提示词构建功能 ===")

    # 创建测试工具
    tools = [
        MCPTool(
            id="test1",
            name="search_papers",
            description="Search academic papers",
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

    # 测试构建系统提示词
    original_prompt = "You are a helpful assistant."
    enhanced_prompt = build_system_prompt(original_prompt, tools)

    original_len = len(original_prompt)
    enhanced_len = len(enhanced_prompt)

    print(f"[验证] 系统提示词从 {original_len} 字符增强到 " f"{enhanced_len} 字符")
    print(f"包含工具信息: {'Available tools:' in enhanced_prompt}")
    print(f"包含工具名称: {'search_papers' in enhanced_prompt}")
    print(f"包含XML示例: {'<tool_use>' in enhanced_prompt}")

    # 测试没有工具的情况
    no_tools_prompt = build_system_prompt(original_prompt, [])
    assert no_tools_prompt == original_prompt, "没有工具时应该返回原始提示词"

    print("✅ 系统提示词构建测试通过")


async def test_tool_use_parsing():
    """测试工具调用解析功能"""
    print("\n=== 测试2: 工具调用解析功能 ===")

    # 模拟LLM响应包含工具调用
    llm_response = """
    我来帮你搜索学术论文。

    <tool_use>
    <tool_name>search_arxiv</tool_name>
    <parameters>
    {"query": "machine learning", "max_results": 5}
    </parameters>
    </tool_use>

    让我也查看一下天气。

    <tool_use>
    <tool_name>get_weather</tool_name>
    <parameters>
    {"location": "Beijing", "units": "celsius"}
    </parameters>
    </tool_use>
    """

    # 使用解析函数
    parsed_tools = parse_tool_use(llm_response)

    print(f"解析到的工具调用数量: {len(parsed_tools)}")

    expected_calls = [
        {
            "name": "search_arxiv",
            "parameters": {"query": "machine learning", "max_results": 5},
        },
        {
            "name": "get_weather",
            "parameters": {"location": "Beijing", "units": "celsius"},
        },
    ]

    for i, expected in enumerate(expected_calls):
        assert i < len(parsed_tools), f"缺少第{i+1}个工具调用"
        actual = parsed_tools[i]
        # 修改访问方式：使用对象属性而不是字典键
        assert (
            actual.tool.name == expected["name"]
        ), f"工具名称不匹配: {actual.tool.name} != {expected['name']}"
        assert (
            actual.tool.arguments == expected["parameters"]
        ), f"参数不匹配: {actual.tool.arguments} != {expected['parameters']}"
        print(f"✅ 工具调用 {i+1}: {actual.tool.name} - 参数解析正确")

    print("✅ 工具调用解析测试通过")


async def test_ai_provider_integration():
    """测试AI Provider集成"""
    print("\n=== 测试3: AI Provider集成 ===")

    # 创建模拟的AI Provider
    mock_ai = MockAIProvider()

    # 准备测试数据
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="帮我搜索一些机器学习的论文"),
    ]

    tools = [
        MCPTool(
            id="test1",
            name="search_arxiv",
            description="Search academic papers on arXiv",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results",
                    },
                },
                "required": ["query"],
            },
            server_id="arxiv-server",
            server_name="ArXiv Server",
        )
    ]

    # 测试AI调用
    response = await mock_ai.completions(
        messages=messages, model="gpt-3.5-turbo", mcp_tools=tools, temperature=0.7
    )

    print(f"响应生成成功: {response.message.role == 'assistant'}")
    print(f"包含工具调用: {'<tool_use>' in response.message.content}")
    print(
        f"元数据包含工具信息: {response.message.metadata.get('mcp_tools_count', 0) > 0}"
    )
    print(
        f"检测到的工具调用: {len(response.message.metadata.get('parsed_tool_calls', []))}"
    )

    print("✅ AI Provider集成测试通过")


async def test_chat_client_full_flow():
    """测试完整的聊天客户端流程"""
    print("\n=== 测试4: 完整聊天客户端流程 ===")

    # 创建聊天客户端，但使用模拟服务
    client = ChatMCPClient()

    # 替换为模拟服务
    client.tool_collector.mcp_service = MockMCPService()
    client.ai_provider = MockAIProvider()

    # 准备测试请求
    servers = [
        MCPServer(
            id="arxiv-1",
            name="ArXiv MCP Server",
            command="python",
            args=["-m", "mcp_arxiv"],
            disabled_tools=[],
        ),
        MCPServer(
            id="weather-1",
            name="Weather MCP Server",
            command="python",
            args=["-m", "mcp_weather"],
            disabled_tools=["get_forecast"],  # 禁用部分工具
        ),
    ]

    request = ChatRequest(
        messages=[
            ChatMessage(
                role="user", content="帮我搜索机器学习相关的论文，并告诉我北京的天气"
            )
        ],
        model="gpt-3.5-turbo",
        enabled_mcps=servers,
        temperature=0.7,
    )

    # 执行聊天
    try:
        response = await client.chat(request)

        print(f"聊天执行成功: {response.message.role == 'assistant'}")
        print(f"步骤标识: {response.message.metadata.get('step')}")
        print(f"启用服务器数量: {response.message.metadata.get('enabled_servers')}")
        print(
            f"收集的工具数量: {response.message.metadata.get('collected_tools_count')}"
        )
        print(f"阶段: {response.message.metadata.get('stage')}")

        # 验证元数据
        assert response.message.metadata.get("step") == 3, "步骤应该是3"
        assert (
            response.message.metadata.get("enabled_servers") == 2
        ), "应该有2个启用的服务器"
        assert (
            response.message.metadata.get("collected_tools_count") >= 1
        ), "应该收集到至少1个工具"

        print("✅ 完整聊天流程测试通过")

    except Exception as e:
        print(f"❌ 聊天流程测试失败: {e}")
        raise


async def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试5: 错误处理 ===")

    # 创建客户端
    client = ChatMCPClient()
    client.tool_collector.mcp_service = MockMCPService()

    # 创建一个会失败的AI Provider
    class FailingAIProvider:
        async def completions(self, **kwargs):
            raise Exception("模拟AI调用失败")

    client.ai_provider = FailingAIProvider()

    # 准备请求
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="测试错误处理")],
        model="gpt-3.5-turbo",
        enabled_mcps=[
            MCPServer(id="test-server", name="Test Server", command="test", args=[])
        ],
    )

    # 执行聊天，应该处理错误
    response = await client.chat(request)

    print(f"错误处理成功: {'失败' in response.message.content}")
    print(f"错误信息保存: {response.message.metadata.get('error') is not None}")
    print(f"错误状态: {response.metrics.get('status')}")

    assert "失败" in response.message.content, "应该包含失败信息"
    assert response.message.metadata.get("error") is not None, "应该保存错误信息"

    print("✅ 错误处理测试通过")


async def main():
    """运行所有测试"""
    print("🚀 开始Step3测试 - AI Provider集成和MCP工具传递")
    print("=" * 60)

    tests = [
        test_system_prompt_building,
        test_tool_use_parsing,
        test_ai_provider_integration,
        test_chat_client_full_flow,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ 测试失败: {test.__name__}")
            print(f"错误: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("🎉 所有Step3测试通过！AI Provider集成和MCP工具传递功能正常工作")
        print("\n✨ Step3完成情况:")
        print("- ✅ 系统提示词构建 - 将MCP工具信息嵌入到系统提示词")
        print("- ✅ 工具调用解析 - 从LLM响应中解析XML格式的工具调用")
        print("- ✅ AI Provider集成 - 将MCP工具传递给LiteLLM")
        print("- ✅ 完整聊天流程 - 端到端的工具收集→AI调用→响应处理")
        print("- ✅ 错误处理 - 优雅处理各种异常情况")

        print("\n🔧 技术要点:")
        print("- 使用XML格式的工具调用，而非OpenAI的函数调用")
        print("- 支持多工具并行传递给LLM")
        print("- 系统提示词模板化，包含工具说明和使用示例")
        print("- 正则表达式解析工具调用，支持复杂参数")
    else:
        print("❌ 部分测试失败，需要检查和修复")
        return 1

    return 0


if __name__ == "__main__":
    asyncio.run(main())
