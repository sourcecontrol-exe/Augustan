# Augustan Bot - Project To-Do List (Phase 2)

This document outlines the prioritized tasks to transition the Augustan bot from a feature-complete state to a fully operational, automated trading system.

## Milestone 1: The Strategy Gauntlet (Finding the Champion)
🎯 **Goal**: To rigorously test and compare multiple trading strategies using the backtesting engine to find a statistically profitable "champion" strategy to deploy.

### [ ] Task 1.1: Develop at Least Two New Strategies
- **File**: Create new files in `services/trading/strategies/` (suggested new folder)
- **Details**: Your current `strategy.py` is a great template. Create at least two more distinct strategies (e.g., a Trend-Following strategy using Donchian Channels, a Mean-Reversion strategy using Bollinger Bands) that inherit from your base Strategy class.
- **Outcome**: A library of different strategies to test and compare.

### [ ] Task 1.2: Implement Strategy Comparison in run_backtest.py
- **File**: `scripts/run_backtest.py`
- **Details**: Modify the script to import and run backtests for all your new strategies in a loop. The script should save the final performance report for each strategy to a results directory, allowing you to directly compare metrics like Sharpe Ratio, Profit Factor, and Max Drawdown.
- **Outcome**: A repeatable, automated process to find your "champion" strategy.

### [ ] Task 1.3: Run Parameter Optimization on the Champion Strategy
- **File**: `scripts/run_backtest.py`
- **Details**: Once a champion strategy is identified, use your backtester's optimize() method to find the best possible parameters for it.
- **Outcome**: A single, fine-tuned strategy that is ready for live simulation.

## Milestone 2: The Proving Ground (End-to-End Simulation)
🎯 **Goal**: To integrate the self-hosted paper trading engine into the main application loop and validate the champion strategy in a live market.

### [ ] Task 2.1: Create the PortfolioManager
- **File**: Create a new file `services/trading/portfolio_manager.py`
- **Details**: Build the PortfolioManager class. It must track account balance, margin, and a dictionary of all open positions. This will be the state manager for both paper and live trading.
- **Outcome**: A central "brain" that knows what the bot owns at all times.

### [ ] Task 2.2: Integrate Paper Trading into main.py
- **File**: `scripts/main.py`
- **Details**: Refactor the main application loop.
  - When in "paper" mode, initialize the PortfolioManager.
  - On each candle, the loop must first call the PortfolioManager to check if any simulated trades should be closed based on the new price data.
  - When a new signal is generated, it should call the PortfolioManager to open a new simulated position.
- **Outcome**: A main.py script that can run a complete, end-to-end paper trading session.

## Milestone 3: Go-Live & Automation
🎯 **Goal**: To activate live trading and create a master script that automates the entire process from strategy selection to deployment.

### [ ] Task 3.1: Implement Live Order Execution & Position Syncing
- **File**: `scripts/main.py`
- **Details**: In the main loop, when in "live" mode, implement the logic to call the exchange adapter's create_order method. Crucially, after placing an order, the result must be recorded in the PortfolioManager. Add a periodic task to sync the PortfolioManager's state with the real open positions from the exchange.
- **Outcome**: The bot can place and manage real trades.

### [ ] Task 3.2: Create the Master Automation Script
- **File**: Create a new file `run_augustan.py`
- **Details**: This script will be the final entry point for the entire system. It should perform the following steps:
  - (Optional) Run a quick comparison backtest to confirm the champion strategy is still the best for recent market conditions.
  - Load the champion strategy and its optimal parameters.
  - Launch the main bot loop (main.py) in either "paper" or "live" mode based on a command-line argument.
- **Outcome**: A single command to launch your fully automated trading operation.

### [ ] Task 3.3: Enhance the CLI for Live Monitoring
- **File**: `cli/cli.py`
- **Details**: Build out the CLI to be a powerful monitoring tool. Add commands to query the PortfolioManager (which will require some form of inter-process communication or reading from a shared state file) to show current PnL, open positions, and account balance in real-time.
- **Outcome**: The ability to safely monitor and manage your live bot without stopping it.

---

## Project Status
- ✅ **Phase 1 Complete**: Service-based architecture restructure with real crypto data integration
- 🔄 **Phase 2 Current**: Strategy development and portfolio management
- ⏳ **Phase 3 Pending**: Live trading automation and monitoring
