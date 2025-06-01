# Chat-MCP

**一个用于在对话中调用MCP（Model Context Protocol）工具的Python客户端库**

Chat-MCP 提供了一个简洁而强大的接口，让您能够轻松地将MCP服务器集成到AI agent项目中。通过两个简单的api，并配置好.env文件，就可以在开发agent和chat助手时高效的调用mcp服务。作为agentic项目的底层脚手架，分享大家使用。

## 核心特性

- **简洁的API设计**: 二个主要接口覆盖所有使用场景，提高agent应用开发效率
- **优化提示词**: 提高tools调用的成功率，持续优化中
- **异步架构**: 完全基于asyncio的高性能处理
- **智能工具管理**: 自动工具收集、过滤和并行执行
- **多模型支持**: 通过LiteLLM支持多种LLM提供商，支持本地模型配置


## 关键技术栈

- **[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)**: Model Context Protocol的官方Python实现
- **[LiteLLM](https://docs.litellm.ai/)**: 统一的LLM API接口库，支持100+模型
- **[Pydantic](https://docs.pydantic.dev/)**: 数据验证和设置管理框架

## 项目结构

```
chat-mcp/
├── docs/                 # 详细的开发文档和规范
├── src/chat_mcp/         # 主要源代码包
│   ├── tests/            # 测试套件
│   ├── __init__.py       # 公共API导出
│   ├── easy_chat.py      # 简化API接口
│   ├── ai_provider.py    # LLM提供商集成
│   ├── mcp_service.py    # MCP服务器管理
│   ├── mcp_chat_handler.py # 聊天处理逻辑
│   ├── ipc_handler.py    # 进程间通信处理
│   └── mcp_types.py      # 数据类型定义
├── temp_arxiv_storage/   # ArXiv演示数据存储
├── pyproject.toml        # uv项目配置
├── uv.lock              # 依赖锁定文件
└── main.py              # 演示入口
```


## 核心API

### MCPChatTool - 主要接口

```python
from chat_mcp import MCPChatTool

# 创建聊天工具实例
chat_tool = MCPChatTool()

# 启动MCP服务器，这里使用arxiv-mcp-server作为演示样例，可以添加多个不同的mcp server，只需要多次调用
server = await chat_tool.start_mcp_server(
    server_id="arxiv",
    name="ArXiv Research",
    command="uv",
    args=["tool", "run", "arxiv-mcp-server"]
)

# 进行对话
result = await chat_tool.chat_with_mcp(
    user_message="搜索关于机器学习的最新论文",
    enabled_server_ids=["arxiv"] # 这里可以不设置enabled_server_ids,默认所有server都会被添加
)
```

## 安装

使用 [uv](https://github.com/astral-sh/uv) (推荐):

```bash
uv add chat-mcp
```

或使用 pip:

```bash
pip install chat-mcp
```

## 快速开始

1. **配置环境变量** (创建 `.env` 文件):

LLM配置：使用litellm规范，可以自行配置，支持大部分模型包括自定义大模型

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
```
如果是vllm本地模型可以如下配置

```env
MODEL_NAME="openai//{VLLM_MODEL_NAME(PATH)}"
OPENAI_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxx"
OPENAI_API_BASE="http://xxx.xxx.xxx.xxx:xxxx/v1"
```

其他模型都已自行尝试配置，具体参考litellm支持的模型

2. **基础使用**:

```python
import asyncio
from chat_mcp import MCPChatTool

async def main():
    # 创建聊天工具
    chat_tool = MCPChatTool()
    
    # 添加ArXiv服务器
    await chat_tool.start_mcp_server(
        server_id="arxiv",
        name="ArXiv Research", 
        command="uv",
        args=["tool", "run", "arxiv-mcp-server"]
    )
    
    # 开始对话
    result = await chat_tool.chat_with_mcp(
        user_message="帮我搜索最新的深度学习论文",
        system_prompt="你是一个研究助手，专门帮助用户搜索和分析学术论文。"
    )
    
    print(f"AI回答: {result['content']}")
    print(f"工具调用: {len(result['tool_calls'])} 次")

# 运行
asyncio.run(main())
```

## 许可证

MIT License - 详见 LICENSE 文件

---

*Chat-MCP: 让AI对话更智能，让工具调用更简单*
