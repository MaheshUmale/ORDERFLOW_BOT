from footprint_candle import FootprintCandle

class OrderFlowEngine:
    def __init__(self, imbalance_ratio=3.0):
        self.imbalance_ratio = imbalance_ratio
        self.cumulative_delta = 0

    def analyze_candle(self, candle: FootprintCandle):
        self.cumulative_delta += candle.delta
        analysis = {
            'time': candle.start_time,
            'delta': candle.delta,
            'cum_delta': self.cumulative_delta,
            'imbalances': [],
            'absorption_zones': [],
            'exhaustion': False
        }

        # 1. Detect Imbalances (Aggression / Raiding Party)
        sorted_prices = sorted(candle.price_levels.keys())
        for i in range(len(sorted_prices) - 1):
            bid_price = sorted_prices[i]
            ask_price = sorted_prices[i+1]

            bid_vol = candle.price_levels[bid_price]['bid_vol']
            ask_vol = candle.price_levels[ask_price]['ask_vol']

            # Diagonal Imbalance logic
            if bid_vol > 0 and ask_vol / bid_vol >= self.imbalance_ratio:
                analysis['imbalances'].append({'type': 'Buy', 'price': ask_price})
            elif ask_vol > 0 and bid_vol / ask_vol >= self.imbalance_ratio:
                analysis['imbalances'].append({'type': 'Sell', 'price': bid_price})

        # 2. Detect Absorption (The "Wall")
        # High volume at a specific price level with minimal price continuation
        if candle.price_levels:
            max_vol_level = max(candle.price_levels.items(), key=lambda x: x[1]['bid_vol'] + x[1]['ask_vol'])
            total_node_vol = max_vol_level[1]['bid_vol'] + max_vol_level[1]['ask_vol']
            if candle.volume > 0 and total_node_vol > (candle.volume * 0.4): # If 40% of candle volume is trapped at one node
                analysis['absorption_zones'].append(max_vol_level[0])

            # 3. Detect Exhaustion (The "Fade")
            # Minimal volume at the extreme wicks
            high_vol = candle.price_levels[candle.high]['bid_vol'] + candle.price_levels[candle.high]['ask_vol']
            low_vol = candle.price_levels[candle.low]['bid_vol'] + candle.price_levels[candle.low]['ask_vol']
            if candle.volume > 0 and (high_vol < (candle.volume * 0.05) or low_vol < (candle.volume * 0.05)):
                analysis['exhaustion'] = True

        return analysis
