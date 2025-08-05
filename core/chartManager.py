import matplotlib
matplotlib.use('Agg')  # 设置为非交互式后端
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import numpy as np
from datetime import datetime
import os
from typing import Dict, List
from core.dataRecorder import data_recorder
from util.sLogger import logger

class ChartManager:
    """静态图表生成器 - 在程序结束时生成综合图表"""
    
    def __init__(self):
        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        logger.info("静态图表生成器初始化完成")
    
    def generate_final_charts(self, output_dir="img"):
        """生成最终的综合图表"""
        try:
            # 创建输出目录
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"创建图表输出目录: {output_dir}")
            
            # 获取数据
            account_data = data_recorder.get_account_data()
            price_data = data_recorder.get_price_data()
            summary = data_recorder.get_summary()
            
            if not account_data['timestamps'] and not price_data['symbols']:
                 logger.warning("没有数据可用于生成图表")
                 return
            
            # 创建2x2的子图布局
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('GLFT网格交易运行报告', fontsize=16, fontweight='bold')
            
            # 生成各个图表
            self._plot_equity_chart(axes[0, 0], account_data, summary)
            self._plot_price_changes_chart(axes[0, 1], price_data)
            self._plot_combined_chart(axes[1, 0], account_data, price_data, summary)
            self._plot_volume_chart(axes[1, 1], summary)
            
            # 调整布局
            plt.tight_layout()
            
            # 保存图表
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(output_dir, f'trading_report_{timestamp}.png')
            fig.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            logger.info(f"交易报告图表已保存: {filename}")
            
        except Exception as e:
            logger.error(f"生成图表时出错: {e}")
    
    def start_charts(self):
        """兼容性方法 - 不再启动实时图表"""
        logger.info("实时图表功能已禁用，将在程序结束时生成静态图表")
    
    def stop_charts(self):
        """停止图表并生成最终报告"""
        logger.info("生成最终交易报告图表...")
        self.generate_final_charts()
    
    def _plot_equity_chart(self, ax, account_data, summary):
        """绘制账户权益变化图表"""
        ax.set_title('账户权益变化', fontsize=12, fontweight='bold')
        ax.set_xlabel('时间')
        ax.set_ylabel('USDT权益')
        ax.grid(True, alpha=0.3)
        
        if account_data['timestamps']:
            times = [datetime.fromtimestamp(ts) for ts in account_data['timestamps']]
            ax.plot(times, account_data['equity'], 'b-', linewidth=2, label='权益')
            
            # 添加统计信息
            initial_equity = summary.get('initial_equity', 0)
            current_equity = account_data['equity'][-1] if account_data['equity'] else 0
            change = current_equity - initial_equity
            change_pct = (change / initial_equity * 100) if initial_equity > 0 else 0
            
            info_text = f'初始权益: {initial_equity:.2f} USDT\n当前权益: {current_equity:.2f} USDT\n变化: {change:+.2f} USDT ({change_pct:+.2f}%)'
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        ax.legend()
        
    def _plot_price_changes_chart(self, ax, price_data):
        """绘制交易对价格变化百分比图表"""
        ax.set_title('交易对价格变化 (%)', fontsize=12, fontweight='bold')
        ax.set_xlabel('时间')
        ax.set_ylabel('价格变化百分比 (%)')
        ax.grid(True, alpha=0.3)
        
        colors = ['red', 'green', 'blue', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, symbol in enumerate(price_data['symbols']):
             if symbol in price_data['timestamps'] and price_data['timestamps'][symbol]:
                 times = [datetime.fromtimestamp(ts) for ts in price_data['timestamps'][symbol]]
                 price_changes = price_data['price_changes_percent'][symbol]
                 color = colors[i % len(colors)]
                 ax.plot(times, price_changes, color=color, linewidth=2, label=symbol)
        
        ax.legend()
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
    def _plot_combined_chart(self, ax, account_data, price_data, summary):
        """绘制权益和价格变化合并图表"""
        ax.set_title('权益与价格变化对比 (%)', fontsize=12, fontweight='bold')
        ax.set_xlabel('时间')
        ax.set_ylabel('变化百分比 (%)')
        ax.grid(True, alpha=0.3)
        
        # 绘制权益变化百分比
        if account_data['timestamps']:
            initial_equity = summary.get('initial_equity', 0)
            if initial_equity > 0:
                times = [datetime.fromtimestamp(ts) for ts in account_data['timestamps']]
                equity_pct = [(eq - initial_equity) / initial_equity * 100 for eq in account_data['equity']]
                ax.plot(times, equity_pct, 'b-', linewidth=3, label='权益变化', alpha=0.8)
        
        # 绘制价格变化百分比
        colors = ['red', 'green', 'orange', 'purple', 'brown']
        for i, symbol in enumerate(price_data['symbols']):
            if symbol in price_data['timestamps'] and price_data['timestamps'][symbol]:
                times = [datetime.fromtimestamp(ts) for ts in price_data['timestamps'][symbol]]
                price_changes = price_data['price_changes_percent'][symbol]
                color = colors[i % len(colors)]
                ax.plot(times, price_changes, color=color, linewidth=2, 
                       label=f'{symbol}价格', alpha=0.7, linestyle='--')
        
        ax.legend()
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        
    def _plot_volume_chart(self, ax, summary):
        """绘制交易额统计图表"""
        ax.set_title('交易额统计', fontsize=12, fontweight='bold')
        
        # 显示总体统计
        total_volume = summary.get('total_volume', 0)
        total_trades = summary.get('total_trades', 0)
        total_fees = summary.get('total_fees', 0)
        
        # 创建简单的统计显示
        stats = [
            f'总交易次数: {total_trades}',
            f'总交易额: {total_volume:.2f} USDT',
            f'总手续费: {total_fees:.2f} USDT',
            f'平均每笔: {total_volume/total_trades:.2f} USDT' if total_trades > 0 else '平均每笔: 0 USDT'
        ]
        
        # 移除坐标轴
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # 显示统计信息
        stats_text = '\n'.join(stats)
        ax.text(0.5, 0.5, stats_text, transform=ax.transAxes, 
               horizontalalignment='center', verticalalignment='center',
               fontsize=14, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    

    
    def save_chart(self, filename=None):
        """兼容性方法 - 现在通过generate_final_charts生成图表"""
        logger.info("请使用generate_final_charts方法生成最终报告")
        self.generate_final_charts()

# 全局图表管理器实例
chart_manager = ChartManager()