class FootprintCandle:
    def __init__(self):
        self.data = []  # Initialize data structure

    def add_tick(self, tick):
        self.data.append(tick)  # Add tick data

    def get_imbalance_ratio(self):
        # Calculate imbalance ratio based on ticks
        if not self.data:
            return 0
        buyer_volume = sum(tick['buyer_volume'] for tick in self.data)
        seller_volume = sum(tick['seller_volume'] for tick in self.data)
        return (buyer_volume - seller_volume) / (buyer_volume + seller_volume)

    def get_level_volume(self, level):
        # Get volume for a specific level
        return sum(tick['volume'] for tick in self.data if tick['level'] == level)

    def get_max_volume_level(self):
        # Get level with maximum volume
        levels = {}  # Dictionary to hold volume per level
        for tick in self.data:
            level = tick['level']
            levels[level] = levels.get(level, 0) + tick['volume']
        max_level = max(levels, key=levels.get)
        return max_level, levels[max_level]

    def to_dict(self):
        # Convert instance data to dictionary
        return {
            'data': self.data,
            'imbalance_ratio': self.get_imbalance_ratio(),
            'max_volume_level': self.get_max_volume_level(),
        }