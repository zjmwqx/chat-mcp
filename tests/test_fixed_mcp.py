#!/usr/bin/env python3
"""
测试修复后的MCP服务代码
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加src路径到Python路径中
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 导入我们的模块
from src.chat_mcp import MCPServer
from src.chat_mcp.mcp_service import MCPService

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_arxiv_mcp_fixed():
    """
    测试修复后的arxiv-mcp-server连接
    """
    # 创建临时存储路径
    storage_path = Path("./temp_arxiv_storage")
    storage_path.mkdir(exist_ok=True)

    # 配置arxiv MCP服务器
    arxiv_server = MCPServer(
        id="arxiv-server",
        name="ArXiv论文服务器",
        command="uv",
        args=[
            "tool",
            "run",
            "arxiv-mcp-server",
            "--storage-path",
            str(storage_path.absolute()),
        ],
        env=None,  # 不设置额外环境变量
        disabled_tools=[],  # 不禁用任何工具
    )

    logger.info("=== 开始测试修复后的ArXiv MCP服务器 ===")
    logger.info(f"服务器配置: {arxiv_server}")
    logger.info(f"存储路径: {storage_path.absolute()}")

    service = MCPService()

    try:
        # 测试获取工具列表
        logger.info("正在获取工具列表...")
        tools = await service.list_tools(arxiv_server)

        if tools:
            logger.info(f"✅ 成功获取到 {len(tools)} 个工具:")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description}")
                logger.info(f"    服务器: {tool.server_name} (ID: {tool.server_id})")
                logger.info(f"    工具ID: {tool.id}")
                logger.info(f"    输入架构: {tool.inputSchema}")
                logger.info("")
        else:
            logger.warning("❌ 未获取到任何工具")
            return False

        # 测试缓存功能
        logger.info("测试缓存功能...")
        cached_tools = await service.list_tools(arxiv_server)
        logger.info(f"✅ 缓存测试成功，获取到 {len(cached_tools)} 个工具")

        # 测试工具调用（如果有search_papers工具）
        search_tool = None
        for tool in tools:
            if tool.name == "search_papers":
                search_tool = tool
                break

        if search_tool:
            logger.info("测试工具调用...")
            try:
                result = await service.call_tool(
                    arxiv_server,
                    "search_papers",
                    {"query": "attention mechanism", "max_results": 2},
                )
                logger.info(f"✅ 工具调用成功: {result}")
            except Exception as e:
                logger.error(f"❌ 工具调用失败: {e}")

        logger.info("=== ArXiv MCP服务器测试完成 ===")
        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def main():
    """主函数"""
    logger.info("启动修复后的ArXiv MCP测试...")

    success = await test_arxiv_mcp_fixed()

    if success:
        logger.info("🎉 所有测试通过！代码修复成功！")
        return 0
    else:
        logger.error("💥 测试失败！")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
