# System Documentation

This document provides a detailed technical overview of the Order Flow & RS Trading Terminal.

## 1. Data Processing Pipeline

### 1.1 Live Tick Reception (`upstox_wss.py`)
- Connects to Upstox Market Data Feed (V3).
- Decodes Protobuf messages into structured dictionaries.
- Standardizes volume using `ltq` (Last Traded Quantity) as tick volume.
- Detects trade side (Buy/Sell) by comparing LTP against the Best Bid/Ask.

### 1.2 Aggregation & Synchronization (`data_manager.py`)
- Aggregates ticks into 1-minute `FootprintCandle` objects.
- Maintains a rolling window of the last 100 candles per instrument.
- Synchronizes Index Spot data with Option data for RS analysis.
- Handles thread-safe updates between the WSS thread and the Dash UI thread.

## 2. Analysis Engines

### 2.1 Order Flow Engine (`order_flow_engine.py`)
- **Diagonal Imbalances**: Compares Bid volume at price $P$ with Ask volume at price $P + TickSize$. A ratio $\ge 3.0$ indicates aggressive buying/selling.
- **Absorption Zones**: Identifies price levels where volume exceeds 40% of the total candle volume, suggesting a "wall".
- **Exhaustion**: Flags candles where volume at the high/low is $< 5\%$ of total volume, indicating a potential reversal.
- **Cumulative Delta**: Tracks the running sum of (Buy Volume - Sell Volume) to gauge overall market bias.

### 2.2 Relative Strength Strategy (`strategy_logic.py`)
- **Swing Detection**: Identifies local highs and lows using a configurable window.
- **Divergence Logic**: Specifically looks for scenarios where the Spot Index breaches a prior swing low, but the Option contract maintains its low, indicating underlying strength in premiums.

### 2.3 Pivot Points (`pivot_algorithm.py`)
- Implements `AutoTrendSupportResistance` to track dynamic SR levels.
- Levels are "tested" when price returns to them and "broken" after a sustained breach.

## 3. UI and Visualization (`app.py`)
- Uses `Plotly Dash` for the dashboard.
- Main chart combines Candlesticks, Support/Resistance lines, and Order Flow annotations.
- Subplot displays Cumulative Delta.
- Real-time statistics panel provides system health and data latency metrics.

## 4. Performance Considerations
- Multi-threaded architecture separates data reception from UI rendering.
- UI updates are throttled via `dcc.Interval`.
- Chart annotations are limited to the most recent candles to maintain high FPS and low JSON payload size.
