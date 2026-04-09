class OrderFlowEngine:
    def __init__(self):
        self.analysis = None
        self.candles = []

    def analyze_candle(self, candle):
        # Analyzing the candle data
        # Example: simple logic to determine bullish/bearish
        if candle['close'] > candle['open']:
            self.analysis = 'bullish'
        else:
            self.analysis = 'bearish'
        self.candles.append(candle)
        return self.analysis

    def get_latest_analysis(self):
        return self.analysis

    def reset(self):
        self.analysis = None
        self.candles.clear()