#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
除零错误修复测试
测试当账户余额为0或价格为0时，程序是否能正常处理而不崩溃
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tradeManager import TradeManager
from util.sLogger import logger

class MockExchange:
    """模拟交易所，用于测试"""
    
    async def fetchBalance(self):
        return {
            'USDT': {
                'free': 0.0,  # 模拟余额为0的情况
                'total': 0.0
            }
        }
    
    async def loadMarkets(self, symbol):
        return {
            symbol: {
                'limits': {
                    'amount': {
                        'min': 0.001
                    }
                },
                'precision': {
                    'price': 0.01,
                    'amount': 0.001
                }
            }
        }
    
    async def fetchTicker(self, symbol):
        return {
            'last': 0.0  # 模拟价格为0的情况
        }
    
    async def fetchOpenOrders(self, symbol=None):
        return []
    
    async def fetchPositions(self):
        return []

async def test_zero_balance_and_price():
    """测试余额为0和价格为0的情况"""
    logger.info("开始测试除零错误修复...")
    
    # 创建模拟交易所
    mock_exchange = MockExchange()
    
    # 创建交易管理器
    trade_manager = TradeManager(
        symbolName="TEST/USDT:USDT",
        wsExchange=mock_exchange,
        baseSpread=0.001,
        minSpread=0.0008,
        maxSpread=0.003,
        orderCoolDown=0.1,
        maxStockRadio=0.25,
        orderAmountRatio=0.05
    )
    
    try:
        # 初始化交易对信息（这里会设置余额为0和价格为0）
        await trade_manager.initSymbolInfo()
        logger.info("✅ 初始化成功，没有发生除零错误")
        
        # 测试updateOrderAmount方法在各种边界条件下的表现
        test_cases = [
            {"name": "余额为0，价格为0", "equity": 0.0, "lastPrice": 0.0},
            {"name": "余额为0，价格正常", "equity": 0.0, "lastPrice": 100.0},
            {"name": "余额正常，价格为0", "equity": 1000.0, "lastPrice": 0.0},
            {"name": "余额为None，价格为None", "equity": None, "lastPrice": None},
            {"name": "余额负数，价格负数", "equity": -100.0, "lastPrice": -50.0},
            {"name": "余额正常，价格正常", "equity": 1000.0, "lastPrice": 100.0},
        ]
        
        for test_case in test_cases:
            logger.info(f"\n测试场景: {test_case['name']}")
            
            # 设置测试条件
            trade_manager.equity = test_case['equity']
            trade_manager.lastPrice = test_case['lastPrice']
            
            try:
                # 调用updateOrderAmount方法
                await trade_manager.updateOrderAmount()
                logger.info(f"✅ {test_case['name']} - 测试通过，订单数量: {trade_manager.orderAmount}")
                
                # 验证订单数量不小于最小值
                assert trade_manager.orderAmount >= trade_manager.minOrderAmount, \
                    f"订单数量 {trade_manager.orderAmount} 小于最小值 {trade_manager.minOrderAmount}"
                
            except Exception as e:
                logger.error(f"❌ {test_case['name']} - 测试失败: {e}")
                raise e
        
        logger.info("\n🎉 所有测试用例都通过了！除零错误修复成功。")
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        raise e

async def test_normal_operation():
    """测试正常操作情况"""
    logger.info("\n开始测试正常操作情况...")
    
    class NormalMockExchange(MockExchange):
        async def fetchBalance(self):
            return {
                'USDT': {
                    'free': 1000.0,  # 正常余额
                    'total': 1000.0
                }
            }
        
        async def fetchTicker(self, symbol):
            return {
                'last': 50000.0  # 正常价格
            }
    
    mock_exchange = NormalMockExchange()
    trade_manager = TradeManager(
        symbolName="BTC/USDT:USDT",
        wsExchange=mock_exchange,
        orderAmountRatio=0.1
    )
    
    try:
        await trade_manager.initSymbolInfo()
        await trade_manager.updateOrderAmount()
        
        # 验证正常情况下的计算
        expected_amount = trade_manager.equity / trade_manager.lastPrice * trade_manager.orderAmountRatio
        logger.info(f"预期订单数量: {expected_amount}")
        logger.info(f"实际订单数量: {trade_manager.orderAmount}")
        
        # 由于可能会被最小订单数量限制，所以检查是否合理
        assert trade_manager.orderAmount > 0, "订单数量应该大于0"
        logger.info("✅ 正常操作测试通过")
        
    except Exception as e:
        logger.error(f"❌ 正常操作测试失败: {e}")
        raise e

async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("除零错误修复测试开始")
    logger.info("=" * 60)
    
    try:
        # 测试边界条件
        await test_zero_balance_and_price()
        
        # 测试正常操作
        await test_normal_operation()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 所有测试完成！修复验证成功！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        logger.info("=" * 60)
        raise e

if __name__ == "__main__":
    asyncio.run(main())