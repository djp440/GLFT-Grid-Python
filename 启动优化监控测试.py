#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版监控功能启动脚本
用于测试改进后的图表性能和显示效果
"""

import sys
import os
import subprocess

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'matplotlib',
        'numpy', 
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - 未安装")
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("\n✅ 所有依赖包检查通过！")
    return True

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        🚀 GLFT网格交易 - 优化版实时监控功能测试 🚀           ║
║                                                              ║
║  📈 性能优化特性:                                            ║
║     • 减少图表更新频率，提升流畅度                           ║
║     • 优化窗口大小，适配4K显示器                             ║
║     • 修复文字重叠问题                                       ║
║     • 智能数据变化检测，避免无效重绘                         ║
║                                                              ║
║  🎯 测试内容:                                                ║
║     • 图表性能和流畅度                                       ║
║     • 窗口大小和布局                                         ║
║     • 文字显示效果                                           ║
║     • 高频数据更新处理                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def main():
    """主函数"""
    print_banner()
    
    print("\n🔍 检查系统依赖...")
    if not check_dependencies():
        input("\n按回车键退出...")
        return
    
    print("\n🚀 启动优化版监控测试...")
    print("\n" + "="*50)
    
    try:
        # 导入并运行测试
        from tests.test_优化监控功能 import test_optimized_monitoring_system
        test_optimized_monitoring_system()
        
    except ImportError as e:
        print(f"❌ 导入测试模块失败: {e}")
        print("请确保项目结构完整")
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
    
    print("\n" + "="*50)
    print("\n📋 测试完成报告:")
    print("   1. 图表是否流畅无卡顿？")
    print("   2. 窗口大小是否合适？")
    print("   3. 文字是否清晰无重叠？")
    print("   4. 数据更新是否及时？")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()