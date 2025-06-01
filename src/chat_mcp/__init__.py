"""
Chat MCP: MCP客户端库，用于在对话中调用MCP工具

主要API：
- MCPChatTool: 主要的聊天工具类
- start_arxiv_server: 启动ArXiv服务器
- chat_with_arxiv: 使用ArXiv进行对话
"""

from .mcp_service import MCPService, init_mcp_server, list_mcp_tools
from .mcp_chat_handler import ChatMCPClient, MCPToolCollector
from .ai_provider import (
    AIProvider,
    build_system_prompt,
    parse_tool_use,
    parse_and_call_tools,
    call_mcp_tool,
    upsert_mcp_tool_response,
    register_server_config,
    get_server_config,
    default_convert_to_message,
    callMCPTool,
    getMcpServerByTool,
    execute_mcp_tool_calls,
    complete_mcp_workflow,
)
from .ipc_handler import (
    MCPIPCHandler,
    get_ipc_handler,
    handle_ipc_request,
    window_api_mcp,
    IpcChannel,
)
from .easy_chat import MCPChatTool, create_server_config
from .mcp_types import (
    MCPServer,
    MCPTool,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    MCPToolCall,
    MCPToolResponse,
    MCPCallToolResponse,
    ToolParseResult,
)

__version__ = "0.1.1"
__all__ = [
    # 主要对外API
    "MCPChatTool",
    "create_server_config",
    # 核心组件
    "MCPService",
    "init_mcp_server",
    "list_mcp_tools",
    "ChatMCPClient",
    "MCPToolCollector",
    "AIProvider",
    "build_system_prompt",
    "parse_tool_use",
    "parse_and_call_tools",
    "call_mcp_tool",
    "upsert_mcp_tool_response",
    "register_server_config",
    "get_server_config",
    "default_convert_to_message",
    "callMCPTool",
    "getMcpServerByTool",
    "execute_mcp_tool_calls",
    "complete_mcp_workflow",
    # IPC处理模块
    "MCPIPCHandler",
    "get_ipc_handler",
    "handle_ipc_request",
    "window_api_mcp",
    "IpcChannel",
    # 数据类型
    "MCPServer",
    "MCPTool",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage",
    "MCPToolCall",
    "MCPToolResponse",
    "MCPCallToolResponse",
    "ToolParseResult",
]
