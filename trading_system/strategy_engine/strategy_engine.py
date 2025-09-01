"""
Strategy Engine - Runs multiple trading strategies and generates signals.
"""
from typing import List, Dict, Optional
from loguru import logger

from .base_strategy import BaseStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from ..core.models import MarketData, TradingSignal, StrategyType


class StrategyEngine:
    """Engine that runs multiple trading strategies."""
    
    def __init__(self):
        """Initialize strategy engine with default strategies."""
        self.strategies: Dict[StrategyType, BaseStrategy] = {
            StrategyType.RSI: RSIStrategy(),
            StrategyType.MACD: MACDStrategy()
        }
        
        logger.info(f"StrategyEngine initialized with {len(self.strategies)} strategies")
    
    def add_strategy(self, strategy: BaseStrategy):
        """Add a new strategy to the engine."""
        self.strategies[strategy.strategy_type] = strategy
        logger.info(f"Added strategy: {strategy.name}")
    
    def remove_strategy(self, strategy_type: StrategyType):
        """Remove a strategy from the engine."""
        if strategy_type in self.strategies:
            del self.strategies[strategy_type]
            logger.info(f"Removed strategy: {strategy_type.value}")
    
    def run_single_strategy(self, strategy_type: StrategyType, 
                          market_data: List[MarketData]) -> List[TradingSignal]:
        """Run a single strategy on market data."""
        if strategy_type not in self.strategies:
            logger.warning(f"Strategy {strategy_type.value} not found")
            return []
        
        try:
            signals = self.strategies[strategy_type].generate_signals(market_data)
            logger.info(f"{strategy_type.value} generated {len(signals)} signals")
            return signals
        except Exception as e:
            logger.error(f"Error running {strategy_type.value}: {e}")
            return []
    
    def run_all_strategies(self, market_data: List[MarketData]) -> Dict[StrategyType, List[TradingSignal]]:
        """Run all strategies on market data."""
        if not market_data:
            logger.warning("No market data provided")
            return {}
        
        all_signals = {}
        symbol = market_data[0].symbol
        
        logger.info(f"Running all strategies for {symbol}")
        
        for strategy_type, strategy in self.strategies.items():
            signals = self.run_single_strategy(strategy_type, market_data)
            all_signals[strategy_type] = signals
        
        total_signals = sum(len(signals) for signals in all_signals.values())
        logger.info(f"Generated {total_signals} total signals for {symbol}")
        
        return all_signals
    
    def run_strategies_for_multiple_symbols(self, 
                                          market_data_dict: Dict[str, List[MarketData]]) -> Dict[str, Dict[StrategyType, List[TradingSignal]]]:
        """Run all strategies for multiple symbols."""
        all_symbol_signals = {}
        
        for symbol, market_data in market_data_dict.items():
            logger.info(f"Processing strategies for {symbol}")
            symbol_signals = self.run_all_strategies(market_data)
            all_symbol_signals[symbol] = symbol_signals
        
        logger.info(f"Completed strategy processing for {len(all_symbol_signals)} symbols")
        return all_symbol_signals
    
    def get_latest_signals(self, 
                          market_data_dict: Dict[str, List[MarketData]]) -> Dict[str, List[TradingSignal]]:
        """Get the latest signals from all strategies for all symbols."""
        all_signals = self.run_strategies_for_multiple_symbols(market_data_dict)
        
        latest_signals = {}
        for symbol, strategy_signals in all_signals.items():
            symbol_latest = []
            for strategy_type, signals in strategy_signals.items():
                if signals:
                    # Get the most recent signal from each strategy
                    symbol_latest.extend(signals)
            
            if symbol_latest:
                latest_signals[symbol] = symbol_latest
        
        return latest_signals
    
    def get_strategy_names(self) -> List[str]:
        """Get list of available strategy names."""
        return [strategy.name for strategy in self.strategies.values()]
