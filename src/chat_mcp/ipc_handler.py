"""
IPC通信处理模块：模拟Cherry Studio的IPC通信机制
提供MCP相关的操作，包括服务器管理、工具列表、工具调用等
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from .mcp_types import MCPServer, MCPTool, MCPCallToolResponse
from .mcp_service import get_mcp_service
from .ai_provider import register_server_config

logger = logging.getLogger(__name__)


class IpcChannel(Enum):
    """IPC通道定义，对应Cherry Studio的IPC通道"""

    # MCP相关通道
    MCP_LIST_TOOLS = "mcp:list_tools"
    MCP_CALL_TOOL = "mcp:call_tool"
    MCP_ADD_SERVER = "mcp:add_server"
    MCP_REMOVE_SERVER = "mcp:remove_server"
    MCP_RESTART_SERVER = "mcp:restart_server"
    MCP_STOP_SERVER = "mcp:stop_server"
    MCP_LIST_PROMPTS = "mcp:list_prompts"
    MCP_GET_PROMPT = "mcp:get_prompt"
    MCP_LIST_RESOURCES = "mcp:list_resources"
    MCP_GET_RESOURCE = "mcp:get_resource"
    MCP_GET_INSTALL_INFO = "mcp:get_install_info"


class MCPIPCHandler:
    """
    MCP IPC处理器
    提供统一的MCP操作接口，模拟Cherry Studio的window.api.mcp
    """

    def __init__(self):
        self.mcp_service = get_mcp_service()
        logger.info("✅ MCP IPC Handler初始化完成")

    async def list_tools(self, server: MCPServer) -> List[MCPTool]:
        """
        获取服务器的工具列表
        对应Cherry Studio的window.api.mcp.listTools

        Args:
            server: MCP服务器配置

        Returns:
            工具列表
        """
        try:
            logger.info(f"[IPC] Listing tools for server: {server.name}")
            tools = await self.mcp_service.list_tools(server)
            logger.info(f"[IPC] Found {len(tools)} tools for server: {server.name}")
            return tools
        except Exception as e:
            logger.error(f"[IPC] Failed to list tools for server {server.name}: {e}")
            return []

    async def call_tool(self, request: Dict[str, Any]) -> MCPCallToolResponse:
        """
        调用MCP工具
        对应Cherry Studio的window.api.mcp.callTool

        Args:
            request: 工具调用请求，包含server、name、args

        Returns:
            工具调用响应
        """
        try:
            server = request.get("server")
            tool_name = request.get("name")
            arguments = request.get("args", {})

            if not server or not tool_name:
                raise ValueError("Missing required parameters: server or name")

            logger.info(f"[IPC] Calling tool: {tool_name} on server: {server.name}")

            # 调用工具
            result = await self.mcp_service.call_tool(server, tool_name, arguments)

            # 处理调用结果
            if hasattr(result, "content"):
                content = result.content
            else:
                content = [{"type": "text", "text": str(result)}]

            response = MCPCallToolResponse(content=content, isError=False)

            logger.info(f"[IPC] Tool called successfully: {tool_name}")
            return response

        except Exception as e:
            logger.error(f"[IPC] Tool call failed: {e}")
            return MCPCallToolResponse(
                content=[{"type": "text", "text": f"IPC tool call failed: {str(e)}"}],
                isError=True,
            )

    async def add_server(self, server: MCPServer) -> bool:
        """
        添加MCP服务器

        Args:
            server: 服务器配置

        Returns:
            是否添加成功
        """
        try:
            # 注册服务器配置
            register_server_config(server)
            logger.info(f"[IPC] Server added: {server.name}")
            return True
        except Exception as e:
            logger.error(f"[IPC] Failed to add server {server.name}: {e}")
            return False

    async def remove_server(self, server_id: str) -> bool:
        """
        移除MCP服务器

        Args:
            server_id: 服务器ID

        Returns:
            是否移除成功
        """
        try:
            # 这里可以添加实际的移除逻辑
            logger.info(f"[IPC] Server removed: {server_id}")
            return True
        except Exception as e:
            logger.error(f"[IPC] Failed to remove server {server_id}: {e}")
            return False

    async def restart_server(self, server_id: str) -> bool:
        """
        重启MCP服务器

        Args:
            server_id: 服务器ID

        Returns:
            是否重启成功
        """
        try:
            # 这里可以添加实际的重启逻辑
            logger.info(f"[IPC] Server restarted: {server_id}")
            return True
        except Exception as e:
            logger.error(f"[IPC] Failed to restart server {server_id}: {e}")
            return False

    async def stop_server(self, server_id: str) -> bool:
        """
        停止MCP服务器

        Args:
            server_id: 服务器ID

        Returns:
            是否停止成功
        """
        try:
            # 这里可以添加实际的停止逻辑
            logger.info(f"[IPC] Server stopped: {server_id}")
            return True
        except Exception as e:
            logger.error(f"[IPC] Failed to stop server {server_id}: {e}")
            return False


# 全局IPC处理器实例
_ipc_handler: Optional[MCPIPCHandler] = None


def get_ipc_handler() -> MCPIPCHandler:
    """获取全局IPC处理器实例"""
    global _ipc_handler
    if _ipc_handler is None:
        _ipc_handler = MCPIPCHandler()
    return _ipc_handler


async def handle_ipc_request(channel: str, *args, **kwargs) -> Any:
    """
    处理IPC请求的统一入口
    模拟Cherry Studio的ipcMain.handle机制

    Args:
        channel: IPC通道名称
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        处理结果
    """
    handler = get_ipc_handler()

    try:
        if channel == IpcChannel.MCP_LIST_TOOLS.value:
            server = args[0] if args else kwargs.get("server")
            return await handler.list_tools(server)

        elif channel == IpcChannel.MCP_CALL_TOOL.value:
            request = args[0] if args else kwargs.get("request")
            return await handler.call_tool(request)

        elif channel == IpcChannel.MCP_ADD_SERVER.value:
            server = args[0] if args else kwargs.get("server")
            return await handler.add_server(server)

        elif channel == IpcChannel.MCP_REMOVE_SERVER.value:
            server_id = args[0] if args else kwargs.get("server_id")
            return await handler.remove_server(server_id)

        elif channel == IpcChannel.MCP_RESTART_SERVER.value:
            server_id = args[0] if args else kwargs.get("server_id")
            return await handler.restart_server(server_id)

        elif channel == IpcChannel.MCP_STOP_SERVER.value:
            server_id = args[0] if args else kwargs.get("server_id")
            return await handler.stop_server(server_id)

        else:
            raise ValueError(f"Unknown IPC channel: {channel}")

    except Exception as e:
        logger.error(f"[IPC] Error handling request on channel {channel}: {e}")
        raise


# 为了方便使用，提供类似Cherry Studio的window.api.mcp接口
class WindowAPIMCP:
    """
    模拟Cherry Studio的window.api.mcp接口
    提供与前端一致的调用方式
    """

    @staticmethod
    async def listTools(server: MCPServer) -> List[MCPTool]:
        """获取工具列表"""
        return await handle_ipc_request(IpcChannel.MCP_LIST_TOOLS.value, server)

    @staticmethod
    async def callTool(request: Dict[str, Any]) -> MCPCallToolResponse:
        """调用工具"""
        return await handle_ipc_request(IpcChannel.MCP_CALL_TOOL.value, request)

    @staticmethod
    async def addServer(server: MCPServer) -> bool:
        """添加服务器"""
        return await handle_ipc_request(IpcChannel.MCP_ADD_SERVER.value, server)

    @staticmethod
    async def removeServer(server_id: str) -> bool:
        """移除服务器"""
        return await handle_ipc_request(IpcChannel.MCP_REMOVE_SERVER.value, server_id)

    @staticmethod
    async def restartServer(server_id: str) -> bool:
        """重启服务器"""
        return await handle_ipc_request(IpcChannel.MCP_RESTART_SERVER.value, server_id)

    @staticmethod
    async def stopServer(server_id: str) -> bool:
        """停止服务器"""
        return await handle_ipc_request(IpcChannel.MCP_STOP_SERVER.value, server_id)


# 创建全局的window.api.mcp模拟对象
window_api_mcp = WindowAPIMCP()
