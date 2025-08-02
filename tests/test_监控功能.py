import asyncio
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

class MockTradeData:
    """模拟交易数据生成器"""
    
    def __init__(self):
        self.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'XRP/USDT:USDT']
        self.base_equity = 1000.0
        self.current_equity = self.base_equity
        self.trade_count = 0
    
    async def generate_mock_trade(self):
        """生成模拟交易数据"""
        symbol = random.choice(self.symbols)
        side = random.choice(['buy', 'sell'])
        amount = random.uniform(10, 100)
        price = random.uniform(0.5, 50000)
        fee = amount * price * 0.001  # 0.1% 手续费
        order_id = f"mock_{self.trade_count}"
        
        await data_recorder.record_trade(
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            fee=fee,
            order_id=order_id
        )
        
        # 模拟权益变化
        equity_change = random.uniform(-10, 15)  # 随机权益变化
        self.current_equity += equity_change
        
        await data_recorder.update_equity(self.current_equity)
        
        self.trade_count += 1
        
        logger.info(f"生成模拟交易: {symbol} {side} {amount:.2f} @ {price:.4f}, 手续费: {fee:.4f}")

async def test_monitoring_system():
    """测试监控系统"""
    logger.info("开始测试监控系统...")
    
    # 启动图表管理器
    chart_manager.start_charts()
    
    # 创建模拟数据生成器
    mock_data = MockTradeData()
    
    try:
        # 生成初始权益数据
        await data_recorder.update_equity(mock_data.current_equity)
        
        # 持续生成模拟交易数据
        for i in range(50):  # 生成50笔模拟交易
            await mock_data.generate_mock_trade()
            
            # 更新图表显示
            chart_manager.update_display()
            
            # 每隔1-3秒生成一笔交易
            await asyncio.sleep(random.uniform(1, 3))
            
            # 每10笔交易显示一次统计信息
            if (i + 1) % 10 == 0:
                summary = data_recorder.get_summary()
                logger.info(f"统计信息 - 总交易: {summary['total_trades']}, "
                          f"总成交量: {summary['total_volume']:.2f}, "
                          f"总手续费: {summary['total_fee']:.4f}, "
                          f"当前权益: {summary['current_equity']:.2f}")
        
        logger.info("测试完成，图表将继续显示。按Ctrl+C退出。")
        
        # 保持程序运行以显示图表
        while True:
            await asyncio.sleep(5)
            # 偶尔生成新的交易数据
            if random.random() < 0.3:  # 30%概率生成新交易
                await mock_data.generate_mock_trade()
            
            # 更新图表显示
            chart_manager.update_display()
    
    except KeyboardInterrupt:
        logger.info("接收到退出信号")
    
    finally:
        # 清理资源
        chart_manager.stop_charts()
        data_recorder.stop()
        logger.info("测试结束")

def main():
    """主函数"""
    print("GLFT网格交易监控系统测试")
    print("=" * 50)
    print("此测试将：")
    print("1. 启动实时监控图表")
    print("2. 生成模拟交易数据")
    print("3. 实时更新图表显示")
    print("4. 按Ctrl+C可以退出测试")
    print("=" * 50)
    
    try:
        asyncio.run(test_monitoring_system())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        logger.error(f"测试错误: {e}")

if __name__ == "__main__":
    main()