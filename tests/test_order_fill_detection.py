#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试订单成交检测机制
用于验证和测试当限价单被直接成交时的检测逻辑
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tradeManager import TradeManager
from core.websocketManager import WebSocketManager


class TestOrderFillDetection(unittest.TestCase):
    """测试订单成交检测机制"""

    def setUp(self):
        """设置测试环境"""
        # 创建模拟的交易所对象
        self.mock_exchange = Mock()
        self.mock_exchange.fetchOpenOrders = AsyncMock(return_value=[])
        self.mock_exchange.fetchPositions = AsyncMock(return_value=[])
        self.mock_exchange.fetchBalance = AsyncMock(return_value={'SUSDT': {'free': 1000, 'total': 1000}})
        self.mock_exchange.loadMarkets = AsyncMock(return_value={
            'SBTC/SUSDT:SUSDT': {
                'limits': {'amount': {'min': 0.001}},
                'precision': {'price': 0.01, 'amount': 0.001}
            }
        })
        
        # 创建交易管理器
        self.trade_manager = TradeManager(
            symbolName='SBTC/SUSDT:SUSDT',
            wsExchange=self.mock_exchange,
            coin='SUSDT'
        )
        
        # 创建websocket管理器
        self.ws_manager = WebSocketManager(
            symbolName='SBTC/SUSDT:SUSDT',
            wsExchange=self.mock_exchange,
            tradeManage=self.trade_manager
        )
        
        # 绑定websocket管理器
        asyncio.run(self.trade_manager.bindWebsocketManager(self.ws_manager))

    def test_instant_fill_detection(self):
        """测试瞬间成交的检测"""
        async def run_test():
            # 模拟下单后立即成交的情况
            order_id = "test_order_123"
            
            # 1. 模拟下单
            await self.ws_manager.runOpenOrderWatch({'id': order_id, 'side': 'buy', 'amount': 0.001})
            
            # 2. 模拟订单立即成交（从未成交列表中消失）
            self.mock_exchange.watchOrders = AsyncMock(return_value=[])
            
            # 3. 验证是否能检测到成交
            # 这里应该触发onOrderFilled
            with patch.object(self.trade_manager, 'onOrderFilled') as mock_on_filled:
                # 模拟一次websocket更新
                await self.ws_manager.watchOpenOrder()
                
                # 验证onOrderFilled被调用
                mock_on_filled.assert_called_once()
        
        asyncio.run(run_test())

    def test_order_status_change_detection(self):
        """测试订单状态变化检测"""
        async def run_test():
            order_id = "test_order_456"
            
            # 1. 模拟下单
            await self.ws_manager.runOpenOrderWatch({'id': order_id, 'side': 'sell', 'amount': 0.001})
            
            # 2. 模拟订单状态变为已成交
            filled_order = {
                'id': order_id,
                'side': 'sell',
                'amount': 0.001,
                'filled': 0.001,
                'status': 'filled',
                'price': 50000,
                'average': 50000
            }
            self.mock_exchange.watchOrders = AsyncMock(return_value=[filled_order])
            
            # 3. 验证是否能检测到成交
            with patch.object(self.trade_manager, 'onOrderFilled') as mock_on_filled:
                # 模拟一次websocket更新
                await self.ws_manager.watchOpenOrder()
                
                # 验证onOrderFilled被调用，并且传入了正确的成交订单
                mock_on_filled.assert_called_once()
                called_args = mock_on_filled.call_args[0]
                self.assertEqual(len(called_args[0]), 1)  # 应该有一个成交订单
                self.assertEqual(called_args[0][0]['id'], order_id)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()