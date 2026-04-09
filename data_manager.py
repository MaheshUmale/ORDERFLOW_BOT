import pandas as pd

class DataManager:
    def __init__(self):
        self.market_data = pd.DataFrame()
        self.simulator_running = False

    def start_simulator(self):
        if not self.simulator_running:
            self.simulator_running = True
            print("Simulator started.")
        else:
            print("Simulator is already running.")

    def get_market_data(self):
        if self.simulator_running:
            # Logic for retrieving market data; this is a placeholder for the actual logic
            self.market_data = pd.DataFrame({
                'price': [100, 101, 102],
                'volume': [10, 15, 12]
            })
            return self.market_data
        else:
            print("Simulator is not running, cannot get market data.")
            return None

    def stop_simulator(self):
        if self.simulator_running:
            self.simulator_running = False
            print("Simulator stopped.")
        else:
            print("Simulator is not running.")

    def reset_data(self):
        self.market_data = pd.DataFrame()
        print("Data has been reset.")
        self.stop_simulator()