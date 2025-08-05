import asyncio
import time
from typing import List, Optional
from util.sLogger import logger
import ccxt.pro
from config.config import get_volatility_config


class VolatilityManager:
    """
    波动率管理器
    负责监听K线数据，计算ATR(10)波动率，并自动调节TradeManager的价差参数
    """
    
    def __init__(self, symbolName: str, wsExchange: ccxt.pro.Exchange, tradeManager=None):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        self.tradeManager = tradeManager
        self.run = True
        
        # 获取配置
        self.config = get_volatility_config()
        
        # ATR计算相关
        self.atr_period = self.config.ATR_PERIOD  # ATR周期
        self.kline_data: List[List[float]] = []  # 存储K线数据 [timestamp, open, high, low, close, volume]
        self.atr_values: List[float] = []  # 存储ATR值
        self.current_volatility = 0.0  # 当前波动率
        
        # 波动率更新相关
        self.last_update_time = 0
        self.update_interval = self.config.UPDATE_INTERVAL  # 更新间隔（秒）
        
        logger.info(f"{self.symbolName}波动率管理器初始化完成")
    
    def bind_trade_manager(self, trade_manager):
        """绑定TradeManager实例"""
        self.tradeManager = trade_manager
        logger.info(f"{self.symbolName}波动率管理器已绑定TradeManager")
    
    def calculate_true_range(self, high: float, low: float, prev_close: float) -> float:
        """
        计算真实波幅(True Range)
        TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        """
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        return max(tr1, tr2, tr3)
    
    def calculate_atr(self, true_ranges: List[float], period: int = None) -> float:
        """
        计算平均真实波幅(ATR)
        
        Args:
            true_ranges: 真实波幅列表
            period: 计算周期，默认使用配置中的ATR_PERIOD
            
        Returns:
            ATR值
        """
        if period is None:
            period = self.config.ATR_PERIOD
            
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
        
        return sum(true_ranges[-period:]) / period
    
    def calculate_volatility(self, atr: float, current_price: float) -> float:
        """
        计算波动率
        波动率 = ATR / 当前价格
        """
        if current_price <= 0:
            return 0.0
        return atr / current_price
    
    def update_kline_data(self, kline: List[float]):
        """
        更新K线数据并计算波动率
        
        Args:
            kline: K线数据 [timestamp, open, high, low, close, volume]
        """
        try:
            self.kline_data.append(kline)
            
            # 保持最多配置数量的K线数据
            if len(self.kline_data) > self.config.MAX_KLINE_CACHE:
                self.kline_data.pop(0)
            
            # 至少需要配置数量的K线才开始计算波动率
            if len(self.kline_data) >= self.config.MIN_KLINE_COUNT:
                self._calculate_and_update_volatility()
                
        except Exception as e:
            logger.error(f"{self.symbolName}更新K线数据时发生错误: {e}")
    
    def _calculate_and_update_volatility(self):
        """
        计算并更新波动率
        """
        try:
            # 计算真实波幅
            true_ranges = []
            for i in range(1, len(self.kline_data)):
                current = self.kline_data[i]
                previous = self.kline_data[i-1]
                
                high = current[2]  # 最高价
                low = current[3]   # 最低价
                prev_close = previous[4]  # 前一根K线收盘价
                
                tr = self.calculate_true_range(high, low, prev_close)
                true_ranges.append(tr)
            
            # 计算ATR
            if len(true_ranges) >= self.atr_period:
                atr = self.calculate_atr(true_ranges, self.atr_period)
                self.atr_values.append(atr)
                
                # 保持最多20个ATR值
                if len(self.atr_values) > 20:
                    self.atr_values.pop(0)
                
                # 计算波动率
                current_price = self.kline_data[-1][4]  # 最新收盘价
                new_volatility = self.calculate_volatility(atr, current_price)
                
                # 应用波动率平滑（如果启用）
                if self.config.VOLATILITY_SMOOTHING and self.current_volatility > 0:
                    # 使用指数移动平均进行平滑
                    smoothing_factor = self.config.SMOOTHING_FACTOR
                    self.current_volatility = (smoothing_factor * new_volatility + 
                                             (1 - smoothing_factor) * self.current_volatility)
                else:
                    # 直接使用新计算的波动率
                    self.current_volatility = new_volatility
                
                logger.info(f"{self.symbolName}波动率更新: ATR={atr:.6f}, 当前价格={current_price:.2f}, 波动率={self.current_volatility:.6f}")
                
                # 更新TradeManager的价差参数
                if self.tradeManager:
                    self._update_trade_manager_spreads(self.current_volatility)
                    
        except Exception as e:
            logger.error(f"{self.symbolName}计算波动率时发生错误: {e}")
    
    def _update_trade_manager_spreads(self, volatility: float):
        """
        根据波动率更新TradeManager的价差参数
        使用配置中的倍数参数
        """
        try:
            # 计算新的价差参数（需要除以2，因为TradeManager内部会除以2）
            new_min_spread = volatility * self.config.MIN_SPREAD_MULTIPLIER * 2
            new_base_spread = volatility * self.config.BASE_SPREAD_MULTIPLIER * 2
            new_max_spread = volatility * self.config.MAX_SPREAD_MULTIPLIER * 2
            
            # 使用配置中的价差限制
            min_allowed = self.config.MIN_ALLOWED_SPREAD
            max_allowed = self.config.MAX_ALLOWED_SPREAD
            
            new_min_spread = max(min_allowed, min(max_allowed, new_min_spread))
            new_base_spread = max(new_min_spread, min(max_allowed, new_base_spread))
            new_max_spread = max(new_base_spread, min(max_allowed, new_max_spread))
            
            # 更新TradeManager的价差参数
            old_min = self.tradeManager.minSpread * 2  # 恢复原始值用于日志
            old_base = self.tradeManager.baseSpread * 2
            old_max = self.tradeManager.maxSpread * 2
            
            self.tradeManager.minSpread = new_min_spread / 2
            self.tradeManager.baseSpread = new_base_spread / 2
            self.tradeManager.maxSpread = new_max_spread / 2
            
            logger.info(f"{self.symbolName}价差参数已更新:")
            logger.info(f"  minSpread: {old_min:.6f} -> {new_min_spread:.6f}")
            logger.info(f"  baseSpread: {old_base:.6f} -> {new_base_spread:.6f}")
            logger.info(f"  maxSpread: {old_max:.6f} -> {new_max_spread:.6f}")
            
        except Exception as e:
            logger.error(f"{self.symbolName}更新TradeManager价差参数时发生错误: {e}")
    
    async def watch_kline(self):
        """
        监听K线数据
        使用配置中的时间框架
        """
        logger.info(f"{self.symbolName}波动率监控模块启动，开始监听{self.config.KLINE_TIMEFRAME}K线数据")
        
        # 首先获取历史K线数据用于初始化
        try:
            logger.info(f"{self.symbolName}获取历史K线数据进行初始化...")
            historical_data = await self.wsExchange.fetch_ohlcv(
                symbol=self.symbolName,
                timeframe=self.config.KLINE_TIMEFRAME,
                limit=20  # 获取20根K线用于初始化
            )
            
            for kline in historical_data:
                self.update_kline_data(kline)
            
            logger.info(f"{self.symbolName}历史K线数据初始化完成，共{len(historical_data)}根K线")
            
        except Exception as e:
            logger.error(f"{self.symbolName}获取历史K线数据失败: {e}")
        
        # 开始监听实时K线数据
        while self.run:
            try:
                # 使用websocket监听K线数据
                ohlcv_data = await self.wsExchange.watch_ohlcv(self.symbolName, self.config.KLINE_TIMEFRAME)
                
                if ohlcv_data:
                    # 获取最新的K线数据
                    latest_kline = ohlcv_data[-1]
                    
                    # 检查是否是新的K线（避免重复处理同一根K线）
                    if not self.kline_data or latest_kline[0] != self.kline_data[-1][0]:
                        self.update_kline_data(latest_kline)
                        logger.debug(f"{self.symbolName}收到新K线数据: {latest_kline}")
                
            except ccxt.NetworkError as e:
                logger.error(f"{self.symbolName}K线数据获取网络错误: {e}")
                await asyncio.sleep(5)  # 网络错误时等待5秒重试
            except ccxt.ExchangeError as e:
                logger.error(f"{self.symbolName}K线数据获取交易所错误: {e}")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                logger.info(f"{self.symbolName}K线数据监听任务已取消")
                self.run = False
                break
            except Exception as e:
                logger.error(f"{self.symbolName}K线数据监听未知错误: {e}")
                await asyncio.sleep(5)
    
    def get_volatility_info(self) -> dict:
        """
        获取当前波动率信息
        """
        return {
            'current_volatility': self.current_volatility,
            'atr_values': self.atr_values[-5:] if self.atr_values else [],  # 最近5个ATR值
            'kline_count': len(self.kline_data),
            'last_update_time': self.last_update_time
        }
    
    def stop(self):
        """
        停止波动率监控
        """
        self.run = False
        logger.info(f"{self.symbolName}波动率管理器已停止")