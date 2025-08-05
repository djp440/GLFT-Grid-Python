import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from util.sLogger import logger
import threading

@dataclass
class TradeRecord:
    """交易记录数据结构"""
    timestamp: float
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    fee: float
    order_id: str

@dataclass
class AccountSnapshot:
    """账户快照数据结构"""
    timestamp: float
    usdt_equity: float
    total_fee: float
    total_volume: float
    equity_plus_half_fee: float

@dataclass
class PriceSnapshot:
    """价格快照数据结构"""
    timestamp: float
    symbol: str
    price: float

class DataRecorder:
    """实时数据记录器"""
    
    def __init__(self):
        self.trade_records: List[TradeRecord] = []
        self.account_snapshots: List[AccountSnapshot] = []
        self.price_snapshots: List[PriceSnapshot] = []  # 价格快照列表
        self.symbol_volumes: Dict[str, float] = {}  # 每个交易对的累计成交量
        self.symbol_fees: Dict[str, float] = {}     # 每个交易对的累计手续费
        self.symbol_initial_prices: Dict[str, float] = {}  # 每个交易对的初始价格
        self.total_volume: float = 0.0
        self.total_fee: float = 0.0
        self.current_equity: float = 0.0
        self.initial_equity: float = 0.0  # 初始权益
        self.lock = asyncio.Lock()
        self.running = True
        
        # 数据更新回调
        self.data_update_callbacks: List[callable] = []
        
        logger.info("数据记录器初始化完成")
    
    def add_data_update_callback(self, callback):
        """添加数据更新回调函数"""
        self.data_update_callbacks.append(callback)
    
    async def record_trade(self, symbol: str, side: str, amount: float, price: float, fee: float, order_id: str):
        """记录交易数据"""
        async with self.lock:
            timestamp = time.time()
            
            # 创建交易记录
            trade_record = TradeRecord(
                timestamp=timestamp,
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                fee=fee,
                order_id=order_id
            )
            
            self.trade_records.append(trade_record)
            
            # 更新累计数据
            if symbol not in self.symbol_volumes:
                self.symbol_volumes[symbol] = 0.0
                self.symbol_fees[symbol] = 0.0
            
            self.symbol_volumes[symbol] += amount
            self.symbol_fees[symbol] += fee
            self.total_volume += amount
            self.total_fee += fee
            
            logger.info(f"记录交易: {symbol} {side} {amount} @ {price}, 手续费: {fee}")
            
            # 触发数据更新回调
            await self._trigger_callbacks()
    
    async def record_price(self, symbol: str, price: float):
        """记录价格数据"""
        async with self.lock:
            # 记录初始价格（如果是第一次记录该交易对）
            if symbol not in self.symbol_initial_prices:
                self.symbol_initial_prices[symbol] = price
                logger.info(f"记录{symbol}初始价格: {price:.2f}")
            
            # 创建价格快照
            price_snapshot = PriceSnapshot(
                timestamp=time.time(),
                symbol=symbol,
                price=price
            )
            
            self.price_snapshots.append(price_snapshot)
            
            # 触发回调
            await self._trigger_callbacks()

    async def update_equity(self, equity: float):
        """更新账户权益"""
        async with self.lock:
            # 记录初始权益（如果是第一次更新）
            if self.initial_equity == 0.0:
                self.initial_equity = equity
                logger.info(f"记录初始权益: {equity:.2f} USDT")
            
            self.current_equity = equity
            
            # 创建账户快照
            timestamp = time.time()
            equity_plus_half_fee = equity + (self.total_fee * 0.5)
            
            snapshot = AccountSnapshot(
                timestamp=timestamp,
                usdt_equity=equity,
                total_fee=self.total_fee,
                total_volume=self.total_volume,
                equity_plus_half_fee=equity_plus_half_fee
            )
            
            self.account_snapshots.append(snapshot)
            
            # 限制历史数据长度，避免内存溢出
            if len(self.account_snapshots) > 10000:
                self.account_snapshots = self.account_snapshots[-5000:]
            
            if len(self.trade_records) > 10000:
                self.trade_records = self.trade_records[-5000:]
            
            # 触发数据更新回调
            await self._trigger_callbacks()
    
    async def _trigger_callbacks(self):
        """触发所有数据更新回调"""
        for callback in self.data_update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"数据更新回调执行失败: {e}")
    
    def get_account_data(self) -> Dict:
        """获取账户数据用于绘图"""
        if not self.account_snapshots:
            return {
                'timestamps': [],
                'equity': [],
                'total_fee': [],
                'equity_plus_half_fee': [],
                'total_volume': []
            }
        
        timestamps = [snapshot.timestamp for snapshot in self.account_snapshots]
        equity = [snapshot.usdt_equity for snapshot in self.account_snapshots]
        total_fee = [snapshot.total_fee for snapshot in self.account_snapshots]
        equity_plus_half_fee = [snapshot.equity_plus_half_fee for snapshot in self.account_snapshots]
        total_volume = [snapshot.total_volume for snapshot in self.account_snapshots]
        
        return {
            'timestamps': timestamps,
            'equity': equity,
            'total_fee': total_fee,
            'equity_plus_half_fee': equity_plus_half_fee,
            'total_volume': total_volume
        }
    
    def get_price_data(self) -> Dict:
        """获取价格数据用于绘图"""
        if not self.price_snapshots:
            return {
                'symbols': [],
                'timestamps': {},
                'prices': {},
                'price_changes_percent': {},
                'initial_prices': self.symbol_initial_prices.copy()
            }
        
        # 按交易对分组价格数据
        symbol_data = {}
        for snapshot in self.price_snapshots:
            if snapshot.symbol not in symbol_data:
                symbol_data[snapshot.symbol] = {
                    'timestamps': [],
                    'prices': []
                }
            symbol_data[snapshot.symbol]['timestamps'].append(snapshot.timestamp)
            symbol_data[snapshot.symbol]['prices'].append(snapshot.price)
        
        # 计算价格变化百分比
        price_changes_percent = {}
        for symbol, data in symbol_data.items():
            if symbol in self.symbol_initial_prices and self.symbol_initial_prices[symbol] > 0:
                initial_price = self.symbol_initial_prices[symbol]
                price_changes_percent[symbol] = [
                    ((price - initial_price) / initial_price) * 100 
                    for price in data['prices']
                ]
            else:
                price_changes_percent[symbol] = [0.0] * len(data['prices'])
        
        return {
            'symbols': list(symbol_data.keys()),
            'timestamps': {symbol: data['timestamps'] for symbol, data in symbol_data.items()},
            'prices': {symbol: data['prices'] for symbol, data in symbol_data.items()},
            'price_changes_percent': price_changes_percent,
            'initial_prices': self.symbol_initial_prices.copy()
        }

    def get_summary(self) -> Dict:
        """获取数据摘要"""
        return {
            'total_trades': len(self.trade_records),
            'total_volume': self.total_volume,
            'total_fee': self.total_fee,
            'current_equity': self.current_equity,
            'initial_equity': self.initial_equity,
            'symbol_volumes': self.symbol_volumes.copy(),
            'symbol_fees': self.symbol_fees.copy()
        }
    
    def reset_data(self):
        """重置所有数据"""
        self.trade_records.clear()
        self.account_snapshots.clear()
        self.symbol_volumes.clear()
        self.symbol_fees.clear()
        self.total_volume = 0.0
        self.total_fee = 0.0
        self.current_equity = 0.0
        logger.info("数据记录器数据已重置")
    
    def record_trade_sync(self, symbol: str, side: str, amount: float, price: float, fee: float, order_id: str = ""):
        """同步版本的交易记录方法（用于测试）"""
        trade_record = TradeRecord(
            timestamp=time.time(),
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            fee=fee,
            order_id=order_id or f"test_{len(self.trade_records)}"
        )
        
        self.trade_records.append(trade_record)
        
        # 更新统计数据
        volume = amount * price
        
        if symbol not in self.symbol_volumes:
            self.symbol_volumes[symbol] = 0.0
            self.symbol_fees[symbol] = 0.0
        
        self.symbol_volumes[symbol] += volume
        self.symbol_fees[symbol] += fee
        self.total_volume += volume
        self.total_fee += fee
        
        logger.info(f"记录交易: {symbol} {side} {amount} @ {price:.2f}, 手续费: {fee:.4f}")
    
    def update_equity_sync(self, equity: float):
        """同步版本的权益更新方法（用于测试）"""
        self.current_equity = equity
        
        # 创建账户快照
        snapshot = AccountSnapshot(
            timestamp=time.time(),
            usdt_equity=equity,
            total_fee=self.total_fee,
            total_volume=self.total_volume,
            equity_plus_half_fee=equity + (self.total_fee * 0.5)
        )
        
        self.account_snapshots.append(snapshot)
        logger.info(f"更新权益: {equity:.2f} USDT")
    
    def stop(self):
        """停止数据记录器"""
        self.running = False
        logger.info("数据记录器已停止")

# 全局数据记录器实例
data_recorder = DataRecorder()