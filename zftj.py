# KC_amplitude_futures.py
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional

class SingleCoinAmplitudeAnalyzer:
    """
    支持市场 market='spot' 或 'futures'（USDT 合约 via fapi）
    amplitude_mode:
        - 'down_percent' (默认) -> (open - low) / open * 100  （仅对下跌K线有意义）
        - 'range' -> (high - low) / low * 100  （保留你原始脚本的计算）
    只统计并返回 close < open 的K线（下跌K线）。
    """
    MARKET_ENDPOINTS = {
        'spot': "https://api.binance.com/api/v3",
        'futures': "https://fapi.binance.com/fapi/v1",   # USDT 永续/交割合约的 REST
        # 如果需要 COIN-M（交割合约）可扩展 'coin_m': "https://dapi.binance.com/dapi/v1"
    }

    def __init__(self, market: str = 'futures', proxy_config: Optional[Dict] = None):
        if market not in self.MARKET_ENDPOINTS:
            raise ValueError("market must be one of: " + ", ".join(self.MARKET_ENDPOINTS.keys()))
        self.base_url = self.MARKET_ENDPOINTS[market]
        self.session = requests.Session()
        if proxy_config:
            self.session.proxies.update(proxy_config)
            print(f"✅ 已配置代理: {proxy_config}")
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.market = market

    def get_kline_data(self, symbol: str, interval: str = '1h', limit: int = 500) -> Optional[List]:
        """获取 K 线，limit 最大1000（Binance 限制）"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'limit': min(max(1, int(limit)), 1000)
            }
            print(f"🔄 [{self.market}] 正在获取 {symbol} 的 {params['limit']} 根 {interval} K 线数据...")
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            print(f"✅ 成功获取 {len(data)} 根K线数据")
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取 {symbol} K线失败: {e}")
            return None

    def analyze_klines(self, symbol: str, interval: str = '1h', limit: int = 500,
                       amplitude_mode: str = 'down_percent') -> List[Dict]:
        """
        分析 K 线，但只保留下跌 K 线（close < open）。
        amplitude_mode: 'down_percent' 或 'range'
        返回按 amplitude 降序的下跌K线列表（完整详情，不限制 top n）。
        """
        kline_data = self.get_kline_data(symbol, interval, limit)
        if not kline_data:
            return []

        results = []
        for i, k in enumerate(kline_data):
            open_time = int(k[0])
            open_price = float(k[1])
            high_price = float(k[2])
            low_price = float(k[3])
            close_price = float(k[4])
            volume = float(k[5])

            # 只处理下跌 K 线
            if close_price >= open_price:
                continue

            # 计算振幅：两种模式
            if amplitude_mode == 'range':
                # 保留你原来的度量（high-low）/low
                amplitude = ((high_price - low_price) / low_price) * 100 if low_price > 0 else 0.0
            else:
                # down_percent: 以开盘价为基准衡量下探幅度
                amplitude = ((open_price - low_price) / open_price) * 100 if open_price > 0 else 0.0

            change_percent = ((close_price - open_price) / open_price) * 100 if open_price > 0 else 0.0
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

        # 按振幅降序排序（最大下探优先）
        results_sorted = sorted(results, key=lambda x: x['amplitude'], reverse=True)
        return results_sorted

    def get_top_amplitudes(self, results: List[Dict], top_n: int = 15) -> List[Dict]:
        return results[:top_n]

    def print_results(self, symbol: str, top_results: List[Dict], interval: str, market: str):
        if not top_results:
            print("❌ 没有下跌 K 线被统计（或数据为空）")
            return

        print(f"\n{'='*100}")
        print(f"📉 {symbol} ({market}) - 仅统计下跌 K 线 的 振幅排名 TOP {len(top_results)}  （时间周期={interval}）")
        print(f"{'='*100}")
        print(f"{'排名':<4} {'时间':<19} {'下探振幅%':<10} {'涨跌%':<8} {'开盘':<12} {'最高':<12} {'最低':<12} {'收盘':<12}")
        print("-"*100)
        for i, r in enumerate(top_results, 1):
            print(f"{i:<4} {r['time']:<19} {r['amplitude']:<9.2f}% {r['change_percent']:<7.2f}% "
                  f"{r['open']:<12.6f} {r['high']:<12.6f} {r['low']:<12.6f} {r['close']:<12.6f}")
        print("="*100)

    def save_results(self, symbol: str, results: List[Dict], interval: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{interval}_futures_down_amplitude_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'symbol': symbol,
                'market': self.market,
                'interval': interval,
                'analysis_time': timestamp,
                'total_down_klines': len(results),
                'results': results
            }, f, ensure_ascii=False, indent=2)
        return filename


def main():
    # proxy_config = None 或者按需配置
    proxy_config = None
    analyzer = SingleCoinAmplitudeAnalyzer(market='futures', proxy_config=proxy_config)

    # ========== 参数 ==========
    symbol = 'BTCUSDT'   # 注意合约对，通常 USDT 永续/交割合约 用 BTCUSDT/ETHUSDT 等
    interval = '1h'
    kline_count = 500
    top_n = 20
    amplitude_mode = 'down_percent'   # 'down_percent' 或 'range'
    # ==========================

    results = analyzer.analyze_klines(symbol, interval, kline_count, amplitude_mode=amplitude_mode)
    if not results:
        print("❌ 没有获取到有效的下跌K线，请检查symbol/market/网络。")
        return

    top_results = analyzer.get_top_amplitudes(results, top_n)
    analyzer.print_results(symbol, top_results, interval, analyzer.market)
    filename = analyzer.save_results(symbol, results, interval)
    print(f"\n💾 结果已保存: {filename}")


if __name__ == "__main__":
    main()

 
