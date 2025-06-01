#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat-MCP Package Setup
用于在对话中调用MCP（Model Context Protocol）工具的Python客户端库

注意：本项目主要使用 pyproject.toml 进行配置，此 setup.py 仅用于兼容性支持。
建议使用 'uv build' 或 'python -m build' 命令进行打包。
"""

from setuptools import setup, find_packages
from pathlib import Path

# 获取项目根目录
here = Path(__file__).parent.absolute()

def read_readme():
    """读取README文件作为长描述"""
    readme_path = here / "README.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def get_version():
    """从__init__.py文件中获取版本号"""
    init_path = here / "src" / "chat_mcp" / "__init__.py"
    if init_path.exists():
        with open(init_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('=')[1].strip().strip('"').strip("'")
    return "0.1.1"

# 基础设置，主要配置在 pyproject.toml 中
setup(
    # 核心信息
    name="chat-mcp",
    version=get_version(),
    description="MCP客户端库，用于在对话中调用MCP工具",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    
    # 包结构 
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Python版本要求
    python_requires=">=3.11",
    
    # 包含数据文件
    include_package_data=True,
    
    # 避免压缩安装
    zip_safe=False,
    
    # 平台支持
    platforms=["any"],
) 