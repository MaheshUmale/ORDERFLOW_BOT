class Trade:
    def __init__(self, instrument_key, side, entry_price, stop_loss, take_profit, confidence=0.5):
        self.instrument_key = instrument_key
        self.side = side # 'BUY' or 'SELL'
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.initial_stop = stop_loss
        self.take_profit = take_profit
        self.confidence = confidence
        self.status = 'OPEN' # 'OPEN', 'CLOSED'
        self.exit_price = None
        self.exit_reason = None # 'TP', 'SL', 'MANUAL'
        self.pnl = 0

    def update(self, current_price):
        if self.status != 'OPEN':
            return

        # Trailing Stop Logic
        if self.side == 'BUY':
            # If price moves up by 2 points, move SL up by 1 point
            potential_new_sl = current_price - 4 # Maintain a 4 point buffer once trailing
            if current_price > self.entry_price + 2:
                self.stop_loss = max(self.stop_loss, potential_new_sl)

            if current_price <= self.stop_loss:
                self.close(self.stop_loss, 'SL')
            elif current_price >= self.take_profit:
                self.close(self.take_profit, 'TP')
        else: # SELL
            potential_new_sl = current_price + 4
            if current_price < self.entry_price - 2:
                self.stop_loss = min(self.stop_loss, potential_new_sl)

            if current_price >= self.stop_loss:
                self.close(self.stop_loss, 'SL')
            elif current_price <= self.take_profit:
                self.close(self.take_profit, 'TP')

    def close(self, price, reason):
        self.exit_price = price
        self.exit_reason = reason
        self.status = 'CLOSED'
        if self.side == 'BUY':
            self.pnl = self.exit_price - self.entry_price
        else:
            self.pnl = self.entry_price - self.exit_price

class TradeManager:
    def __init__(self, daily_loss_limit=50, max_active_trades=3, helper=None):
        self.trades = []
        self.daily_loss_limit = daily_loss_limit
        self.max_active_trades = max_active_trades
        self.helper = helper # UpstoxHelper
        self.live_mode = False # Safety toggle
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'realized_pnl': 0,
            'win_rate': 0
        }

    def add_trade(self, instrument_key, side, entry_price, confidence=0.5):
        # Risk Guardrails
        if self.stats['realized_pnl'] <= -self.daily_loss_limit:
            print(f"GUARDRAIL: Daily loss limit reached ({self.stats['realized_pnl']:.2f})", flush=True)
            return None

        active_trades = [t for t in self.trades if t.status == 'OPEN']
        if len(active_trades) >= self.max_active_trades:
            print(f"GUARDRAIL: Max active trades reached ({len(active_trades)})", flush=True)
            return None

        # Default RR 1:2
        risk = 5 # Fixed risk points for now
        reward = risk * 2

        if side == 'BUY':
            sl = entry_price - risk
            tp = entry_price + reward
        else:
            sl = entry_price + risk
            tp = entry_price - reward

        new_trade = Trade(instrument_key, side, entry_price, sl, tp, confidence)
        self.trades.append(new_trade)

        if self.live_mode and self.helper:
            print(f"LIVE ORDER: Sending {side} for {instrument_key}", flush=True)
            res = self.helper.place_order(instrument_key, side, quantity=25) # Fixed qty for now
            print(f"UPSTOX RESPONSE: {res}", flush=True)

        return new_trade

    def update_trades(self, instrument_key, current_price):
        for trade in self.trades:
            if trade.instrument_key == instrument_key and trade.status == 'OPEN':
                trade.update(current_price)
                if trade.status == 'CLOSED':
                    self.update_stats(trade)

    def update_stats(self, trade):
        self.stats['total_trades'] += 1
        if trade.pnl > 0:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
        self.stats['realized_pnl'] += trade.pnl
        self.stats['win_rate'] = (self.stats['wins'] / self.stats['total_trades']) * 100

    def get_ev(self, confidence):
        # Simplified EV: win_prob * reward - loss_prob * risk
        # For now, let's assume confidence maps to win_prob
        # And R:R is 1:2
        win_prob = confidence
        loss_prob = 1 - win_prob
        risk = 5
        reward = 10
        ev = (win_prob * reward) - (loss_prob * risk)
        return ev
