#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版交易管理器
高性能交易管理器，提供更好的性能、稳定性和可维护性
"""

import asyncio
from typing import Optional

from core.tradeManager import TradeManager
from util.sLogger import logger
from config.config import get_trade_config


class EnhancedTradeManager(TradeManager):
    """
    增强版交易管理器
    提供更好的性能、稳定性和可维护性的高效订单管理功能
    """

    def __init__(self, symbolName: str, wsExchange, baseSpread=0.001, minSpread=0.0008, 
                 maxSpread=0.003, orderCoolDown=0.1, maxStockRadio=0.25, 
                 orderAmountRatio=0.05, coin='USDT', direction='both'):
        super().__init__(symbolName, wsExchange, baseSpread, minSpread, maxSpread, 
                        orderCoolDown, maxStockRadio, orderAmountRatio, coin, direction)
        
        # 获取配置
        trade_config = get_trade_config()
        
        # 设置增强功能标志
        self.enhanced_mode = True
        self.performance_monitoring = getattr(trade_config, 'ENABLE_PERFORMANCE_MONITORING', True)
        
        # 性能统计
        self.trade_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'avg_execution_time': 0.0
        }
        
        logger.info(f"{self.symbolName}增强版交易管理器初始化完成")

    async def runTrade(self):
        """
        重写交易方法，提供增强的交易逻辑
        """
        import time
        start_time = time.time()
        
        try:
            # 执行增强版交易逻辑
            result = await self.runTradeEnhanced()
            
            # 更新统计信息
            if self.performance_monitoring:
                execution_time = time.time() - start_time
                self.trade_stats['total_trades'] += 1
                if result:
                    self.trade_stats['successful_trades'] += 1
                else:
                    self.trade_stats['failed_trades'] += 1
                
                # 更新平均执行时间
                total = self.trade_stats['total_trades']
                current_avg = self.trade_stats['avg_execution_time']
                self.trade_stats['avg_execution_time'] = (current_avg * (total - 1) + execution_time) / total
            
            return result
            
        except Exception as e:
            logger.error(f"{self.symbolName}增强版交易执行异常: {e}")
            if self.performance_monitoring:
                self.trade_stats['total_trades'] += 1
                self.trade_stats['failed_trades'] += 1
            return False

    async def runTradeEnhanced(self):
        """
        增强版交易流程
        提供更好的性能和稳定性的交易逻辑
        """
        try:
            logger.info(f"{self.symbolName}开始执行增强版交易流程")

            # 重新计算订单数量
            await self.calculateOrderAmount()

            # 检查必要的交易条件
            if self.orderAmount is None or self.orderAmount <= 0:
                logger.error(f"{self.symbolName}订单数量无效: {self.orderAmount}，跳过交易")
                return False

            if self.lastPrice is None or self.lastPrice <= 0:
                logger.error(f"{self.symbolName}价格信息无效: {self.lastPrice}，跳过交易")
                return False

            # 计算中间价（使用买一卖一平均价而非最新成交价）
            mid_price = await self._calculate_mid_price()
            if mid_price is None:
                logger.error(f"{self.symbolName}无法获取有效的中间价")
                return False

            # 计算当前持仓
            current_position = self._get_net_position()
            max_position = self.maxStockRadio * self.equity if self.equity else 1000

            # 计算动态价差
            spread = await self._calculate_dynamic_spread()

            # 执行增强版订单管理逻辑
            success = await self._execute_enhanced_orders(
                mid_price=mid_price,
                spread=spread,
                current_position=current_position,
                max_position=max_position
            )
            
            if success:
                logger.info(f"{self.symbolName}增强版交易执行成功")
                return True
            else:
                logger.warning(f"{self.symbolName}增强版交易执行失败")
                return False

        except Exception as e:
            logger.error(f"{self.symbolName}增强版交易流程异常: {e}")
            return False

    async def _calculate_mid_price(self) -> float:
        """
        计算中间价（买一卖一平均价）
        
        Returns:
            中间价或None
        """
        try:
            # 尝试从WebSocket获取实时订单簿
            if hasattr(self.wsExchange, 'watchOrderBook'):
                orderbook = await self.wsExchange.fetchOrderBook(self.symbolName, limit=1)
                if orderbook and orderbook.get('bids') and orderbook.get('asks'):
                    best_bid = orderbook['bids'][0][0]
                    best_ask = orderbook['asks'][0][0]
                    mid_price = (best_bid + best_ask) / 2.0
                    logger.debug(f"{self.symbolName}中间价: {mid_price} (买一: {best_bid}, 卖一: {best_ask})")
                    return mid_price
            
            # 回退到使用最新价格
            if self.lastPrice:
                logger.debug(f"{self.symbolName}使用最新价格作为中间价: {self.lastPrice}")
                return self.lastPrice
            
            return None
            
        except Exception as e:
            logger.warning(f"{self.symbolName}获取中间价失败: {e}，使用最新价格")
            return self.lastPrice

    def _get_net_position(self) -> float:
        """
        获取净持仓数量
        
        Returns:
            净持仓数量
        """
        if hasattr(self, 'netPosition') and self.netPosition is not None:
            return self.netPosition
        
        # 回退到传统持仓计算
        if self.position:
            return sum(pos.get('contracts', 0) for pos in self.position)
        
        return 0.0

    async def _calculate_dynamic_spread(self) -> float:
        """
        计算动态价差
        
        Returns:
            动态价差
        """
        try:
            # 如果启用了波动率管理，使用动态价差
            if self.volatilityEnabled and hasattr(self.volatilityManager, 'getCurrentVolatility'):
                volatility = await self.volatilityManager.getCurrentVolatility()
                if volatility is not None:
                    # 基于波动率调整价差
                    base_spread = self.baseSpread
                    volatility_factor = max(0.5, min(2.0, 1 + volatility * 10))
                    dynamic_spread = base_spread * volatility_factor
                    
                    # 确保在最小和最大价差范围内
                    dynamic_spread = max(self.minSpread, min(self.maxSpread, dynamic_spread))
                    
                    logger.debug(f"{self.symbolName}动态价差: {dynamic_spread} (波动率: {volatility:.4f})")
                    return dynamic_spread
            
            # 回退到基础价差
            return self.baseSpread
            
        except Exception as e:
            logger.warning(f"{self.symbolName}计算动态价差失败: {e}，使用基础价差")
            return self.baseSpread

    async def _execute_enhanced_orders(self, mid_price: float, spread: float, 
                                     current_position: float, max_position: float) -> bool:
        """
        执行增强版订单管理逻辑
        
        Args:
            mid_price: 中间价
            spread: 价差
            current_position: 当前持仓
            max_position: 最大持仓
            
        Returns:
            是否执行成功
        """
        try:
            # 计算买卖价格
            buy_price = mid_price - spread
            sell_price = mid_price + spread
            
            # 检查持仓限制
            can_buy = abs(current_position) < max_position
            can_sell = abs(current_position) < max_position
            
            # 取消现有订单（增强版会更智能地管理订单）
            try:
                await self.cancelAllOrder()
            except Exception as e:
                # 如果没有订单需要取消，这是正常情况
                if "No order to cancel" in str(e) or "22001" in str(e):
                    logger.debug(f"{self.symbolName}没有现有订单需要取消")
                else:
                    logger.warning(f"{self.symbolName}取消订单时发生异常: {e}")
            
            orders_placed = 0
            
            # 根据方向和持仓情况下单
            if self.direction in ['both', 'buy'] and can_buy:
                try:
                    await self.wsExchange.createOrder(
                        self.symbolName, 'limit', 'buy', self.orderAmount, buy_price
                    )
                    orders_placed += 1
                    logger.info(f"{self.symbolName}增强版买单已下达: 价格={buy_price}, 数量={self.orderAmount}")
                except Exception as e:
                    logger.error(f"{self.symbolName}增强版买单下达失败: {e}")
            
            if self.direction in ['both', 'sell'] and can_sell:
                try:
                    await self.wsExchange.createOrder(
                        self.symbolName, 'limit', 'sell', self.orderAmount, sell_price
                    )
                    orders_placed += 1
                    logger.info(f"{self.symbolName}增强版卖单已下达: 价格={sell_price}, 数量={self.orderAmount}")
                except Exception as e:
                    logger.error(f"{self.symbolName}增强版卖单下达失败: {e}")
            
            return orders_placed > 0
            
        except Exception as e:
            logger.error(f"{self.symbolName}增强版订单执行异常: {e}")
            return False

    def get_performance_stats(self) -> dict:
        """
        获取性能统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'mode': '增强版',
            'trade_stats': self.trade_stats.copy(),
            'success_rate': (self.trade_stats['successful_trades'] / max(1, self.trade_stats['total_trades'])) * 100
        }