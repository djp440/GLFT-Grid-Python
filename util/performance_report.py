#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控报告工具
用于生成和显示系统性能报告
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from util.performanceMonitor import get_performance_monitor
from util.sLogger import logger


class PerformanceReporter:
    """性能报告生成器"""
    
    def __init__(self):
        self.monitor = get_performance_monitor()
    
    def generate_summary_report(self) -> Dict:
        """生成性能摘要报告"""
        stats = self.monitor.get_stats()
        
        report = {
            "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "监控时长": f"{(time.time() - self.monitor.start_time) / 3600:.2f}小时",
            "性能指标": {}
        }
        
        for metric_type, data in stats.items():
            if data["count"] > 0:
                report["性能指标"][metric_type] = {
                    "总次数": data["count"],
                    "成功次数": data["success_count"],
                    "失败次数": data["failure_count"],
                    "成功率": f"{data['success_rate']:.2f}%",
                    "平均延迟": f"{data['avg_latency']:.2f}ms",
                    "最小延迟": f"{data['min_latency']:.2f}ms",
                    "最大延迟": f"{data['max_latency']:.2f}ms",
                    "P95延迟": f"{data['p95_latency']:.2f}ms",
                    "P99延迟": f"{data['p99_latency']:.2f}ms"
                }
        
        return report
    
    def print_summary_report(self):
        """打印性能摘要报告"""
        report = self.generate_summary_report()
        
        print("\n" + "="*60)
        print("📊 系统性能监控报告")
        print("="*60)
        print(f"生成时间: {report['生成时间']}")
        print(f"监控时长: {report['监控时长']}")
        print()
        
        if not report["性能指标"]:
            print("暂无性能数据")
            return
        
        for metric_type, data in report["性能指标"].items():
            print(f"📈 {metric_type.upper()}性能指标:")
            print(f"  总次数: {data['总次数']}")
            print(f"  成功率: {data['成功率']}")
            print(f"  平均延迟: {data['平均延迟']}")
            print(f"  延迟范围: {data['最小延迟']} ~ {data['最大延迟']}")
            print(f"  P95延迟: {data['P95延迟']}")
            print(f"  P99延迟: {data['P99延迟']}")
            
            # 性能评级
            avg_latency = float(data['平均延迟'].replace('ms', ''))
            if avg_latency < 100:
                grade = "🟢 优秀"
            elif avg_latency < 500:
                grade = "🟡 良好"
            elif avg_latency < 1000:
                grade = "🟠 一般"
            else:
                grade = "🔴 需要优化"
            
            print(f"  性能评级: {grade}")
            print()
    
    def save_report_to_file(self, filename: Optional[str] = None):
        """保存报告到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
        
        report = self.generate_summary_report()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"📄 报告已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
    
    def get_recent_latencies(self, metric_type: str, minutes: int = 10) -> List[float]:
        """获取最近N分钟的延迟数据"""
        cutoff_time = time.time() - (minutes * 60)
        recent_latencies = []
        
        if metric_type in self.monitor.latencies:
            for latency, timestamp in self.monitor.latencies[metric_type]:
                if timestamp >= cutoff_time:
                    recent_latencies.append(latency)
        
        return recent_latencies
    
    def check_performance_alerts(self) -> List[str]:
        """检查性能告警"""
        alerts = []
        stats = self.monitor.get_stats()
        
        for metric_type, data in stats.items():
            if data["count"] > 0:
                # 检查平均延迟
                if data["avg_latency"] > 1000:
                    alerts.append(f"⚠️ {metric_type}平均延迟过高: {data['avg_latency']:.2f}ms")
                
                # 检查成功率
                if data["success_rate"] < 95:
                    alerts.append(f"⚠️ {metric_type}成功率过低: {data['success_rate']:.2f}%")
                
                # 检查P99延迟
                if data["p99_latency"] > 2000:
                    alerts.append(f"⚠️ {metric_type} P99延迟过高: {data['p99_latency']:.2f}ms")
        
        return alerts


def main():
    """主函数 - 生成性能报告"""
    reporter = PerformanceReporter()
    
    # 打印摘要报告
    reporter.print_summary_report()
    
    # 检查告警
    alerts = reporter.check_performance_alerts()
    if alerts:
        print("🚨 性能告警:")
        for alert in alerts:
            print(f"  {alert}")
        print()
    
    # 保存报告
    reporter.save_report_to_file()


if __name__ == "__main__":
    main()