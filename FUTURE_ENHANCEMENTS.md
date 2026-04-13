# Future Enhancements & Task List

This document outlines the roadmap for the Order Flow & RS Trading Terminal.

## Phase 1: Trade Management & EV Optimization (COMPLETED)
- [x] **Simulated Trade Manager**: Implement `trade_manager.py` to handle virtual entry/exit, TP/SL, and PnL tracking.
- [x] **Expected Value (EV) Module**: Calculate EV for signals based on historical win rates and average payouts.
- [x] **Confidence Scoring**: Assign weights to Order Flow signals based on imbalance clusters and delta magnitude.
- [x] **UI Trade Panel**: Add a dedicated UI section to monitor active trades and total session PnL.

## Phase 2: Performance & Latency (IN PROGRESS)
- [x] **Lock Optimization**: Refactor `data_manager.py` to use `RLock` for safe multi-threaded updates.
- [x] **Pre-calculated Analytics**: Analysis is now computed on candle completion in `data_manager.py`.
- [ ] **High-Performance Aggregation**: Optimize `footprint_candle.py` with NumPy or specialized structures.

## Phase 3: Advanced Strategies (COMPLETED)
- [x] **Volume Profile (VPVR)**: Implemented price-level volume distribution on the main chart.
- [x] **VWAP & Standard Deviation Bands**: Integrated anchored VWAP with volatility bands.
- [ ] **Multi-Timeframe Analysis**: Support 1m, 5m, and 15m views simultaneously.

## Phase 4: Live Order Execution (NEXT)
- [x] **Automated Trailing Stop**: Implemented dynamic SL adjustment in `TradeManager`.
- [ ] **Upstox API Integration**: Connect the Trade Manager to the Upstox Order Management System (OMS).
- [ ] **Risk Guardrails**: Implement daily loss limits and maximum position size checks.
- [ ] **Backtest Engine**: (EXTRA) Added a historical simulation engine for strategy validation.
