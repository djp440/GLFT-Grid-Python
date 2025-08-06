#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
固定价差模式测试脚本
用于验证在fixed模式下波动率管理器不会更新价差参数
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import get_trade_config, get_volatility_config
from core.volatilityManager import VolatilityManager
from util.sLogger import logger

class MockTradeManager:
    """模拟TradeManager用于测试"""
    def __init__(self):
        self.symbolName = "TEST/USDT:USDT"
        self.minSpread = 0.0005
        self.baseSpread = 0.001
        self.maxSpread = 0.004
        
    def log_spreads(self, prefix=""):
        """记录当前价差参数"""
        logger.info(f"{prefix}当前价差参数:")
        logger.info(f"  minSpread: {self.minSpread:.6f}")
        logger.info(f"  baseSpread: {self.baseSpread:.6f}")
        logger.info(f"  maxSpread: {self.maxSpread:.6f}")

def test_fixed_spread_mode():
    """测试固定价差模式"""
    logger.info("=== 开始测试固定价差模式 ===")
    
    # 检查当前配置
    trade_config = get_trade_config()
    spread_mode = getattr(trade_config, 'SPREAD_MODE', 'fixed')
    logger.info(f"当前价差模式: {spread_mode}")
    
    if spread_mode != 'fixed':
        logger.warning("当前不是固定价差模式，请修改config.py中的SPREAD_MODE为'fixed'")
        return False
    
    # 创建模拟TradeManager
    mock_trade_manager = MockTradeManager()
    mock_trade_manager.log_spreads("初始")
    
    # 创建波动率管理器
    volatility_manager = VolatilityManager(
        symbolName="TEST/USDT:USDT",
        wsExchange=None,  # 测试时不需要真实的交易所连接
        tradeManager=mock_trade_manager
    )
    
    # 模拟波动率更新
    logger.info("\n模拟波动率更新...")
    test_volatility = 0.002  # 2%的波动率
    
    # 调用价差更新方法
    volatility_manager._update_trade_manager_spreads(test_volatility)
    
    # 检查价差是否保持不变
    mock_trade_manager.log_spreads("更新后")
    
    # 验证结果
    expected_min = 0.0005
    expected_base = 0.001
    expected_max = 0.004
    
    success = (
        abs(mock_trade_manager.minSpread - expected_min) < 1e-6 and
        abs(mock_trade_manager.baseSpread - expected_base) < 1e-6 and
        abs(mock_trade_manager.maxSpread - expected_max) < 1e-6
    )
    
    if success:
        logger.info("\n✅ 测试通过：固定价差模式下价差参数保持不变")
    else:
        logger.error("\n❌ 测试失败：固定价差模式下价差参数发生了变化")
    
    return success

def test_dynamic_spread_mode():
    """测试动态价差模式（需要手动修改配置）"""
    logger.info("\n=== 测试动态价差模式提示 ===")
    logger.info("要测试动态价差模式，请：")
    logger.info("1. 修改config.py中的SPREAD_MODE为'dynamic'")
    logger.info("2. 重新运行此测试脚本")
    logger.info("3. 观察价差参数是否会根据波动率更新")

if __name__ == "__main__":
    try:
        # 测试固定价差模式
        success = test_fixed_spread_mode()
        
        # 提示动态模式测试
        test_dynamic_spread_mode()
        
        if success:
            logger.info("\n🎉 所有测试完成，固定价差模式工作正常！")
        else:
            logger.error("\n⚠️ 测试发现问题，请检查代码修改")
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()