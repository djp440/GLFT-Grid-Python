#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版交易管理器演示脚本

本脚本演示如何使用增强版交易管理器的各种功能
注意：这是一个演示脚本，请在沙盒环境中运行
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhancedTradeManager import EnhancedTradeManager
from config.config import GlobalConfig
from util.sLogger import logger
import ccxt.pro

# 加载环境变量
load_dotenv()

class EnhancedManagerDemo:
    """增强版交易管理器演示类"""
    
    def __init__(self):
        self.exchange = None
        self.manager = None
        
    async def setup_exchange(self):
        """设置交易所连接（沙盒环境）"""
        try:
            # 使用沙盒环境的API密钥
            api_key = os.getenv("apiKey")
            secret = os.getenv("secret")
            password = os.getenv("password")
            
            if not all([api_key, secret, password]):
                logger.error("请在 .env 文件中设置沙盒环境的API密钥")
                return False
                
            self.exchange = ccxt.pro.bitget({
                'apiKey': api_key,
                'secret': secret,
                'password': password,
                'options': {
                    'defaultType': 'swap',
                },
                'sandbox': True  # 使用沙盒环境
            })
            
            logger.info("交易所连接设置完成（沙盒环境）")
            return True
            
        except Exception as e:
            logger.error(f"设置交易所连接失败: {e}")
            return False
    
    async def create_enhanced_manager(self):
        """创建增强版交易管理器"""
        try:
            # 获取配置
            config = GlobalConfig()
            
            # 创建增强版交易管理器
            self.manager = EnhancedTradeManager(
                symbolName='BTC/USDT:USDT',
                wsExchange=self.exchange,
                baseSpread=0.001,
                minSpread=0.0008,
                maxSpread=0.003,
                orderCoolDown=0.1,
                maxStockRadio=0.25,
                orderAmountRatio=0.05,
                coin='USDT',
                direction='both'
            )
            
            logger.info("增强版交易管理器创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建增强版交易管理器失败: {e}")
            return False
    
    async def demo_basic_features(self):
        """演示基本功能"""
        logger.info("=== 演示基本功能 ===")
        
        try:
            # 初始化交易对信息
            await self.manager.initSymbolInfo()
            logger.info(f"交易对信息初始化完成: {self.manager.symbolName}")
            
            # 模拟设置一些基本数据
            await self.manager.updateBalance(1000.0, 1000.0)
            await self.manager.updateLastPrice(50000.0)
            
            logger.info(f"当前余额: {self.manager.balance} USDT")
            logger.info(f"当前价格: {self.manager.lastPrice} USDT")
            logger.info(f"基础价差: {self.manager.baseSpread * 2:.4f} ({self.manager.baseSpread * 2 * 100:.2f}%)")
            
        except Exception as e:
            logger.error(f"基本功能演示失败: {e}")
    
    async def demo_incremental_updates(self):
        """演示增量更新功能"""
        logger.info("=== 演示增量更新功能 ===")
        
        try:
            # 检查当前增量更新状态
            logger.info(f"增量更新状态: {'启用' if self.manager.use_incremental_updates else '禁用'}")
            
            # 切换增量更新模式
            if self.manager.use_incremental_updates:
                self.manager.disable_incremental_updates()
                logger.info("已禁用增量更新")
            else:
                self.manager.enable_incremental_updates()
                logger.info("已启用增量更新")
            
            # 再次检查状态
            logger.info(f"新的增量更新状态: {'启用' if self.manager.use_incremental_updates else '禁用'}")
            
        except Exception as e:
            logger.error(f"增量更新功能演示失败: {e}")
    
    async def demo_performance_monitoring(self):
        """演示性能监控功能"""
        logger.info("=== 演示性能监控功能 ===")
        
        try:
            # 获取性能统计（如果可用）
            if hasattr(self.manager, 'get_performance_stats'):
                stats = self.manager.get_performance_stats()
                logger.info("性能统计:")
                for key, value in stats.items():
                    logger.info(f"  {key}: {value}")
            else:
                logger.info("性能统计功能暂未实现")
            
            # 演示网格订单管理器功能（如果可用）
            if hasattr(self.manager, 'grid_manager') and self.manager.grid_manager:
                logger.info("网格订单管理器已初始化")
                logger.info(f"网格间隔: {self.manager.grid_manager.grid_spacing}")
                logger.info(f"价格精度: {self.manager.grid_manager.price_precision}")
            else:
                logger.info("网格订单管理器未初始化")
                
        except Exception as e:
            logger.error(f"性能监控功能演示失败: {e}")
    
    async def demo_configuration(self):
        """演示配置功能"""
        logger.info("=== 演示配置功能 ===")
        
        try:
            config = GlobalConfig()
            
            logger.info("当前配置:")
            logger.info(f"  使用增强版管理器: {config.TradeConfig.USE_ENHANCED_MANAGER}")
            logger.info(f"  启用增量更新: {config.TradeConfig.ENABLE_INCREMENTAL_UPDATE}")
            logger.info(f"  默认基础价差: {config.TradeConfig.DEFAULT_BASE_SPREAD}")
            logger.info(f"  默认订单冷却时间: {config.TradeConfig.DEFAULT_ORDER_COOL_DOWN}")
            
            # 网格配置
            grid_config = config.GridOrderConfig
            logger.info("网格订单配置:")
            logger.info(f"  默认价格精度: {grid_config.DEFAULT_TICK_SIZE}")
            logger.info(f"  默认网格间隔: {grid_config.DEFAULT_GRID_INTERVAL}")
            logger.info(f"  批量操作超时: {grid_config.BATCH_OPERATION_TIMEOUT}s")
            logger.info(f"  最大并发操作: {grid_config.MAX_CONCURRENT_OPERATIONS}")
            
        except Exception as e:
            logger.error(f"配置功能演示失败: {e}")
    
    async def run_demo(self):
        """运行完整演示"""
        logger.info("开始增强版交易管理器演示")
        logger.info("注意：这是一个演示脚本，运行在沙盒环境中")
        
        try:
            # 设置交易所连接
            if not await self.setup_exchange():
                return
            
            # 创建增强版交易管理器
            if not await self.create_enhanced_manager():
                return
            
            # 演示各种功能
            await self.demo_configuration()
            await self.demo_basic_features()
            await self.demo_incremental_updates()
            await self.demo_performance_monitoring()
            
            logger.info("演示完成！")
            
        except Exception as e:
            logger.error(f"演示过程中发生错误: {e}")
        finally:
            # 清理资源
            if self.exchange:
                await self.exchange.close()
                logger.info("交易所连接已关闭")

async def main():
    """主函数"""
    demo = EnhancedManagerDemo()
    await demo.run_demo()

if __name__ == "__main__":
    print("增强版交易管理器演示脚本")
    print("=" * 50)
    print("本脚本将演示增强版交易管理器的各种功能")
    print("请确保已在 .env 文件中配置沙盒环境的API密钥")
    print("=" * 50)
    print()
    
    # 运行演示
    asyncio.run(main())