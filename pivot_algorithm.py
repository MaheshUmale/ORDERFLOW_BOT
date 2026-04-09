# Pivot Algorithm Implementation

class PivotPoint:
    def __init__(self, high, low, close):
        self.high = high
        self.low = low
        self.close = close
        self.pivot = (high + low + close) / 3
        self.support1 = self.pivot * 2 - high
        self.support2 = self.pivot - (high - low)
        self.resistance1 = self.pivot * 2 - low
        self.resistance2 = self.pivot + (high - low)

    def get_levels(self):
        return {
            'pivot': self.pivot,
            'support1': self.support1,
            'support2': self.support2,
            'resistance1': self.resistance1,
            'resistance2': self.resistance2
        }

class AutoTrendSupportResistance:
    def __init__(self, price_data):
        self.price_data = price_data

    def identify_levels(self):
        levels = []
        for i in range(1, len(self.price_data) - 1):
            if (self.price_data[i] > self.price_data[i - 1] and self.price_data[i] > self.price_data[i + 1]):
                levels.append(('resistance', self.price_data[i]))
            elif (self.price_data[i] < self.price_data[i - 1] and self.price_data[i] < self.price_data[i + 1]):
                levels.append(('support', self.price_data[i]))
        return levels

    def level_testing(self, current_price):
        for level_type, level_value in self.identify_levels():
            if current_price >= level_value and level_type == 'resistance':
                return 'Breaking Resistance'
            elif current_price <= level_value and level_type == 'support':
                return 'Breaking Support'
        return 'No Break'

# Example Usage
# price_data = [high, low, close]
# pp = PivotPoint(high, low, close)
# print(pp.get_levels())

# auto_trend = AutoTrendSupportResistance(price_data)
# print(auto_trend.level_testing(current_price))
