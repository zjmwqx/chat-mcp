"""
测试完整的MCP工作流程
演示如何使用新的 easy_chat API 进行 MCP 工具对话

使用方法：
1. 确保在 .venv 环境中
2. 确保 .env 文件配置了 OPENAI_API_KEY 等必要参数
3. 运行: python test_final_workflow.py
"""

import asyncio
import logging
from chat_mcp import MCPChatTool

# 设置日志级别
logging.basicConfig(level=logging.INFO)


async def test_mcp_chat_tool():
    """测试 MCPChatTool 主要API"""
    print("🧪 测试 1: MCPChatTool 完整工作流程")

    # 创建聊天工具
    chat_tool = MCPChatTool()

    # 启动ArXiv MCP服务器
    try:
        server = await chat_tool.start_mcp_server(
            server_id="test_arxiv",
            name="Test ArXiv Server",
            command="uv",
            args=["tool", "run", "arxiv-mcp-server"],
        )
        print(f"✅ 服务器启动成功: {server.name}")

        # 查看服务器列表
        servers = chat_tool.list_servers()
        print(f"📋 当前管理的服务器: {len(servers)} 个")
        for s in servers:
            print(f"   - {s['name']} (ID: {s['id']})")

        # 进行对话，会自动工具调用
        print("\n💬 开始对话...")

        def progress_callback(message):
            print(f"📈 {message}")

        result = await chat_tool.chat_with_mcp(
            user_message="搜索最新的关于 transformer neural networks 的论文，帮我找到3篇相关的论文",
            system_prompt="你是一个学术研究助手，善于帮助用户找到相关的学术论文。",
            on_progress=progress_callback,
        )

        print(f"\n🎯 最终回答: {result['content']}")
        print(f"🔧 工具调用次数: {len(result.get('tool_calls', []))}")
        print(f"📊 使用情况: {result.get('usage', {})}")

        if "error" in result:
            print(f"❌ 错误: {result['error']}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


async def test_custom_server():
    """测试自定义服务器配置"""
    print("\n🧪 测试 4: 自定义服务器配置")

    from chat_mcp import create_server_config

    # 创建自定义服务器配置（这里还是用ArXiv做演示）
    custom_server = create_server_config(
        server_id="my_custom_arxiv",
        name="My Custom ArXiv Server",
        command="uv",
        args=["tool", "run", "arxiv-mcp-server"],
    )

    print("✅ 自定义服务器配置创建成功:")
    print(f"   ID: {custom_server.id}")
    print(f"   名称: {custom_server.name}")
    print(f"   命令: {custom_server.command} {' '.join(custom_server.args)}")


async def main():
    """主测试函数"""
    print("🚀 开始测试完整的MCP工作流程\n")

    # 测试主要API
    await test_mcp_chat_tool()

    # 测试便捷函数
    # await test_convenience_functions()  # TODO: 需要实现这个函数

    # 测试同步函数
    # test_sync_function()  # TODO: 需要实现这个函数

    # 测试自定义服务器
    await test_custom_server()

    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
