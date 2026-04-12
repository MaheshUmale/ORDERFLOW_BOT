# Future Enhancements & Task List

This document outlines the roadmap for the Order Flow & RS Trading Terminal.

## Phase 1: Trade Management & EV Optimization (COMPLETED)
- [x] **Simulated Trade Manager**: Implement `trade_manager.py` to handle virtual entry/exit, TP/SL, and PnL tracking.
- [x] **Expected Value (EV) Module**: Calculate EV for signals based on historical win rates and average payouts.
- [x] **Confidence Scoring**: Assign weights to Order Flow signals based on imbalance clusters and delta magnitude.
- [x] **UI Trade Panel**: Add a dedicated UI section to monitor active trades and total session PnL. (Next step)

## Phase 2: Performance & Latency (IN PROGRESS)
- [/] **Lock Optimization**: Refactor `data_manager.py` to use `ReadWriteLock` or lock-free structures for high-frequency updates. (Basic optimization done)
- [/] **Pre-calculated Analytics**: Move more computation from the UI callback to the `DM TICK` processing stage. (Basic pre-calc done)
- [ ] **C++ Extensions**: Port `footprint_candle.py` aggregation logic to Cython or C++ for extreme performance.

## Phase 3: Advanced Strategies (NEXT)
- [ ] **Volume Profile (VPVR)**: Implement Volume Profile Visible Range on the Y-axis.
- [ ] **VWAP & Standard Deviation Bands**: Add VWAP as a core structural reference.
- [ ] **Multi-Timeframe Analysis**: Support 1m, 5m, and 15m views simultaneously.

## Phase 4: Live Order Execution
- [ ] **Upstox API Integration**: Connect the Trade Manager to the Upstox Order Management System (OMS).
- [ ] **Risk Guardrails**: Implement daily loss limits and maximum position size checks.
- [ ] **Automated Trailing Stop**: Logic to move SL to breakeven after a certain profit threshold.
