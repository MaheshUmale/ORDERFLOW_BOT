# Order Flow & Relative Strength Trading Terminal

A high-performance real-time trading terminal built with Plotly Dash and Upstox API. It focuses on Order Flow (Footprint) analysis and Relative Strength strategies to identify high-probability trading opportunities.

## Key Features

- **Real-Time Order Flow**: Live Footprint charts with delta, absorption zones, aggression (imbalances), and exhaustion detection.
- **Relative Strength Strategy**: Detects structural divergence between the Spot Index (NIFTY/BANKNIFTY) and Option contracts.
- **Multi-Tab Support**: Browser-based terminal allows independent instrument tracking across multiple tabs.
- **Automatic Trend Levels**: Integrated Support and Resistance levels based on real-time price action.
- **Upstox V3 Integration**: Robust WebSocket implementation for low-latency market data.

## Architecture Overview

- **Frontend**: Dash & Plotly for interactive, real-time charting.
- **Data Engine**: `data_manager.py` handles multi-instrument data aggregation, synchronization, and historical bootstrapping.
- **Analysis Engine**: `order_flow_engine.py` processes per-candle footprint data for micro-structure signals.
- **Strategy Engine**: `strategy_logic.py` implements the RS divergence logic.
- **Live Feed**: `upstox_wss.py` manages the WebSocket connection and Protobuf decoding.

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your Upstox credentials.
3. **Run Terminal**:
   ```bash
   python3 app.py
   ```

## Signal Indicators

- **OF BUY/SELL**: Order Flow signals based on diagonal imbalances and delta.
- **RS BUY**: Relative Strength bullish divergence signals (Index makes a lower low while Option holds).
- **Absorption**: Highlights price levels with high volume concentration.
- **Exhaustion**: Detects fading momentum at candle extremes.

---
*Developed for professional traders seeking institutional-grade order flow insights.*
