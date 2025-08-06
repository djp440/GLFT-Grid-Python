#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格订单管理器
基于 hftbacktest 的启发，实现高效的增量式订单管理
"""

import asyncio
import math
from typing import Dict, List, Tuple, Optional
from util.sLogger import logger
import ccxt.pro


class GridOrderManager:
    """
    网格订单管理器
    
    核心功能：
    1. 增量式订单更新（避免全量取消重下）
    2. 基于价格网格的订单ID管理
    3. 智能订单检查和恢复机制
    4. 批量订单操作优化
    """

    def __init__(self, symbol_name: str, exchange: ccxt.pro.Exchange, tick_size: float, grid_interval: float):
        self.symbol_name = symbol_name
        self.exchange = exchange
        self.tick_size = tick_size
        self.grid_interval = grid_interval
        
        # 活跃订单管理：{price_tick: order_info}
        self.active_orders: Dict[int, dict] = {}
        
        # 订单操作锁，防止并发冲突
        self._order_lock = asyncio.Lock()
        
        # 性能统计
        self.stats = {
            'total_updates': 0,
            'incremental_updates': 0,
            'full_updates': 0,
            'orders_saved': 0  # 通过增量更新节省的订单操作数
        }
        
        logger.info(f"{self.symbol_name}网格订单管理器初始化完成")

    def get_price_tick(self, price: float) -> int:
        """
        将价格转换为价格tick（用作订单ID）
        
        Args:
            price: 订单价格
            
        Returns:
            价格tick（整数）
        """
        return int(round(price / self.tick_size))

    def align_price_to_grid(self, price: float, side: str) -> float:
        """
        将价格对齐到网格
        
        Args:
            price: 原始价格
            side: 订单方向 ('buy' 或 'sell')
            
        Returns:
            对齐后的价格
        """
        if side == 'buy':
            # 买单向下对齐
            return math.floor(price / self.grid_interval) * self.grid_interval
        else:
            # 卖单向上对齐
            return math.ceil(price / self.grid_interval) * self.grid_interval

    async def update_active_orders(self, current_orders: List[dict]):
        """
        更新活跃订单列表
        
        Args:
            current_orders: 当前的订单列表
        """
        async with self._order_lock:
            self.active_orders.clear()
            
            for order in current_orders:
                try:
                    price = float(order.get('price', 0))
                    if price > 0:
                        price_tick = self.get_price_tick(price)
                        self.active_orders[price_tick] = {
                            'id': order.get('id'),
                            'side': order.get('side'),
                            'price': price,
                            'amount': float(order.get('amount', 0)),
                            'status': order.get('status')
                        }
                except (ValueError, TypeError) as e:
                    logger.warning(f"{self.symbol_name}解析订单信息失败: {order}, 错误: {e}")

    async def calculate_target_orders(self, mid_price: float, spread: float, order_amount: float, 
                                    max_position: float, current_position: float) -> Dict[str, Optional[dict]]:
        """
        计算目标订单配置
        
        Args:
            mid_price: 中间价
            spread: 价差
            order_amount: 订单数量
            max_position: 最大持仓
            current_position: 当前持仓
            
        Returns:
            目标订单配置 {'buy': order_info, 'sell': order_info}
        """
        target_orders = {'buy': None, 'sell': None}
        
        # 计算目标价格
        target_buy_price = mid_price - spread
        target_sell_price = mid_price + spread
        
        # 对齐到网格
        target_buy_price = self.align_price_to_grid(target_buy_price, 'buy')
        target_sell_price = self.align_price_to_grid(target_sell_price, 'sell')
        
        # 检查持仓限制
        can_buy = current_position < max_position
        can_sell = current_position > -max_position
        
        if can_buy:
            target_orders['buy'] = {
                'side': 'buy',
                'price': target_buy_price,
                'amount': order_amount,
                'price_tick': self.get_price_tick(target_buy_price)
            }
        
        if can_sell:
            target_orders['sell'] = {
                'side': 'sell',
                'price': target_sell_price,
                'amount': order_amount,
                'price_tick': self.get_price_tick(target_sell_price)
            }
        
        return target_orders

    async def plan_incremental_update(self, target_orders: Dict[str, Optional[dict]]) -> Tuple[List[str], List[dict]]:
        """
        规划增量式订单更新
        
        Args:
            target_orders: 目标订单配置
            
        Returns:
            (需要取消的订单ID列表, 需要下达的订单列表)
        """
        orders_to_cancel = []
        orders_to_place = []
        
        async with self._order_lock:
            # 检查每个目标订单
            for side, target_order in target_orders.items():
                if target_order is None:
                    # 该方向不需要订单，取消现有的同方向订单
                    for price_tick, order_info in self.active_orders.items():
                        if order_info['side'] == side:
                            orders_to_cancel.append(order_info['id'])
                else:
                    # 该方向需要订单
                    target_price_tick = target_order['price_tick']
                    
                    # 检查是否已有相同价格的订单
                    if target_price_tick in self.active_orders:
                        existing_order = self.active_orders[target_price_tick]
                        if (existing_order['side'] == side and 
                            abs(existing_order['amount'] - target_order['amount']) < 1e-8):
                            # 订单已存在且参数相同，无需操作
                            logger.debug(f"{self.symbol_name}{side}订单已存在于价格{target_order['price']}，跳过")
                            continue
                        else:
                            # 价格相同但参数不同，需要取消重下
                            orders_to_cancel.append(existing_order['id'])
                    
                    # 取消该方向的其他价格订单
                    for price_tick, order_info in self.active_orders.items():
                        if (order_info['side'] == side and 
                            price_tick != target_price_tick and 
                            order_info['id'] not in orders_to_cancel):
                            orders_to_cancel.append(order_info['id'])
                    
                    # 添加到下单列表
                    orders_to_place.append(target_order)
        
        # 统计节省的操作数
        total_possible_operations = len([o for o in target_orders.values() if o is not None]) * 2  # 取消+下单
        actual_operations = len(orders_to_cancel) + len(orders_to_place)
        self.stats['orders_saved'] += max(0, total_possible_operations - actual_operations)
        
        return orders_to_cancel, orders_to_place

    async def execute_batch_operations(self, orders_to_cancel: List[str], orders_to_place: List[dict]) -> bool:
        """
        批量执行订单操作
        
        Args:
            orders_to_cancel: 需要取消的订单ID列表
            orders_to_place: 需要下达的订单列表
            
        Returns:
            操作是否成功
        """
        if not orders_to_cancel and not orders_to_place:
            logger.debug(f"{self.symbol_name}无需执行订单操作")
            return True
        
        logger.info(f"{self.symbol_name}执行批量订单操作: 取消{len(orders_to_cancel)}个, 下达{len(orders_to_place)}个")
        
        tasks = []
        
        # 并行取消订单
        for order_id in orders_to_cancel:
            task = self._cancel_order_safe(order_id)
            tasks.append(task)
        
        # 并行下达订单
        for order_info in orders_to_place:
            task = self._place_order_safe(order_info)
            tasks.append(task)
        
        # 执行所有操作
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查结果
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"{self.symbol_name}订单操作失败: {result}")
                elif i < len(orders_to_cancel):
                    # 取消订单操作，返回bool
                    if result is True:
                        success_count += 1
                else:
                    # 下达订单操作，返回dict或None
                    if result is not None:
                        success_count += 1
            
            success_rate = success_count / len(results) if results else 1.0
            logger.info(f"{self.symbol_name}批量操作完成，成功率: {success_rate:.2%}")
            
            return success_rate > 0.8  # 80%以上成功率认为操作成功
            
        except Exception as e:
            logger.error(f"{self.symbol_name}批量订单操作异常: {e}")
            return False

    async def _cancel_order_safe(self, order_id: str) -> bool:
        """
        安全取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            是否成功
        """
        try:
            await self.exchange.cancelOrder(order_id, self.symbol_name)
            logger.debug(f"{self.symbol_name}成功取消订单: {order_id}")
            return True
        except Exception as e:
            logger.warning(f"{self.symbol_name}取消订单失败: {order_id}, 错误: {e}")
            return False

    async def _place_order_safe(self, order_info: dict) -> Optional[dict]:
        """
        安全下达订单
        
        Args:
            order_info: 订单信息
            
        Returns:
            订单结果或None
        """
        try:
            side = order_info['side']
            amount = order_info['amount']
            price = order_info['price']
            
            if side == 'buy':
                result = await self.exchange.createLimitBuyOrder(self.symbol_name, amount, price)
            else:
                result = await self.exchange.createLimitSellOrder(self.symbol_name, amount, price)
            
            logger.debug(f"{self.symbol_name}成功下达{side}订单: {amount}@{price}")
            return result
            
        except Exception as e:
            logger.warning(f"{self.symbol_name}下达订单失败: {order_info}, 错误: {e}")
            return None

    async def update_orders_incremental(self, mid_price: float, spread: float, order_amount: float,
                                      max_position: float, current_position: float) -> bool:
        """
        增量式订单更新（主要接口）
        
        Args:
            mid_price: 中间价
            spread: 价差
            order_amount: 订单数量
            max_position: 最大持仓
            current_position: 当前持仓
            
        Returns:
            更新是否成功
        """
        try:
            # 计算目标订单
            target_orders = await self.calculate_target_orders(
                mid_price, spread, order_amount, max_position, current_position
            )
            
            # 规划增量更新
            orders_to_cancel, orders_to_place = await self.plan_incremental_update(target_orders)
            
            # 执行批量操作
            success = await self.execute_batch_operations(orders_to_cancel, orders_to_place)
            
            # 更新统计
            self.stats['total_updates'] += 1
            if orders_to_cancel or orders_to_place:
                self.stats['incremental_updates'] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"{self.symbol_name}增量订单更新失败: {e}")
            return False

    def get_performance_stats(self) -> dict:
        """
        获取性能统计信息
        
        Returns:
            性能统计字典
        """
        total_updates = self.stats['total_updates']
        if total_updates == 0:
            return self.stats
        
        return {
            **self.stats,
            'incremental_rate': self.stats['incremental_updates'] / total_updates,
            'efficiency_improvement': self.stats['orders_saved'] / max(1, total_updates * 2)
        }

    def reset_stats(self):
        """
        重置性能统计
        """
        self.stats = {
            'total_updates': 0,
            'incremental_updates': 0,
            'full_updates': 0,
            'orders_saved': 0
        }
        logger.info(f"{self.symbol_name}性能统计已重置")