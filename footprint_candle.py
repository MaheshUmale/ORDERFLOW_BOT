class FootprintCandle:
    __slots__ = ('start_time', 'open', 'high', 'low', 'close', 'volume', 'delta', 'price_levels')

    def __init__(self, open_price, start_time):
        self.start_time = start_time
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0
        self.delta = 0
        # Tracks { price: {'bid_vol': x, 'ask_vol': y} }
        self.price_levels = {}

    def add_tick(self, price, volume, is_buy_trade):
        if price > self.high: self.high = price
        elif price < self.low: self.low = price

        self.close = price
        self.volume += volume

        # Manual lookup is faster than defaultdict(lambda) for high freq
        if price not in self.price_levels:
            self.price_levels[price] = {'bid_vol': 0, 'ask_vol': 0}

        level = self.price_levels[price]
        if is_buy_trade:
            level['ask_vol'] += volume
            self.delta += volume
        else:
            level['bid_vol'] += volume
            self.delta -= volume
