from footprint_candle import FootprintCandle

class OrderFlowEngine:
    def __init__(self, imbalance_ratio=3.0):
        self.imbalance_ratio = imbalance_ratio
        self.cumulative_delta = 0

    def analyze_candle(self, candle: FootprintCandle, current_cum_delta=0):
        new_cum_delta = current_cum_delta + candle.delta
        analysis = {
            'time': candle.start_time,
            'delta': candle.delta,
            'cum_delta': new_cum_delta,
            'imbalances': [],
            'absorption_zones': [],
            'exhaustion': False,
            'signal': None, # Buy, Sell, or None
            'confidence': 0
        }

        if not candle.price_levels:
            return analysis

        # 1. Detect Imbalances (Aggression)
        sorted_prices = sorted(candle.price_levels.keys())
        # Cache price levels to avoid repeated dict lookups
        levels = candle.price_levels

        for i in range(len(sorted_prices) - 1):
            bid_price = sorted_prices[i]
            ask_price = sorted_prices[i+1]

            bid_vol = levels[bid_price]['bid_vol']
            ask_vol = levels[ask_price]['ask_vol']

            # Diagonal Imbalance logic
            if bid_vol > 0 and ask_vol / bid_vol >= self.imbalance_ratio:
                analysis['imbalances'].append({'type': 'Buy', 'price': ask_price})
            elif ask_vol > 0 and bid_vol / ask_vol >= self.imbalance_ratio:
                analysis['imbalances'].append({'type': 'Sell', 'price': bid_price})

        # 2. Detect Absorption (The "Wall")
        max_vol_level = max(levels.items(), key=lambda x: x[1]['bid_vol'] + x[1]['ask_vol'])
        total_node_vol = max_vol_level[1]['bid_vol'] + max_vol_level[1]['ask_vol']
        if candle.volume > 0 and total_node_vol > (candle.volume * 0.4):
            analysis['absorption_zones'].append(max_vol_level[0])

        # 3. Detect Exhaustion (The "Fade")
        high_vol = levels[candle.high]['bid_vol'] + levels[candle.high]['ask_vol']
        low_vol = levels[candle.low]['bid_vol'] + levels[candle.low]['ask_vol']
        if candle.volume > 0 and (high_vol < (candle.volume * 0.05) or low_vol < (candle.volume * 0.05)):
            analysis['exhaustion'] = True

        # 4. Determine Simple Trade Signal
        # A signal occurs if we have multiple bullish/bearish signs
        buy_imbalances = len([imb for imb in analysis['imbalances'] if imb['type'] == 'Buy'])
        sell_imbalances = len([imb for imb in analysis['imbalances'] if imb['type'] == 'Sell'])

        if buy_imbalances >= 2 and candle.delta > 0:
            analysis['signal'] = 'BUY'
            analysis['confidence'] = min(0.9, 0.5 + (buy_imbalances * 0.1))
        elif sell_imbalances >= 2 and candle.delta < 0:
            analysis['signal'] = 'SELL'
            analysis['confidence'] = min(0.9, 0.5 + (sell_imbalances * 0.1))
        elif analysis['exhaustion'] and abs(candle.delta) < (candle.volume * 0.1):
             # Exhaustion at wick with low delta might suggest reversal
             if candle.close > candle.open:
                 analysis['signal'] = 'SELL'
                 analysis['confidence'] = 0.6
             else:
                 analysis['signal'] = 'BUY'
                 analysis['confidence'] = 0.6

        return analysis
