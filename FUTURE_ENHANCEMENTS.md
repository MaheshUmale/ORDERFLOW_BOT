# Future Enhancements & Task List

This document outlines the roadmap for the Order Flow & RS Trading Terminal.

## Phase 1: Trade Management & EV Optimization (COMPLETED)
- [x] **Simulated Trade Manager**: Implement `trade_manager.py` to handle virtual entry/exit, TP/SL, and PnL tracking.
- [x] **Expected Value (EV) Module**: Calculate EV for signals based on historical win rates and average payouts.
- [x] **Confidence Scoring**: Assign weights to Order Flow signals based on imbalance clusters and delta magnitude.
- [x] **UI Trade Panel**: Add a dedicated UI section to monitor active trades and total session PnL.

## Phase 2: Performance & Latency (COMPLETED)
- [x] **Lock Optimization**: Refactor `data_manager.py` to use `RLock` for safe multi-threaded updates.
- [x] **Pre-calculated Analytics**: Analysis is now computed on candle completion in `data_manager.py`.
- [x] **High-Performance Aggregation**: Optimized `footprint_candle.py` with `__slots__` and efficient dict lookups.

## Phase 3: Advanced Strategies (COMPLETED)
- [x] **Volume Profile (VPVR)**: Implemented price-level volume distribution on the main chart.
- [x] **VWAP & Standard Deviation Bands**: Integrated anchored VWAP with volatility bands.
- [x] **Multi-Timeframe Analysis**: Support 1m, 5m, and 15m views simultaneously.

## Phase 4: Live Order Execution (COMPLETED)
- [x] **Automated Trailing Stop**: Implemented dynamic SL adjustment in `TradeManager`.
- [x] **Upstox API Integration**: Implemented `place_order` in `UpstoxHelper` and linked to `TradeManager`.
- [x] **Risk Guardrails**: Implemented daily loss limits and maximum position size checks.
- [x] **Backtest Engine**: Added a historical simulation engine for strategy validation.
