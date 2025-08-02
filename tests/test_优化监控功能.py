#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版监控功能测试脚本
测试改进后的图表性能和显示效果
"""

import sys
import os
import time
import random
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.dataRecorder import data_recorder
from core.chartManager import chart_manager
from util.sLogger import logger

class OptimizedMockTradeData:
    """优化的模拟交易数据生成器"""
    
    def __init__(self):
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        self.base_prices = {
            'BTC/USDT': 45000,
            'ETH/USDT': 3000,
            'BNB/USDT': 300,
            'ADA/USDT': 0.5
        }
        self.trade_count = 0
        
    def generate_trade(self):
        """生成一笔模拟交易"""
        symbol = random.choice(self.symbols)
        side = random.choice(['buy', 'sell'])
        
        # 生成价格波动
        base_price = self.base_prices[symbol]
        price_variation = random.uniform(-0.02, 0.02)  # ±2%波动
        price = base_price * (1 + price_variation)
        
        # 生成交易量
        if 'BTC' in symbol:
            amount = random.uniform(0.001, 0.1)
        elif 'ETH' in symbol:
            amount = random.uniform(0.01, 1.0)
        else:
            amount = random.uniform(0.1, 10.0)
        
        # 计算手续费 (0.1%)
        fee = price * amount * 0.001
        
        self.trade_count += 1
        
        return {
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'fee': fee,
            'timestamp': time.time()
        }
    
    def generate_equity_change(self):
        """生成权益变化"""
        # 模拟权益波动
        change = random.uniform(-50, 100)  # USDT变化
        return change

def test_optimized_monitoring_system():
    """测试优化后的监控系统"""
    print("\n" + "="*60)
    print("🚀 启动优化版GLFT网格交易监控功能测试")
    print("="*60)
    
    try:
        # 初始化组件
        print("\n📊 初始化数据记录器...")
        data_recorder.reset_data()  # 清空之前的数据
        
        print("📈 初始化图表管理器...")
        chart_manager.start_charts()
        
        # 创建模拟数据生成器
        mock_data = OptimizedMockTradeData()
        
        print("\n✅ 初始化完成！图表窗口已弹出")
        print("\n🔄 开始生成模拟交易数据...")
        print("提示：观察图表性能改进，窗口应该更流畅且大小适中")
        
        # 初始权益
        initial_equity = 10000.0
        data_recorder.update_equity_sync(initial_equity)
        
        # 生成模拟数据
        for i in range(200):  # 增加测试数据量
            # 生成交易
            trade = mock_data.generate_trade()
            data_recorder.record_trade_sync(
                symbol=trade['symbol'],
                side=trade['side'],
                amount=trade['amount'],
                price=trade['price'],
                fee=trade['fee']
            )
            
            # 模拟权益变化
            if i % 3 == 0:  # 每3笔交易更新一次权益
                equity_change = mock_data.generate_equity_change()
                new_equity = initial_equity + equity_change * (i + 1) / 10
                data_recorder.update_equity_sync(new_equity)
            
            # 更新显示
            chart_manager.update_display()
            
            # 打印进度
            if i % 20 == 0:
                summary = data_recorder.get_summary()
                print(f"\n📈 进度: {i+1}/200")
                print(f"   当前权益: {summary['current_equity']:.2f} USDT")
                print(f"   累计手续费: {summary['total_fee']:.4f} USDT")
                print(f"   累计成交量: {summary['total_volume']:.2f}")
            
            # 控制生成速度
            time.sleep(0.1)  # 减少延迟，测试高频更新性能
        
        print("\n🎉 数据生成完成！")
        print("\n📊 最终统计:")
        final_summary = data_recorder.get_summary()
        print(f"   总交易笔数: {len(data_recorder.trade_records)}")
        print(f"   最终权益: {final_summary['current_equity']:.2f} USDT")
        print(f"   总手续费: {final_summary['total_fee']:.4f} USDT")
        print(f"   总成交量: {final_summary['total_volume']:.2f}")
        
        print("\n⏰ 图表将继续运行60秒，请观察性能表现...")
        print("   - 检查窗口是否流畅")
        print("   - 确认文字不重叠")
        print("   - 验证窗口大小适中")
        
        # 持续更新显示
        for i in range(60):
            chart_manager.update_display()
            time.sleep(1)
            if i % 10 == 0:
                print(f"   ⏱️  剩余时间: {60-i} 秒")
        
        print("\n✅ 测试完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        logger.error(f"测试错误: {e}")
    finally:
        print("\n🔄 清理资源...")
        try:
            chart_manager.stop_charts()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️  清理资源时出错: {e}")

if __name__ == "__main__":
    test_optimized_monitoring_system()