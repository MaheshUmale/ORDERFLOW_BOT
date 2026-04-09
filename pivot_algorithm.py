class PivotPoint:
    def __init__(self, bar_number, price, close, is_high):
        self.bar_number = bar_number
        self.price = price
        self.close = close
        self.is_high = is_high
        self.display_level = True
        self.is_level_tested = False
        self.is_level_broken = False

class AutoTrendSupportResistance:
    def __init__(self, required_ticks_for_broken=4, tick_size=0.05):
        self.pivots = []
        self.current_pivot = None
        self.is_looking_for_high = True
        self.has_first_pivot = False
        self.required_threshold = required_ticks_for_broken * tick_size

    def update(self, current_bar_idx, prev_open, prev_high, prev_low, prev_close):
        if not self.has_first_pivot:
            if prev_open <= prev_close:
                self.current_pivot = PivotPoint(current_bar_idx, prev_low, prev_close, False)
                self.pivots.append(self.current_pivot)
            else:
                self.current_pivot = PivotPoint(current_bar_idx, prev_high, prev_close, True)
                self.pivots.append(self.current_pivot)
                self.is_looking_for_high = False

            self.has_first_pivot = True
            return

        # Check if existing levels are tested or broken
        for pivot in self.pivots:
            if not pivot.display_level:
                continue

            # Resistance Checks
            if pivot.is_high:
                if pivot.price <= prev_high <= (pivot.price + self.required_threshold):
                    pivot.is_level_tested = True
                elif prev_high > (pivot.price + self.required_threshold):
                    pivot.is_level_broken = True
                    pivot.display_level = False
            # Support Checks
            else:
                if pivot.price >= prev_low >= (pivot.price - self.required_threshold):
                    pivot.is_level_tested = True
                elif prev_low < (pivot.price - self.required_threshold):
                    pivot.is_level_broken = True
                    pivot.display_level = False

        # Find new pivots
        if self.is_looking_for_high:
            if prev_high > self.current_pivot.price:
                self.current_pivot.bar_number = current_bar_idx
                self.current_pivot.price = prev_high
                self.current_pivot.close = prev_close
            elif prev_high < self.current_pivot.price:
                # Lower high found, lock in the peak and look for low
                self.pivots.append(PivotPoint(self.current_pivot.bar_number, self.current_pivot.price, self.current_pivot.close, True))
                self.current_pivot = PivotPoint(current_bar_idx, prev_low, prev_close, False)
                self.is_looking_for_high = False
        else:
            if prev_low < self.current_pivot.price:
                self.current_pivot.bar_number = current_bar_idx
                self.current_pivot.price = prev_low
                self.current_pivot.close = prev_close
            elif prev_low > self.current_pivot.price:
                # Higher low found, lock in the trough and look for high
                self.pivots.append(PivotPoint(self.current_pivot.bar_number, self.current_pivot.price, self.current_pivot.close, False))
                self.current_pivot = PivotPoint(current_bar_idx, prev_high, prev_close, True)
                self.is_looking_for_high = True
