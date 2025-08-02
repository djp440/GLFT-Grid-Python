#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多交易对配置测试脚本
用于验证配置文件加载和多交易对管理功能
"""

import json
import os
from main import load_symbols_config
from util.sLogger import logger

def test_config_loading():
    """测试配置文件加载功能"""
    print("=== 测试配置文件加载功能 ===")
    
    try:
        # 加载配置
        symbol_configs = load_symbols_config()
        
        print(f"成功加载 {len(symbol_configs)} 个交易对配置:")
        
        for i, config in enumerate(symbol_configs, 1):
            print(f"\n{i}. 交易对: {config['symbol']}")
            print(f"   启用状态: {config.get('enabled', 'N/A')}")
            print(f"   基础价差: {config.get('baseSpread', 'N/A')}")
            print(f"   最小价差: {config.get('minSpread', 'N/A')}")
            print(f"   最大价差: {config.get('maxSpread', 'N/A')}")
            print(f"   下单冷却: {config.get('orderCoolDown', 'N/A')}s")
            print(f"   最大持仓比例: {config.get('maxStockRadio', 'N/A')}")
            print(f"   订单金额比例: {config.get('orderAmountRatio', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"配置加载失败: {e}")
        return False

def test_config_file_exists():
    """测试配置文件是否存在"""
    print("\n=== 测试配置文件存在性 ===")
    
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'symbols.json')
    
    if os.path.exists(config_path):
        print(f"✓ 配置文件存在: {config_path}")
        
        # 验证JSON格式
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("✓ 配置文件JSON格式正确")
            
            if 'symbols' in config:
                print(f"✓ 配置文件包含symbols字段，共 {len(config['symbols'])} 个配置")
            else:
                print("✗ 配置文件缺少symbols字段")
                
        except json.JSONDecodeError as e:
            print(f"✗ 配置文件JSON格式错误: {e}")
        except Exception as e:
            print(f"✗ 读取配置文件失败: {e}")
            
    else:
        print(f"✗ 配置文件不存在: {config_path}")

def main():
    """主测试函数"""
    print("多交易对配置测试")
    print("=" * 50)
    
    # 测试配置文件存在性
    test_config_file_exists()
    
    # 测试配置加载功能
    success = test_config_loading()
    
    print("\n=== 测试结果 ===")
    if success:
        print("✓ 所有测试通过，多交易对配置功能正常")
    else:
        print("✗ 测试失败，请检查配置文件")
    
    print("\n=== 使用说明 ===")
    print("1. 编辑 config/symbols.json 文件来配置交易对")
    print("2. 设置 enabled: true 来启用交易对")
    print("3. 根据币种特性调整各项参数")
    print("4. 运行 python main.py 启动多交易对网格交易")

if __name__ == "__main__":
    main()