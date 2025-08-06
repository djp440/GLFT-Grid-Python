#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版交易管理器
集成GridOrderManager的高性能交易管理器
"""

import asyncio
from typing import Optional

from core.gridOrderManager import GridOrderManager
from core.tradeManager import TradeManager
from util.sLogger import logger
from config.config import get_trade_config


class EnhancedTradeManager(TradeManager):
    """
    增强版交易管理器
    集成了GridOrderManager的高效订单管理功能
    """

    def __init__(self, symbolName: str, wsExchange, baseSpread=0.001, minSpread=0.0008, 
                 maxSpread=0.003, orderCoolDown=0.1, maxStockRadio=0.25, 
                 orderAmountRatio=0.05, coin='USDT', direction='both'):
        super().__init__(symbolName, wsExchange, baseSpread, minSpread, maxSpread, 
                        orderCoolDown, maxStockRadio, orderAmountRatio, coin, direction)
        
        # 初始化网格订单管理器
        self.grid_order_manager = None
        
        # 获取配置
        trade_config = get_trade_config()
        
        # 设置增量更新模式
        self.use_incremental_updates = getattr(trade_config, 'ENABLE_INCREMENTAL_UPDATE', True)
        
        logger.info(f"{self.symbolName}增强版交易管理器初始化完成")

    async def init_grid_order_manager(self):
        """
        初始化网格订单管理器
        """
        try:
            # 获取交易对信息
            market_info = await self.wsExchange.loadMarkets()
            symbol_info = market_info.get(self.symbolName)
            
            if not symbol_info:
                raise ValueError(f"无法获取{self.symbolName}的市场信息")
            
            # 获取tick_size和计算grid_interval
            tick_size = symbol_info.get('precision', {}).get('price', 0.01)
            grid_interval = self.baseSpread * 2  # 网格间隔为双倍基础价差
            
            self.grid_order_manager = GridOrderManager(
                symbol_name=self.symbolName,
                exchange=self.wsExchange,
                tick_size=tick_size,
                grid_interval=grid_interval
            )
            
            logger.info(f"{self.symbolName}网格订单管理器初始化成功，tick_size={tick_size}, grid_interval={grid_interval}")
            
        except Exception as e:
            logger.error(f"{self.symbolName}网格订单管理器初始化失败: {e}")
            self.grid_order_manager = None

    async def runTradeEnhanced(self):
        """
        增强版交易流程
        使用GridOrderManager进行高效的增量订单更新
        """
        try:
            logger.info(f"{self.symbolName}开始执行增强版交易流程")

            # 检查网格订单管理器
            if not self.grid_order_manager:
                logger.warning(f"{self.symbolName}网格订单管理器未初始化，回退到传统模式")
                return await self.runTrade()

            # 重新计算订单数量
            await self.calculateOrderAmount()

            # 检查必要的交易条件
            if self.orderAmount is None or self.orderAmount <= 0:
                logger.error(f"{self.symbolName}订单数量无效: {self.orderAmount}，跳过交易")
                return

            if self.lastPrice is None or self.lastPrice <= 0:
                logger.error(f"{self.symbolName}价格信息无效: {self.lastPrice}，跳过交易")
                return

            # 更新网格订单管理器的活跃订单列表
            await self.grid_order_manager.update_active_orders(self.openOrders)

            # 计算中间价（使用买一卖一平均价而非最新成交价）
            mid_price = await self._calculate_mid_price()
            if mid_price is None:
                logger.error(f"{self.symbolName}无法获取有效的中间价")
                return

            # 计算当前持仓
            current_position = self._get_net_position()
            max_position = self.maxStockRadio * self.equity if self.equity else 1000

            # 计算动态价差
            spread = await self._calculate_dynamic_spread()

            # 使用增量更新模式
            if self.use_incremental_updates:
                success = await self.grid_order_manager.update_orders_incremental(
                    mid_price=mid_price,
                    spread=spread,
                    order_amount=self.orderAmount,
                    max_position=max_position,
                    current_position=current_position
                )
                
                if success:
                    logger.info(f"{self.symbolName}增量订单更新成功")
                    # 打印性能统计
                    stats = self.grid_order_manager.get_performance_stats()
                    logger.info(f"{self.symbolName}订单管理性能: {stats}")
                else:
                    logger.warning(f"{self.symbolName}增量订单更新失败，回退到传统模式")
                    return await self.runTrade()
            else:
                # 回退到传统模式
                return await self.runTrade()

        except Exception as e:
            logger.error(f"{self.symbolName}增强版交易流程异常: {e}")
            # 异常时回退到传统模式
            return await self.runTrade()

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

    async def toggle_incremental_mode(self, enabled: bool):
        """
        切换增量更新模式
        
        Args:
            enabled: 是否启用增量更新
        """
        self.use_incremental_updates = enabled
        mode = "增量更新" if enabled else "传统"
        logger.info(f"{self.symbolName}订单管理模式切换为: {mode}")

    def get_order_management_stats(self) -> dict:
        """
        获取订单管理统计信息
        
        Returns:
            统计信息字典
        """
        if self.grid_order_manager:
            return {
                'mode': '增量更新' if self.use_incremental_updates else '传统',
                'grid_manager_stats': self.grid_order_manager.get_performance_stats()
            }
        else:
            return {
                'mode': '传统',
                'grid_manager_stats': None
            }