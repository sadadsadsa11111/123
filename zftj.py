import requests
import json
import pandas as pd
from datetime import datetime
import time
from typing import List, Dict, Optional

 # ==================== 参数设置 ====================
    symbol = 'SUIUSDT'      # 币种设置，如：'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
    interval = '1h'         # 时间周期：1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    kline_count = 1000       # K线数量（最大1000）
    top_n = 15             # 显示振幅排名前N名
    # ================================================


class SingleCoinAmplitudeAnalyzer:
    def __init__(self, proxy_config: Optional[Dict] = None):
        """
        初始化单币种振幅分析器
        
        Args:
            proxy_config: 代理配置字典，格式如下：
                {
                    'http': 'http:127.0.0.1:7777',
                    'https': 'https:127.0.0.1:7777'
                }
        """
        self.base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()
        
        # 设置代理
        if proxy_config:
            self.session.proxies.update(proxy_config)
            print(f"✅ 已配置代理: {proxy_config}")
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_kline_data(self, symbol: str, interval: str = '1h', limit: int = 100) -> Optional[List]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对符号，如 'BTCUSDT'
            interval: 时间间隔，可选值：1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
            limit: 获取的K线数量，最大1000
        
        Returns:
            K线数据列表或None
        """
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'limit': limit
            }
            
            print(f"🔄 正在获取 {symbol} 的 {limit} 根 {interval} K线数据...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            kline_data = response.json()
            print(f"✅ 成功获取 {len(kline_data)} 根K线数据")
            return kline_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取 {symbol} K线数据失败: {e}")
            return None
    
    def analyze_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[Dict]:
        """
        分析单个币种的K线振幅
        
        Args:
            symbol: 交易对符号
            interval: 时间间隔
            limit: K线数量
        
        Returns:
            每根K线的详细分析结果
        """
        kline_data = self.get_kline_data(symbol, interval, limit)
        
        if not kline_data:
            return []
        
        results = []
        
        print(f"\n📊 开始分析 {symbol} 的K线振幅...")
        print("-" * 80)
        
        for i, kline in enumerate(kline_data):
            # K线数据格式：
            # [开盘时间, 开盘价, 最高价, 最低价, 收盘价, 成交量, 收盘时间, ...]
            open_time = int(kline[0])
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])
            
            # 计算振幅
            if low_price > 0:
                amplitude = ((high_price - low_price) / low_price) * 100
            else:
                amplitude = 0.0
            
            # 计算涨跌幅
            if open_price > 0:
                change_percent = ((close_price - open_price) / open_price) * 100
            else:
                change_percent = 0.0
            
            # 转换时间戳
            time_str = datetime.fromtimestamp(open_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
            
            results.append({
                'index': i + 1,
                'time': time_str,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'amplitude': amplitude,
                'change_percent': change_percent
            })
        
        return results
    
    def get_top_amplitudes(self, results: List[Dict], top_n: int = 15) -> List[Dict]:
        """
        获取振幅最大的前N根K线
        
        Args:
            results: K线分析结果
            top_n: 返回前N名
        
        Returns:
            按振幅排序的前N名
        """
        sorted_results = sorted(results, key=lambda x: x['amplitude'], reverse=True)
        return sorted_results[:top_n]
    
    def print_results(self, symbol: str, top_results: List[Dict], interval: str):
        """打印分析结果"""
        if not top_results:
            print("❌ 没有可显示的结果")
            return
        
        print(f"\n" + "="*100)
        print(f"📈 {symbol} - {interval} K线振幅排名 TOP {len(top_results)}")
        print("="*100)
        print(f"{'排名':<4} {'时间':<19} {'振幅%':<8} {'涨跌%':<8} {'开盘':<12} {'最高':<12} {'最低':<12} {'收盘':<12}")
        print("-"*100)
        
        for i, result in enumerate(top_results, 1):
            print(f"{i:<4} {result['time']:<19} "
                  f"{result['amplitude']:<7.2f}% "
                  f"{result['change_percent']:<7.2f}% "
                  f"{result['open']:<12.6f} "
                  f"{result['high']:<12.6f} "
                  f"{result['low']:<12.6f} "
                  f"{result['close']:<12.6f}")
        
        print("="*100)
        
        # 统计信息
        amplitudes = [r['amplitude'] for r in top_results]
        avg_amplitude = sum(amplitudes) / len(amplitudes)
        max_amplitude = max(amplitudes)
        min_amplitude = min(amplitudes)
        
        print(f"\n📊 统计信息:")
        print(f"   平均振幅: {avg_amplitude:.2f}%")
        print(f"   最大振幅: {max_amplitude:.2f}%")
        print(f"   最小振幅: {min_amplitude:.2f}%")
    
    def save_results(self, symbol: str, results: List[Dict], interval: str) -> str:
        """保存结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{interval}_amplitude_analysis_{timestamp}.json"
        
        save_data = {
            'symbol': symbol,
            'interval': interval,
            'analysis_time': timestamp,
            'total_klines': len(results),
            'results': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        return filename


def main():
    """主函数"""
    # 代理配置（根据您的实际代理修改）
    proxy_config = {
        'http': 'http://127.0.0.1:7890',    # 替换为您的代理地址和端口
        'https': 'http://127.0.0.1:7890'    # 替换为您的代理地址和端口
    }
    
    # 如果不需要代理，设置为None
    # proxy_config = None
    
    # 初始化分析器
    analyzer = SingleCoinAmplitudeAnalyzer(proxy_config=proxy_config)
    
   
    
    print(f"🚀 开始分析 {symbol} 币种")
    print(f"📋 分析参数: 时间周期={interval}, K线数量={kline_count}, 显示前{top_n}名")
    
    # 执行分析
    results = analyzer.analyze_klines(symbol, interval, kline_count)
    
    if not results:
        print("❌ 分析失败，请检查网络连接、代理设置或币种名称")
        return
    
    # 获取振幅排名前N的K线
    top_results = analyzer.get_top_amplitudes(results, top_n)
    
    # 显示结果
    analyzer.print_results(symbol, top_results, interval)
    
    # 保存完整结果
    filename = analyzer.save_results(symbol, results, interval)
    print(f"\n💾 完整分析结果已保存到: {filename}")
    
    # 额外信息
    print(f"\n🔍 如需分析其他币种，请修改代码中的以下参数：")
    print(f"   symbol = '{symbol}'     # 改为其他币种如 'ETHUSDT', 'SOLUSDT'")
    print(f"   interval = '{interval}'       # 改为其他时间周期如 '4h', '1d'")
    print(f"   kline_count = {kline_count}      # 改为其他K线数量（1-1000）")


if __name__ == "__main__":
    main()
