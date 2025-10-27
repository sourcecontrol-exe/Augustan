"""
Refactored Strategy Engine - Uses factory/registry pattern for dynamic loading.

Benefits:
- Dynamic strategy loading from configuration
- No tight coupling to specific strategy classes
- Easy to add/remove strategies
- Plugin-based architecture
- Testable with dependency injection
"""
from typing import Dict, List, Optional, Any
from loguru import logger

from .base_strategy import BaseStrategy
from .strategy_factory import StrategyFactory, StrategyRegistry, StrategyConfig
from ..core.models import MarketData, TradingSignal, StrategyType


class StrategyEngineRefactored:
    """
    Refactored strategy engine using factory/registry pattern.
    
    Features:
    - Dynamic strategy loading from configuration
    - No hardcoded strategy instantiation
    - Easy to extend with custom strategies
    - Configuration-driven behavior
    """
    
    def __init__(
        self,
        strategy_configs: Optional[List[StrategyConfig]] = None,
        strategies: Optional[Dict[StrategyType, BaseStrategy]] = None
    ):
        """
        Initialize strategy engine.
        
        Args:
            strategy_configs: Optional list of strategy configurations
            strategies: Optional pre-created strategies (for testing)
        """
        if strategies is not None:
            # Use provided strategies
            self.strategies = strategies
            logger.info(f"StrategyEngine initialized with {len(strategies)} provided strategies")
        elif strategy_configs:
            # Create strategies from configs
            self.strategies = StrategyFactory.create_batch_from_configs(strategy_configs)
            logger.info(f"StrategyEngine initialized with {len(self.strategies)} strategies from config")
        else:
            # Use default strategies
            self.strategies = self._create_default_strategies()
            logger.info(f"StrategyEngine initialized with {len(self.strategies)} default strategies")
    
    def _create_default_strategies(self) -> Dict[StrategyType, BaseStrategy]:
        """Create default strategies."""
        from .rsi_strategy import RSIStrategy
        from .macd_strategy import MACDStrategy
        
        return {
            StrategyType.RSI: RSIStrategy(),
            StrategyType.MACD: MACDStrategy()
        }
    
    def add_strategy(self, strategy: BaseStrategy):
        """Add a strategy to the engine."""
        self.strategies[strategy.strategy_type] = strategy
        logger.info(f"Added strategy: {strategy.name}")
    
    def add_strategy_from_config(self, config: StrategyConfig):
        """Add a strategy from configuration."""
        strategy = StrategyFactory.create_from_config(config)
        if strategy:
            self.strategies[strategy.strategy_type] = strategy
    
    def remove_strategy(self, strategy_type: StrategyType):
        """Remove a strategy from the engine."""
        if strategy_type in self.strategies:
            del self.strategies[strategy_type]
            logger.info(f"Removed strategy: {strategy_type.value}")
    
    def reload_strategies(self, strategy_configs: List[StrategyConfig]):
        """Reload strategies from configuration."""
        new_strategies = StrategyFactory.create_batch_from_configs(strategy_configs)
        self.strategies.update(new_strategies)
        logger.info("Strategies reloaded")
    
    def run_single_strategy(
        self, 
        strategy_type: StrategyType, 
        market_data: List[MarketData]
    ) -> List[TradingSignal]:
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
    
    def run_all_strategies(
        self, 
        market_data: List[MarketData]
    ) -> Dict[StrategyType, List[TradingSignal]]:
        """Run all enabled strategies on market data."""
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
    
    def run_strategies_for_multiple_symbols(
        self,
        market_data_dict: Dict[str, List[MarketData]]
    ) -> Dict[str, Dict[StrategyType, List[TradingSignal]]]:
        """Run all strategies for multiple symbols."""
        all_symbol_signals = {}
        
        for symbol, market_data in market_data_dict.items():
            logger.info(f"Processing strategies for {symbol}")
            symbol_signals = self.run_all_strategies(market_data)
            all_symbol_signals[symbol] = symbol_signals
        
        logger.info(f"Completed strategy processing for {len(all_symbol_signals)} symbols")
        return all_symbol_signals
    
    def get_latest_signals(
        self,
        market_data_dict: Dict[str, List[MarketData]]
    ) -> Dict[str, List[TradingSignal]]:
        """Get the latest signals from all strategies."""
        all_signals = self.run_strategies_for_multiple_symbols(market_data_dict)
        
        latest_signals = {}
        for symbol, strategy_signals in all_signals.items():
            symbol_latest = []
            for strategy_type, signals in strategy_signals.items():
                if signals:
                    symbol_latest.extend(signals)
            
            if symbol_latest:
                latest_signals[symbol] = symbol_latest
        
        return latest_signals
    
    def get_strategy_names(self) -> List[str]:
        """Get list of available strategy names."""
        return [strategy.name for strategy in self.strategies.values()]
    
    def get_strategy_types(self) -> List[StrategyType]:
        """Get list of enabled strategy types."""
        return list(self.strategies.keys())
    
    def is_strategy_enabled(self, strategy_type: StrategyType) -> bool:
        """Check if a strategy is enabled."""
        return strategy_type in self.strategies
    
    @classmethod
    def from_config_dict(cls, config_dict: Dict[str, Any]) -> 'StrategyEngineRefactored':
        """
        Create strategy engine from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
                Example: {
                    "strategies": {
                        "rsi": {"enabled": True, "parameters": {"period": 14}},
                        "macd": {"enabled": True}
                    }
                }
        
        Returns:
            StrategyEngineRefactored instance
        """
        strategies_config = config_dict.get('strategies', {})
        strategies = StrategyFactory.create_from_config_dict(strategies_config)
        return cls(strategies=strategies)


# Backward compatibility
# Create default engine instance
_default_engine: Optional[StrategyEngineRefactored] = None


def get_default_engine() -> StrategyEngineRefactored:
    """Get or create default strategy engine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = StrategyEngineRefactored()
    return _default_engine


def set_default_engine(engine: StrategyEngineRefactored):
    """Set the default strategy engine."""
    global _default_engine
    _default_engine = engine

