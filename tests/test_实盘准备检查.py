#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘准备检查测试脚本
验证程序的关键功能是否正常工作
"""

import asyncio
import os
import sys
import json
from decimal import Decimal
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util.sLogger import logger
from util import tradeUtil
from core.tradeManager import TradeManager
import ccxt
import ccxt.pro

class RealTradingReadinessTest:
    """实盘交易准备检查测试类"""
    
    def __init__(self):
        self.test_results = []
        self.exchange = None
        self.trade_manager = None
    
    def log_test(self, test_name, passed, message=""):
        """记录测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append((test_name, passed, message))
    
    def test_environment_config(self):
        """测试环境配置"""
        print("\n=== 环境配置测试 ===")
        
        # 测试.env文件存在
        env_exists = os.path.exists('.env')
        self.log_test("环境配置文件存在", env_exists)
        
        if not env_exists:
            return False
        
        # 加载环境变量
        load_dotenv()
        
        # 测试基础环境变量
        sandbox = os.getenv("sandbox")
        sandbox_present = sandbox is not None
        self.log_test("环境变量 sandbox", sandbox_present)
        
        # 根据sandbox参数检查相应的API配置
        all_vars_present = sandbox_present
        
        if sandbox == "False":
            # 实盘模式，检查实盘API配置
            required_vars = ['prod_apiKey', 'prod_secret', 'prod_password']
            self.log_test("检测到实盘模式", True, "将检查实盘API配置")
        else:
            # 沙盒模式，检查沙盒API配置
            required_vars = ['apiKey', 'secret', 'password']
            self.log_test("检测到沙盒模式", True, "将检查沙盒API配置")
        
        for var in required_vars:
            value = os.getenv(var)
            var_present = value is not None and value != ""
            self.log_test(f"环境变量 {var}", var_present)
            if not var_present:
                all_vars_present = False
        
        # 测试沙盒模式设置
        is_sandbox = sandbox == "True"
        self.log_test("沙盒模式状态", True, f"当前值: {sandbox}, 是否沙盒: {is_sandbox}")
        
        return all_vars_present
    
    def test_config_file(self):
        """测试配置文件"""
        print("\n=== 配置文件测试 ===")
        
        # 测试配置文件存在
        config_exists = os.path.exists('config/symbols.json')
        self.log_test("交易对配置文件存在", config_exists)
        
        if not config_exists:
            return False
        
        try:
            with open('config/symbols.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.log_test("配置文件格式正确", True)
            
            # 检查是否有启用的交易对
            enabled_symbols = [s for s in config['symbols'] if s['enabled']]
            has_enabled = len(enabled_symbols) > 0
            self.log_test("存在启用的交易对", has_enabled, f"数量: {len(enabled_symbols)}")
            
            # 检查风险参数合理性
            for symbol in enabled_symbols:
                symbol_name = symbol['symbol']
                
                # 检查最大持仓比例
                max_stock = symbol.get('maxStockRadio', 0)
                reasonable_stock = 0 < max_stock <= 0.5
                self.log_test(f"{symbol_name} 持仓比例合理", reasonable_stock, 
                            f"{max_stock*100:.1f}%")
                
                # 检查订单金额比例
                order_ratio = symbol.get('orderAmountRatio', 0)
                reasonable_order = 0 < order_ratio <= 0.1
                self.log_test(f"{symbol_name} 订单比例合理", reasonable_order, 
                            f"{order_ratio*100:.1f}%")
                
                # 检查价差设置
                base_spread = symbol.get('baseSpread', 0)
                min_spread = symbol.get('minSpread', 0)
                max_spread = symbol.get('maxSpread', 0)
                
                spread_valid = (0 < min_spread <= base_spread <= max_spread <= 0.02)
                self.log_test(f"{symbol_name} 价差设置合理", spread_valid, 
                            f"min:{min_spread*100:.2f}% base:{base_spread*100:.2f}% max:{max_spread*100:.2f}%")
            
            return has_enabled
            
        except Exception as e:
            self.log_test("配置文件解析", False, str(e))
            return False
    
    async def test_exchange_connection(self):
        """测试交易所连接"""
        print("\n=== 交易所连接测试 ===")
        
        try:
            load_dotenv()
            
            # 根据sandbox参数选择API配置
            sandbox = os.getenv('sandbox')
            if sandbox == "False":
                # 实盘模式
                api_key = os.getenv('prod_apiKey')
                secret = os.getenv('prod_secret')
                password = os.getenv('prod_password')
                is_sandbox = False
                self.log_test("使用实盘API配置", True)
            else:
                # 沙盒模式
                api_key = os.getenv('apiKey')
                secret = os.getenv('secret')
                password = os.getenv('password')
                is_sandbox = True
                self.log_test("使用沙盒API配置", True)
            
            # 创建交易所实例
            self.exchange = ccxt.pro.bitget({
                'apiKey': api_key,
                'secret': secret,
                'password': password,
                'options': {
                    'defaultType': 'swap',
                },
                'sandbox': is_sandbox
            })
            
            self.log_test("交易所实例创建", True)
            
            # 测试API连接
            try:
                balance = await self.exchange.fetchBalance()
                self.log_test("API连接正常", True, f"USDT余额: {balance['USDT']['free']:.2f}")
                
                # 测试市场数据获取
                ticker = await self.exchange.fetchTicker('BTC/USDT:USDT')
                self.log_test("市场数据获取", True, f"BTC价格: ${ticker['last']:.2f}")
                
                return True
                
            except Exception as e:
                self.log_test("API连接", False, str(e))
                return False
                
        except Exception as e:
            self.log_test("交易所实例创建", False, str(e))
            return False
    
    async def test_trade_manager(self):
        """测试交易管理器"""
        print("\n=== 交易管理器测试 ===")
        
        if not self.exchange:
            self.log_test("交易管理器测试", False, "交易所连接失败")
            return False
        
        try:
            # 创建交易管理器实例
            self.trade_manager = TradeManager(
                'BTC/USDT:USDT',
                self.exchange,
                baseSpread=0.002,
                minSpread=0.001,
                maxSpread=0.005,
                orderCoolDown=0.5,
                maxStockRadio=0.25,
                orderAmountRatio=0.02
            )
            
            self.log_test("交易管理器创建", True)
            
            # 测试初始化
            await self.trade_manager.initSymbolInfo()
            self.log_test("交易管理器初始化", True)
            
            # 测试价格计算
            buy_price, sell_price = await self.trade_manager.calculateOrderPrice()
            price_valid = buy_price > 0 and sell_price > 0 and sell_price > buy_price
            self.log_test("价格计算正确", price_valid, 
                        f"买价: ${buy_price:.2f}, 卖价: ${sell_price:.2f}")
            
            # 测试除零错误防护
            original_balance = self.trade_manager.balance
            original_equity = self.trade_manager.equity
            
            # 模拟零余额情况
            await self.trade_manager.updateBalance(0, 0)
            await self.trade_manager.updateOrderAmount()
            
            zero_protection = self.trade_manager.orderAmount >= self.trade_manager.minOrderAmount
            self.log_test("除零错误防护", zero_protection, 
                        f"最小订单量: {self.trade_manager.minOrderAmount}")
            
            # 恢复原始值
            await self.trade_manager.updateBalance(original_balance, original_equity)
            
            return True
            
        except Exception as e:
            self.log_test("交易管理器测试", False, str(e))
            return False
    
    async def test_utility_functions(self):
        """测试工具函数"""
        print("\n=== 工具函数测试 ===")
        
        # 测试订单过滤函数
        test_orders = [
            {'symbol': 'BTC/USDT:USDT', 'status': 'open', 'id': '1'},
            {'symbol': 'ETH/USDT:USDT', 'status': 'open', 'id': '2'},
            {'symbol': 'BTC/USDT:USDT', 'status': 'closed', 'id': '3'}
        ]
        
        try:
            filtered = await tradeUtil.openOrderFilter(test_orders, 'BTC/USDT:USDT')
            filter_result = len(filtered) == 1 and filtered[0]['id'] == '1'
            self.log_test("订单过滤函数", filter_result)
        except Exception as e:
            self.log_test("订单过滤函数", False, str(e))
        
        # 测试持仓保证金计算
        test_positions = [
            {'symbol': 'BTC/USDT:USDT', 'info': {'marginSize': '100.5'}},
            {'symbol': 'ETH/USDT:USDT', 'info': {'marginSize': '50.0'}}
        ]
        
        try:
            margin = await tradeUtil.positionMarginSize(test_positions, 'BTC/USDT:USDT')
            margin_result = margin == 100.5
            self.log_test("保证金计算函数", margin_result)
        except Exception as e:
            self.log_test("保证金计算函数", False, str(e))
        
        # 测试订单检查函数
        test_open_orders = [
            {'info': {'side': 'buy'}},
            {'info': {'side': 'sell'}}
        ]
        
        try:
            check_result = await tradeUtil.checkOpenOrder(test_open_orders)
            self.log_test("订单检查函数", check_result)
        except Exception as e:
            self.log_test("订单检查函数", False, str(e))
    
    def test_decimal_precision(self):
        """测试精度计算"""
        print("\n=== 精度计算测试 ===")
        
        # 测试价格精度计算
        test_cases = [
            (0.01, 2),
            (0.001, 3),
            (0.0001, 4),
            (1.0, 0)
        ]
        
        all_passed = True
        for price_precision, expected in test_cases:
            calculated = abs(Decimal(str(price_precision)).as_tuple().exponent)
            passed = calculated == expected
            self.log_test(f"精度计算 {price_precision}", passed, 
                        f"期望: {expected}, 实际: {calculated}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    async def cleanup(self):
        """清理资源"""
        if self.exchange:
            try:
                await self.exchange.close()
                self.log_test("资源清理", True)
            except Exception as e:
                self.log_test("资源清理", False, str(e))
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed, _ in self.test_results if passed)
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"通过率: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for test_name, passed, message in self.test_results:
                if not passed:
                    print(f"  - {test_name}: {message}")
        
        # 给出建议
        print("\n💡 建议:")
        if failed_tests == 0:
            print("  ✅ 所有测试通过，程序已准备好进行实盘测试")
            print("  ⚠️  请确保在小额资金下先进行测试")
        else:
            print("  ❌ 存在失败的测试，请修复后再进行实盘测试")
            print("  🔧 检查配置文件和环境变量设置")

async def main():
    """主测试函数"""
    print("🧪 GLFT网格交易程序 - 实盘准备检查")
    print("=" * 60)
    
    tester = RealTradingReadinessTest()
    
    try:
        # 运行所有测试
        tester.test_environment_config()
        tester.test_config_file()
        await tester.test_exchange_connection()
        await tester.test_trade_manager()
        await tester.test_utility_functions()
        tester.test_decimal_precision()
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        logger.error(f"测试过程中发生错误: {e}")
    
    finally:
        await tester.cleanup()
        tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main())