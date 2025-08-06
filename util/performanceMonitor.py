#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具
用于实时监控订单延迟和系统性能指标
"""

import time
import asyncio
from collections import deque
from typing import Dict, List, Optional
import statistics
from util.sLogger import logger


class PerformanceMonitor:
    """
    性能监控器
    监控订单延迟、网络请求时间等关键性能指标
    """
    
    def __init__(self, max_samples=1000):
        self.max_samples = max_samples
        
        # 延迟数据存储
        self.order_latencies = deque(maxlen=max_samples)  # 订单延迟
        self.network_latencies = deque(maxlen=max_samples)  # 网络延迟
        self.processing_times = deque(maxlen=max_samples)  # 处理时间
        
        # 计数器
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        
        # 时间戳记录
        self.start_time = time.time()
        self.last_report_time = time.time()
        
        # 性能阈值
        self.latency_warning_threshold = 200.0  # 200ms
        self.latency_critical_threshold = 500.0  # 500ms
        
    def record_order_latency(self, latency_ms: float, success: bool = True):
        """
        记录订单延迟
        
        Args:
            latency_ms: 延迟时间（毫秒）
            success: 是否成功
        """
        self.order_latencies.append(latency_ms)
        self.total_orders += 1
        
        if success:
            self.successful_orders += 1
        else:
            self.failed_orders += 1
            
        # 检查是否超过阈值
        if latency_ms > self.latency_critical_threshold:
            logger.warning(f"订单延迟过高: {latency_ms:.2f}ms (临界阈值: {self.latency_critical_threshold}ms)")
        elif latency_ms > self.latency_warning_threshold:
            logger.info(f"订单延迟警告: {latency_ms:.2f}ms (警告阈值: {self.latency_warning_threshold}ms)")
            
    def record_network_latency(self, latency_ms: float):
        """
        记录网络延迟
        
        Args:
            latency_ms: 网络延迟时间（毫秒）
        """
        self.network_latencies.append(latency_ms)
        
    def record_processing_time(self, processing_ms: float):
        """
        记录处理时间
        
        Args:
            processing_ms: 处理时间（毫秒）
        """
        self.processing_times.append(processing_ms)
        
    def get_latency_stats(self, data: deque) -> Dict:
        """
        计算延迟统计信息
        
        Args:
            data: 延迟数据队列
            
        Returns:
            统计信息字典
        """
        if not data:
            return {
                'count': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0
            }
            
        data_list = list(data)
        sorted_data = sorted(data_list)
        
        return {
            'count': len(data_list),
            'avg': statistics.mean(data_list),
            'min': min(data_list),
            'max': max(data_list),
            'p50': sorted_data[len(sorted_data) // 2],
            'p95': sorted_data[int(len(sorted_data) * 0.95)],
            'p99': sorted_data[int(len(sorted_data) * 0.99)]
        }
        
    def get_performance_report(self) -> Dict:
        """
        获取性能报告
        
        Returns:
            性能报告字典
        """
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # 计算各项统计
        order_stats = self.get_latency_stats(self.order_latencies)
        network_stats = self.get_latency_stats(self.network_latencies)
        processing_stats = self.get_latency_stats(self.processing_times)
        
        # 计算成功率
        success_rate = (self.successful_orders / self.total_orders * 100) if self.total_orders > 0 else 0
        
        # 计算吞吐量（每分钟订单数）
        throughput = (self.total_orders / uptime * 60) if uptime > 0 else 0
        
        return {
            'uptime_seconds': uptime,
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': success_rate,
            'throughput_per_minute': throughput,
            'order_latency': order_stats,
            'network_latency': network_stats,
            'processing_time': processing_stats
        }
        
    def print_performance_report(self):
        """
        打印性能报告
        """
        report = self.get_performance_report()
        
        logger.info("\n" + "="*60)
        logger.info("性能监控报告")
        logger.info("="*60)
        logger.info(f"运行时间: {report['uptime_seconds']:.1f}秒")
        logger.info(f"总订单数: {report['total_orders']}")
        logger.info(f"成功订单: {report['successful_orders']}")
        logger.info(f"失败订单: {report['failed_orders']}")
        logger.info(f"成功率: {report['success_rate']:.1f}%")
        logger.info(f"吞吐量: {report['throughput_per_minute']:.1f} 订单/分钟")
        
        # 订单延迟统计
        order_stats = report['order_latency']
        if order_stats['count'] > 0:
            logger.info("\n订单延迟统计:")
            logger.info(f"  样本数: {order_stats['count']}")
            logger.info(f"  平均延迟: {order_stats['avg']:.2f}ms")
            logger.info(f"  最小延迟: {order_stats['min']:.2f}ms")
            logger.info(f"  最大延迟: {order_stats['max']:.2f}ms")
            logger.info(f"  P50延迟: {order_stats['p50']:.2f}ms")
            logger.info(f"  P95延迟: {order_stats['p95']:.2f}ms")
            logger.info(f"  P99延迟: {order_stats['p99']:.2f}ms")
            
        # 网络延迟统计
        network_stats = report['network_latency']
        if network_stats['count'] > 0:
            logger.info("\n网络延迟统计:")
            logger.info(f"  样本数: {network_stats['count']}")
            logger.info(f"  平均延迟: {network_stats['avg']:.2f}ms")
            logger.info(f"  P95延迟: {network_stats['p95']:.2f}ms")
            
        # 处理时间统计
        processing_stats = report['processing_time']
        if processing_stats['count'] > 0:
            logger.info("\n处理时间统计:")
            logger.info(f"  样本数: {processing_stats['count']}")
            logger.info(f"  平均时间: {processing_stats['avg']:.2f}ms")
            logger.info(f"  P95时间: {processing_stats['p95']:.2f}ms")
            
        logger.info("="*60)
        
    def should_report(self, interval_seconds: float = 300) -> bool:
        """
        检查是否应该生成报告
        
        Args:
            interval_seconds: 报告间隔（秒）
            
        Returns:
            是否应该报告
        """
        current_time = time.time()
        if current_time - self.last_report_time >= interval_seconds:
            self.last_report_time = current_time
            return True
        return False
        
    def get_health_status(self) -> str:
        """
        获取系统健康状态
        
        Returns:
            健康状态字符串
        """
        if not self.order_latencies:
            return "无数据"
            
        recent_latencies = list(self.order_latencies)[-10:]  # 最近10个样本
        avg_recent_latency = statistics.mean(recent_latencies)
        
        success_rate = (self.successful_orders / self.total_orders * 100) if self.total_orders > 0 else 0
        
        if avg_recent_latency > self.latency_critical_threshold or success_rate < 90:
            return "严重"
        elif avg_recent_latency > self.latency_warning_threshold or success_rate < 95:
            return "警告"
        else:
            return "健康"
            
    def reset_stats(self):
        """
        重置统计数据
        """
        self.order_latencies.clear()
        self.network_latencies.clear()
        self.processing_times.clear()
        
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        
        self.start_time = time.time()
        self.last_report_time = time.time()
        
        logger.info("性能监控统计数据已重置")


class LatencyTracker:
    """
    延迟跟踪器上下文管理器
    用于自动测量代码块的执行时间
    """
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str = "operation"):
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            elapsed_ms = (time.time() - self.start_time) * 1000
            
            if self.operation_name == "order":
                success = exc_type is None
                self.monitor.record_order_latency(elapsed_ms, success)
            elif self.operation_name == "network":
                self.monitor.record_network_latency(elapsed_ms)
            elif self.operation_name == "processing":
                self.monitor.record_processing_time(elapsed_ms)
                
            logger.debug(f"{self.operation_name}执行时间: {elapsed_ms:.2f}ms")


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """
    获取全局性能监控器实例
    
    Returns:
        性能监控器实例
    """
    return performance_monitor


async def start_performance_reporting(interval_seconds: float = 300):
    """
    启动定期性能报告
    
    Args:
        interval_seconds: 报告间隔（秒）
    """
    logger.info(f"启动性能监控，报告间隔: {interval_seconds}秒")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            if performance_monitor.total_orders > 0:
                performance_monitor.print_performance_report()
                
                # 检查健康状态
                health = performance_monitor.get_health_status()
                if health != "健康":
                    logger.warning(f"系统健康状态: {health}")
                    
        except asyncio.CancelledError:
            logger.info("性能监控报告任务已取消")
            break
        except Exception as e:
            logger.error(f"性能监控报告任务发生错误: {e}")
            await asyncio.sleep(10)  # 错误后等待10秒再继续


if __name__ == "__main__":
    # 测试代码
    import random
    
    monitor = PerformanceMonitor()
    
    # 模拟一些延迟数据
    for i in range(100):
        latency = random.uniform(50, 150)  # 50-150ms的随机延迟
        monitor.record_order_latency(latency, success=random.random() > 0.05)
        
    # 打印报告
    monitor.print_performance_report()
    
    # 测试延迟跟踪器
    with LatencyTracker(monitor, "order"):
        time.sleep(0.1)  # 模拟100ms的操作
        
    print(f"健康状态: {monitor.get_health_status()}")