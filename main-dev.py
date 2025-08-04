#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发测试脚本 - 用于测试订单成交检测机制的改进
"""

import ccxt
import ccxt.pro
import asyncio
import core.tradeManager
import core.websocketManager
from util.sLogger import logger
import os
from dotenv import load_dotenv
import time

load_dotenv()

# 使用生产环境进行测试
apiKey = os.getenv("prod_apiKey")
secret = os.getenv("prod_secret")
password = os.getenv("prod_password")

# 测试交易对（必须使用SBTC/SUSDT:SUSDT）
TEST_SYMBOL = "SBTC/SUSDT:SUSDT"

async def test_order_fill_detection():
    """
    测试订单成交检测机制
    """
    logger.info("开始测试订单成交检测机制")
    
    # 创建交易所连接
    exchange = ccxt.pro.bitget({
        'apiKey': apiKey,
        'secret': secret,
        'password': password,
        'options': {
            'defaultType': 'swap',
        },
        'sandbox': False
    })
    
    try:
        # 设置持仓模式和杠杆
        await exchange.set_position_mode(True, TEST_SYMBOL, {'productType': 'USDT-FUTURES'})
        await exchange.set_leverage(1, TEST_SYMBOL, {'productType': 'USDT-FUTURES'})
        
        # 创建交易管理器
        tm = core.tradeManager.TradeManager(
            symbolName=TEST_SYMBOL,
            wsExchange=exchange,
            baseSpread=0.01,  # 使用较大的价差进行测试
            minSpread=0.008,
            maxSpread=0.02,
            orderCoolDown=1.0,
            coin='SUSDT'
        )
        
        await tm.initSymbolInfo()
        
        # 创建websocket管理器
        wm = core.websocketManager.WebSocketManager(
            symbolName=TEST_SYMBOL,
            wsExchange=exchange,
            tradeManage=tm
        )
        
        await tm.bindWebsocketManager(wm)
        
        logger.info("测试环境初始化完成")
        
        # 测试1: 正常下单和监听
        logger.info("\n=== 测试1: 正常下单和监听 ===")
        await tm.runTrade()
        
        # 等待一段时间观察
        await asyncio.sleep(10)
        
        # 检查当前订单状态
        allOrders = await exchange.fetchOpenOrders(TEST_SYMBOL)
        logger.info(f"当前未成交订单数量: {len(allOrders)}")
        
        # 测试2: 主动检查机制
        logger.info("\n=== 测试2: 主动检查机制 ===")
        if wm.inWatchOpenOrder:
            filled_orders = await wm._activeCheckOrderStatus()
            logger.info(f"主动检查结果: {len(filled_orders)}个已成交订单")
        
        # 测试3: 自动恢复机制
        logger.info("\n=== 测试3: 自动恢复机制 ===")
        await tm.checkAndRecoverTrading()
        
        # 测试4: 模拟长时间无订单情况
        logger.info("\n=== 测试4: 模拟长时间无订单情况 ===")
        
        # 取消所有订单
        await tm.cancelAllOrder()
        await asyncio.sleep(2)
        
        # 停止订单监听
        if wm.inWatchOpenOrder:
            wm.inWatchOpenOrder = False
            wm.openOrders = []
            logger.info("已停止订单监听")
        
        # 设置较短的超时时间进行测试
        original_timeout = tm.noOrderTimeout
        tm.noOrderTimeout = 5.0  # 5秒超时
        tm.lastTradeTime = time.time() - 10  # 模拟10秒前的交易时间
        
        logger.info("等待自动恢复机制触发...")
        await asyncio.sleep(2)
        
        # 触发检查
        await tm.checkAndRecoverTrading()
        
        # 恢复原始超时时间
        tm.noOrderTimeout = original_timeout
        
        # 等待观察结果
        await asyncio.sleep(5)
        
        # 最终状态检查
        final_orders = await exchange.fetchOpenOrders(TEST_SYMBOL)
        logger.info(f"测试结束，最终未成交订单数量: {len(final_orders)}")
        
        logger.info("\n=== 测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        # 清理资源
        try:
            await tm.cancelAllOrder()
            await exchange.close()
            logger.info("测试资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时发生错误: {e}")

async def main():
    """
    主测试函数
    """
    logger.info("开始订单成交检测机制测试")
    
    # 运行测试
    await test_order_fill_detection()
    
    logger.info("所有测试完成")

if __name__ == "__main__":
    asyncio.run(main())
