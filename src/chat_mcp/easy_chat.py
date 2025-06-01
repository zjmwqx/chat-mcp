"""
MCP聊天工具脚手架 - 主要对外API
提供MCP服务器管理和完整的工具调用对话流程

使用方法：
1. 启动MCP服务器
2. 调用聊天API进行对话

这是一个脚手架，其他项目可以直接import使用
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from dotenv import load_dotenv

from .ai_provider import complete_mcp_workflow, register_server_config
from .mcp_service import get_mcp_service
from .mcp_types import ChatMessage, MCPServer

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MCPChatTool:
    """
    MCP聊天工具 - 脚手架的主要API类
    提供MCP服务器管理和完整对话流程
    """

    def __init__(self):
        """初始化MCP聊天工具"""
        # 加载环境变量
        load_dotenv()

        # 管理的MCP服务器
        self.managed_servers: Dict[str, MCPServer] = {}

        logger.info("✅ MCP聊天工具初始化完成")

    async def start_mcp_server(
        self,
        server_id: str,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
    ) -> MCPServer:
        """
        启动MCP服务器

        Args:
            server_id: 服务器ID
            name: 服务器名称
            command: 启动命令
            args: 命令参数
            env: 环境变量

        Returns:
            MCP服务器配置对象
        """
        logger.info(f"🚀 启动MCP服务器: {name}")

        # 创建服务器配置
        server = MCPServer(id=server_id, name=name, command=command, args=args, env=env)

        # 注册服务器配置（用于后续工具调用）
        register_server_config(server)

        # 测试连接
        try:
            mcp_service = get_mcp_service()
            tools = await mcp_service.list_tools(server)
            logger.info(f"✅ 服务器 {name} 启动成功，发现 {len(tools)} 个工具")

            # 保存到管理列表
            self.managed_servers[server_id] = server

            return server

        except Exception as e:
            logger.error(f"❌ 服务器 {name} 启动失败: {e}")
            raise Exception(f"MCP服务器启动失败: {e}")

    def list_servers(self) -> List[Dict[str, Any]]:
        """
        列出已管理的MCP服务器

        Returns:
            服务器信息列表
        """
        return [
            {
                "id": server.id,
                "name": server.name,
                "command": server.command,
                "args": server.args,
                "env": server.env,
            }
            for server in self.managed_servers.values()
        ]

    async def chat_with_mcp(
        self,
        user_message: str,
        enabled_server_ids: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 3,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        使用MCP工具进行完整对话

        Args:
            user_message: 用户消息
            enabled_server_ids: 启用的服务器ID列表，None表示使用所有服务器
            system_prompt: 系统提示词
            max_iterations: 最大迭代次数
            on_progress: 进度回调函数

        Returns:
            包含最终回答、工具调用历史、使用情况的字典
        """
        # 确定启用的服务器
        if enabled_server_ids is None:
            enabled_servers = list(self.managed_servers.values())
        else:
            enabled_servers = [
                self.managed_servers[server_id]
                for server_id in enabled_server_ids
                if server_id in self.managed_servers
            ]

        if not enabled_servers:
            logger.warning("⚠️ 没有可用的MCP服务器")
            return {
                "content": "抱歉，没有可用的MCP服务器来处理您的请求。",
                "tool_calls": [],
                "usage": {},
                "error": "no_servers",
            }

        # 构建消息列表
        messages = []

        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        else:
            messages.append(
                ChatMessage(
                    role="system",
                    content="你是一个智能助手，可以使用工具来帮助用户完成任务。",
                )
            )

        messages.append(ChatMessage(role="user", content=user_message))

        try:
            # 执行完整的MCP工作流程
            response = await complete_mcp_workflow(
                messages=messages,
                enabled_servers=enabled_servers,
                max_iterations=max_iterations,
                on_progress=on_progress,
            )

            return {
                "content": response.message.content,
                "tool_calls": response.message.tool_calls or [],
                "usage": response.usage,
                "metadata": response.message.metadata,
                "metrics": response.metrics,
            }

        except Exception as e:
            logger.error(f"聊天失败: {e}")
            return {
                "content": f"抱歉，聊天过程中出现错误：{str(e)}",
                "tool_calls": [],
                "usage": {},
                "error": str(e),
            }


# 创建自定义服务器的便捷函数
def create_server_config(
    server_id: str,
    name: str,
    command: str,
    args: List[str],
    env: Optional[Dict[str, str]] = None,
) -> MCPServer:
    """
    创建自定义MCP服务器配置

    Args:
        server_id: 服务器ID
        name: 服务器名称
        command: 启动命令
        args: 命令参数
        env: 环境变量

    Returns:
        MCP服务器配置
    """
    return MCPServer(id=server_id, name=name, command=command, args=args, env=env)
