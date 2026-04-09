from collections import defaultdict

class FootprintCandle:
    def __init__(self, open_price, start_time):
        self.start_time = start_time
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0
        self.delta = 0
        # Tracks { price: {'bid_vol': x, 'ask_vol': y} }
        self.price_levels = defaultdict(lambda: {'bid_vol': 0, 'ask_vol': 0})

    def add_tick(self, price, volume, is_buy_trade):
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume

        if is_buy_trade:
            self.price_levels[price]['ask_vol'] += volume
            self.delta += volume
        else:
            self.price_levels[price]['bid_vol'] += volume
            self.delta -= volume
