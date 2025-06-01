"""
MCP服务模块：负责管理MCP服务器连接和工具操作
"""

import logging
from typing import Dict, List, Optional, Any
import time
import hashlib

# 修正导入方式
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_types import MCPServer, MCPTool

# 设置日志
logger = logging.getLogger(__name__)


def generate_id() -> str:
    """生成唯一ID"""
    return f"f{int(time.time() * 1000000) % 1000000:06d}"


class MCPService:
    """
    MCP服务管理类

    管理MCP服务器连接和工具列表获取，提供缓存功能
    """

    def __init__(self):
        self._tool_cache: Dict[str, List[MCPTool]] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._cache_duration = 5 * 60  # 5分钟缓存

    def _get_server_key(self, server: MCPServer) -> str:
        """获取服务器缓存键"""
        server_data = f"{server.command}:{':'.join(server.args)}"
        return hashlib.md5(server_data.encode()).hexdigest()

    async def _list_tools_impl(self, server: MCPServer) -> List[MCPTool]:
        """
        从MCP服务器获取工具列表的实现

        Args:
            server: MCP服务器配置

        Returns:
            List[MCPTool]: 工具列表
        """
        logger.info(f"[MCP] 正在获取工具列表: {server.name}")

        try:
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=server.command, args=server.args, env=server.env
            )

            # 使用正确的连接方式
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化会话
                    await session.initialize()
                    logger.info(f"[MCP] 成功连接服务器: {server.name}")

                    # 获取工具列表
                    tools_response = await session.list_tools()
                    tools = (
                        tools_response.tools if hasattr(tools_response, "tools") else []
                    )

                    server_tools: List[MCPTool] = []

                    for tool in tools:
                        # 创建MCPTool对象
                        server_tool = MCPTool(
                            id=generate_id(),
                            name=tool.name,
                            description=tool.description or "",
                            inputSchema=tool.inputSchema or {},
                            server_id=server.id,
                            server_name=server.name,
                        )
                        server_tools.append(server_tool)

                    logger.info(
                        f"[MCP] 获取到 {len(server_tools)} 个工具: {server.name}"
                    )
                    return server_tools

        except Exception as error:
            logger.error(f"[MCP] 获取工具列表失败: {server.name}", exc_info=error)
            return []

    def _is_cache_valid(self, server_key: str) -> bool:
        """检查缓存是否有效"""
        if server_key not in self._cache_ttl:
            return False
        return time.time() - self._cache_ttl[server_key] < self._cache_duration

    async def list_tools(self, server: MCPServer) -> List[MCPTool]:
        """
        获取MCP服务器的工具列表（带缓存）

        Args:
            server: MCP服务器配置

        Returns:
            List[MCPTool]: 工具列表
        """
        server_key = self._get_server_key(server)

        # 检查缓存
        if self._is_cache_valid(server_key) and server_key in self._tool_cache:
            logger.debug(f"[MCP] 使用缓存的工具列表: {server.name}")
            return self._tool_cache[server_key]

        # 获取工具列表
        tools = await self._list_tools_impl(server)

        # 过滤被禁用的工具
        if server.disabled_tools:
            tools = [tool for tool in tools if tool.name not in server.disabled_tools]
            logger.info(f"[MCP] 过滤后剩余 {len(tools)} 个工具: {server.name}")

        # 更新缓存
        self._tool_cache[server_key] = tools
        self._cache_ttl[server_key] = time.time()

        return tools

    async def get_all_tools(self, servers: List[MCPServer]) -> List[MCPTool]:
        """
        获取所有启用的MCP服务器的工具列表

        Args:
            servers: MCP服务器列表

        Returns:
            List[MCPTool]: 所有工具列表
        """
        all_tools: List[MCPTool] = []

        for server in servers:
            try:
                tools = await self.list_tools(server)
                all_tools.extend(tools)
            except Exception as error:
                logger.error(f"[MCP] 获取服务器工具失败: {server.name}", exc_info=error)
                continue

        logger.info(f"[MCP] 总共获取到 {len(all_tools)} 个工具")
        return all_tools

    async def call_tool(
        self, server: MCPServer, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用MCP工具

        Args:
            server: MCP服务器配置
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            Dict[str, Any]: 工具调用结果
        """
        try:
            logger.info(f"[MCP] 调用工具: {tool_name} 在服务器: {server.name}")

            # 创建服务器参数
            server_params = StdioServerParameters(
                command=server.command, args=server.args, env=server.env
            )

            # 使用正确的连接方式调用工具
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)

                    logger.info(f"[MCP] 工具调用成功: {tool_name}")
                    return result

        except Exception as error:
            logger.error(f"[MCP] 工具调用失败: {tool_name}", exc_info=error)
            raise


# 全局服务实例
_mcp_service_instance: Optional[MCPService] = None


def get_mcp_service() -> MCPService:
    """获取全局MCP服务实例"""
    global _mcp_service_instance
    if _mcp_service_instance is None:
        _mcp_service_instance = MCPService()
    return _mcp_service_instance


# 便捷函数
async def init_mcp_server(server: MCPServer) -> MCPService:
    """
    初始化MCP服务器

    Args:
        server: MCP服务器配置

    Returns:
        MCPService: MCP服务实例
    """
    service = get_mcp_service()
    # 预热连接 - 获取一次工具列表
    await service.list_tools(server)
    return service


async def list_mcp_tools(servers: List[MCPServer]) -> List[MCPTool]:
    """
    获取MCP工具列表

    Args:
        servers: MCP服务器列表

    Returns:
        List[MCPTool]: 工具列表
    """
    service = get_mcp_service()
    return await service.get_all_tools(servers)
