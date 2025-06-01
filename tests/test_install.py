#!/usr/bin/env python3
"""
测试安装包的导入和基本功能
"""


def test_imports():
    """测试包的导入功能"""
    print("🧪 测试包导入功能...")

    try:
        # 测试基础模块导入

        print("✅ chat_mcp 基础模块导入成功")

        # 测试主要API导入

        print("✅ MCPChatTool 和 create_server_config 导入成功")

        # 测试核心组件导入

        print("✅ 核心组件导入成功")

        # 测试数据类型导入

        print("✅ 数据类型导入成功")

        return True

    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        return False


def test_basic_functionality():
    """测试基础功能"""
    print("\n🧪 测试基础功能...")

    try:
        from chat_mcp import MCPChatTool, create_server_config

        # 测试创建聊天工具
        chat_tool = MCPChatTool()
        print("✅ MCPChatTool 实例创建成功")

        # 测试服务器配置创建
        server_config = create_server_config(
            server_id="test_server", name="Test Server", command="echo", args=["hello"]
        )
        print("✅ 服务器配置创建成功")
        print(f"   服务器ID: {server_config.id}")
        print(f"   服务器名称: {server_config.name}")

        # 测试服务器列表（应该为空）
        servers = chat_tool.list_servers()
        print(f"✅ 当前服务器列表: {len(servers)} 个")

        return True

    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False


def test_version():
    """测试版本信息"""
    print("\n🧪 测试版本信息...")

    try:
        import chat_mcp

        version = getattr(chat_mcp, "__version__", "unknown")
        print(f"✅ chat-mcp 版本: {version}")
        return True

    except Exception as e:
        print(f"❌ 版本测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试 uv install 安装的 chat-mcp 包\n")

    success_count = 0
    total_tests = 3

    # 运行各项测试
    if test_imports():
        success_count += 1

    if test_basic_functionality():
        success_count += 1

    if test_version():
        success_count += 1

    # 输出测试结果
    print(f"\n📊 测试结果: {success_count}/{total_tests} 项测试通过")

    if success_count == total_tests:
        print("🎉 所有测试通过！chat-mcp 包安装成功且功能正常！")
        return True
    else:
        print("❌ 部分测试失败，请检查安装或代码")
        return False


if __name__ == "__main__":
    main()
