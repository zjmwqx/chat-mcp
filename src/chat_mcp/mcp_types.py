"""
类型定义模块：定义MCP相关的数据结构
"""

import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class MCPServer:
    """MCP服务器配置"""

    id: str
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    disabled_tools: Optional[List[str]] = None


class MCPTool(BaseModel):
    """MCP工具定义"""

    id: str
    name: str
    description: str
    inputSchema: Dict[str, Any]
    server_id: str
    server_name: str


class MCPToolCall(BaseModel):
    """MCP工具调用"""

    id: str
    name: str
    arguments: Dict[str, Any]


class MCPToolResponse(BaseModel):
    """MCP工具响应"""

    id: str
    tool: MCPToolCall
    status: str  # 'invoking', 'success', 'error'
    content: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class ChatMessage(BaseModel):
    """聊天消息"""

    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[MCPToolCall]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求"""

    messages: List[ChatMessage]
    model: str = Field(
        default_factory=lambda: os.getenv(
            "MODEL_NAME", os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        )
    )
    enabled_mcps: Optional[List[MCPServer]] = None
    stream: bool = False
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    )


class ChatResponse(BaseModel):
    """聊天响应"""

    message: ChatMessage
    usage: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


class MCPCallToolResponse(BaseModel):
    """MCP工具调用响应"""

    content: List[Dict[str, Any]]
    isError: bool = False


class ToolParseResult(BaseModel):
    """工具解析结果"""

    id: str
    tool: MCPToolCall
