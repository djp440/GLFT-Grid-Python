#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单监听修复测试脚本

此脚本用于测试订单监听系统的修复效果，包括：
1. onOrderFilled方法的异常处理
2. 订单监听状态检查和恢复
3. websocket异常处理
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.tradeManager import TradeManager
from core.websocketManager import WebSocketManager
from util.sLogger import logger

class TestOrderMonitoringFix(unittest.TestCase):
    """订单监听修复测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建模拟的交易所对象
        self.mock_exchange = AsyncMock()
        self.mock_exchange.fetchBalance = AsyncMock(return_value={
            'USDT': {'free': 1000.0, 'total': 1000.0}
        })
        self.mock_exchange.loadMarkets = AsyncMock(return_value={
            'SOL/USDT:USDT': {
                'limits': {'amount': {'min': 0.1}},
                'precision': {'price': 0.001, 'amount': 0.1}
            }
        })
        self.mock_exchange.fetchTicker = AsyncMock(return_value={'last': 100.0})
        self.mock_exchange.fetchOpenOrders = AsyncMock(return_value=[])
        self.mock_exchange.fetchPositions = AsyncMock(return_value=[])
        
        # 创建TradeManager实例
        self.trade_manager = TradeManager('SOL/USDT:USDT', self.mock_exchange)
        
    async def test_onOrderFilled_with_none_parameter(self):
        """测试onOrderFilled方法处理None参数"""
        logger.info("测试onOrderFilled方法处理None参数")
        
        # 初始化TradeManager
        await self.trade_manager.initSymbolInfo()
        
        # 模拟websocketManager
        mock_ws_manager = AsyncMock()
        await self.trade_manager.bindWebsocketManager(mock_ws_manager)
        
        try:
            # 测试传入None参数
            await self.trade_manager.onOrderFilled(None)
            logger.info("✅ onOrderFilled(None) 测试通过")
        except Exception as e:
            logger.error(f"❌ onOrderFilled(None) 测试失败: {e}")
            raise
            
        try:
            # 测试传入空列表
            await self.trade_manager.onOrderFilled([])
            logger.info("✅ onOrderFilled([]) 测试通过")
        except Exception as e:
            logger.error(f"❌ onOrderFilled([]) 测试失败: {e}")
            raise
    
    async def test_websocket_manager_order_watch_active(self):
        """测试websocketManager的订单监听状态检查"""
        logger.info("测试websocketManager的订单监听状态检查")
        
        # 创建WebSocketManager实例
        ws_manager = WebSocketManager('SOL/USDT:USDT', self.mock_exchange, self.trade_manager, run=False)
        
        # 测试初始状态
        is_active = await ws_manager.isOrderWatchActive()
        assert not is_active, "初始状态应该是非活跃的"
        logger.info("✅ 初始状态检查通过")
        
        # 测试启动监听后的状态
        mock_order1 = {'id': '123456'}
        mock_order2 = {'id': '789012'}
        await ws_manager.runOpenOrderWatch(mock_order1, mock_order2)
        
        is_active = await ws_manager.isOrderWatchActive()
        assert is_active, "启动监听后应该是活跃的"
        logger.info("✅ 启动监听状态检查通过")
        
        # 测试停止监听后的状态
        ws_manager.inWatchOpenOrder = False
        ws_manager.openOrders = []
        
        is_active = await ws_manager.isOrderWatchActive()
        assert not is_active, "停止监听后应该是非活跃的"
        logger.info("✅ 停止监听状态检查通过")
    
    async def test_check_and_recover_order_watch(self):
        """测试订单监听检查和恢复机制"""
        logger.info("测试订单监听检查和恢复机制")
        
        # 初始化TradeManager
        await self.trade_manager.initSymbolInfo()
        
        # 创建模拟的websocketManager
        mock_ws_manager = AsyncMock()
        mock_ws_manager.isOrderWatchActive = AsyncMock(return_value=False)
        mock_ws_manager.runOpenOrderWatch = AsyncMock()
        
        await self.trade_manager.bindWebsocketManager(mock_ws_manager)
        
        # 模拟有未成交订单的情况
        mock_orders = [
            {'id': '123456', 'side': 'buy'},
            {'id': '789012', 'side': 'sell'}
        ]
        self.mock_exchange.fetchOpenOrders.return_value = mock_orders
        
        try:
            # 执行检查和恢复
            await self.trade_manager.checkAndRecoverOrderWatch()
            
            # 验证是否调用了恢复方法
            mock_ws_manager.runOpenOrderWatch.assert_called_once()
            logger.info("✅ 订单监听恢复机制测试通过")
        except Exception as e:
            logger.error(f"❌ 订单监听恢复机制测试失败: {e}")
            raise
    
    async def test_price_update_counter(self):
        """测试价格更新计数器和定期检查机制"""
        logger.info("测试价格更新计数器和定期检查机制")
        
        # 初始化TradeManager
        await self.trade_manager.initSymbolInfo()
        
        # 创建模拟的websocketManager
        mock_ws_manager = AsyncMock()
        mock_ws_manager.isOrderWatchActive = AsyncMock(return_value=True)
        await self.trade_manager.bindWebsocketManager(mock_ws_manager)
        
        # 模拟价格更新
        for i in range(105):
            await self.trade_manager.updateLastPrice(100.0 + i * 0.01)
        
        # 验证计数器是否正确
        assert hasattr(self.trade_manager, '_price_update_counter'), "应该有价格更新计数器"
        assert self.trade_manager._price_update_counter == 105, f"计数器应该是105，实际是{self.trade_manager._price_update_counter}"
        
        logger.info("✅ 价格更新计数器测试通过")

async def run_tests():
    """运行所有测试"""
    logger.info("开始运行订单监听修复测试")
    
    test_instance = TestOrderMonitoringFix()
    test_instance.setUp()
    
    try:
        # 运行各项测试
        await test_instance.test_onOrderFilled_with_none_parameter()
        await test_instance.test_websocket_manager_order_watch_active()
        await test_instance.test_check_and_recover_order_watch()
        await test_instance.test_price_update_counter()
        
        logger.info("🎉 所有测试通过！修复效果良好")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise

def main():
    """主函数"""
    print("订单监听修复测试脚本")
    print("=" * 50)
    
    try:
        asyncio.run(run_tests())
        print("\n✅ 测试完成，修复验证成功！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())