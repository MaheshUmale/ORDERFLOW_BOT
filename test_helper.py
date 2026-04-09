from upstox_helper import UpstoxHelper
import pandas as pd

def test_helper():
    helper = UpstoxHelper()
    print("Testing get_instruments...")
    df = helper.get_instruments()
    if df is not None:
        print(f"Fetched {len(df)} instruments.")
        print("Columns:", df.columns.tolist())
    else:
        print("Failed to fetch instruments.")
        return

    print("\nTesting find_nearest_expiry for NIFTY...")
    expiry = helper.find_nearest_expiry('NIFTY')
    print(f"Nearest expiry: {expiry}")

    print("\nTesting get_option_chain for NIFTY...")
    chain = helper.get_option_chain('NIFTY', expiry)
    print(f"Found {len(chain)} options for {expiry}.")
    if not chain.empty:
        print("Example option labels:")
        for _, row in chain.head(3).iterrows():
            print(f"{row['name']} {row['expiry']} {row['strike']} {row['option_type']}")

if __name__ == "__main__":
    test_helper()
