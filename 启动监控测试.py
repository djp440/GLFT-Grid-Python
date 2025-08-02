#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLFT网格交易实时监控功能测试启动脚本

此脚本用于快速启动和测试新增的实时监控功能，包括：
1. 实时交易数据记录
2. 账户权益监控
3. 可视化图表显示

使用方法：
    python 启动监控测试.py

注意：
- 此脚本会生成模拟数据进行测试
- 不会进行真实交易
- 按Ctrl+C可以退出测试
"""

import sys
import os
import asyncio
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'matplotlib',
        'numpy',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装：")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def print_banner():
    """打印启动横幅"""
    print("\n" + "=" * 60)
    print("🚀 GLFT网格交易实时监控功能测试")
    print("=" * 60)
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📊 功能特性:")
    print("   • 实时交易数据记录")
    print("   • 账户权益变化监控")
    print("   • 双组折线图实时显示")
    print("   • 累计成交量和手续费统计")
    print("\n💡 操作提示:")
    print("   • 图表窗口支持缩放、平移操作")
    print("   • 按 Ctrl+C 可以退出测试")
    print("   • 测试数据为模拟数据，不涉及真实交易")
    print("=" * 60 + "\n")

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        return
    
    print("✅ 依赖检查通过")
    print("🔄 正在启动监控系统...")
    
    try:
        # 导入测试模块
        from tests.test_监控功能 import test_monitoring_system
        
        print("📈 图表窗口即将弹出，请稍候...")
        print("⏳ 开始生成模拟交易数据...\n")
        
        # 运行测试
        asyncio.run(test_monitoring_system())
        
    except ImportError as e:
        print(f"❌ 导入测试模块失败: {e}")
        print("请确保项目文件完整")
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断测试")
        print("👋 感谢使用GLFT网格交易监控系统！")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        print("\n🔧 故障排除建议:")
        print("   1. 检查是否安装了所有依赖包")
        print("   2. 确保系统支持GUI显示")
        print("   3. 检查matplotlib后端配置")
        print("   4. 查看详细错误日志")
    finally:
        print("\n" + "=" * 60)
        print("📋 测试结束")
        print("📖 更多信息请查看: docs/实时监控功能说明.md")
        print("=" * 60)

if __name__ == "__main__":
    main()