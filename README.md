# Order Flow & Relative Strength Trading Terminal

A real-time trading terminal built with Plotly Dash and Upstox API for Order Flow (Footprint) analysis and Relative Strength strategies.

## Key Features

- **Real-Time Order Flow**: Live Footprint charts with delta, absorption zones, aggression (imbalances), and exhaustion detection.
- **Relative Strength Strategy**: Detects structural divergence between the Spot Index (NIFTY/BANKNIFTY) and Option contracts.
- **Multi-Tab Support**: Open multiple instruments in different browser tabs independently.
- **Automatic Trend Levels**: Real-time Support and Resistance levels based on pivot algorithms.
- **Live Upstox Integration**: Uses Upstox V3 WebSocket for live market data and V2 Historical API for bootstrapping.

## Architecture

- **`app.py`**: Dash UI and real-time charting logic.
- **`data_manager.py`**: Orchestrates live data aggregation, historical bootstrapping, and multi-instrument state.
- **`upstox_wss.py`**: Robust WebSocket client (V3) with Protobuf decoding and automatic subscriptions.
- **`order_flow_engine.py`**: Core logic for analyzing footprint candles (imbalances, walls, exhaustion).
- **`strategy_logic.py`**: Implementation of the Relative Strength divergence strategy.
- **`upstox_helper.py`**: API utilities for instrument discovery, option chains, and historical data.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure `.env` with your Upstox credentials (see `.env.example`).
3. Start the terminal:
   ```bash
   python3 app.py
   ```

## Logs & Observability

The terminal logs real-time data flow to the console:
- `WSS TICK`: Raw tick received from Upstox WebSocket.
- `DM TICK`: Tick processed and aggregated into a candle by the Data Manager.

## Dashboard Usage

- **Base Index**: Choose between NIFTY and BANKNIFTY.
- **Option Instrument**: Search and select specific option contracts.
- **Terminal Mode**: Switch between 'Order Flow' and 'Rel. Strength' views.
- **Connect & Start**: Initialize the live feed for the selected instrument.

---
*Inspired by NinjaTrader 8 Order Flow Bot.*
