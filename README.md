# Order Flow & Relative Strength Trading Terminal

A high-performance real-time trading terminal built with Plotly Dash and Upstox API. It focuses on Order Flow (Footprint) analysis and Relative Strength strategies to identify high-probability trading opportunities.

## Key Features

- **Real-Time Order Flow**: Live Footprint charts with delta, absorption zones, aggression (imbalances), and exhaustion detection.
- **Relative Strength Strategy**: Detects structural divergence between the Spot Index and Option contracts.
- **Multi-Timeframe Support**: Toggle between 1m, 5m, and 15m views with optimized aggregation.
- **Automated Trade Manager**: Virtual trade execution with dynamic Trailing Stops and PnL tracking.
- **Expected Value (EV) Logic**: Signal prioritization based on statistical mathematical expectancy.
- **Institutional Indicators**: Built-in Anchored VWAP with SD bands and Volume Profile (VPVR).
- **Backtesting Framework**: Evaluate strategies on historical data before going live.
- **Risk Guardrails**: Automated daily loss limits and max concurrent trade controls.

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

## Backtesting

Run the historical simulation to evaluate strategy performance:
```bash
python3 backtest_engine.py
```

---
*Developed for professional traders seeking institutional-grade order flow insights.*
