#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统使用示例
演示如何使用新的统一配置管理系统
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import (
    get_websocket_config,
    get_trade_config,
    get_chart_config,
    get_log_config,
    validate_config,
    update_config,
    export_config_to_dict
)

def demonstrate_config_reading():
    """
    演示如何读取配置项
    """
    print("=== 配置读取示例 ===")
    
    # 读取WebSocket配置
    ws_config = get_websocket_config()
    print(f"WebSocket配置:")
    print(f"  订单检查间隔: {ws_config.ORDER_CHECK_INTERVAL}秒")
    print(f"  订单监听超时: {ws_config.ORDER_WATCH_TIMEOUT}秒")
    
    # 读取交易配置
    trade_config = get_trade_config()
    print(f"\n交易配置:")
    print(f"  使用成交价基准: {trade_config.USE_TRANSACTION_PRICE}")
    print(f"  无订单超时时间: {trade_config.NO_ORDER_TIMEOUT}秒")
    print(f"  最小订单价值: {trade_config.MIN_ORDER_VALUE} USDT")
    print(f"  价格偏差系数: {trade_config.PRICE_DEVIATION_FACTOR}")
    
    # 读取图表配置
    chart_config = get_chart_config()
    print(f"\n图表配置:")
    print(f"  更新间隔: {chart_config.CHART_UPDATE_INTERVAL}秒")
    print(f"  图表尺寸: {chart_config.CHART_WIDTH}x{chart_config.CHART_HEIGHT}")
    print(f"  最大数据点: {chart_config.MAX_DATA_POINTS}")
    
    # 读取日志配置
    log_config = get_log_config()
    print(f"\n日志配置:")
    print(f"  日志级别: {log_config.LOG_LEVEL}")
    print(f"  文件最大大小: {log_config.LOG_FILE_MAX_SIZE / (1024*1024):.1f}MB")
    print(f"  备份文件数: {log_config.LOG_FILE_BACKUP_COUNT}")

def demonstrate_config_validation():
    """
    演示配置验证功能
    """
    print("\n=== 配置验证示例 ===")
    
    try:
        validate_config()
        print("✅ 配置验证通过")
    except ValueError as e:
        print(f"❌ 配置验证失败: {e}")

def demonstrate_dynamic_config_update():
    """
    演示动态配置更新功能
    """
    print("\n=== 动态配置更新示例 ===")
    
    # 获取当前配置
    trade_config = get_trade_config()
    original_value = trade_config.MIN_ORDER_VALUE
    print(f"原始最小订单价值: {original_value}")
    
    try:
        # 动态更新配置
        new_value = 8.0
        update_config('TradeConfig', 'MIN_ORDER_VALUE', new_value)
        print(f"✅ 成功更新最小订单价值为: {trade_config.MIN_ORDER_VALUE}")
        
        # 恢复原始值
        update_config('TradeConfig', 'MIN_ORDER_VALUE', original_value)
        print(f"✅ 已恢复原始值: {trade_config.MIN_ORDER_VALUE}")
        
    except Exception as e:
        print(f"❌ 动态更新失败: {e}")

def demonstrate_config_export():
    """
    演示配置导出功能
    """
    print("\n=== 配置导出示例 ===")
    
    config_dict = export_config_to_dict()
    
    print(f"配置节数量: {len(config_dict)}")
    print(f"配置项总数: {sum(len(section) for section in config_dict.values())}")
    
    print("\n配置节列表:")
    for section_name, section_config in config_dict.items():
        print(f"  {section_name}: {len(section_config)}个配置项")
    
    # 显示部分配置内容
    print("\n部分配置内容示例:")
    if 'TradeConfig' in config_dict:
        trade_section = config_dict['TradeConfig']
        for key, value in list(trade_section.items())[:5]:  # 只显示前5个
            print(f"  TradeConfig.{key} = {value}")

def demonstrate_config_usage_in_class():
    """
    演示在类中使用配置的最佳实践
    """
    print("\n=== 类中使用配置示例 ===")
    
    class ExampleTradeManager:
        """
        示例交易管理器，演示如何在类中使用配置
        """
        
        def __init__(self):
            # 在初始化时读取配置
            self.trade_config = get_trade_config()
            self.ws_config = get_websocket_config()
            
            # 使用配置项
            self.use_transaction_price = self.trade_config.USE_TRANSACTION_PRICE
            self.min_order_value = self.trade_config.MIN_ORDER_VALUE
            self.order_check_interval = self.ws_config.ORDER_CHECK_INTERVAL
            
            print(f"  初始化交易管理器:")
            print(f"    使用成交价基准: {self.use_transaction_price}")
            print(f"    最小订单价值: {self.min_order_value}")
            print(f"    订单检查间隔: {self.order_check_interval}")
        
        def update_settings(self):
            """
            动态更新设置（重新读取配置）
            """
            self.trade_config = get_trade_config()
            self.min_order_value = self.trade_config.MIN_ORDER_VALUE
            print(f"  设置已更新，最小订单价值: {self.min_order_value}")
    
    # 创建示例实例
    manager = ExampleTradeManager()
    manager.update_settings()

def main():
    """
    主函数，运行所有示例
    """
    print("配置系统使用示例")
    print("=" * 50)
    
    try:
        demonstrate_config_reading()
        demonstrate_config_validation()
        demonstrate_dynamic_config_update()
        demonstrate_config_export()
        demonstrate_config_usage_in_class()
        
        print("\n=== 示例运行完成 ===")
        print("\n💡 提示:")
        print("1. 可以直接修改 config/config.py 文件来调整配置")
        print("2. 修改后需要重启程序才能生效（除非使用动态更新）")
        print("3. 配置会在程序启动时自动验证")
        print("4. symbols.json 中的配置会覆盖默认配置")
        
    except Exception as e:
        print(f"\n❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()