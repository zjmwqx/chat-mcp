#!/usr/bin/env python3
"""
外部项目测试：模拟真实项目中使用 chat-mcp 包

这个测试模拟了一个独立项目如何使用我们发布的 chat-mcp 包
"""


def test_external_usage():
    """测试外部使用场景"""
    print("🧪 测试外部项目使用 chat-mcp 包...")

    try:
        # 模拟外部项目的典型使用方式
        from chat_mcp import MCPChatTool, create_server_config

        print("✅ 成功从已安装的包导入 MCPChatTool")

        # 创建聊天工具实例
        chat_tool = MCPChatTool()
        print("✅ 成功创建 MCPChatTool 实例")

        # 创建服务器配置
        server_config = create_server_config(
            server_id="external_test_server",
            name="External Test Server",
            command="echo",
            args=["test from external project"],
        )
        print("✅ 成功创建服务器配置")
        print(f"   配置详情: {server_config.name} (ID: {server_config.id})")

        # 验证可以调用方法
        servers = chat_tool.list_servers()
        print(f"✅ 成功调用 list_servers() 方法，当前服务器数量: {len(servers)}")

        # 测试类型提示和属性访问
        print(f"✅ 服务器配置类型正确: {type(server_config).__name__}")
        print(f"✅ 访问属性成功: command={server_config.command}")

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("这可能意味着包没有正确安装或路径配置有问题")
        return False

    except AttributeError as e:
        print(f"❌ 属性错误: {e}")
        print("这可能意味着API发生了变化或版本不兼容")
        return False

    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


def test_package_info():
    """测试包信息"""
    print("\n🧪 测试包信息...")

    try:
        import chat_mcp

        # 检查版本
        version = getattr(chat_mcp, "__version__", None)
        if version:
            print(f"✅ 包版本: {version}")
        else:
            print("⚠️  未找到版本信息")

        # 检查可用的API
        available_apis = [attr for attr in dir(chat_mcp) if not attr.startswith("_")]
        print(f"✅ 可用的公共API: {len(available_apis)} 个")
        print("   主要API:")
        for api in ["MCPChatTool", "create_server_config", "MCPService", "AIProvider"][
            :4
        ]:
            if api in available_apis:
                print(f"   ✓ {api}")
            else:
                print(f"   ✗ {api} (缺失)")

        return True

    except Exception as e:
        print(f"❌ 包信息测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 外部项目测试 - 验证 chat-mcp 包的可用性\n")
    print("=" * 50)

    success_count = 0
    total_tests = 2

    # 执行测试
    if test_external_usage():
        success_count += 1

    if test_package_info():
        success_count += 1

    # 总结
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_tests} 项测试通过")

    if success_count == total_tests:
        print("🎉 外部测试全部通过！")
        print("✅ chat-mcp 包可以被外部项目正常使用")
    else:
        print("❌ 部分外部测试失败")
        print("❗ 可能需要检查包的安装或API设计")

    return success_count == total_tests


if __name__ == "__main__":
    main()
