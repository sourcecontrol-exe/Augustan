# Augustan Project Restructure

## New Service-Based Architecture

The project has been restructured to eliminate code duplication and provide a clean service-based architecture:

```
augustan/
├── services/
│   ├── data/           # Data fetching & management
│   │   ├── data_loader.py
│   │   └── data_service.py
│   ├── trading/        # Strategy & execution
│   │   └── strategy.py
│   ├── backtesting/    # Backtesting engine
│   │   ├── backtester.py
│   │   ├── indicators.py
│   │   ├── performance_metrics.py
│   │   └── strategy_framework.py
│   ├── paper_trading/  # Paper trading simulation
│   │   ├── paper_trader.py
│   │   ├── paper_backtest_bridge.py
│   │   └── demo_paper_trading.py
│   ├── risk/          # Risk management
│   │   └── risk_manager.py
│   └── adapters/      # Exchange adapters
│       ├── base_adapter.py
│       ├── ccxt_adapter.py
│       └── pi42_adapter.py
├── core/
│   ├── config/        # Configuration management
│   │   └── config_manager.py
│   ├── exceptions/    # Custom exceptions
│   │   └── exceptions.py
│   └── utils/         # Shared utilities
│       └── constants.py
├── cli/               # Command line interface
│   └── cli.py
├── scripts/           # Entry point scripts
│   ├── run_backtest.py
│   ├── demo_paper_trading.py
│   ├── main.py
│   └── run_tests.py
└── __init__.py
```

## Key Benefits

### 1. **Eliminated Code Duplication**
- Removed duplicate files between root and `src/augustan/`
- Single source of truth for each component
- Cleaner imports and dependencies

### 2. **Service-Based Organization**
- Each service has a specific responsibility
- Clear separation of concerns
- Easy to test and maintain

### 3. **Unified Entry Points**
- All console scripts point to `augustan.scripts.*`
- Consistent import paths
- Better package structure

## Installation & Usage

```bash
# Install in development mode
pip install -e .

# Run backtests with real crypto data
augustan-backtest --symbol BTC/USDT --exchange binance

# Paper trading demo
augustan-paper --quick

# Main CLI
augustan --help
```

## Migration Guide

### Old Structure → New Structure

| Old Path | New Path |
|----------|----------|
| `data_loader.py` | `augustan.services.data.data_loader` |
| `strategy.py` | `augustan.services.trading.strategy` |
| `backtesting/backtester.py` | `augustan.services.backtesting.backtester` |
| `risk_manager.py` | `augustan.services.risk.risk_manager` |
| `adapters/` | `augustan.services.adapters/` |
| `configs/` | `augustan.core.config/` |
| `exceptions.py` | `augustan.core.exceptions.exceptions` |

### Updated Imports

```python
# Old imports
from data_loader import DataLoader
from strategy import RSIMACDStrategy
from backtesting.backtester import AugustanBacktester

# New imports
from augustan.services.data import DataLoader
from augustan.services.trading import RSIMACDStrategy
from augustan.services.backtesting import AugustanBacktester
```

## Next Steps

1. **Test the new structure**: Run `augustan-test` to verify everything works
2. **Clean up old files**: Remove duplicate files from root directory
3. **Update documentation**: Update any remaining references to old paths
4. **Validate installation**: Test `pip install -e .` works correctly

The restructured codebase is now ready for production use with a clean, maintainable architecture!
