"""
MCP聊天处理器：内部的聊天处理逻辑
这不是对外API，对外API请使用easy_chat.py
"""

from typing import List, Optional
from .mcp_types import MCPServer, MCPTool, ChatRequest, ChatResponse, ChatMessage
from .mcp_service import MCPService
from .ai_provider import AIProvider
import logging

logger = logging.getLogger(__name__)


class MCPToolCollector:
    """
    MCP工具收集器：负责从启用的MCP服务器收集工具列表

    """

    def __init__(self):
        self.mcp_service = MCPService()

    async def collect_mcp_tools(
        self, enabled_mcps: Optional[List[MCPServer]]
    ) -> List[MCPTool]:
        """
        从启用的MCP服务器收集工具列表

        Args:
            enabled_mcps: 启用的MCP服务器列表

        Returns:
            收集到的MCP工具列表


        """
        mcp_tools: List[MCPTool] = []

        if not enabled_mcps or len(enabled_mcps) == 0:
            logger.info("[MCP] No enabled MCP servers found")
            return mcp_tools

        logger.info(
            f"[MCP] Collecting tools from {len(enabled_mcps)} enabled MCP servers"
        )

        # 遍历每个启用的MCP服务器
        for mcp_server in enabled_mcps:
            try:
                logger.info(f"[MCP] Getting tools from server: {mcp_server.name}")

                # 从MCP服务器获取工具列表
                tools = await self.mcp_service.list_tools(mcp_server)

                # 过滤被禁用的工具
                available_tools = self._filter_disabled_tools(
                    tools, mcp_server.disabled_tools
                )

                logger.info(
                    f"[MCP] Server {mcp_server.name}: {len(tools)} total tools, "
                    f"{len(available_tools)} available"
                )

                # 添加到工具列表
                mcp_tools.extend(available_tools)

            except Exception as e:
                logger.error(
                    f"[MCP] Failed to get tools from server {mcp_server.name}: {e}"
                )
                continue

        logger.info(
            f"[MCP] Collected {len(mcp_tools)} total tools from enabled servers"
        )
        return mcp_tools

    def _filter_disabled_tools(
        self, tools: List[MCPTool], disabled_tools: Optional[List[str]]
    ) -> List[MCPTool]:
        """
        过滤被禁用的工具

        Args:
            tools: 工具列表
            disabled_tools: 被禁用的工具名称列表

        Returns:
            过滤后的工具列表
        """
        if not disabled_tools:
            return tools

        # 过滤掉被禁用的工具
        available_tools = [tool for tool in tools if tool.name not in disabled_tools]

        filtered_count = len(tools) - len(available_tools)
        if filtered_count > 0:
            logger.info(
                f"[MCP] Filtered out {filtered_count} disabled tools: {disabled_tools}"
            )

        return available_tools


class ChatMCPClient:
    """
    MCP聊天客户端：管理聊天流程和MCP工具集成
    """

    def __init__(self):
        self.tool_collector = MCPToolCollector()
        self.ai_provider = AIProvider()

    async def collect_tools_from_request(self, request: ChatRequest) -> List[MCPTool]:
        """
        从聊天请求中收集MCP工具

        Args:
            request: 聊天请求

        Returns:
            收集到的MCP工具列表
        """
        return await self.tool_collector.collect_mcp_tools(request.enabled_mcps)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        执行聊天请求（Step3阶段：将MCP工具传递给AI Provider）

        Args:
            request: 聊天请求

        Returns:
            聊天响应


        """
        logger.info(f"[Chat] Starting chat with model: {request.model}")

        # Step1: 收集MCP工具
        mcp_tools = await self.collect_tools_from_request(request)
        logger.info(f"[Chat] Collected {len(mcp_tools)} MCP tools")

        # 确保有系统消息，如果没有则添加默认的
        messages = request.messages.copy()
        has_system_message = any(msg.role == "system" for msg in messages)

        if not has_system_message:
            # 添加默认系统消息
            system_message = ChatMessage(
                role="system", content="You are a helpful assistant."
            )
            messages.insert(0, system_message)
            logger.info("[Chat] Added default system message")

        # Step2: 将MCP工具传递给AI Provider
        logger.info(f"[Chat] Calling AI provider with {len(mcp_tools)} MCP tools")

        try:
            response = await self.ai_provider.completions(
                messages=messages,
                model=request.model,
                mcp_tools=mcp_tools,
                temperature=request.temperature,
                stream=request.stream,
            )

            # 在响应元数据中添加MCP工具信息
            if response.message.metadata is None:
                response.message.metadata = {}

            response.message.metadata.update(
                {
                    "enabled_servers": (
                        len(request.enabled_mcps) if request.enabled_mcps else 0
                    ),
                    "collected_tools_count": len(mcp_tools),
                    "step": 3,
                    "stage": "ai_provider_integration_complete",
                }
            )

            logger.info("[Chat] AI response generated successfully")
            logger.info(
                "[Chat] Tool calls detected: "
                f"{len(response.message.tool_calls) if response.message.tool_calls else 0}"
            )

            return response

        except Exception as e:
            logger.error(f"[Chat] Chat execution failed: {e}")

            # 返回错误响应
            error_message = ChatMessage(
                role="assistant",
                content=f"抱歉，聊天执行失败：{str(e)}",
                metadata={
                    "error": str(e),
                    "collected_tools_count": len(mcp_tools),
                    "enabled_servers": (
                        len(request.enabled_mcps) if request.enabled_mcps else 0
                    ),
                    "step": 3,
                    "stage": "ai_provider_integration_error",
                },
            )

            return ChatResponse(
                message=error_message,
                usage={"error": True},
                metrics={"step": 3, "status": "chat_execution_error"},
            )
