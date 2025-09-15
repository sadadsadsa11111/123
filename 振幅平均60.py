#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币圈K线平均振幅统计工具
支持代理访问币安API，可配置K线周期和币种
"""

import requests
import json
import time
import statistics
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import argparse


class BinanceKlineAnalyzer:
    """币安K线振幅分析器"""
    
    def __init__(self, proxy_url: Optional[str] = None):
        """
        初始化分析器
        
        Args:
            proxy_url: 代理地址，格式如 'http://127.0.0.1:7890' 或 'socks5://127.0.0.1:1080'
        """
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.session = requests.Session()
        
        # 设置代理
        if proxy_url:
            self.setup_proxy(proxy_url)
            
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        
        # K线周期映射
        self.intervals = {
            '1m': '1分钟', '3m': '3分钟', '5m': '5分钟', '15m': '15分钟',
            '30m': '30分钟', '1h': '1小时', '2h': '2小时', '4h': '4小时',
            '6h': '6小时', '8h': '8小时', '12h': '12小时', '1d': '1天',
            '3d': '3天', '1w': '1周', '1M': '1月'
        }
    
    def setup_proxy(self, proxy_url: str):
        """设置代理"""
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            self.session.proxies.update(proxies)
            print(f"✅ 代理设置成功: {proxy_url}")
        except Exception as e:
            print(f"❌ 代理设置失败: {e}")
            
    def get_klines(self, symbol: str, interval: str, limit: int = 60) -> List[List]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对，如 'BTCUSDT'
            interval: K线周期
            limit: 获取数量
            
        Returns:
            K线数据列表
        """
        url = f"{self.base_url}/klines"
        params = {
            'symbol': symbol.upper(),
            'interval': interval,
            'limit': limit
        }
        
        try:
            print(f"🔄 正在获取 {symbol} {self.intervals.get(interval, interval)} K线数据...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise ValueError("未获取到K线数据")
                
            print(f"✅ 成功获取 {len(data)} 根K线数据")
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败: {e}")
        except json.JSONDecodeError:
            raise Exception("API返回数据格式错误")
    
    def calculate_amplitude(self, klines: List[List]) -> Dict:
        """
        计算振幅统计数据
        
        Args:
            klines: K线数据
            
        Returns:
            振幅分析结果
        """
        if not klines:
            raise ValueError("K线数据为空")
            
        amplitudes = []
        kline_details = []
        
        print("📊 正在计算振幅数据...")
        
        for i, kline in enumerate(klines):
            try:
                timestamp = int(kline[0])
                open_price = float(kline[1])
                high_price = float(kline[2])
                low_price = float(kline[3])
                close_price = float(kline[4])
                volume = float(kline[5])
                
                # 计算振幅百分比: (最高价 - 最低价) / 开盘价 * 100
                if open_price > 0:
                    amplitude = ((high_price - low_price) / open_price) * 100
                else:
                    amplitude = 0
                    
                amplitudes.append(amplitude)
                
                kline_detail = {
                    'index': i + 1,
                    'timestamp': timestamp,
                    'datetime': datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume,
                    'amplitude': amplitude
                }
                kline_details.append(kline_detail)
                
            except (ValueError, IndexError) as e:
                print(f"⚠️  第 {i+1} 根K线数据解析错误: {e}")
                continue
        
        if not amplitudes:
            raise ValueError("没有有效的振幅数据")
        
        # 计算统计指标
        avg_amplitude = statistics.mean(amplitudes)
        max_amplitude = max(amplitudes)
        min_amplitude = min(amplitudes)
        median_amplitude = statistics.median(amplitudes)
        
        # 计算标准差
        if len(amplitudes) > 1:
            std_deviation = statistics.stdev(amplitudes)
        else:
            std_deviation = 0
            
        # 找出极值K线
        max_idx = amplitudes.index(max_amplitude)
        min_idx = amplitudes.index(min_amplitude)
        
        max_amplitude_kline = kline_details[max_idx]
        min_amplitude_kline = kline_details[min_idx]
        
        # 计算振幅区间分布
        amplitude_ranges = self.calculate_amplitude_distribution(amplitudes)
        
        return {
            'summary': {
                'total_klines': len(amplitudes),
                'average_amplitude': avg_amplitude,
                'median_amplitude': median_amplitude,
                'max_amplitude': max_amplitude,
                'min_amplitude': min_amplitude,
                'std_deviation': std_deviation,
                'amplitude_range': max_amplitude - min_amplitude
            },
            'extremes': {
                'max_amplitude_kline': max_amplitude_kline,
                'min_amplitude_kline': min_amplitude_kline
            },
            'distribution': amplitude_ranges,
            'raw_data': kline_details
        }
    
    def calculate_amplitude_distribution(self, amplitudes: List[float]) -> Dict:
        """计算振幅分布统计"""
        if not amplitudes:
            return {}
            
        # 定义振幅区间
        ranges = [
            (0, 1, "0-1%"),
            (1, 2, "1-2%"),
            (2, 3, "2-3%"),
            (3, 5, "3-5%"),
            (5, 10, "5-10%"),
            (10, float('inf'), ">10%")
        ]
        
        distribution = {}
        total = len(amplitudes)
        
        for min_val, max_val, label in ranges:
            count = sum(1 for amp in amplitudes if min_val <= amp < max_val)
            percentage = (count / total) * 100 if total > 0 else 0
            distribution[label] = {
                'count': count,
                'percentage': percentage
            }
        
        return distribution
    
    def print_analysis_results(self, results: Dict, symbol: str, interval: str):
        """打印分析结果"""
        print("\n" + "="*80)
        print(f"📈 {symbol} - {self.intervals.get(interval, interval)} K线振幅分析报告")
        print("="*80)
        
        summary = results['summary']
        extremes = results['extremes']
        distribution = results['distribution']
        
        # 基础统计
        print(f"\n📊 基础统计信息:")
        print(f"   统计K线数量: {summary['total_klines']} 根")
        print(f"   平均振幅:     {summary['average_amplitude']:.4f}%")
        print(f"   中位数振幅:   {summary['median_amplitude']:.4f}%")
        print(f"   最大振幅:     {summary['max_amplitude']:.4f}%")
        print(f"   最小振幅:     {summary['min_amplitude']:.4f}%")
        print(f"   标准差:       {summary['std_deviation']:.4f}%")
        print(f"   振幅范围:     {summary['amplitude_range']:.4f}%")
        
        # 极值详情
        print(f"\n🔝 最大振幅详情:")
        max_kline = extremes['max_amplitude_kline']
        print(f"   时间: {max_kline['datetime']}")
        print(f"   开盘: {max_kline['open']:.6f}")
        print(f"   最高: {max_kline['high']:.6f}")
        print(f"   最低: {max_kline['low']:.6f}")
        print(f"   收盘: {max_kline['close']:.6f}")
        print(f"   成交量: {max_kline['volume']:.2f}")
        print(f"   振幅: {max_kline['amplitude']:.4f}%")
        
        print(f"\n🔻 最小振幅详情:")
        min_kline = extremes['min_amplitude_kline']
        print(f"   时间: {min_kline['datetime']}")
        print(f"   开盘: {min_kline['open']:.6f}")
        print(f"   最高: {min_kline['high']:.6f}")
        print(f"   最低: {min_kline['low']:.6f}")
        print(f"   收盘: {min_kline['close']:.6f}")
        print(f"   成交量: {min_kline['volume']:.2f}")
        print(f"   振幅: {min_kline['amplitude']:.4f}%")
        
        # 振幅分布
        print(f"\n📈 振幅区间分布:")
        for range_label, data in distribution.items():
            print(f"   {range_label:>8}: {data['count']:>3} 根 ({data['percentage']:>5.1f}%)")
        
        # 波动性评估
        print(f"\n💡 波动性评估:")
        avg_amp = summary['average_amplitude']
        std_dev = summary['std_deviation']
        
        if avg_amp < 1:
            volatility = "极低"
        elif avg_amp < 2:
            volatility = "低"
        elif avg_amp < 5:
            volatility = "中等"
        elif avg_amp < 10:
            volatility = "高"
        else:
            volatility = "极高"
            
        print(f"   波动程度: {volatility}")
        print(f"   稳定性: {'较稳定' if std_dev < avg_amp * 0.5 else '波动较大'}")
        
        print("\n" + "="*80)
    
    def save_results_to_file(self, results: Dict, symbol: str, interval: str, filename: Optional[str] = None):
        """保存结果到文件"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"amplitude_analysis_{symbol}_{interval}_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"✅ 分析结果已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
    
    def analyze_symbol(self, symbol: str, interval: str = '15m', limit: int = 60, 
                      save_to_file: bool = False) -> Dict:
        """
        分析指定交易对的振幅
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: K线数量
            save_to_file: 是否保存到文件
            
        Returns:
            分析结果
        """
        try:
            # 获取K线数据
            klines = self.get_klines(symbol, interval, limit)
            
            # 计算振幅
            results = self.calculate_amplitude(klines)
            
            # 添加元数据
            results['metadata'] = {
                'symbol': symbol.upper(),
                'interval': interval,
                'interval_name': self.intervals.get(interval, interval),
                'analysis_time': datetime.now().isoformat(),
                'limit': limit
            }
            
            # 打印结果
            self.print_analysis_results(results, symbol, interval)
            
            # 保存文件
            if save_to_file:
                self.save_results_to_file(results, symbol, interval)
            
            return results
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            return {}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='币圈K线平均振幅统计工具')
    parser.add_argument('--symbol', '-s', default='MYXUSDT', help='交易对 (默认: BTCUSDT)')
    parser.add_argument('--interval', '-i', default='1m', 
                       choices=['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', 
                               '6h', '8h', '12h', '1d', '3d', '1w', '1M'],
                       help='K线周期 (默认: 15m)')
    parser.add_argument('--limit', '-l', type=int, default=1400, help='K线数量 (默认: 60)')
    parser.add_argument('--proxy', '-p', help='代理地址 (如: http://127.0.0.1:7890)')
    parser.add_argument('--save', action='store_true', help='保存结果到JSON文件')
    
    args = parser.parse_args()
    
    print("🚀 币圈K线平均振幅统计工具启动")
    print(f"📋 配置信息:")
    print(f"   交易对: {args.symbol}")
    print(f"   K线周期: {args.interval}")
    print(f"   统计数量: {args.limit} 根")
    if args.proxy:
        print(f"   代理地址: {args.proxy}")
    print()
    
    # 创建分析器
    analyzer = BinanceKlineAnalyzer(proxy_url=args.proxy)
    
    # 执行分析
    results = analyzer.analyze_symbol(
        symbol=args.symbol,
        interval=args.interval,
        limit=args.limit,
        save_to_file=args.save
    )
    
    if results:
        print("✅ 分析完成!")
    else:
        print("❌ 分析失败!")


if __name__ == "__main__":
    main()


# 示例用法
"""
# 基础用法 - 合约市场（默认）
python amplitude_analyzer.py --symbol BTCUSDT --interval 15m

# 指定合约市场
python amplitude_analyzer.py --symbol ETHUSDT --interval 1h --market futures

# 现货市场分析
python amplitude_analyzer.py --symbol BNBUSDT --interval 4h --market spot

# 合约市场使用代理
python amplitude_analyzer.py --symbol ADAUSDT --interval 1d --proxy http://127.0.0.1:7890

# 保存合约市场结果到文件
python amplitude_analyzer.py --symbol DOGEUSDT --interval 15m --save --market futures

# SOCKS5代理分析合约
python amplitude_analyzer.py --symbol SOLUSDT --proxy socks5://127.0.0.1:1080 --market futures

# 程序化调用示例
# 合约市场分析
analyzer = BinanceKlineAnalyzer(proxy_url='http://127.0.0.1:7890', market_type='futures')
results = analyzer.analyze_symbol('BTCUSDT', '15m')

# 现货市场分析
analyzer_spot = BinanceKlineAnalyzer(market_type='spot')
results_spot = analyzer_spot.analyze_symbol('ETHUSDT', '1h')
"""