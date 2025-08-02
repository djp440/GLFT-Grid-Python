#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘测试启动脚本
包含安全检查和用户确认步骤
"""

import os
import sys
import json
from dotenv import load_dotenv
import asyncio
from util.sLogger import logger

def check_environment():
    """检查环境配置"""
    print("=" * 60)
    print("🔍 环境配置检查")
    print("=" * 60)
    
    # 检查.env文件
    if not os.path.exists('.env'):
        print("❌ .env文件不存在！")
        return False
    
    load_dotenv()
    sandbox = os.getenv("sandbox")
    
    print(f"📋 沙盒模式: {sandbox}")
    
    if sandbox == "True":
        print("⚠️  当前为沙盒模式，这是安全的测试环境")
        mode = "沙盒测试"
    else:
        print("🚨 当前为实盘模式，将使用真实资金交易！")
        mode = "实盘交易"
    
    # 根据sandbox参数检查相应的API密钥
    if sandbox == "False":
        # 实盘模式，检查实盘API配置
        api_key = os.getenv("prod_apiKey")
        secret = os.getenv("prod_secret")
        password = os.getenv("prod_password")
        if not all([api_key, secret, password]):
            print("❌ 实盘API配置不完整！请检查prod_apiKey, prod_secret, prod_password")
            return False
        print(f"✅ 实盘API密钥已配置: {api_key[:8]}...")
    else:
        # 沙盒模式，检查沙盒API配置
        api_key = os.getenv("apiKey")
        secret = os.getenv("secret")
        password = os.getenv("password")
        if not all([api_key, secret, password]):
            print("❌ 沙盒API配置不完整！请检查apiKey, secret, password")
            return False
        print(f"✅ 沙盒API密钥已配置: {api_key[:8]}...")
    
    return True, mode

def check_config():
    """检查交易配置"""
    print("\n" + "=" * 60)
    print("⚙️  交易配置检查")
    print("=" * 60)
    
    try:
        with open('config/symbols.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        enabled_symbols = [s for s in config['symbols'] if s['enabled']]
        
        if not enabled_symbols:
            print("❌ 没有启用的交易对！")
            return False
        
        print(f"📊 启用的交易对数量: {len(enabled_symbols)}")
        
        for symbol in enabled_symbols:
            print(f"\n🔸 {symbol['symbol']}:")
            print(f"   基础价差: {symbol['baseSpread']*100:.2f}%")
            print(f"   最大持仓比例: {symbol['maxStockRadio']*100:.1f}%")
            print(f"   单次下单比例: {symbol['orderAmountRatio']*100:.1f}%")
            
            # 风险评估
            if symbol['maxStockRadio'] > 0.3:
                print(f"   ⚠️  持仓比例较高 ({symbol['maxStockRadio']*100:.1f}%)")
            
            if symbol['orderAmountRatio'] > 0.03:
                print(f"   ⚠️  单次下单比例较高 ({symbol['orderAmountRatio']*100:.1f}%)")
        
        return True, enabled_symbols
        
    except FileNotFoundError:
        print("❌ 配置文件 config/symbols.json 不存在！")
        return False
    except Exception as e:
        print(f"❌ 配置文件读取错误: {e}")
        return False

def show_risk_warning():
    """显示风险警告"""
    print("\n" + "=" * 60)
    print("⚠️  风险警告")
    print("=" * 60)
    
    warnings = [
        "网格交易在单边行情中可能面临较大亏损",
        "程序可能因网络问题、API限制等原因异常停止",
        "市场极端波动可能导致超出预期的损失",
        "请确保只使用可承受损失的闲置资金",
        "建议设定明确的止损条件和退出策略",
        "实盘运行期间需要密切监控程序状态"
    ]
    
    for i, warning in enumerate(warnings, 1):
        print(f"{i}. {warning}")

def get_user_confirmation(mode):
    """获取用户确认"""
    print("\n" + "=" * 60)
    print("✋ 用户确认")
    print("=" * 60)
    
    print(f"您即将启动 {mode} 模式")
    
    if mode == "实盘交易":
        print("\n🚨 这将使用真实资金进行交易！")
        
        # 多重确认
        confirm1 = input("\n请输入 'YES' 确认您了解风险: ")
        if confirm1 != "YES":
            return False
        
        confirm2 = input("请再次输入 'CONFIRM' 确认启动实盘交易: ")
        if confirm2 != "CONFIRM":
            return False
        
        print("\n✅ 用户确认完成，准备启动实盘交易...")
    else:
        confirm = input("\n请输入 'yes' 确认启动沙盒测试: ")
        if confirm.lower() != "yes":
            return False
        
        print("\n✅ 用户确认完成，准备启动沙盒测试...")
    
    return True

def show_safety_tips():
    """显示安全提示"""
    print("\n" + "=" * 60)
    print("💡 安全提示")
    print("=" * 60)
    
    tips = [
        "程序启动后，请保持终端窗口开启",
        "可以按 Ctrl+C 安全停止程序",
        "程序会自动保存交易日志到 logs 目录",
        "建议定期检查账户余额和持仓情况",
        "如发现异常，请立即停止程序并检查",
        "可以通过交易所网页版随时查看和手动干预"
    ]
    
    for i, tip in enumerate(tips, 1):
        print(f"{i}. {tip}")

def main():
    """主函数"""
    print("🚀 GLFT网格交易程序 - 实盘测试启动器")
    print("版本: 1.0.0")
    print("作者: AI Assistant")
    
    try:
        # 1. 环境检查
        env_result = check_environment()
        if not env_result:
            print("\n❌ 环境检查失败，程序退出")
            return
        
        env_ok, mode = env_result
        
        # 2. 配置检查
        config_result = check_config()
        if not config_result:
            print("\n❌ 配置检查失败，程序退出")
            return
        
        config_ok, symbols = config_result
        
        # 3. 显示风险警告
        show_risk_warning()
        
        # 4. 获取用户确认
        if not get_user_confirmation(mode):
            print("\n❌ 用户取消操作，程序退出")
            return
        
        # 5. 显示安全提示
        show_safety_tips()
        
        # 6. 启动主程序
        print("\n" + "=" * 60)
        print("🚀 启动交易程序")
        print("=" * 60)
        
        print("\n正在启动主程序...")
        
        # 导入并运行主程序
        import main
        main.main()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  程序被用户中断")
        logger.info("程序被用户手动中断")
    except Exception as e:
        print(f"\n\n❌ 程序启动失败: {e}")
        logger.error(f"程序启动失败: {e}")
    finally:
        print("\n👋 程序已退出")

if __name__ == "__main__":
    main()