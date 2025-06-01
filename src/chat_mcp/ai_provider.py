"""
AI Provider模块：实现LLM调用和MCP工具集成
"""

import asyncio
import json
import re
import logging
import os
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv

import litellm

from .mcp_types import (
    MCPTool,
    ChatMessage,
    ChatResponse,
    MCPToolCall,
    MCPCallToolResponse,
    ToolParseResult,
    MCPServer,
    MCPToolResponse,
)
from .mcp_service import get_mcp_service

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 系统提示词模板
SYSTEM_PROMPT_TEMPLATE = """{{ USER_SYSTEM_PROMPT }}

{{ TOOL_USE_EXAMPLES }}

{{ AVAILABLE_TOOLS }}"""

# 工具使用示例
TOOL_USE_EXAMPLES = """
You have access to tools that you can use to help answer questions. 
When using a tool, format your request using XML tags:

<tool_use>
<tool_name>tool_name_here</tool_name>
<parameters>
{
  "required_parameter": "value",
  "optional_parameter": "value_if_needed"
}
</parameters>
</tool_use>

IMPORTANT RULES:
1. Only call tools when you need additional information
2. After receiving tool results (success or error), provide your final answer directly
3. Do NOT retry failed tool calls or call the same tool multiple times
4. For optional parameters: ONLY include them if you have a specific value - 
   do NOT pass empty strings "", null, or placeholder values
5. When tool parameters are not mentioned or not needed, 
   simply omit them from the parameters object
"""

# 全局服务器配置存储
_server_configs: Dict[str, MCPServer] = {}


def register_server_config(server: MCPServer) -> None:
    """注册服务器配置"""
    _server_configs[server.id] = server


def get_server_config(server_id: str) -> Optional[MCPServer]:
    """获取服务器配置"""
    return _server_configs.get(server_id)


def build_available_tools_prompt(tools: List[MCPTool]) -> str:
    """
    构建可用工具的提示词

    Args:
        tools: MCP工具列表

    Returns:
        格式化的工具描述字符串
    """
    if not tools:
        return ""

    tools_desc = "Available tools:\n\n"
    for tool in tools:
        tools_desc += f"- **{tool.name}**: {tool.description}\n"

        # 添加参数描述
        if tool.inputSchema and "properties" in tool.inputSchema:
            properties = tool.inputSchema["properties"]
            required = tool.inputSchema.get("required", [])

            tools_desc += "  Parameters:\n"
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                req_marker = " (required)" if is_required else ""

                tools_desc += (
                    f"    - {param_name} ({param_type}){req_marker}: {param_desc}\n"
                )

        tools_desc += "\n"

    return tools_desc


def build_system_prompt(user_system_prompt: str, tools: List[MCPTool]) -> str:
    """
    构建包含工具信息的系统提示词

    Args:
        user_system_prompt: 用户定义的系统提示词
        tools: MCP工具列表

    Returns:
        完整的系统提示词


    """
    if tools and len(tools) > 0:
        return (
            SYSTEM_PROMPT_TEMPLATE.replace(
                "{{ USER_SYSTEM_PROMPT }}", user_system_prompt
            )
            .replace("{{ TOOL_USE_EXAMPLES }}", TOOL_USE_EXAMPLES)
            .replace("{{ AVAILABLE_TOOLS }}", build_available_tools_prompt(tools))
        )

    return user_system_prompt


def parse_tool_use(
    content: str, mcp_tools: Optional[List[MCPTool]] = None
) -> List[ToolParseResult]:
    """
    解析LLM响应中的工具调用


    Args:
        content: LLM响应内容
        mcp_tools: 可用的MCP工具列表

    Returns:
        解析出的工具调用列表
    """
    tools = []

    # 使用正则表达式匹配工具调用XML
    pattern = (
        r"<tool_use>\s*<tool_name>([^<]+)</tool_name>\s*"
        r"<parameters>([^<]*)</parameters>\s*</tool_use>"
    )
    matches = re.findall(pattern, content, re.DOTALL)

    for i, match in enumerate(matches):
        tool_name = match[0].strip()
        parameters_str = match[1].strip()

        try:
            # 解析参数
            parameters = json.loads(parameters_str.strip())

            # 查找对应的MCP工具（可选验证）
            if mcp_tools:
                for tool in mcp_tools:
                    if tool.name == tool_name:
                        break

            # 创建工具调用
            tool_call = MCPToolCall(
                id=f"call_{i}", name=tool_name, arguments=parameters
            )

            # 创建解析结果
            parse_result = ToolParseResult(id=f"parse_{i}", tool=tool_call)

            tools.append(parse_result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool parameters for {tool_name}: {e}")
            continue

    return tools


async def call_mcp_tool(
    tool_call: MCPToolCall, mcp_tools: Optional[List[MCPTool]] = None
) -> MCPCallToolResponse:
    """
    调用MCP工具


    Args:
        tool_call: 工具调用信息
        mcp_tools: 可用的MCP工具列表

    Returns:
        工具调用响应
    """
    try:
        # 查找对应的MCP工具
        target_tool = None
        if mcp_tools:
            for tool in mcp_tools:
                if tool.name == tool_call.name:
                    target_tool = tool
                    break

        if not target_tool:
            logger.error(f"Tool not found: {tool_call.name}")
            return MCPCallToolResponse(
                content=[
                    {"type": "text", "text": f"错误：找不到工具 {tool_call.name}"}
                ],
                isError=True,
            )

        # 获取服务器配置
        server_config = get_server_config(target_tool.server_id)
        if not server_config:
            logger.error(f"Server config not found: {target_tool.server_id}")
            return MCPCallToolResponse(
                content=[
                    {
                        "type": "text",
                        "text": f"错误：找不到服务器配置 {target_tool.server_id}",
                    }
                ],
                isError=True,
            )

        # 获取MCP服务
        mcp_service = get_mcp_service()

        # 调用工具
        result = await mcp_service.call_tool(
            server_config, tool_call.name, tool_call.arguments
        )

        # 处理调用结果
        if hasattr(result, "content"):
            # 转换MCP SDK返回的内容格式
            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    # 处理TextContent对象
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                    # 处理ImageContent对象
                    content.append(
                        {
                            "type": "image",
                            "data": item.data,
                            "mimeType": getattr(item, "mimeType", "image/png"),
                        }
                    )
                elif isinstance(item, dict):
                    # 如果已经是字典格式
                    content.append(item)
                else:
                    # 其他情况，转为文本
                    content.append({"type": "text", "text": str(item)})
        else:
            content = [{"type": "text", "text": str(result)}]

        return MCPCallToolResponse(content=content, isError=False)

    except Exception as e:
        logger.error(f"Failed to call MCP tool {tool_call.name}: {e}")
        return MCPCallToolResponse(
            content=[{"type": "text", "text": f"工具调用失败：{str(e)}"}], isError=True
        )


def upsert_mcp_tool_response(
    tool_responses: List[MCPToolResponse],
    tool_response: MCPToolResponse,
    on_chunk: Optional[Callable] = None,
) -> None:
    """
    更新或插入MCP工具响应


    Args:
        tool_responses: 工具响应列表
        tool_response: 新的工具响应
        on_chunk: 流式响应回调函数
    """
    # 查找是否已存在相同ID的响应
    for i, existing_response in enumerate(tool_responses):
        if existing_response.id == tool_response.id:
            tool_responses[i] = tool_response
            if on_chunk:
                on_chunk(
                    {
                        "text": (
                            f"[工具更新] {tool_response.tool.name}: "
                            f"{tool_response.status}\n"
                        ),
                        "tool_response": tool_response.model_dump(),
                    }
                )
            return

    # 如果不存在，则添加新的响应
    tool_responses.append(tool_response)
    if on_chunk:
        on_chunk(
            {
                "text": f"[工具调用] {tool_response.tool.name}: {tool_response.status}\n",
                "tool_response": tool_response.model_dump(),
            }
        )


def default_convert_to_message(
    tool_call_id: str, response: MCPCallToolResponse, is_vision_model: bool = False
) -> ChatMessage:
    """
    默认的工具调用结果转换为消息的函数

    Args:
        tool_call_id: 工具调用ID
        response: 工具调用响应
        is_vision_model: 是否为视觉模型

    Returns:
        转换后的聊天消息
    """
    # 提取文本内容
    text_content = ""
    for content_item in response.content:
        if content_item.get("type") == "text":
            text_content += content_item.get("text", "")
        elif content_item.get("type") == "image":
            text_content += f"[图像: {content_item.get('mimeType', 'image')}]"

    return ChatMessage(
        role="tool",
        content=text_content,
        tool_call_id=tool_call_id,
        metadata={"tool_response": response.model_dump(), "is_error": response.isError},
    )


async def parse_and_call_tools(
    content: str,
    tool_responses: List[MCPToolResponse],
    on_chunk: Optional[Callable],
    idx: int,
    convert_to_message: Optional[Callable] = None,
    mcp_tools: Optional[List[MCPTool]] = None,
    is_vision_model: bool = False,
) -> List[ChatMessage]:
    """
    解析LLM响应中的工具调用并执行

    Args:
        content: LLM响应内容
        tool_responses: 工具响应列表
        on_chunk: 流式响应回调函数
        idx: 消息索引
        convert_to_message: 转换为消息的函数（可选，使用默认函数）
        mcp_tools: 可用的MCP工具列表
        is_vision_model: 是否为视觉模型

    Returns:
        工具调用结果消息列表
    """
    # 使用默认转换函数如果未提供
    if convert_to_message is None:
        convert_to_message = default_convert_to_message

    tool_results: List[ChatMessage] = []

    # 解析工具使用
    tools = parse_tool_use(content, mcp_tools or [])
    if not tools or len(tools) == 0:
        return tool_results

    # 为每个工具创建初始响应
    for i, tool_parse_result in enumerate(tools):
        tool_response = MCPToolResponse(
            id=f"{tool_parse_result.id}-{idx}-{i}",
            tool=tool_parse_result.tool,
            status="invoking",
        )
        upsert_mcp_tool_response(tool_responses, tool_response, on_chunk)

    # 并行执行所有工具调用
    images: List[str] = []

    async def execute_single_tool(
        tool_parse_result: ToolParseResult, i: int
    ) -> ChatMessage:
        """执行单个工具调用"""
        try:
            tool_call_response = await call_mcp_tool(tool_parse_result.tool, mcp_tools)

            # 更新工具响应状态
            tool_response = MCPToolResponse(
                id=f"{tool_parse_result.id}-{idx}-{i}",
                tool=tool_parse_result.tool,
                status="done" if not tool_call_response.isError else "error",
                content=tool_call_response.content,
                error=None if not tool_call_response.isError else "工具调用失败",
            )
            upsert_mcp_tool_response(tool_responses, tool_response, on_chunk)

            # 处理图像内容
            for content_item in tool_call_response.content:
                if content_item.get("type") == "image" and content_item.get("data"):
                    mime_type = content_item.get("mimeType", "image/png")
                    images.append(f"data:{mime_type};base64,{content_item['data']}")

            # 发送图像更新
            if images and on_chunk:
                on_chunk(
                    {
                        "text": "\n",
                        "generateImage": {"type": "base64", "images": images},
                    }
                )

            # 转换为聊天消息
            return convert_to_message(
                tool_parse_result.tool.id, tool_call_response, is_vision_model
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            # 创建错误响应
            error_response = MCPCallToolResponse(
                content=[{"type": "text", "text": f"工具执行失败：{str(e)}"}],
                isError=True,
            )
            return convert_to_message(
                tool_parse_result.tool.id, error_response, is_vision_model
            )

    # 并行执行所有工具
    tool_promises = [execute_single_tool(tool, i) for i, tool in enumerate(tools)]

    tool_results.extend(await asyncio.gather(*tool_promises))
    return tool_results


class AIProvider:
    """
    AI Provider：负责LLM调用和响应处理
    """

    def __init__(self):
        # 设置LiteLLM的基础URL（如果有的话）
        if os.getenv("OPENAI_API_BASE"):
            os.environ["OPENAI_API_BASE"] = os.getenv("OPENAI_API_BASE")
            logger.info(f"✅ 使用自定义API基础URL: {os.getenv('OPENAI_API_BASE')}")

        # 获取默认模型配置
        self.default_model = os.getenv(
            "MODEL_NAME", os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        )
        self.default_temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))

        logger.info(f"✅ AI Provider初始化完成，默认模型: {self.default_model}")

    async def completions(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        mcp_tools: Optional[List[MCPTool]] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        on_chunk: Optional[Callable] = None,
    ) -> ChatResponse:
        """
        执行LLM completions调用，集成MCP工具

        Args:
            messages: 聊天消息列表
            model: 模型名称（可选，使用环境变量默认值）
            mcp_tools: MCP工具列表
            temperature: 温度参数（可选，使用环境变量默认值）
            stream: 是否流式响应
            on_chunk: 流式响应回调函数

        Returns:
            聊天响应
        """
        # 使用提供的参数或环境变量默认值
        actual_model = model or self.default_model
        actual_temperature = (
            temperature if temperature is not None else self.default_temperature
        )

        logger.info(f"[AI] Starting completions with model: {actual_model}")
        logger.info(f"[AI] MCP tools available: {len(mcp_tools) if mcp_tools else 0}")

        # 准备消息列表
        processed_messages = []

        for msg in messages:
            # 处理系统消息，添加MCP工具信息
            if msg.role == "system":
                if mcp_tools and len(mcp_tools) > 0:
                    enhanced_content = build_system_prompt(msg.content, mcp_tools)
                    processed_messages.append(
                        {"role": "system", "content": enhanced_content}
                    )
                    logger.info(
                        f"[AI] Enhanced system message with {len(mcp_tools)} MCP tools"
                    )
                else:
                    processed_messages.append(
                        {"role": msg.role, "content": msg.content}
                    )
            else:
                processed_messages.append({"role": msg.role, "content": msg.content})

        try:
            # 调用LiteLLM
            if stream:
                return await self._stream_completion(
                    processed_messages,
                    actual_model,
                    actual_temperature,
                    mcp_tools,
                    on_chunk,
                )
            else:
                return await self._sync_completion(
                    processed_messages, actual_model, actual_temperature, mcp_tools
                )

        except Exception as e:
            logger.error(f"[AI] LLM completion failed: {e}")
            error_message = ChatMessage(
                role="assistant",
                content=f"抱歉，AI调用失败：{str(e)}",
                metadata={"error": str(e)},
            )
            return ChatResponse(
                message=error_message,
                usage={"error": True},
                metrics={"step": 3, "status": "ai_completion_error"},
            )

    async def _sync_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        mcp_tools: Optional[List[MCPTool]],
    ) -> ChatResponse:
        """同步完成LLM调用"""
        response = await litellm.acompletion(
            model=model, messages=messages, temperature=temperature
        )

        # 提取响应内容
        content = response.choices[0].message.content
        usage = response.usage.dict() if response.usage else {}

        # 解析工具调用
        tool_calls = parse_tool_use(content, mcp_tools)

        response_message = ChatMessage(
            role="assistant",
            content=content,
            metadata={
                "mcp_tools": (
                    [tool.tool.dict() for tool in tool_calls] if mcp_tools else []
                ),
                "tool_calls_detected": len(tool_calls),
                "parsed_tool_calls": tool_calls,
            },
            tool_calls=[tool.tool for tool in tool_calls] if tool_calls else None,
        )

        return ChatResponse(
            message=response_message,
            usage=usage,
            metrics={
                "step": 3,
                "status": "ai_completion_success",
                "tool_calls_detected": len(tool_calls),
            },
        )

    async def _stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        mcp_tools: Optional[List[MCPTool]],
        on_chunk: Optional[Callable],
    ) -> ChatResponse:
        """流式完成LLM调用"""
        # 流式实现的占位符
        # 在实际应用中，这里会实现真正的流式处理
        logger.info(
            "[AI] Stream completion not fully implemented, falling back to sync"
        )
        return await self._sync_completion(messages, model, temperature, mcp_tools)


def getMcpServerByTool(tool: MCPTool) -> Optional[MCPServer]:
    """
    根据工具获取对应的MCP服务器配置


    Args:
        tool: MCP工具对象

    Returns:
        对应的服务器配置，如果未找到则返回None
    """
    return get_server_config(tool.server_id)


async def callMCPTool(
    tool_name: str, arguments: Dict[str, Any], mcp_tools: List[MCPTool]
) -> MCPCallToolResponse:
    """
    使用工具名称和参数调用MCP工具
    这是Task7的核心功能：接收LLM生成的工具调用参数，实际执行MCP工具

    Args:
        tool_name: 工具名称
        arguments: 工具调用参数（从LLM响应中解析出来的）
        mcp_tools: 可用的MCP工具列表

    Returns:
        工具调用响应
    """
    logger.info(f"[MCP] Calling Tool: {tool_name} with args: {arguments}")

    try:
        # 清理参数：去除空字符串、None值和空列表
        cleaned_arguments = {}
        for key, value in arguments.items():
            # 跳过空值参数
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            # 保留有意义的参数
            cleaned_arguments[key] = value

        logger.info(f"[MCP] Cleaned args: {cleaned_arguments}")

        # 查找对应的MCP工具定义
        target_tool = None
        for tool in mcp_tools:
            if tool.name == tool_name:
                target_tool = tool
                break

        if not target_tool:
            raise Exception(f"Tool not found: {tool_name}")

        # 获取服务器配置
        server = getMcpServerByTool(target_tool)
        if not server:
            raise Exception(f"Server not found for tool: {tool_name}")

        # 获取MCP服务
        mcp_service = get_mcp_service()

        # 使用清理后的参数调用工具
        result = await mcp_service.call_tool(server, tool_name, cleaned_arguments)

        # 处理调用结果
        if hasattr(result, "content"):
            # 转换MCP SDK返回的内容格式
            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    # 处理TextContent对象
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                    # 处理ImageContent对象
                    content.append(
                        {
                            "type": "image",
                            "data": item.data,
                            "mimeType": getattr(item, "mimeType", "image/png"),
                        }
                    )
                elif isinstance(item, dict):
                    # 如果已经是字典格式
                    content.append(item)
                else:
                    # 其他情况，转为文本
                    content.append({"type": "text", "text": str(item)})
        else:
            content = [{"type": "text", "text": str(result)}]

        logger.info(f"[MCP] Tool called successfully: {tool_name}")
        return MCPCallToolResponse(content=content, isError=False)

    except Exception as e:
        logger.error(f"[MCP] Error calling Tool: {tool_name}: {e}")
        return MCPCallToolResponse(
            content=[
                {"type": "text", "text": (f"Error calling tool {tool_name}: {str(e)}")}
            ],
            isError=True,
        )


async def execute_mcp_tool_calls(
    tool_calls: List[ToolParseResult],
    mcp_tools: List[MCPTool],
    on_progress: Optional[Callable] = None,
) -> List[MCPCallToolResponse]:
    """
    批量执行MCP工具调用
    这是完整的Task7流程：接收解析的工具调用列表，执行并返回结果

    Args:
        tool_calls: 从LLM响应中解析出的工具调用列表
        mcp_tools: 可用的MCP工具列表
        on_progress: 进度回调函数

    Returns:
        工具调用响应列表
    """
    results = []

    for i, tool_call in enumerate(tool_calls):
        if on_progress:
            on_progress(f"执行工具 {i+1}/{len(tool_calls)}: {tool_call.tool.name}")

        # 调用单个工具
        response = await callMCPTool(
            tool_call.tool.name, tool_call.tool.arguments, mcp_tools
        )
        results.append(response)

        if on_progress:
            status = "成功" if not response.isError else "失败"
            on_progress(f"工具 {tool_call.tool.name} 执行{status}")

    return results


async def complete_mcp_workflow(
    messages: List[ChatMessage],
    enabled_servers: List[MCPServer],
    model: Optional[str] = None,
    max_iterations: int = 3,
    on_progress: Optional[Callable] = None,
) -> ChatResponse:
    """
    完整的MCP工作流程：
    1. 从启用的服务器获取工具列表
    2. LLM生成工具调用
    3. 执行工具
    4. 返回结果给LLM
    5. 生成最终答案

    Args:
        messages: 聊天消息列表
        enabled_servers: 启用的MCP服务器列表
        model: LLM模型名称
        max_iterations: 最大迭代次数（防止无限循环）
        on_progress: 进度回调函数

    Returns:
        最终的聊天响应
    """
    if on_progress:
        on_progress("🚀 开始MCP完整工作流程")

    # 1. 从启用的服务器获取工具列表
    if on_progress:
        on_progress(f"📡 从 {len(enabled_servers)} 个服务器获取工具列表")

    from .mcp_chat_handler import MCPToolCollector

    tool_collector = MCPToolCollector()
    mcp_tools = await tool_collector.collect_mcp_tools(enabled_servers)

    if on_progress:
        on_progress(f"✅ 获取到 {len(mcp_tools)} 个可用工具")

    # 2. 执行完整的对话流程
    provider = AIProvider()
    current_messages = messages.copy()

    # 打印初始消息
    if on_progress:
        on_progress("=" * 50)
        on_progress("📋 初始对话消息:")
        for i, msg in enumerate(current_messages):
            on_progress(f"  [{i+1}] Role: {msg.role}")
            on_progress(
                f"      Content: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}"
            )
        on_progress("=" * 50)

    for iteration in range(max_iterations):
        if on_progress:
            on_progress(f"🔄 开始第 {iteration + 1} 轮对话")
            on_progress(f"📨 当前消息历史长度: {len(current_messages)}")

        # 调用LLM生成响应
        llm_response = await provider.completions(
            current_messages, model=model, mcp_tools=mcp_tools
        )

        # 打印LLM响应
        if on_progress:
            on_progress("-" * 30)
            on_progress(f"🤖 LLM第{iteration + 1}轮响应:")
            on_progress(f"   📝 Content: {llm_response.message.content}")
            on_progress(f"   📊 Usage: {llm_response.usage}")
            on_progress("-" * 30)

        # 解析工具调用
        tool_calls = parse_tool_use(llm_response.message.content, mcp_tools)

        if not tool_calls:
            # 没有工具调用，返回最终结果
            if on_progress:
                on_progress("✅ LLM未请求工具调用，返回最终答案")
                on_progress("=" * 50)
            return llm_response

        if on_progress:
            on_progress(f"🔧 解析到 {len(tool_calls)} 个工具调用")
            for i, tool_call in enumerate(tool_calls):
                on_progress(f"   [{i+1}] 工具: {tool_call.tool.name}")
                on_progress(f"       参数: {tool_call.tool.arguments}")

        # 执行工具调用
        tool_results = await execute_mcp_tool_calls(tool_calls, mcp_tools, on_progress)

        # 将LLM响应添加到消息历史
        current_messages.append(llm_response.message)

        # 将工具结果添加到消息历史
        for i, (tool_call, result) in enumerate(zip(tool_calls, tool_results)):
            # 提取工具结果的文本内容
            result_text = ""
            if result.content:
                for content_item in result.content:
                    if content_item.get("type") == "text":
                        result_text += content_item.get("text", "")
                    else:
                        result_text += str(content_item)

            # 创建更清晰的工具结果消息，让LLM明确知道工具已执行完成
            tool_message = ChatMessage(
                role="user",  # 改为user角色，让LLM更容易理解这是输入信息
                content=(
                    f"工具调用结果：\n工具名称：{tool_call.tool.name}\n"
                    f"执行状态：{'成功' if not result.isError else '失败'}\n"
                    f"结果内容：\n{result_text}"
                ),
                metadata={
                    "tool_name": tool_call.tool.name,
                    "tool_result": result.model_dump(),
                    "is_error": result.isError,
                    "message_type": "tool_result",
                },
            )
            current_messages.append(tool_message)

            # 打印工具结果消息
            if on_progress:
                on_progress("📤 添加到消息历史 - 工具结果:")
                on_progress(f"   🔧 工具: {tool_call.tool.name}")
                on_progress(
                    f"   📄 结果: {result_text[:150]}"
                    f"{'...' if len(result_text) > 150 else ''}"
                )

        if on_progress:
            on_progress(f"🔄 第 {iteration + 1} 轮工具调用完成，继续对话")
            on_progress(f"📨 更新后消息历史长度: {len(current_messages)}")

    # 达到最大迭代次数，返回最后一次响应
    if on_progress:
        on_progress(f"⚠️ 达到最大迭代次数 {max_iterations}，返回当前结果")
        on_progress("=" * 50)

    return llm_response
